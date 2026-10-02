# recipe_rag/app.py
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Sequence
import warnings

import numpy as np

from .config import load_env, load_llm_config
from .embedding import get_embedder
from .llm import LLMClient
from .prompting import get_system_prompt
from .retrieval import _entry_title, embedding_matrix, search_for_prompt
from .vector_store import load_index

# Measured similarity on the 829-recipe corpus sits in the 0.39–0.64 band for
# real matches. The old 0.15 threshold never rejected anything.
DEFAULT_K = 4
DEFAULT_MIN_SIMILARITY = 0.35
#: Each extra round is another model call, which dominates latency. Two or three
#: is enough for "search, maybe rephrase, then answer"; five was the old default
#: and produced four searches for a single simple question.
DEFAULT_MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "4"))

# Used only when an index predates model metadata (legacy .emb pickle).
_LEGACY_MODEL = "all-MiniLM-L6-v2"


@dataclass
class Hit:
    """One retrieved recipe, with the score the UI needs to display."""

    title: str
    text: str
    score: float
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def snippet(self) -> str:
        body = (self.text or "").strip()
        if body.startswith(self.title):
            body = body[len(self.title) :].lstrip("\n")
        body = " ".join(body.split())
        return (body[:220] + "…") if len(body) > 220 else body


@dataclass
class RecipeRAGAssistant:
    embedder: Any
    vector_store: list[dict[str, Any]]
    llm: LLMClient
    index_meta: dict[str, Any] = field(default_factory=dict)
    k: int = DEFAULT_K
    min_similarity: float = DEFAULT_MIN_SIMILARITY
    #: "grounded" (answers only from retrieved recipes) or "creative" (may improvise)
    answer_mode: str | None = None
    #: how many tool-calling rounds the agent may take; each one costs a round trip
    max_iterations: int = DEFAULT_MAX_ITERATIONS
    #: hits from the most recent tool call — the UI reads this, the LLM never sees it
    last_hits: list[Hit] = field(default_factory=list, repr=False)
    _matrix: np.ndarray | None = field(default=None, repr=False)

    # ── construction ─────────────────────────────────────────────────────────
    @classmethod
    def from_files(
        cls,
        *,
        vector_store_path: str | Path,
        dotenv_path: str | Path | None = None,
        embedding_model: str | None = None,
        backend: str | None = None,
        k: int = DEFAULT_K,
        min_similarity: float = DEFAULT_MIN_SIMILARITY,
    ) -> "RecipeRAGAssistant":
        load_env(dotenv_path)
        llm = LLMClient.from_config(load_llm_config())
        vector_store, meta = load_index(vector_store_path)

        index_model = meta.get("model")
        if index_model:
            if embedding_model and embedding_model != index_model:
                warnings.warn(
                    f"embedding_model={embedding_model!r} ignored: the index was built with "
                    f"{index_model!r}. Embeddings are only comparable within one model — "
                    "rebuild the index to change it.",
                    stacklevel=2,
                )
            model = index_model
            backend = meta.get("backend") or backend
        elif embedding_model:
            model = embedding_model
        else:
            model = _LEGACY_MODEL
            backend = backend or "st"
            warnings.warn(
                "This index has no recorded embedding model (legacy pickle). Assuming "
                f"{model!r} — rebuild with scripts/build_index.py to make this explicit.",
                stacklevel=2,
            )

        embedder = get_embedder(backend, model)

        expected_dim = meta.get("dim")
        if expected_dim and embedder.dimension != expected_dim:
            raise ValueError(
                f"Embedding dimension mismatch: index has {expected_dim}, "
                f"{getattr(embedder, 'model_name', model)!r} produces {embedder.dimension}. "
                "Rebuild the index with scripts/build_index.py."
            )

        return cls(
            embedder=embedder,
            vector_store=vector_store,
            llm=llm,
            index_meta=meta,
            k=k,
            min_similarity=min_similarity,
        )

    # ── retrieval ────────────────────────────────────────────────────────────
    @property
    def matrix(self) -> np.ndarray:
        if self._matrix is None:
            self._matrix = embedding_matrix(self.vector_store)
        return self._matrix

    def search_cookbook(self, query: str) -> str:
        """Tool handler. Returns text for the LLM and records hits for the UI."""
        result = search_for_prompt(
            self.embedder,
            self.vector_store,
            query,
            k=self.k,
            min_similarity=self.min_similarity,
            max_chars_per_entry=400,
            matrix=self.matrix,
        )
        self.last_hits = [
            Hit(
                title=_entry_title(entry),
                text=entry.get("text", ""),
                score=float(score),
                source=(entry.get("metadata") or {}).get("notes", ""),
                metadata=entry.get("metadata") or {},
            )
            for score, entry in result.hits
        ]
        if not result.blocks:
            return "No matching recipes found."
        return "\n\n---\n\n".join(result.blocks)

    # ── agent ────────────────────────────────────────────────────────────────
    def run(self, query: str, history: Sequence[dict[str, Any]] | None = None) -> Iterator[str]:
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_cookbook",
                    "description": (
                        "Searches the cookbook database for recipes, ingredients, and cooking "
                        "instructions. Use this to find specific recipes or culinary information."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": (
                                    "The search query (e.g., 'strawberry pie', 'chicken', "
                                    "'sugar substitute')"
                                ),
                            }
                        },
                        "required": ["query"],
                        "additionalProperties": False,
                    },
                },
            }
        ]

        tool_handlers = {"search_cookbook": self.search_cookbook}

        yield from self.llm.agent_loop(
            system_prompt=get_system_prompt(self.answer_mode),
            user_query=query,
            tools=tools,
            tool_handlers=tool_handlers,
            history=history,
            max_iterations=self.max_iterations,
            max_tokens=2048,
        )

    # Provide a route alias to avoid immediately breaking UI/evaluators that still call .route()
    def route(self, query: str, history: Sequence[dict[str, Any]] | None = None):
        yield from self.run(query, history)
