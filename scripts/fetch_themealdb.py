"""
fetch_themealdb.py — expand the recipe corpus with real modern recipes.

The current corpus (week_2/.../lab1_recipes_f.json) is 137 entries from a 1956
Bisquick booklet: "spinach" appears 0 times, "pasta" 0 times, "chicken thigh" 0
times. It also contains non-recipes (the booklet cover got indexed as a dish:
title "© 1956 GEN. MILLS INC.", "instructions" = a marketing blurb).

This script:
  1. drops non-recipes from the Bisquick set (keeps the real ones)
  2. pulls ~300 modern meals from TheMealDB (free, no API key)
  3. writes one merged JSON in the schema the rest of the pipeline expects:
     {title, ingredients, instructions, serving_size, notes}

Usage:
    python scripts/fetch_themealdb.py --out artifacts/recipes_all.json
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.request
from pathlib import Path
from typing import Any

API = "https://www.themealdb.com/api/json/v1/1"
UA = {"User-Agent": "recipe-rag-corpus-builder/1.0"}


# ── TheMealDB ────────────────────────────────────────────────────────────────
def _get(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_all_meals(pause: float = 0.25) -> list[dict[str, Any]]:
    """TheMealDB has no 'list everything' endpoint; walk a-z and de-duplicate."""
    meals: dict[str, dict[str, Any]] = {}
    for letter in "abcdefghijklmnopqrstuvwxyz":
        try:
            for meal in _get(f"{API}/search.php?f={letter}").get("meals") or []:
                meals[meal["idMeal"]] = meal
        except Exception as exc:  # keep going; a missing letter is not fatal
            print(f"  ! letter {letter}: {exc}")
        time.sleep(pause)
    return list(meals.values())


def meal_to_recipe(meal: dict[str, Any]) -> dict[str, Any] | None:
    title = (meal.get("strMeal") or "").strip()
    instructions = (meal.get("strInstructions") or "").strip()
    if not title or len(instructions) < 40:
        return None

    parts = []
    for i in range(1, 21):
        ing = (meal.get(f"strIngredient{i}") or "").strip()
        measure = (meal.get(f"strMeasure{i}") or "").strip()
        if ing:
            parts.append(f"{measure} {ing}".strip())

    area = (meal.get("strArea") or "").strip()
    category = (meal.get("strCategory") or "").strip()
    return {
        "title": title,
        "ingredients": ", ".join(parts),
        "instructions": re.sub(r"\r\n?|\n{2,}", "\n", instructions),
        # TheMealDB does not publish serving counts — 0/0 means "unknown".
        "serving_size": [0, 0],
        "notes": f"Source: TheMealDB · {category} · {area}".strip(" ·"),
        # extra metadata; recipe_to_text() ignores these, the UI can use them
        "source": "themealdb",
        "category": category,
        "area": area,
        "image": meal.get("strMealThumb") or "",
    }


# ── Bisquick cleanup ─────────────────────────────────────────────────────────
def _is_real_recipe(r: dict[str, Any]) -> bool:
    title = (r.get("title") or "").strip()
    ing = (r.get("ingredients") or "").strip()
    ins = (r.get("instructions") or "").strip()
    if not title or not ins:
        return False
    if re.search(r"©|copyright|gen\.?\s*mills", title, re.I):
        return False
    # a real recipe lists ingredients and has more than a blurb
    if len(ing) < 10 or len(ins) < 40:
        return False
    return True


def main() -> int:
    p = argparse.ArgumentParser(description="Build a merged, cleaned recipe corpus.")
    p.add_argument("--base", default="week_2/COLX_563_lab2_Lyken35/lab1_recipes_f.json")
    p.add_argument("--out", default="artifacts/recipes_all.json")
    p.add_argument("--no-themealdb", action="store_true")
    args = p.parse_args()

    base_path = Path(args.base)
    base = json.loads(base_path.read_text(encoding="utf-8")) if base_path.is_file() else []
    kept = [r for r in base if _is_real_recipe(r)]
    dropped = len(base) - len(kept)
    print(f"Bisquick: kept {len(kept)} / {len(base)}  (dropped {dropped} non-recipes)")

    meals: list[dict[str, Any]] = []
    if not args.no_themealdb:
        print("Fetching TheMealDB (a–z)…")
        raw = fetch_all_meals()
        meals = [m for m in (meal_to_recipe(x) for x in raw) if m]
        print(f"TheMealDB: {len(meals)} usable recipes from {len(raw)} meals")

    merged = kept + meals
    seen: set[str] = set()
    unique = []
    for r in merged:
        key = r["title"].strip().lower()
        if key not in seen:
            seen.add(key)
            unique.append(r)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(unique, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nWrote {len(unique)} recipes -> {out}")

    blob = " ".join((r["title"] + " " + r["ingredients"] + " " + r["instructions"]).lower() for r in unique)
    print("\ncoverage now:")
    for kw in ["spinach", "pasta", "rice", "chicken thigh", "olive oil", "garlic", "lemon", "tofu", "bean"]:
        print(f"   {kw:15s} {blob.count(kw)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
