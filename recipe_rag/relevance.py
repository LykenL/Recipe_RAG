from __future__ import annotations

import re
from typing import Any

from .retrieval import _entry_title

_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "how",
        "make",
        "recipe",
        "recipes",
        "cook",
        "cooking",
        "what",
        "can",
        "you",
        "need",
        "want",
        "about",
        "from",
        "this",
        "that",
        "your",
        "have",
        "does",
        "are",
        "any",
        "use",
        "using",
    }
)


def _significant_words(text: str) -> set[str]:
    words = re.findall(r"[a-z]{3,}", (text or "").lower())
    return {w for w in words if w not in _STOPWORDS}


def is_cookbook_relevant(
    query: str,
    hits: list[tuple[float, dict[str, Any]]],
    *,
    recipe_name: str | None = None,
    min_score: float = 0.35,
) -> bool:
    """
    True when a retrieved dish title plausibly matches what the user asked for.
    High embedding score alone is not enough (e.g. shrimp casserole vs cream spaghetti).
    """
    if not hits:
        return False

    focus = (recipe_name or query).strip()
    focus_words = _significant_words(focus)
    if not focus_words:
        return False

    focus_lower = focus.lower()
    for score, entry in hits[:3]:
        if score < min_score:
            continue
        title = _entry_title(entry)
        title_lower = title.lower()
        if focus_lower in title_lower or title_lower in focus_lower:
            return True
        title_words = _significant_words(title)
        overlap = focus_words & title_words
        if not overlap:
            continue
        # Require most focus words to appear in the title, or a tight 2+ word overlap.
        if len(overlap) >= 2 and len(overlap) / max(len(focus_words), 1) >= 0.5:
            return True
        if len(focus_words) == 1 and overlap == focus_words:
            return True
    return False
