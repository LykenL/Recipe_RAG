from __future__ import annotations

from typing import Iterable, Literal

PromptMode = Literal["recipe", "cooking", "no_cookbook_match"]

_CONCISE_STYLE = (
    "Keep the whole answer under 110 words. "
    "Structure: (1) one-sentence verdict on its own line; (2) a blank line; "
    "(3) 2–3 bullets, each on its own line starting with '• ' (do not put multiple bullets on one line). "
    "no long intro paragraphs. "
    "When citing the cookbook, use the plain dish name in Title Case "
    "(e.g. Cheese Sauce), not 【brackets】 or 'Recipe 1' / 'Recipe 2'."
)

RECIPE_SYSTEM_PROMPT = (
    "You are Betty Talker, a friendly culinary assistant for a Bisquick-style cookbook. "
    "Answer using the COOKBOOK EXCERPTS below when they apply. "
    + _CONCISE_STYLE
    + " Do not reply with generic greetings or ask what the user wants to make."
)

COOKING_SYSTEM_PROMPT = (
    "You are Betty Talker, a practical home-cooking assistant. "
    "Answer the user's question directly. "
    "For substitutions: verdict first, then texture/fat/flavor trade-offs and one practical ratio tip. "
    + _CONCISE_STYLE
    + " Use COOKBOOK EXCERPTS only when a listed dish is clearly relevant. "
    "Never deflect with 'What would you like to make?'"
)

NO_COOKBOOK_MATCH_PROMPT = (
    "You are Betty Talker, assistant for a specific Bisquick-style cookbook. "
    "The user asked about a dish that is NOT in this cookbook (no matching excerpt was found). "
    + _CONCISE_STYLE
    + " Rules: "
    "State clearly in the first sentence that this exact dish is not in the cookbook. "
    "Do NOT name or adapt unrelated cookbook recipes (no 'try the casserole but swap corn for pasta'). "
    "Do NOT mention any dish name from the excerpts section — there are none for this question. "
    "Give 2–3 bullets of brief, general cooking guidance for their goal (technique, timing, safety), "
    "or suggest they rephrase with a dish that might be in a classic Bisquick book (e.g. pancakes, biscuits, cheese sauce). "
    "Stay honest and helpful without pretending we have their recipe."
)

OFF_TOPIC_REFUSAL = (
    "I can only help with cooking and recipes from this assistant. "
    "Ask me about a dish, ingredients, substitutions, or scaling a recipe."
)


def _format_recipes(top_recipes: Iterable[str]) -> str:
    recipes = [r for r in top_recipes if r and r != "No matching documents!"]
    if not recipes:
        return "(No matching dish in this cookbook.)"
    return "\n\n---\n\n".join(recipes)


def construct_prompt(
    query: str,
    top_recipes: Iterable[str],
    *,
    mode: PromptMode = "recipe",
) -> str:
    if mode == "no_cookbook_match":
        system_prompt = NO_COOKBOOK_MATCH_PROMPT
        recipe_section = "(No matching dish in this cookbook — do not cite cookbook recipes.)"
    else:
        system_prompt = RECIPE_SYSTEM_PROMPT if mode == "recipe" else COOKING_SYSTEM_PROMPT
        recipe_section = _format_recipes(top_recipes)

    return f"""SYSTEM:
{system_prompt}

COOKBOOK EXCERPTS:
{recipe_section}

USER QUESTION:
{query}

Answer as Betty Talker:
"""
