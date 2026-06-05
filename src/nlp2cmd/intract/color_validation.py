"""Canvas color validation for Intract policy checks."""

from __future__ import annotations

import re

_HEX_COLOR_RE = re.compile(
    r"^#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$",
)


def is_valid_hex_color(color: str) -> bool:
    """Return True for #RGB, #RRGGBB, or #RRGGBBAA values."""
    if not color:
        return False
    return bool(_HEX_COLOR_RE.fullmatch(color.strip()))
