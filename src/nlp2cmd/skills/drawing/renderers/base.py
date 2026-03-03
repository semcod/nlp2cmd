"""
Abstract Renderer — interface for all drawing backends.

Follows Dependency Inversion Principle: high-level drawing logic depends
on this abstraction, not on concrete implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from nlp2cmd.skills.drawing.events import DrawingEvent, ShapeDrawn


PointGroup = list[tuple[float, float]]


class Renderer(ABC):
    """
    Abstract renderer interface.

    Concrete implementations:
    - PlaywrightRenderer: draws on browser canvas via mouse movements
    - SVGRenderer: generates SVG markup
    - (extensible: TkinterRenderer, PillowRenderer, etc.)
    """

    @abstractmethod
    async def init_canvas(self, width: float, height: float, url: str = "", app: str = "generic") -> dict[str, Any]:
        """
        Initialize the drawing surface.

        Returns:
            Dict with canvas info: {"width", "height", "center_x", "center_y", ...}
        """
        ...

    @abstractmethod
    async def set_color(self, color: str) -> None:
        """Set the active drawing color."""
        ...

    @abstractmethod
    async def draw_path(self, points: PointGroup, color: str = "", fill: bool = False) -> None:
        """
        Draw a continuous path through the given points.

        Args:
            points: List of (x, y) coordinate tuples
            color: Override color (uses current color if empty)
            fill: Whether to fill the shape
        """
        ...

    @abstractmethod
    async def draw_shape(self, event: ShapeDrawn) -> None:
        """
        Render a ShapeDrawn event.

        The default implementation iterates over event.points groups
        and calls draw_path for each. Override for optimized rendering.
        """
        ...

    @abstractmethod
    async def clear(self) -> None:
        """Clear the canvas."""
        ...

    @abstractmethod
    async def screenshot(self, path: str) -> str | None:
        """Take a screenshot, return the file path or None."""
        ...

    async def render_events(self, events: list[DrawingEvent]) -> None:
        """Render a sequence of events (replay support)."""
        for event in events:
            if isinstance(event, ShapeDrawn):
                await self.draw_shape(event)

    async def dispose(self) -> None:
        """Clean up resources. Override if needed."""
        pass
