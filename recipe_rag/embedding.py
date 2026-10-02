"""
Pluggable text embedder.

Why this module exists
----------------------
The original code called `SentenceTransformer(...)` directly in three places.
That pulls in PyTorch: a ~2GB image and ~500MB of resident memory, which does
not fit Render's 512MB free instance.

`fastembed` runs the same class of model through ONNX Runtime instead:
~150MB image, ~120MB memory, no API key, no torch. This module keeps the
`SentenceTransformer.encode` call signature so `retrieval.py` is unchanged.

Backends
--------
  fastembed  (default) ONNX, local, no key, small enough for a 512MB instance
  st                   sentence-transformers / torch — local dev parity
  openai               API-based; biggest quality jump, needs a key

Index compatibility
-------------------
Embeddings are only comparable within one model. `EMBEDDING_MODEL` is recorded
in the index metadata at build time and checked at load time, so a mismatch
fails loudly instead of silently returning garbage neighbours.
"""

from __future__ import annotations

import os
from typing import Any, Iterable, Sequence

import numpy as np

# Chosen by measurement, not by leaderboard. On the 829-recipe corpus:
#
#   model                        relevant(min)  off-topic(max)  separation
#   BAAI/bge-small-en-v1.5             0.605          0.600        +0.005
#   sentence-transformers/all-MiniLM   0.460          0.288        +0.172
#
# bge-small ranks higher on MTEB but squeezes every input into a narrow
# high-cosine band, so a similarity threshold cannot distinguish "here is a
# relevant recipe" from "we have nothing like this". With only 829 short
# documents, separation matters more than benchmark rank.
DEFAULT_FASTEMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_ST_MODEL = "all-MiniLM-L6-v2"
DEFAULT_OPENAI_MODEL = "text-embedding-3-small"


class EmbedderError(RuntimeError):
    pass


class FastEmbedEmbedder:
    """Local ONNX embeddings. No torch, no network after the first download."""

    backend = "fastembed"

    def __init__(self, model_name: str = DEFAULT_FASTEMBED_MODEL) -> None:
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:  # pragma: no cover
            raise EmbedderError(
                "fastembed is not installed. `pip install fastembed` (it is in requirements.txt)."
            ) from exc
        self.model_name = model_name
        self._model = TextEmbedding(model_name=model_name)

    def encode(self, texts: str | Sequence[str], **_: Any) -> np.ndarray:
        single = isinstance(texts, str)
        items = [texts] if single else list(texts)
        if not items:
            return np.zeros((0, self.dimension), dtype=np.float32)
        vecs = np.asarray(list(self._model.embed(items)), dtype=np.float32)
        return vecs[0] if single else vecs

    @property
    def dimension(self) -> int:
        return len(self.encode("dimension probe"))


class SentenceTransformerEmbedder:
    """Local torch embeddings — kept for dev parity with the old behaviour."""

    backend = "st"

    def __init__(self, model_name: str = DEFAULT_ST_MODEL) -> None:
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self._model = SentenceTransformer(model_name)

    def encode(self, texts: str | Sequence[str], **kwargs: Any) -> np.ndarray:
        return self._model.encode(texts, **kwargs)

    @property
    def dimension(self) -> int:
        return int(self._model.get_sentence_embedding_dimension())


class OpenAIEmbedder:
    """Hosted embeddings via any OpenAI-compatible endpoint."""

    backend = "openai"

    def __init__(
        self,
        model_name: str = DEFAULT_OPENAI_MODEL,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        batch_size: int = 96,
    ) -> None:
        from openai import OpenAI

        key = api_key or os.getenv("EMBEDDING_API_KEY") or os.getenv("OPENAI_API", "")
        if not key:
            raise EmbedderError("OpenAI embedder needs EMBEDDING_API_KEY (or OPENAI_API).")
        self.model_name = model_name
        self._batch = batch_size
        self._client = OpenAI(
            api_key=key,
            base_url=base_url or os.getenv("EMBEDDING_BASE_URL") or os.getenv("OPENAI_BASE_URL"),
        )

    def encode(self, texts: str | Sequence[str], **_: Any) -> np.ndarray:
        single = isinstance(texts, str)
        items = [texts] if single else list(texts)
        out: list[list[float]] = []
        for i in range(0, len(items), self._batch):
            resp = self._client.embeddings.create(model=self.model_name, input=items[i : i + self._batch])
            out.extend(d.embedding for d in resp.data)
        vecs = np.asarray(out, dtype=np.float32)
        return vecs[0] if single else vecs

    @property
    def dimension(self) -> int:
        return len(self.encode("dimension probe"))


_BACKENDS = {
    "fastembed": (FastEmbedEmbedder, DEFAULT_FASTEMBED_MODEL),
    "st": (SentenceTransformerEmbedder, DEFAULT_ST_MODEL),
    "sentence-transformers": (SentenceTransformerEmbedder, DEFAULT_ST_MODEL),
    "openai": (OpenAIEmbedder, DEFAULT_OPENAI_MODEL),
}


def get_embedder(backend: str | None = None, model: str | None = None, **kwargs: Any):
    """Build an embedder. Backend/model fall back to env vars, then to fastembed."""
    name = (backend or os.getenv("EMBEDDING_BACKEND") or "fastembed").strip().lower()
    if name not in _BACKENDS:
        raise EmbedderError(f"Unknown EMBEDDING_BACKEND={name!r}. Choose one of {sorted(_BACKENDS)}.")
    cls, default_model = _BACKENDS[name]
    return cls(model or os.getenv("EMBEDDING_MODEL") or default_model, **kwargs)
