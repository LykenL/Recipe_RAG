from __future__ import annotations

import argparse
from pathlib import Path

from sentence_transformers import SentenceTransformer

from recipe_rag.retrieval import search
from recipe_rag.vector_store import load_vector_store


DEFAULT_QUERIES = [
    "strawberry pie",
    "tuna broccoli casserole notes",
    "cranberry muffin ingredients",
    "what can I cook with pineapple?",
]


def main() -> int:
    p = argparse.ArgumentParser(description="Quick retrieval sanity check (no LLM).")
    p.add_argument("--vector-store", default="week_3/COLX_563_lab3_Lyken35/recipes.emb")
    p.add_argument("--embedding-model", default="all-MiniLM-L6-v2")
    p.add_argument("--k", type=int, default=3)
    p.add_argument("--min-similarity", type=float, default=0.2)
    p.add_argument("query", nargs="*")
    args = p.parse_args()

    queries = args.query or DEFAULT_QUERIES
    embedder = SentenceTransformer(args.embedding_model)
    store = load_vector_store(Path(args.vector_store))

    for q in queries:
        print("\n===", q, "===")
        results = search(embedder, store, q, k=args.k, min_similarity=args.min_similarity)
        for i, r in enumerate(results):
            s = str(r).replace("\n", " ")
            print(f"[{i}] {s[:220]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

