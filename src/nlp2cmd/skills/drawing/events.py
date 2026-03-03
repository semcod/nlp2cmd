"""
Drawing events — Event Sourcing building blocks.

Every state change in the drawing system is captured as an immutable event.
Events are append-only and can be replayed to reconstruct canvas state.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EventType(str, Enum):
    CANVAS_INITIALIZED = "canvas_initialized"
    CANVAS_CLEARED = "canvas_cleared"
    SHAPE_DRAWN = "shape_drawn"
    COLOR_CHANGED = "color_changed"
    TOOL_SELECTED = "tool_selected"


@dataclass(frozen=True)
class DrawingEvent:
    """Base immutable event — all drawing events inherit from this."""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    event_type: EventType = EventType.CANVAS_INITIALIZED
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type.value,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DrawingEvent:
        et = EventType(data["event_type"])
        factory = _EVENT_FACTORIES.get(et, cls)
        return factory(
            event_id=data.get("event_id", str(uuid.uuid4())),
            timestamp=data.get("timestamp", time.time()),
            **data.get("payload", {}),
        )


@dataclass(frozen=True)
class CanvasInitialized(DrawingEvent):
    """Fired when a canvas is created or discovered."""

    width: float = 1024
    height: float = 768
    url: str = ""
    app: str = "generic"

    def __post_init__(self):
        object.__setattr__(self, "event_type", EventType.CANVAS_INITIALIZED)
        object.__setattr__(self, "payload", {
            "width": self.width,
            "height": self.height,
            "url": self.url,
            "app": self.app,
        })


@dataclass(frozen=True)
class CanvasCleared(DrawingEvent):
    """Fired when the canvas is cleared."""

    def __post_init__(self):
        object.__setattr__(self, "event_type", EventType.CANVAS_CLEARED)
        object.__setattr__(self, "payload", {})


@dataclass(frozen=True)
class ShapeDrawn(DrawingEvent):
    """Fired when a shape is drawn on the canvas."""

    shape_type: str = "circle"
    points: list[list[tuple[float, float]]] = field(default_factory=list)
    color: str = "#000000"
    fill: bool = False
    center_x: float = 0.0
    center_y: float = 0.0
    params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(self, "event_type", EventType.SHAPE_DRAWN)
        object.__setattr__(self, "payload", {
            "shape_type": self.shape_type,
            "points": self.points,
            "color": self.color,
            "fill": self.fill,
            "center_x": self.center_x,
            "center_y": self.center_y,
            "params": self.params,
        })


@dataclass(frozen=True)
class ColorChanged(DrawingEvent):
    """Fired when the active drawing color is changed."""

    color: str = "#000000"
    previous_color: str = ""

    def __post_init__(self):
        object.__setattr__(self, "event_type", EventType.COLOR_CHANGED)
        object.__setattr__(self, "payload", {
            "color": self.color,
            "previous_color": self.previous_color,
        })


@dataclass(frozen=True)
class ToolSelected(DrawingEvent):
    """Fired when a drawing tool is selected."""

    tool: str = "brush"
    previous_tool: str = ""

    def __post_init__(self):
        object.__setattr__(self, "event_type", EventType.TOOL_SELECTED)
        object.__setattr__(self, "payload", {
            "tool": self.tool,
            "previous_tool": self.previous_tool,
        })


_EVENT_FACTORIES: dict[EventType, type] = {
    EventType.CANVAS_INITIALIZED: CanvasInitialized,
    EventType.CANVAS_CLEARED: CanvasCleared,
    EventType.SHAPE_DRAWN: ShapeDrawn,
    EventType.COLOR_CHANGED: ColorChanged,
    EventType.TOOL_SELECTED: ToolSelected,
}
