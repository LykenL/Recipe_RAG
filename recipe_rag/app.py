from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sentence_transformers import SentenceTransformer

from .config import load_env, load_llm_config
from .formatting import normalize_answer_lines
from .llm import LLMClient
from .prompting import OFF_TOPIC_REFUSAL, PromptMode, construct_prompt
from .relevance import is_cookbook_relevant
from .retrieval import search_for_prompt
from .router import classify_intent, is_cooking_related
from .vector_store import load_vector_store


@dataclass
class RecipeRAGAssistant:
    embedder: Any
    vector_store: list[dict[str, Any]]
    llm: LLMClient

    @classmethod
    def from_files(
        cls,
        *,
        vector_store_path: str | Path,
        dotenv_path: str | Path | None = None,
        embedding_model: str = "all-MiniLM-L6-v2",
    ) -> "RecipeRAGAssistant":
        load_env(dotenv_path)
        llm = LLMClient.from_config(load_llm_config())
        embedder = SentenceTransformer(embedding_model)
        vector_store = load_vector_store(vector_store_path)
        return cls(embedder=embedder, vector_store=vector_store, llm=llm)

    def answer(
        self,
        query: str,
        *,
        search_query: str | None = None,
        mode: PromptMode = "recipe",
        recipe_name: str | None = None,
        require_cookbook_match: bool = False,
    ) -> str:
        retrieval_query = (search_query or query).strip()
        k = 2 if mode == "cooking" else 3
        result = search_for_prompt(
            self.embedder,
            self.vector_store,
            retrieval_query,
            k=k,
            min_similarity=0.15,
            max_chars_per_entry=400 if mode == "cooking" else 520,
        )

        relevant = is_cookbook_relevant(
            query,
            result.hits,
            recipe_name=recipe_name or search_query,
        )
        if require_cookbook_match and not relevant:
            mode = "no_cookbook_match"
            blocks: list[str] = []
        elif mode == "cooking" and not relevant:
            # Weak vector hits do more harm than good for general cooking Qs.
            blocks = []
        else:
            blocks = result.blocks

        prompt = construct_prompt(query, blocks, mode=mode)
        max_tokens = 220 if mode in ("cooking", "no_cookbook_match") else 280
        return normalize_answer_lines(self.llm.chat(prompt, max_tokens=max_tokens))

    def route(self, query: str) -> str:
        intent = classify_intent(self.llm, query)
        name = intent.get("intent")

        if name == "ScaleRecipeIntent":
            recipe_name = (intent.get("recipe_name") or "").strip()
            if not recipe_name or recipe_name.lower() in ("recipe", "a recipe", "the recipe", "this recipe"):
                return self.answer(query, mode="cooking")
            return self.answer(
                query,
                search_query=recipe_name,
                mode="recipe",
                recipe_name=recipe_name,
                require_cookbook_match=False,
            )
        if name == "OtherIntent":
            if is_cooking_related(query):
                return self.answer(query, mode="cooking")
            return OFF_TOPIC_REFUSAL

        if name == "CookingQuestionIntent":
            return self.answer(query, mode="cooking")

        recipe_name = (intent.get("recipe_name") or "").strip()
        search_query = recipe_name if recipe_name else query
        return self.answer(
            query,
            search_query=search_query,
            mode="recipe",
            recipe_name=recipe_name or None,
            require_cookbook_match=True,
        )
