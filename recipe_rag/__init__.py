# -*- coding: utf-8 -*-
"""Top-level package for the Recipe RAG demo.

Imports here are **lazy** (PEP 562) on purpose.

`recipe_rag.app` pulls in an embedding backend. The deployment image ships only
ONNX Runtime (`fastembed`) and deliberately does *not* install PyTorch, so an
eager ``from .app import RecipeRAGAssistant`` would make even
``import recipe_rag.vector_store`` explode with ModuleNotFoundError.
"""

from typing import Any

__all__ = [
    "RecipeRAGAssistant",
    "Hit",
    "search",
    "LLMClient",
    "get_embedder",
]

_LAZY = {
    "RecipeRAGAssistant": (".app", "RecipeRAGAssistant"),
    "Hit": (".app", "Hit"),
    "search": (".retrieval", "search"),
    "LLMClient": (".llm", "LLMClient"),
    "get_embedder": (".embedding", "get_embedder"),
}


def __getattr__(name: str) -> Any:
    try:
        module_name, attr = _LAZY[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    import importlib

    return getattr(importlib.import_module(module_name, __name__), attr)


def __dir__() -> list[str]:
    return sorted(__all__)
