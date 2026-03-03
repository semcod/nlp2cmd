"""
Event Store — append-only log of drawing events.

Supports persistence to JSON and replay for state reconstruction.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from nlp2cmd.skills.drawing.events import DrawingEvent


class EventStore:
    """
    Append-only event store with optional persistence and subscriber support.

    Usage:
        store = EventStore()
        store.subscribe(lambda e: print(f"Event: {e.event_type}"))
        store.append(ShapeDrawn(shape_type="circle", color="#ff0000"))
        history = store.events  # all events
        store.save("drawing_session.json")
        store2 = EventStore.load("drawing_session.json")
    """

    def __init__(self) -> None:
        self._events: list[DrawingEvent] = []
        self._subscribers: list[Callable[[DrawingEvent], None]] = []

    @property
    def events(self) -> list[DrawingEvent]:
        """All events in chronological order (read-only copy)."""
        return list(self._events)

    @property
    def count(self) -> int:
        return len(self._events)

    def append(self, event: DrawingEvent) -> None:
        """Append an event and notify subscribers."""
        self._events.append(event)
        for subscriber in self._subscribers:
            subscriber(event)

    def subscribe(self, callback: Callable[[DrawingEvent], None]) -> None:
        """Register a subscriber to be notified on every new event."""
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[DrawingEvent], None]) -> None:
        """Remove a subscriber."""
        self._subscribers = [s for s in self._subscribers if s is not callback]

    def replay(self, handler: Callable[[DrawingEvent], None]) -> None:
        """Replay all events through a handler (for state reconstruction)."""
        for event in self._events:
            handler(event)

    def events_since(self, timestamp: float) -> list[DrawingEvent]:
        """Get events after a given timestamp."""
        return [e for e in self._events if e.timestamp > timestamp]

    def events_of_type(self, event_type: str) -> list[DrawingEvent]:
        """Get events of a specific type."""
        return [e for e in self._events if e.event_type.value == event_type]

    def clear(self) -> None:
        """Clear all events (use with caution — breaks event sourcing invariant)."""
        self._events.clear()

    def to_dict(self) -> list[dict[str, Any]]:
        """Serialize all events to a list of dicts."""
        return [e.to_dict() for e in self._events]

    def save(self, path: str | Path) -> None:
        """Persist events to a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: str | Path) -> EventStore:
        """Load events from a JSON file."""
        path = Path(path)
        store = cls()
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                event = DrawingEvent.from_dict(item)
                store._events.append(event)
        return store

    def __len__(self) -> int:
        return len(self._events)

    def __repr__(self) -> str:
        return f"EventStore(events={len(self._events)})"
