"""
CQRS Queries — read side of the drawing system.

Queries never mutate state. They reconstruct projections from the event store.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from nlp2cmd.skills.drawing.events import (
    CanvasCleared,
    CanvasInitialized,
    ColorChanged,
    DrawingEvent,
    EventType,
    ShapeDrawn,
    ToolSelected,
)
from nlp2cmd.skills.drawing.event_store import EventStore


# ── Query Protocol ────────────────────────────────────────────────────────

class DrawQuery(ABC):
    """Abstract base for all drawing queries."""

    @abstractmethod
    def execute(self, store: EventStore) -> Any:
        ...


# ── Concrete Queries ──────────────────────────────────────────────────────

@dataclass
class GetCanvasState(DrawQuery):
    """Reconstruct current canvas state from events."""

    def execute(self, store: EventStore) -> dict[str, Any]:
        state = {
            "width": 0,
            "height": 0,
            "url": "",
            "app": "generic",
            "current_color": "#000000",
            "current_tool": "brush",
            "shapes_count": 0,
            "is_blank": True,
        }
        for event in store.events:
            if isinstance(event, CanvasInitialized):
                state["width"] = event.width
                state["height"] = event.height
                state["url"] = event.url
                state["app"] = event.app
            elif isinstance(event, ColorChanged):
                state["current_color"] = event.color
            elif isinstance(event, ToolSelected):
                state["current_tool"] = event.tool
            elif isinstance(event, ShapeDrawn):
                state["shapes_count"] += 1
                state["is_blank"] = False
            elif isinstance(event, CanvasCleared):
                state["shapes_count"] = 0
                state["is_blank"] = True
                state["current_color"] = "#000000"
                state["current_tool"] = "brush"
        return state


@dataclass
class GetDrawingHistory(DrawQuery):
    """Get the full drawing history as a list of event summaries."""

    event_type_filter: str | None = None

    def execute(self, store: EventStore) -> list[dict[str, Any]]:
        events = store.events
        if self.event_type_filter:
            events = store.events_of_type(self.event_type_filter)
        return [
            {
                "event_id": e.event_id,
                "timestamp": e.timestamp,
                "type": e.event_type.value,
                "payload": e.payload,
            }
            for e in events
        ]


@dataclass
class GetShapePoints(DrawQuery):
    """Get all shape point groups from drawn shapes (for rendering)."""

    def execute(self, store: EventStore) -> list[dict[str, Any]]:
        shapes = []
        for event in store.events:
            if isinstance(event, ShapeDrawn):
                shapes.append({
                    "shape_type": event.shape_type,
                    "points": event.points,
                    "color": event.color,
                    "fill": event.fill,
                    "center_x": event.center_x,
                    "center_y": event.center_y,
                })
            elif isinstance(event, CanvasCleared):
                shapes.clear()
        return shapes


@dataclass
class GetLastNShapes(DrawQuery):
    """Get the last N drawn shapes."""

    n: int = 1

    def execute(self, store: EventStore) -> list[dict[str, Any]]:
        all_shapes = GetShapePoints().execute(store)
        return all_shapes[-self.n:] if all_shapes else []


# ── Query Bus ─────────────────────────────────────────────────────────────

class QueryBus:
    """
    Dispatches queries against the event store.

    Usage:
        bus = QueryBus(store)
        state = bus.execute(GetCanvasState())
        history = bus.execute(GetDrawingHistory())
    """

    def __init__(self, store: EventStore) -> None:
        self._store = store

    def execute(self, query: DrawQuery) -> Any:
        return query.execute(self._store)
