from __future__ import annotations

import re
from typing import Iterable


_FRACTION_RE = re.compile(r"^\s*(\d+)\s*/\s*(\d+)\s*$")


def parse_token(token: str) -> float | None:
    token = token.strip()
    if not token:
        return None
    try:
        return float(token)
    except ValueError:
        pass
    m = _FRACTION_RE.match(token)
    if m:
        num, den = int(m.group(1)), int(m.group(2))
        if den != 0:
            return num / den
    return None


def scale_line(line: str, factor: float) -> str:
    parts = line.strip().split()
    if not parts:
        return line

    first = parse_token(parts[0])
    if first is None:
        return line

    scaled = first * factor
    if abs(scaled - round(scaled)) < 1e-9:
        scaled_str = str(int(round(scaled)))
    else:
        scaled_str = f"{scaled:.2f}".rstrip("0").rstrip(".")
    return " ".join([scaled_str] + parts[1:])


def scale(
    ingredients: Iterable[str],
    *,
    original_size: float = 0,
    target_size: float | None = None,
    scaling_factor: float | None = None,
) -> list[str]:
    if scaling_factor is None:
        if target_size is not None and original_size > 0:
            scaling_factor = target_size / original_size
        else:
            return list(ingredients)
    return [scale_line(line, float(scaling_factor)) for line in ingredients]

