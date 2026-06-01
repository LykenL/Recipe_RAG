from __future__ import annotations

import html
import re


def normalize_answer_lines(text: str) -> str:
    """Ensure verdict and bullets render on separate lines in HTML/UI."""
    text = (text or "").strip()
    if not text:
        return text
    # LLMs often join bullets on one line: "...sauce. • Using milk..."
    text = re.sub(r"(?<!\n)\s*•\s*", "\n\n• ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def answer_to_html(text: str) -> str:
    """Escape HTML and preserve newlines (use with CSS white-space: pre-wrap)."""
    return html.escape(normalize_answer_lines(text))
