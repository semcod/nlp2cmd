"""
CQRS Commands — write side of the drawing system.

Commands represent user intentions that mutate state.
Each command is handled by the CommandBus which validates,
executes, and emits corresponding events to the EventStore.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from nlp2cmd.skills.drawing.events import (
    CanvasCleared,
    CanvasInitialized,
    ColorChanged,
    DrawingEvent,
    ShapeDrawn,
    ToolSelected,
)
from nlp2cmd.skills.drawing.event_store import EventStore


# ── Command Protocol ──────────────────────────────────────────────────────

class DrawCommand(ABC):
    """Abstract base for all drawing commands."""

    @abstractmethod
    def validate(self) -> list[str]:
        """Return list of validation errors (empty = valid)."""
        ...


# ── Concrete Commands ─────────────────────────────────────────────────────

@dataclass
class InitCanvas(DrawCommand):
    """Initialize a drawing canvas."""
    width: float = 1024
    height: float = 768
    url: str = ""
    app: str = "generic"

    def validate(self) -> list[str]:
        errors = []
        if self.width <= 0:
            errors.append("width must be positive")
        if self.height <= 0:
            errors.append("height must be positive")
        return errors


@dataclass
class DrawShape(DrawCommand):
    """Draw a shape on the canvas."""
    shape_type: str = "circle"
    color: str = "#000000"
    fill: bool = False
    center_x: float = 0.0
    center_y: float = 0.0
    params: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        errors = []
        if not self.shape_type:
            errors.append("shape_type is required")
        return errors


@dataclass
class SetColor(DrawCommand):
    """Change the active drawing color."""
    color: str = "#000000"

    def validate(self) -> list[str]:
        if not self.color:
            return ["color is required"]
        return []


@dataclass
class SelectTool(DrawCommand):
    """Select a drawing tool."""
    tool: str = "brush"

    def validate(self) -> list[str]:
        if not self.tool:
            return ["tool name is required"]
        return []


@dataclass
class ClearCanvas(DrawCommand):
    """Clear the entire canvas."""

    def validate(self) -> list[str]:
        return []


# ── Command Handler Protocol ──────────────────────────────────────────────

class CommandHandler(Protocol):
    """Protocol for command handlers."""

    def __call__(self, command: DrawCommand, store: EventStore, state: dict[str, Any]) -> DrawingEvent:
        ...


# ── Command Bus ───────────────────────────────────────────────────────────

class CommandBus:
    """
    Dispatches commands to handlers, validates, and emits events.

    Follows the Mediator pattern — commands are routed to registered handlers.
    Each handler produces an event that is appended to the EventStore.

    Usage:
        bus = CommandBus(store)
        bus.dispatch(DrawShape(shape_type="circle", color="#ff0000"))
        bus.dispatch(SetColor(color="#00ff00"))
    """

    def __init__(self, store: EventStore) -> None:
        self._store = store
        self._state: dict[str, Any] = {
            "current_color": "#000000",
            "current_tool": "brush",
            "canvas_width": 0,
            "canvas_height": 0,
            "canvas_url": "",
            "canvas_app": "generic",
        }
        self._handlers: dict[type, Callable] = {
            InitCanvas: self._handle_init_canvas,
            DrawShape: self._handle_draw_shape,
            SetColor: self._handle_set_color,
            SelectTool: self._handle_select_tool,
            ClearCanvas: self._handle_clear_canvas,
        }
        self._pre_hooks: list[Callable[[DrawCommand], None]] = []
        self._post_hooks: list[Callable[[DrawCommand, DrawingEvent], None]] = []

    @property
    def state(self) -> dict[str, Any]:
        """Current canvas state (read-only copy)."""
        return dict(self._state)

    def register_handler(self, command_type: type, handler: Callable) -> None:
        """Register a custom command handler (Open/Closed Principle)."""
        self._handlers[command_type] = handler

    def add_pre_hook(self, hook: Callable[[DrawCommand], None]) -> None:
        """Add a pre-dispatch hook (e.g., logging, validation)."""
        self._pre_hooks.append(hook)

    def add_post_hook(self, hook: Callable[[DrawCommand, DrawingEvent], None]) -> None:
        """Add a post-dispatch hook (e.g., rendering trigger)."""
        self._post_hooks.append(hook)

    def dispatch(self, command: DrawCommand) -> DrawingEvent:
        """
        Validate and dispatch a command, returning the emitted event.

        Raises:
            ValueError: If command validation fails.
            TypeError: If no handler is registered for the command type.
        """
        errors = command.validate()
        if errors:
            raise ValueError(f"Command validation failed: {'; '.join(errors)}")

        handler = self._handlers.get(type(command))
        if handler is None:
            raise TypeError(f"No handler registered for {type(command).__name__}")

        for hook in self._pre_hooks:
            hook(command)

        event = handler(command)
        self._store.append(event)

        for hook in self._post_hooks:
            hook(command, event)

        return event

    def rebuild_state(self) -> None:
        """Rebuild state from event store (event sourcing replay)."""
        self._state = {
            "current_color": "#000000",
            "current_tool": "brush",
            "canvas_width": 0,
            "canvas_height": 0,
            "canvas_url": "",
            "canvas_app": "generic",
        }
        self._store.replay(self._apply_event)

    def _apply_event(self, event: DrawingEvent) -> None:
        """Apply a single event to update internal state."""
        p = event.payload
        if isinstance(event, CanvasInitialized):
            self._state["canvas_width"] = p.get("width", 0)
            self._state["canvas_height"] = p.get("height", 0)
            self._state["canvas_url"] = p.get("url", "")
            self._state["canvas_app"] = p.get("app", "generic")
        elif isinstance(event, ColorChanged):
            self._state["current_color"] = p.get("color", "#000000")
        elif isinstance(event, ToolSelected):
            self._state["current_tool"] = p.get("tool", "brush")
        elif isinstance(event, CanvasCleared):
            self._state["current_color"] = "#000000"
            self._state["current_tool"] = "brush"

    # ── Built-in Handlers ─────────────────────────────────────────────

    def _handle_init_canvas(self, cmd: InitCanvas) -> CanvasInitialized:
        event = CanvasInitialized(
            width=cmd.width, height=cmd.height,
            url=cmd.url, app=cmd.app,
        )
        self._apply_event(event)
        return event

    def _handle_draw_shape(self, cmd: DrawShape) -> ShapeDrawn:
        from nlp2cmd.skills.drawing.shapes import ShapeRegistry

        # Generate points via registry
        cx = cmd.center_x or self._state["canvas_width"] / 2
        cy = cmd.center_y or self._state["canvas_height"] / 2
        size = cmd.params.get("size", min(cx, cy) * 0.5) if cx > 0 else 150

        generator = ShapeRegistry.get(cmd.shape_type)
        params_without_size = {k: v for k, v in cmd.params.items() if k != "size"}
        points = generator.generate(cx, cy, size, **params_without_size)

        event = ShapeDrawn(
            shape_type=cmd.shape_type,
            points=points,
            color=cmd.color or self._state["current_color"],
            fill=cmd.fill,
            center_x=cx,
            center_y=cy,
            params=cmd.params,
        )
        return event

    def _handle_set_color(self, cmd: SetColor) -> ColorChanged:
        prev = self._state["current_color"]
        event = ColorChanged(color=cmd.color, previous_color=prev)
        self._apply_event(event)
        return event

    def _handle_select_tool(self, cmd: SelectTool) -> ToolSelected:
        prev = self._state["current_tool"]
        event = ToolSelected(tool=cmd.tool, previous_tool=prev)
        self._apply_event(event)
        return event

    def _handle_clear_canvas(self, cmd: ClearCanvas) -> CanvasCleared:
        event = CanvasCleared()
        self._apply_event(event)
        return event
