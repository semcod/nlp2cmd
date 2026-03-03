"""
Color resolver — maps color names (PL + EN) to hex codes.

Single Responsibility: color name resolution and hex validation.
"""

from __future__ import annotations

import re
from typing import Optional


class ColorResolver:
    """
    Resolves color names to hex codes with Polish + English support.

    Extensible via register() for custom color names.

    Usage:
        resolver = ColorResolver()
        resolver.resolve("czerwony")  # "#FF0000"
        resolver.resolve("blue")      # "#0000FF"
        resolver.extract_colors("narysuj czerwone koło z niebieskim obramowaniem")
        # ["#FF0000", "#0000FF"]
    """

    _BUILTIN: dict[str, str] = {
        # Red — all Polish declensions: nom/acc/gen/dat/ins/loc × m/f/n
        "czerwony": "#FF0000", "czerwone": "#FF0000", "czerwona": "#FF0000",
        "czerwonym": "#FF0000", "czerwonego": "#FF0000", "czerwoną": "#FF0000",
        "czerwonej": "#FF0000", "czerwonemu": "#FF0000",
        "red": "#FF0000",
        # Black
        "czarny": "#000000", "czarne": "#000000", "czarna": "#000000",
        "czarnym": "#000000", "czarną": "#000000", "czarnej": "#000000",
        "black": "#000000",
        # White
        "biały": "#FFFFFF", "białe": "#FFFFFF", "biała": "#FFFFFF",
        "białym": "#FFFFFF", "białą": "#FFFFFF", "białej": "#FFFFFF",
        "white": "#FFFFFF",
        # Yellow
        "żółty": "#FFFF00", "żółte": "#FFFF00", "żółta": "#FFFF00",
        "żółtym": "#FFFF00", "żółtą": "#FFFF00", "żółtej": "#FFFF00",
        "yellow": "#FFFF00",
        # Blue
        "niebieski": "#0000FF", "niebieskie": "#0000FF", "niebieska": "#0000FF",
        "niebieskim": "#0000FF", "niebieską": "#0000FF", "niebieskiej": "#0000FF",
        "blue": "#0000FF",
        # Green
        "zielony": "#00FF00", "zielone": "#00FF00", "zielona": "#00FF00",
        "zielonym": "#00FF00", "zieloną": "#00FF00", "zielonej": "#00FF00",
        "green": "#00FF00",
        # Orange
        "pomarańczowy": "#FF8800", "pomarańczowe": "#FF8800",
        "pomarańczowa": "#FF8800", "pomarańczowym": "#FF8800",
        "pomarańczową": "#FF8800", "pomarańczowej": "#FF8800",
        "orange": "#FF8800",
        # Purple
        "fioletowy": "#8800FF", "fioletowe": "#8800FF", "fioletowa": "#8800FF",
        "fioletowym": "#8800FF", "fioletową": "#8800FF", "fioletowej": "#8800FF",
        "purple": "#8800FF",
        # Pink
        "różowy": "#FF69B4", "różowe": "#FF69B4", "różowa": "#FF69B4",
        "różowym": "#FF69B4", "różową": "#FF69B4", "różowej": "#FF69B4",
        "pink": "#FF69B4",
        # Gray
        "szary": "#808080", "szare": "#808080", "szara": "#808080",
        "szarym": "#808080", "szarą": "#808080", "szarej": "#808080",
        "gray": "#808080", "grey": "#808080",
        # Brown
        "brązowy": "#8B4513", "brązowe": "#8B4513", "brązowa": "#8B4513",
        "brązowym": "#8B4513", "brązową": "#8B4513", "brązowej": "#8B4513",
        "brown": "#8B4513",
        # Cyan
        "turkusowy": "#00FFFF", "turkusowe": "#00FFFF",
        "turkusową": "#00FFFF", "turkusowej": "#00FFFF",
        "cyan": "#00FFFF",
    }

    def __init__(self) -> None:
        self._colors: dict[str, str] = dict(self._BUILTIN)

    def register(self, name: str, hex_code: str) -> None:
        """Register a custom color name → hex mapping."""
        self._colors[name.lower()] = hex_code.upper()

    def resolve(self, name: str, default: str = "#000000") -> str:
        """Resolve a color name to hex. Returns default if not found."""
        # Direct lookup
        result = self._colors.get(name.lower())
        if result:
            return result

        # Check if it's already a hex code
        if re.match(r"^#[0-9a-fA-F]{6}$", name):
            return name.upper()

        return default

    def extract_colors(self, text: str) -> list[str]:
        """Extract all color hex codes from natural language text."""
        text_lower = text.lower()
        found: list[str] = []
        seen: set[str] = set()

        # Sort by length (longest first) to match "niebieskim" before "niebieski"
        sorted_names = sorted(self._colors.keys(), key=len, reverse=True)

        for name in sorted_names:
            if name in text_lower:
                hex_code = self._colors[name]
                if hex_code not in seen:
                    found.append(hex_code)
                    seen.add(hex_code)

        # Also match hex codes directly in text
        for m in re.finditer(r"#[0-9a-fA-F]{6}", text):
            code = m.group(0).upper()
            if code not in seen:
                found.append(code)
                seen.add(code)

        return found

    def available(self) -> dict[str, str]:
        """Return all registered color mappings."""
        return dict(self._colors)

    def unique_colors(self) -> dict[str, str]:
        """Return one canonical name per unique hex code."""
        seen: dict[str, str] = {}
        for name, hex_code in sorted(self._colors.items()):
            if hex_code not in seen:
                seen[hex_code] = name
        return {v: k for k, v in seen.items()}
