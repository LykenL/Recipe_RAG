from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
import json
import pickle
import re

import numpy as np


def _restore_abbrev(text: str) -> str:
    text = re.sub(r"\btsp\b(?!\.)", "tsp.", text)
    text = re.sub(r"\btbsp\b(?!\.)", "tbsp.", text)
    return text


def load_recipes_json(path: str | Path, *, restore_abbrev: bool = True) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not restore_abbrev:
        return data
    for recipe in data:
        for field in ("ingredients", "instructions", "notes"):
            val = recipe.get(field)
            if isinstance(val, str) and val:
                recipe[field] = _restore_abbrev(val)
    return data


def recipe_to_text(recipe: dict[str, Any]) -> str:
    parts: list[str] = []
    title = recipe.get("title")
    if isinstance(title, str) and title.strip():
        parts.append(title.strip())
    for field in ("ingredients", "instructions", "notes"):
        val = recipe.get(field)
        if isinstance(val, str) and val.strip():
            parts.append(val.strip())
    return "\n".join(parts).strip()


@dataclass
class VectorStoreEntry:
    text: str
    embedding: np.ndarray
    metadata: dict[str, Any]


def build_vector_store(embedder: Any, recipes: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    store: list[dict[str, Any]] = []
    for recipe in recipes:
        text = recipe_to_text(recipe)
        if not text:
            continue
        embedding = embedder.encode(text)
        store.append({"text": text, "embedding": embedding, "metadata": recipe})
    return store


def save_vector_store(path: str | Path, vector_store: list[dict[str, Any]]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(vector_store, f)


def load_vector_store(path: str | Path) -> list[dict[str, Any]]:
    with open(path, "rb") as f:
        return pickle.load(f)

