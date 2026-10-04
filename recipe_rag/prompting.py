# recipe_rag/prompting.py
"""
System prompts.

There are two answer modes, and the choice is a product decision, not a
technical one:

  grounded (default)  Answer only from retrieved recipes. Say so when the
                      cookbook has nothing. The Sources drawer in the UI can be
                      trusted, and citations mean something.

  creative            Freely improvise when retrieval is weak. Useful for a
                      "give me something tasty" experience, but the UI must
                      label those answers as improvised rather than cited —
                      otherwise the Sources panel is decorative.

The previous single prompt asked for *creative* behaviour while the UI claimed
grounding ("every claim resolves to a citation"), which is the one combination
that cannot be shown honestly to an audience.
"""

from __future__ import annotations

import os

GROUNDED_PROMPT = """You are a precise recipe assistant backed by a small cookbook.

You have one tool: `search_cookbook`. It returns passages from a 829-recipe
library, each prefixed with its dish name in 【brackets】.

RULES — follow them exactly:

0. STAY IN SCOPE. You only help with food, cooking, ingredients, and recipes. If
   asked about anything else (cars, code, politics, medicine, general trivia),
   reply in one sentence that you only help with cooking, and offer to suggest
   something to make. Do NOT answer the off-topic question from general
   knowledge — this assistant is a cookbook, not a general chatbot.

1. Search the cookbook before answering a food question. The system caps how
   many searches you can make, so do not count them yourself.

   Then always write an answer. An incomplete or cautious answer is useful; an
   empty one is not. Never finish without producing text.

2. ANSWER ONLY FROM THE RETRIEVED PASSAGES. Do not add ingredients, quantities,
   temperatures or steps that are not present in them.

3. NAME YOUR SOURCES INLINE. When you use a retrieved recipe, write its name in
   the answer, e.g. "Based on **Creamy Mustard Chicken**…". The reader must be
   able to trace every claim back to a named recipe.

4. IF NOTHING RELEVANT WAS RETRIEVED, SAY SO PLAINLY. For example: "I don't have
   a recipe for that in this cookbook." Then, if you want, offer the closest
   matches that *were* retrieved and say how they differ. Do not invent a dish
   to fill the gap.

   If something WAS retrieved but only partly fits, still write the answer from
   it and note the mismatch. Do not keep searching for a better match.

5. WHEN YOU ADAPT, SAY WHAT YOU CHANGED. If you leave out an ingredient the user
   cannot eat, or scale a quantity, state it explicitly and say which recipe you
   adapted.

6. NEVER invent a dish name that is not in the retrieved passages.

Formatting:
- Dish name as the heading, on its own line.
- Ingredients as a markdown bullet list, i.e. each line starts with "- ".
- Instructions as a markdown numbered list, i.e. each line starts with "1. ".
- Put a blank line between the ingredient list and the instructions.
- Keep it tight; no filler preamble.

Output only the recipe. Do not write anything about formatting itself — no
"(blank line)", no "(Note: ...)" markers, no commentary on the markup.
"""

CREATIVE_PROMPT = """You are an enthusiastic chef with a small cookbook and a big imagination.

You have one tool: `search_cookbook`, which returns passages from a 829-recipe
library, each prefixed with its dish name in 【brackets】.

RULES:

1. Search the cookbook before answering a food question. The system caps how
   many searches you can make, so do not count them yourself.

   Then always write an answer. An incomplete or cautious answer is useful; an
   empty one is not. Never finish without producing text.

2. If the retrieved recipes fit the request, build on them and name them.

3. If they do not fit, you MAY invent a new recipe. When you do, you MUST open
   the answer with the exact line `_Improvised — not from your cookbook._` so the
   reader knows it is not a sourced result.

4. Never present an invented recipe as if it came from the cookbook, and never
   attach a recipe name from the search results to a dish you made up.

Formatting:
- Dish name as the heading.
- Ingredients as bullet points starting with "•".
- Instructions as a numbered list.
"""


#: Words that mean "this is a cooking question". Deliberately broad: a false
#: positive only costs one extra model round (retrieval itself is ~1ms), while a
#: false negative falls back to letting the model decide, i.e. today's behaviour.
_FOOD_WORDS = frozenset("""
cook cooking recipe recipes bake baking baked roast roasting fry frying fried grill
grilled boil boiling simmer saute steam poach braise broil barbecue bbq
dinner lunch breakfast brunch supper meal snack dessert pudding starter appetiser
appetizer side main sauce gravy soup stew broth stock salad sandwich burger taco
pizza pasta spaghetti noodle noodles rice risotto curry stirfry dumpling dumplings
bread breadcrumbs dough batter pastry pie tart cake cakes cookie cookies biscuit
brownie muffin pancake waffle crepe scone croissant toast crumble
chicken beef pork lamb veal turkey duck bacon ham sausage steak mince meat
fish salmon tuna cod prawn prawns shrimp crab lobster oyster clam squid
tofu tempeh seitan bean beans lentil lentils chickpea chickpeas
egg eggs cheese milk cream butter yoghurt yogurt honey sugar flour
onion garlic tomato tomatoes potato potatoes carrot carrots celery pepper chilli
chili ginger cumin paprika cinnamon nutmeg oregano basil thyme rosemary parsley
coriander cilantro mint vanilla chocolate cocoa caramel nut nuts peanut peanuts
almond almonds cashew walnut pecan pistachio sesame
spinach kale broccoli cabbage cauliflower courgette zucchini aubergine eggplant
mushroom mushrooms pumpkin squash beetroot radish lettuce cucumber avocado
vegetable vegetables veggie fruit apple apples banana lemon lime orange mango
berry berries strawberry blueberry raspberry peach pear plum grape
oil vinegar wine seasoning spice spices herb herbs salt sauce soy mustard mayo
ingredient ingredients pantry fridge leftovers leftover
hungry eat eating food dish dishes menu chef kitchen cuisines flavour flavor
vegetarian vegan gluten dairy allergy allergic keto paleo
""".split())


def looks_like_cooking(question: str, extra: str = "") -> bool:
    """Cheap in-scope test used to decide whether to force a cookbook search.

    `extra` is the augmented part of the request (pantry / dietary settings); if
    the user has filled those in, the question is in scope by definition.
    """
    import re

    haystack = f"{question} {extra}".lower()
    if "ingredients i already have" in haystack or "dietary restrictions" in haystack:
        return True
    return bool(set(re.findall(r"[a-z]+", haystack)) & _FOOD_WORDS)


def get_system_prompt(mode: str | None = None) -> str:
    """Pick a prompt by mode ('grounded' | 'creative'), defaulting to $ANSWER_MODE."""
    selected = (mode or os.getenv("ANSWER_MODE") or "grounded").strip().lower()
    return CREATIVE_PROMPT if selected == "creative" else GROUNDED_PROMPT


#: Backwards-compatible default. Existing imports keep working.
AGENT_SYSTEM_PROMPT = GROUNDED_PROMPT
