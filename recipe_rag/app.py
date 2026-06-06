# recipe_rag/app.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sentence_transformers import SentenceTransformer

from .config import load_env, load_llm_config
from .formatting import normalize_answer_lines
from .llm import LLMClient
from .prompting import AGENT_SYSTEM_PROMPT
from .retrieval import search_for_prompt
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

    def search_cookbook(self, query: str) -> str:
        """Tool handler for searching the cookbook vector database."""
        result = search_for_prompt(
            self.embedder,
            self.vector_store,
            query,
            k=3,
            min_similarity=0.15,
            max_chars_per_entry=400,
        )
        if not result.blocks:
            return "No matching recipes found."
        return "\n\n---\n\n".join(result.blocks)

    def run(self, query: str) -> str:
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_cookbook",
                    "description": "Searches the cookbook database for recipes, ingredients, and cooking instructions. Use this to find specific recipes or culinary information.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query (e.g., 'strawberry pie', 'chicken', 'sugar substitute')"
                            }
                        },
                        "required": ["query"],
                        "additionalProperties": False
                    }
                }
            }
        ]
        
        tool_handlers = {
            "search_cookbook": self.search_cookbook
        }

        # Run the autonomous execution loop
        raw_answer = self.llm.agent_loop(
            system_prompt=AGENT_SYSTEM_PROMPT,
            user_query=query,
            tools=tools,
            tool_handlers=tool_handlers,
            max_iterations=5,
            max_tokens=400
        )
        
        return normalize_answer_lines(raw_answer)

    # Provide a route alias to avoid immediately breaking UI/evaluators that still call .route()
    def route(self, query: str) -> str:
        return self.run(query)
