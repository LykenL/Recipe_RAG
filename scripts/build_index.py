from __future__ import annotations

import argparse
from pathlib import Path

from sentence_transformers import SentenceTransformer

from recipe_rag.vector_store import build_vector_store, load_recipes_json, save_vector_store


def main() -> int:
    p = argparse.ArgumentParser(description="Build recipe vector store (.emb via pickle).")
    p.add_argument("--recipes", default="week_2/COLX_563_lab2_Lyken35/lab1_recipes_f.json")
    p.add_argument("--out", default="artifacts/recipes.emb")
    p.add_argument("--embedding-model", default="all-MiniLM-L6-v2")
    args = p.parse_args()

    recipes = load_recipes_json(Path(args.recipes))
    embedder = SentenceTransformer(args.embedding_model)
    store = build_vector_store(embedder, recipes)
    save_vector_store(Path(args.out), store)
    print(f"Wrote {len(store)} entries -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

