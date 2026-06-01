from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import re

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _coerce_embedding(arr: Any) -> np.ndarray:
    emb = np.asarray(arr)
    if emb.ndim == 2 and emb.shape[0] == 1:
        emb = emb[0]
    return emb


def _entry_title(entry: dict[str, Any]) -> str:
    meta = entry.get("metadata") or {}
    title = (meta.get("title") or "").strip()
    if title:
        return title
    first_line = (entry.get("text") or "").split("\n", 1)[0].strip()
    return first_line or "Unknown dish"


def format_entry_for_prompt(entry: dict[str, Any], *, max_chars: int = 520) -> str:
    """Format one hit for the LLM using the real dish name (never 'Recipe 1')."""
    title = _entry_title(entry)
    body = (entry.get("text") or "").strip()
    if body.startswith(title):
        body = body[len(title) :].lstrip("\n")
    if len(body) > max_chars:
        body = body[:max_chars].rstrip() + "…"
    return f"【{title}】\n{body}" if body else f"【{title}】"


def _rank_entries(
    embedder: Any,
    vector_store: list[dict[str, Any]],
    query: str,
    *,
    k: int = 3,
    min_similarity: float = 0.2,
) -> tuple[str | None, list[tuple[float, dict[str, Any]]]]:
    query = (query or "").strip()
    if not query:
        return None, []

    original_query = query
    attribute = None
    attribute_keywords = ["serving size", "ingredients", "instructions", "notes"]
    clean_query = original_query.lower()
    for attr in attribute_keywords:
        if attr in clean_query:
            attribute = attr
            clean_query = clean_query.replace(attr, "").strip()
            break

    query_embedding = _coerce_embedding(embedder.encode(clean_query))
    scored_results: list[tuple[float, dict[str, Any]]] = []
    for entry in vector_store:
        similarity = cosine_similarity(
            [query_embedding],
            [_coerce_embedding(entry["embedding"])],
        )[0][0]
        scored_results.append((float(similarity), entry))

    scored_results.sort(key=lambda x: x[0], reverse=True)
    top_results = scored_results[: max(0, int(k))]
    if not top_results or top_results[0][0] < float(min_similarity):
        return attribute, []

    filtered = [(score, entry) for score, entry in top_results if score >= float(min_similarity)]
    return attribute, filtered


@dataclass
class RetrievalResult:
    blocks: list[str]
    hits: list[tuple[float, dict[str, Any]]]


def search_for_prompt(
    embedder: Any,
    vector_store: list[dict[str, Any]],
    query: str,
    *,
    k: int = 3,
    min_similarity: float = 0.2,
    max_chars_per_entry: int = 520,
    verbose: bool = False,
) -> RetrievalResult:
    attribute, filtered = _rank_entries(
        embedder, vector_store, query, k=k, min_similarity=min_similarity
    )
    if not filtered:
        return RetrievalResult(blocks=["No matching documents!"], hits=[])

    blocks: list[str] = []
    for score, entry in filtered:
        if attribute:
            attribute_key_map = {
                "serving size": "serving_size",
                "ingredients": "ingredients",
                "instructions": "instructions",
                "notes": "notes",
            }
            metadata_key = attribute_key_map.get(attribute, attribute)
            val = entry.get("metadata", {}).get(metadata_key, "Attribute not found")
            blocks.append(f"【{_entry_title(entry)}】\n{val}")
        else:
            blocks.append(format_entry_for_prompt(entry, max_chars=max_chars_per_entry))
        if verbose:
            print(f"similarity={score:.3f} | {_entry_title(entry)}")
    return RetrievalResult(blocks=blocks, hits=filtered)


def search(
    embedder: Any,
    vector_store: list[dict[str, Any]],
    query: str,
    *,
    k: int = 3,
    min_similarity: float = 0.2,
    verbose: bool = False,
) -> list[Any]:
    attribute, filtered = _rank_entries(
        embedder, vector_store, query, k=k, min_similarity=min_similarity
    )
    if not filtered:
        return ["No matching documents!"]

    attribute_key_map = {
        "serving size": "serving_size",
        "ingredients": "ingredients",
        "instructions": "instructions",
        "notes": "notes",
    }
    results: list[Any] = []
    for score, entry in filtered:
        if attribute:
            metadata_key = attribute_key_map.get(attribute, attribute)
            results.append(entry.get("metadata", {}).get(metadata_key, "Attribute not found"))
        else:
            results.append(entry["text"])
        if verbose:
            print(f"similarity={score:.3f} | {_entry_title(entry)}")
    return results if results else ["No matching documents!"]

