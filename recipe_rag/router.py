from __future__ import annotations

import json
import re
from typing import Any


CLASSIFICATION_PROMPT = """System: You are an intent classifier for Betty Talker, a recipe assistant.
Classify the user's utterance into exactly ONE intent. Output ONLY valid JSON (no markdown).

Intents:
- SearchRecipeIntent: User wants info about a specific recipe in the cookbook
  (ingredients, instructions, bake time, servings, "how do I make X").
  Slots: {"intent":"SearchRecipeIntent","recipe_name":"<string>"}

- ScaleRecipeIntent: User wants to scale a recipe by a factor or target servings.
  Slots: {"intent":"ScaleRecipeIntent","recipe_name":"<string>","scaling_factor":<number|null>,"target_size":<number|null>}

- CookingQuestionIntent: General cooking help — substitutions, techniques, food safety,
  "can I use X instead of Y", equipment, timing, without naming one cookbook recipe.
  Slots: {"intent":"CookingQuestionIntent"}

- OtherIntent: Clearly NOT about cooking or food (trivia, politics, homework, etc.).
  Slots: {"intent":"OtherIntent"}

Examples:
{"utterance":"how do I make asparagus shortcake?","intent":"SearchRecipeIntent","recipe_name":"asparagus shortcake"}
{"utterance":"what are the ingredients for cheese snacks?","intent":"SearchRecipeIntent","recipe_name":"cheese snacks"}
{"utterance":"double the fritters recipe","intent":"ScaleRecipeIntent","recipe_name":"fritters","scaling_factor":2.0,"target_size":null}
{"utterance":"I only want 12 fritters","intent":"ScaleRecipeIntent","recipe_name":"fritters","scaling_factor":null,"target_size":12}
{"utterance":"can I replace cream with milk plus cheese?","intent":"CookingQuestionIntent"}
{"utterance":"what can I use instead of buttermilk?","intent":"CookingQuestionIntent"}
{"utterance":"will milk and cheese curdle if I boil them like cream?","intent":"CookingQuestionIntent"}
{"utterance":"describe the Mexican flag","intent":"OtherIntent"}
{"utterance":"what is the capital of France?","intent":"OtherIntent"}

Now classify this utterance and return JSON only:
{"utterance":"PLACEHOLDER"}
"""

# Fallback when the classifier returns OtherIntent but the query is clearly culinary.
_COOKING_HINTS = re.compile(
    r"\b("
    r"recipe|cook|bake|roast|simmer|boil|fry|grill|oven|stovetop|"
    r"ingredient|substitut|replace|swap|instead of|alternative|"
    r"serving|cup|tablespoon|teaspoon|ounce|gram|"
    r"cream|milk|cheese|butter|flour|sugar|egg|salt|pepper|"
    r"sauce|dough|batter|marinate|knead|whisk|fold"
    r")\b",
    re.IGNORECASE,
)


def is_cooking_related(query: str) -> bool:
    return bool(_COOKING_HINTS.search(query or ""))


def parse_json_strictish(raw: str) -> dict[str, Any]:
    raw = (raw or "").strip()
    raw = re.sub(r"```json?\s*", "", raw).strip().rstrip("`").strip()
    return json.loads(raw)


def classify_intent(llm_client: Any, query: str) -> dict[str, Any]:
    prompt = CLASSIFICATION_PROMPT.replace("PLACEHOLDER", (query or "").replace('"', '\\"'))
    raw = llm_client.chat(prompt, max_tokens=150)
    try:
        intent = parse_json_strictish(raw)
    except Exception:
        if "ScaleRecipeIntent" in raw:
            return {
                "intent": "ScaleRecipeIntent",
                "recipe_name": query,
                "scaling_factor": None,
                "target_size": None,
            }
        if "SearchRecipeIntent" in raw:
            return {"intent": "SearchRecipeIntent", "recipe_name": query}
        if "CookingQuestionIntent" in raw:
            return {"intent": "CookingQuestionIntent"}
        intent = {"intent": "OtherIntent"}

    name = intent.get("intent")
    if name == "OtherIntent" and is_cooking_related(query):
        return {"intent": "CookingQuestionIntent"}
    return intent
