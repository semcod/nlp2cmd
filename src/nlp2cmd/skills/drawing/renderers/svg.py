"""
SVG Renderer — generates SVG markup from drawing events.

Useful for testing, previewing, and exporting drawings without a browser.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nlp2cmd.skills.drawing.events import ShapeDrawn
from nlp2cmd.skills.drawing.renderers.base import PointGroup, Renderer


class SVGRenderer(Renderer):
    """
    Render drawings as SVG markup.

    Usage:
        renderer = SVGRenderer()
        await renderer.init_canvas(800, 600)
        await renderer.draw_path([(100, 100), (200, 200)], color="#ff0000")
        svg_string = renderer.to_svg()
        await renderer.screenshot("output.svg")
    """

    def __init__(self) -> None:
        self._width = 800
        self._height = 600
        self._elements: list[str] = []
        self._current_color = "#000000"

    async def init_canvas(self, width: float, height: float, url: str = "", app: str = "generic") -> dict[str, Any]:
        self._width = width
        self._height = height
        self._elements.clear()
        return {
            "width": width,
            "height": height,
            "center_x": width / 2,
            "center_y": height / 2,
            "offset_x": 0,
            "offset_y": 0,
        }

    async def set_color(self, color: str) -> None:
        self._current_color = color

    async def draw_path(self, points: PointGroup, color: str = "", fill: bool = False) -> None:
        if not points or len(points) < 2:
            return

        stroke = color or self._current_color
        d_parts = [f"M {points[0][0]:.1f} {points[0][1]:.1f}"]
        for x, y in points[1:]:
            d_parts.append(f"L {x:.1f} {y:.1f}")
        d = " ".join(d_parts)

        fill_attr = stroke if fill else "none"
        self._elements.append(
            f'<path d="{d}" stroke="{stroke}" stroke-width="2" fill="{fill_attr}" />'
        )

    async def draw_shape(self, event: ShapeDrawn) -> None:
        if event.color:
            self._current_color = event.color

        for group in event.points:
            await self.draw_path(group, color=event.color, fill=event.fill)

    async def clear(self) -> None:
        self._elements.clear()

    async def screenshot(self, path: str) -> str | None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        svg_path = p.with_suffix(".svg")
        svg_path.write_text(self.to_svg(), encoding="utf-8")
        return str(svg_path)

    def to_svg(self) -> str:
        """Generate the complete SVG string."""
        elements = "\n  ".join(self._elements)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{self._width}" height="{self._height}" '
            f'viewBox="0 0 {self._width} {self._height}">\n'
            f'  <rect width="100%" height="100%" fill="white" />\n'
            f'  {elements}\n'
            f'</svg>'
        )
