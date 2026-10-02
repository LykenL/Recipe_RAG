from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence
import json
import pickle
import re

import numpy as np

# Bumped when the on-disk layout changes.
INDEX_FORMAT_VERSION = 1


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


# ── build ────────────────────────────────────────────────────────────────────
def _as_matrix(vectors: Sequence[Any]) -> np.ndarray:
    rows = [np.asarray(v, dtype=np.float32).reshape(-1) for v in vectors]
    return np.vstack(rows).astype(np.float32) if rows else np.zeros((0, 0), dtype=np.float32)


def build_vector_store(
    embedder: Any,
    recipes: Iterable[dict[str, Any]],
    *,
    batch_size: int = 64,
    progress: bool = False,
) -> list[dict[str, Any]]:
    """Embed recipes in batches.

    The original encoded one recipe per call, which dominates build time for
    any corpus of a useful size.
    """
    texts: list[str] = []
    metas: list[dict[str, Any]] = []
    for recipe in recipes:
        text = recipe_to_text(recipe)
        if text:
            texts.append(text)
            metas.append(recipe)

    if not texts:
        return []

    chunks: list[np.ndarray] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        chunks.append(_as_matrix(embedder.encode(batch)))
        if progress:
            print(f"  embedded {min(start + batch_size, len(texts))}/{len(texts)}", flush=True)

    embeddings = np.vstack(chunks)
    return [
        {"text": text, "embedding": embeddings[i], "metadata": metas[i]}
        for i, text in enumerate(texts)
    ]


# ── new directory format: embeddings.npy + records.jsonl + meta.json ─────────
def save_index(
    path: str | Path,
    vector_store: list[dict[str, Any]],
    *,
    model: str,
    backend: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write a portable index directory.

    Preferred over pickle: it is inspectable, diffable, and — importantly for a
    public repo — loading it cannot execute arbitrary code the way
    ``pickle.load`` can.
    """
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)

    embeddings = _as_matrix([e["embedding"] for e in vector_store])
    np.save(directory / "embeddings.npy", embeddings)

    with (directory / "records.jsonl").open("w", encoding="utf-8") as fh:
        for entry in vector_store:
            fh.write(
                json.dumps(
                    {"text": entry["text"], "metadata": entry["metadata"]},
                    ensure_ascii=False,
                )
                + "\n"
            )

    meta = {
        "format_version": INDEX_FORMAT_VERSION,
        "count": len(vector_store),
        "dim": int(embeddings.shape[1]) if embeddings.size else 0,
        "model": model,
        "backend": backend,
        **(extra or {}),
    }
    (directory / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return meta


def load_index(path: str | Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load an index. Accepts the new directory format or a legacy .emb pickle."""
    target = Path(path)

    if target.is_dir():
        meta = json.loads((target / "meta.json").read_text(encoding="utf-8"))
        embeddings = np.load(target / "embeddings.npy")
        # Iterate the file rather than str.splitlines(): splitlines() also breaks on
        # U+2028/U+2029, which json.dumps leaves unescaped, and would cut records in half.
        with (target / "records.jsonl").open("r", encoding="utf-8", newline="") as fh:
            records = [json.loads(line) for line in fh if line.strip()]
        if len(records) != len(embeddings):
            raise ValueError(
                f"Index is corrupt: {len(records)} records vs {len(embeddings)} embeddings in {target}"
            )
        store = [
            {"text": rec["text"], "embedding": embeddings[i], "metadata": rec["metadata"]}
            for i, rec in enumerate(records)
        ]
        return store, meta

    if not target.is_file():
        raise FileNotFoundError(f"No index at {target}")

    # Legacy pickle — still readable so existing setups keep working.
    with target.open("rb") as fh:
        store = pickle.load(fh)
    dim = 0
    if store:
        dim = int(np.asarray(store[0]["embedding"]).reshape(-1).shape[0])
    return store, {
        "format_version": 0,
        "format": "legacy-pickle",
        "count": len(store),
        "dim": dim,
        "model": None,
        "backend": None,
    }


# ── legacy pickle helpers (kept for backwards compatibility) ─────────────────
def save_vector_store(path: str | Path, vector_store: list[dict[str, Any]]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(vector_store, f)


def load_vector_store(path: str | Path) -> list[dict[str, Any]]:
    store, _ = load_index(path)
    return store
