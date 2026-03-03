"""
Natural Language parser for drawing commands.

Parses PL + EN natural language into DrawCommand objects.
Single Responsibility: NL text → structured commands.
"""

from __future__ import annotations

import re
from typing import Any

from nlp2cmd.skills.drawing.commands import ClearCanvas, DrawCommand, DrawShape, InitCanvas, SetColor
from nlp2cmd.skills.drawing.colors import ColorResolver
from nlp2cmd.skills.drawing.shapes import ShapeRegistry


class NLDrawingParser:
    """
    Parse natural language drawing instructions into DrawCommand sequences.

    Supports Polish and English. Extensible via custom shape/color mappings.

    Usage:
        parser = NLDrawingParser()
        commands = parser.parse("narysuj czerwone koło i niebieski trójkąt")
        # [SetColor("#FF0000"), DrawShape("circle"), SetColor("#0000FF"), DrawShape("triangle")]
    """

    SHAPE_PATTERNS: dict[str, str] = {
        # Basic shapes
        "circle":    r"(?:okr[aąę]g|ko[lł][oa]|k[oó][lł]k[oaą]|circle)",
        "ellipse":   r"(?:elips[aeę]|ellipse|owal|oval)",
        "rectangle": r"(?:prostok[aą]t|rectangle|rect)",
        "square":    r"(?:kwadrat|square)",
        "triangle":  r"(?:tr[oó]jk[aą]t|triangle)",
        "star":      r"(?:gwiazd[aęk]|gwiazdka|star)",
        "heart":     r"(?:serce|serduszko|heart)",
        "spiral":    r"(?:spiral[aęy]|spiral)",
        "house":     r"(?:dom|domek|house)",
        "flower":    r"(?:kwiat|kwiatek|flower)",
        "sun":       r"(?:s[lł]o[nń]ce|sun)",
        "tree":      r"(?:drzew[oa]|tree)",
        "line":      r"(?:lini[aeę]|kres[kę]|line)",
        "dot":       r"(?:kropk[aęi]|punkt|dot|point)",
        "grid":      r"(?:siatk[aęi]|grid|krat[aęi])",
        "wave":      r"(?:fal[aęi]|wave)",
        # Complex shapes
        "car":       r"(?:samoch[oó]d|auto|car)",
        "bird":      r"(?:ptak|ptasz[eę]k|bird)",
        "butterfly": r"(?:motyl|motylek|butterfly)",
        "boat":      r"(?:ł[oó]d[zźkk]|łódka|statek|boat|ship)",
        "mountain":  r"(?:g[oó]r[ayę]|mountain)",
        "cat":       r"(?:kot|kotek|cat)",
        "fish":      r"(?:ryb[aęk]|rybka|fish)",
        "rocket":    r"(?:rakiet[aęy]|rocket)",
        "castle":    r"(?:zamek|zamku|castle)",
        "diamond":   r"(?:diament|brylant|diamond)",
        "arrow":     r"(?:strza[lł][aęk]|strzałka|arrow)",
        "pentagon":  r"(?:pi[eę]ciok[aą]t|pentagon)",
        "hexagon":   r"(?:sze[sś]ciok[aą]t|hexagon)",
        "octagon":   r"(?:o[sś]miok[aą]t|octagon)",
        "cross":     r"(?:krzy[żz]|cross)",
        "crescent":  r"(?:p[oó][lł]ksi[eę][żz]yc|crescent|sierp)",
        "submarine": r"(?:okr[eę]t|podwodn[ay]|submarine|sub|u-boat)",
        "cloud_detailed": r"(?:chmur[aęk]|chmurka|cloud)",
    }

    CLEAR_PATTERNS = re.compile(
        r"(?:wyczy[sś][cć]|kasuj|usu[nń]|clear|erase|reset)", re.IGNORECASE
    )

    def __init__(self, color_resolver: ColorResolver | None = None) -> None:
        self._colors = color_resolver or ColorResolver()

    def parse(self, text: str, canvas_width: float = 0, canvas_height: float = 0) -> list[DrawCommand]:
        """
        Parse NL text into a list of DrawCommands.

        Args:
            text: Natural language drawing instruction
            canvas_width: Canvas width (for center calculation)
            canvas_height: Canvas height (for center calculation)

        Returns:
            Ordered list of DrawCommand objects
        """
        text_lower = text.lower()
        commands: list[DrawCommand] = []

        # Check for clear command
        if self.CLEAR_PATTERNS.search(text_lower):
            commands.append(ClearCanvas())
            return commands

        # Extract colors and shapes
        colors = self._colors.extract_colors(text)
        shapes = self._extract_shapes(text_lower)

        # Default color if none found
        if not colors:
            colors = ["#000000"]

        # Default shape if none found
        if not shapes:
            shapes = ["circle"]

        # Build command sequence: for each shape, set color then draw
        cx = canvas_width / 2 if canvas_width > 0 else 0
        cy = canvas_height / 2 if canvas_height > 0 else 0

        # Extract size hint from text
        size_params = self._extract_size_params(text_lower)

        for i, shape in enumerate(shapes):
            color = colors[i] if i < len(colors) else colors[0]
            commands.append(SetColor(color=color))

            params = dict(size_params)
            params.update(self._extract_shape_specific_params(text_lower, shape))

            commands.append(DrawShape(
                shape_type=shape,
                color=color,
                center_x=cx,
                center_y=cy,
                params=params,
            ))

        return commands

    def detect_shape(self, text: str) -> str:
        """Detect the primary shape from text. Returns shape name or 'circle'."""
        shapes = self._extract_shapes(text.lower())
        return shapes[0] if shapes else "circle"

    def detect_color(self, text: str, default: str = "#000000") -> str:
        """Detect the primary color from text. Returns hex code."""
        colors = self._colors.extract_colors(text)
        return colors[0] if colors else default

    def _extract_shapes(self, text_lower: str) -> list[str]:
        """Extract shape names from text."""
        found: list[str] = []
        for shape_name, pattern in self.SHAPE_PATTERNS.items():
            if re.search(pattern, text_lower):
                found.append(shape_name)
        return found

    def _extract_size_params(self, text_lower: str) -> dict[str, Any]:
        """Extract size hints from text."""
        params: dict[str, Any] = {}

        # "duże/large" → bigger
        if re.search(r"(?:du[zż][eay]|large|big|wielk[ie])", text_lower):
            params["size_multiplier"] = 1.5

        # "małe/small" → smaller
        if re.search(r"(?:ma[lł][eay]|small|tiny|drobne)", text_lower):
            params["size_multiplier"] = 0.5

        # Explicit radius: "r=100" or "radius 100"
        m = re.search(r"(?:r(?:adius)?[=:\s]+)(\d+)", text_lower)
        if m:
            params["radius"] = int(m.group(1))

        return params

    def _extract_shape_specific_params(self, text_lower: str, shape: str) -> dict[str, Any]:
        """Extract shape-specific parameters from text."""
        params: dict[str, Any] = {}

        if shape == "star":
            m = re.search(r"(\d+)\s*(?:ramion|punkt[oó]w|points|arms)", text_lower)
            if m:
                params["points_count"] = int(m.group(1))

        elif shape == "flower":
            m = re.search(r"(\d+)\s*(?:p[lł]atk[oó]w|petals)", text_lower)
            if m:
                params["petals"] = int(m.group(1))

        elif shape == "spiral":
            m = re.search(r"(\d+)\s*(?:obrot[oó]w|turns)", text_lower)
            if m:
                params["turns"] = int(m.group(1))

        elif shape == "wave":
            m = re.search(r"(\d+)\s*(?:fal[ie]?|waves)", text_lower)
            if m:
                params["waves"] = int(m.group(1))

        elif shape == "grid":
            m = re.search(r"(\d+)\s*[x×]\s*(\d+)", text_lower)
            if m:
                params["cols"] = int(m.group(1))
                params["rows"] = int(m.group(2))

        return params
