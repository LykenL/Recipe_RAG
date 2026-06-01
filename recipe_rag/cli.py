from __future__ import annotations

import argparse
from pathlib import Path

from .app import RecipeRAGAssistant


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="recipe-rag", description="Recipe RAG assistant (showcase).")
    p.add_argument("--vector-store", default="week_3/COLX_563_lab3_Lyken35/recipes.emb")
    p.add_argument("--env", default=None, help="Path to .env (optional).")
    p.add_argument("--embedding-model", default="all-MiniLM-L6-v2")
    sub = p.add_subparsers(dest="cmd", required=True)

    ask = sub.add_parser("ask", help="Ask a cooking question (RAG).")
    ask.add_argument("query")

    route = sub.add_parser("route", help="Intent route then respond.")
    route.add_argument("query")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    assistant = RecipeRAGAssistant.from_files(
        vector_store_path=Path(args.vector_store),
        dotenv_path=args.env,
        embedding_model=args.embedding_model,
    )
    if args.cmd == "ask":
        print(assistant.answer(args.query))
        return 0
    if args.cmd == "route":
        print(assistant.route(args.query))
        return 0
    raise RuntimeError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())

