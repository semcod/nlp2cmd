"""
DrawingSkill — high-level facade for the drawing system.

Orchestrates commands, queries, events, and rendering through a clean API.
This is the main entry point for external consumers (examples, CLI, etc.).

Usage:
    from nlp2cmd.skills.drawing import DrawingSkill

    # From natural language
    skill = DrawingSkill()
    skill.execute_nl("narysuj czerwone koło i niebieski trójkąt")

    # Programmatic
    skill.init_canvas(1024, 768)
    skill.draw("circle", color="#ff0000")
    skill.draw("star", color="#0000ff", points_count=6)

    # Render to browser
    from nlp2cmd.skills.drawing.renderers.playwright import PlaywrightRenderer
    renderer = PlaywrightRenderer(page)
    await skill.render(renderer)

    # Or render to SVG
    from nlp2cmd.skills.drawing.renderers.svg import SVGRenderer
    renderer = SVGRenderer()
    await skill.render(renderer)
    print(renderer.to_svg())

    # Event sourcing: save/load sessions
    skill.save_session("my_drawing.json")
    skill2 = DrawingSkill.load_session("my_drawing.json")
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nlp2cmd.skills.drawing.colors import ColorResolver
from nlp2cmd.skills.drawing.commands import (
    ClearCanvas,
    CommandBus,
    DrawShape,
    InitCanvas,
    SelectTool,
    SetColor,
)
from nlp2cmd.skills.drawing.event_store import EventStore
from nlp2cmd.skills.drawing.events import DrawingEvent, ShapeDrawn
from nlp2cmd.skills.drawing.nl_parser import NLDrawingParser
from nlp2cmd.skills.drawing.queries import (
    GetCanvasState,
    GetDrawingHistory,
    GetShapePoints,
    QueryBus,
)
from nlp2cmd.skills.drawing.renderers.base import Renderer
from nlp2cmd.skills.drawing.shapes import ShapeRegistry


class DrawingSkill:
    """
    Facade for the drawing skill — single entry point for all drawing operations.

    Combines:
    - CQRS (CommandBus for writes, QueryBus for reads)
    - Event Sourcing (EventStore for history)
    - NL parsing (NLDrawingParser for natural language)
    - Rendering (Renderer protocol for environment independence)
    """

    def __init__(self, event_store: EventStore | None = None) -> None:
        self._store = event_store or EventStore()
        self._command_bus = CommandBus(self._store)
        self._query_bus = QueryBus(self._store)
        self._parser = NLDrawingParser()
        self._colors = ColorResolver()
        self._renderer: Renderer | None = None

    # ── Canvas setup ──────────────────────────────────────────────────

    def init_canvas(self, width: float = 1024, height: float = 768,
                    url: str = "", app: str = "generic") -> DrawingEvent:
        """Initialize the drawing canvas."""
        return self._command_bus.dispatch(InitCanvas(
            width=width, height=height, url=url, app=app,
        ))

    # ── Drawing commands ──────────────────────────────────────────────

    def draw(self, shape_type: str, color: str = "", fill: bool = False,
             center_x: float = 0, center_y: float = 0, **params: Any) -> DrawingEvent:
        """
        Draw a shape on the canvas.

        Args:
            shape_type: Shape name (circle, star, house, etc.)
            color: Hex color code or color name (PL/EN)
            fill: Whether to fill the shape
            center_x: Center X (0 = canvas center)
            center_y: Center Y (0 = canvas center)
            **params: Shape-specific params (radius, points_count, petals, etc.)

        Returns:
            ShapeDrawn event
        """
        resolved_color = self._colors.resolve(color) if color else ""
        return self._command_bus.dispatch(DrawShape(
            shape_type=shape_type,
            color=resolved_color,
            fill=fill,
            center_x=center_x,
            center_y=center_y,
            params=params,
        ))

    def set_color(self, color: str) -> DrawingEvent:
        """Change the active drawing color."""
        return self._command_bus.dispatch(SetColor(
            color=self._colors.resolve(color),
        ))

    def select_tool(self, tool: str) -> DrawingEvent:
        """Select a drawing tool."""
        return self._command_bus.dispatch(SelectTool(tool=tool))

    def clear(self) -> DrawingEvent:
        """Clear the canvas."""
        return self._command_bus.dispatch(ClearCanvas())

    # ── Natural language ──────────────────────────────────────────────

    def execute_nl(self, text: str) -> list[DrawingEvent]:
        """
        Execute a natural language drawing command.

        Args:
            text: Natural language instruction (PL or EN)

        Returns:
            List of emitted events
        """
        state = self.get_state()
        commands = self._parser.parse(
            text,
            canvas_width=state.get("width", 0),
            canvas_height=state.get("height", 0),
        )
        events = []
        for cmd in commands:
            event = self._command_bus.dispatch(cmd)
            events.append(event)
        return events

    def detect_shape(self, text: str) -> str:
        """Detect shape name from NL text."""
        return self._parser.detect_shape(text)

    def detect_color(self, text: str, default: str = "#000000") -> str:
        """Detect color from NL text."""
        return self._parser.detect_color(text, default)

    # ── Queries ───────────────────────────────────────────────────────

    def get_state(self) -> dict[str, Any]:
        """Get current canvas state (reconstructed from events)."""
        return self._query_bus.execute(GetCanvasState())

    def get_history(self, event_type: str | None = None) -> list[dict[str, Any]]:
        """Get drawing history."""
        return self._query_bus.execute(GetDrawingHistory(event_type_filter=event_type))

    def get_shapes(self) -> list[dict[str, Any]]:
        """Get all current shapes with their points."""
        return self._query_bus.execute(GetShapePoints())

    @staticmethod
    def available_shapes() -> list[str]:
        """List all available shape types."""
        return ShapeRegistry.available()

    # ── Rendering ─────────────────────────────────────────────────────

    async def render(self, renderer: Renderer, url: str = "", app: str = "generic") -> dict[str, Any]:
        """
        Render all drawn shapes using the given renderer.

        Args:
            renderer: Renderer implementation (Playwright, SVG, etc.)
            url: URL to navigate to (for browser renderers)
            app: App name hint

        Returns:
            Canvas info dict
        """
        self._renderer = renderer

        state = self.get_state()
        canvas_info = await renderer.init_canvas(
            width=state.get("width", 1024),
            height=state.get("height", 768),
            url=url,
            app=app,
        )

        # Scale coordinates if actual canvas differs from initialized canvas
        actual_w = canvas_info.get("width", 0)
        actual_h = canvas_info.get("height", 0)
        init_w = state.get("width", 1024) or 1024
        init_h = state.get("height", 768) or 768
        need_scale = (
            actual_w > 0 and actual_h > 0
            and (abs(actual_w - init_w) > 10 or abs(actual_h - init_h) > 10)
        )
        if need_scale:
            sx = actual_w / init_w
            sy = actual_h / init_h

        # Render all shape events
        shapes = self.get_shapes()
        for shape_data in shapes:
            points = shape_data["points"]
            cx = shape_data["center_x"]
            cy = shape_data["center_y"]

            if need_scale:
                points = [
                    [(x * sx, y * sy) for x, y in group]
                    for group in points
                ]
                cx *= sx
                cy *= sy

            event = ShapeDrawn(
                shape_type=shape_data["shape_type"],
                points=points,
                color=shape_data["color"],
                fill=shape_data["fill"],
                center_x=cx,
                center_y=cy,
            )
            await renderer.draw_shape(event)

        return canvas_info

    async def render_and_screenshot(self, renderer: Renderer, path: str,
                                     url: str = "", app: str = "generic") -> str | None:
        """Render and take a screenshot."""
        await self.render(renderer, url=url, app=app)
        return await renderer.screenshot(path)

    # ── Event Sourcing: persistence ───────────────────────────────────

    def save_session(self, path: str | Path) -> None:
        """Save the drawing session (all events) to JSON."""
        self._store.save(path)

    @classmethod
    def load_session(cls, path: str | Path) -> DrawingSkill:
        """Load a drawing session from JSON."""
        store = EventStore.load(path)
        skill = cls(event_store=store)
        skill._command_bus.rebuild_state()
        return skill

    # ── Introspection ─────────────────────────────────────────────────

    @property
    def event_count(self) -> int:
        """Number of events in the store."""
        return self._store.count

    @property
    def event_store(self) -> EventStore:
        """Direct access to the event store (for advanced usage)."""
        return self._store

    @property
    def command_bus(self) -> CommandBus:
        """Direct access to the command bus (for custom handlers)."""
        return self._command_bus

    def __repr__(self) -> str:
        state = self.get_state()
        return (
            f"DrawingSkill(shapes={state['shapes_count']}, "
            f"events={self._store.count}, "
            f"canvas={state['width']}x{state['height']})"
        )
