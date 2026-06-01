# -*- coding: utf-8 -*-
"""Top‑level package for the RAG demo.
Provides convenient shortcuts for interactive use.
"""

from .app import RecipeRAGAssistant  # noqa: F401
from .retrieval import search  # noqa: F401
from .llm import LLMClient  # noqa: F401

__all__ = [
    "RecipeRAGAssistant",
    "search",
    "LLMClient",
]
