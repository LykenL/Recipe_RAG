from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow `python scripts/build_index.py` from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from recipe_rag.embedding import get_embedder  # noqa: E402
from recipe_rag.vector_store import build_vector_store, load_recipes_json, save_index  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Build the recipe index (embeddings.npy + records.jsonl + meta.json).")
    p.add_argument("--recipes", default="artifacts/recipes_all.json")
    p.add_argument("--out", default="artifacts/index")
    p.add_argument("--backend", default=None, help="fastembed (default) | st | openai")
    p.add_argument("--model", default=None, help="e.g. BAAI/bge-small-en-v1.5")
    p.add_argument("--batch-size", type=int, default=64)
    args = p.parse_args()

    recipes_path = Path(args.recipes)
    if not recipes_path.is_file():
        print(
            f"Recipe file not found: {recipes_path}\n"
            "Build it first:  python scripts/fetch_themealdb.py --out artifacts/recipes_all.json",
            file=sys.stderr,
        )
        return 2

    recipes = load_recipes_json(recipes_path)
    embedder = get_embedder(args.backend, args.model)
    print(
        f"Embedding {len(recipes)} recipes "
        f"with backend={embedder.backend} model={embedder.model_name} …",
        flush=True,
    )

    store = build_vector_store(embedder, recipes, batch_size=args.batch_size, progress=True)
    meta = save_index(
        args.out,
        store,
        model=embedder.model_name,
        backend=embedder.backend,
        extra={"recipes_file": str(recipes_path)},
    )
    print(json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"\nWrote {meta['count']} vectors (dim {meta['dim']}) -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
