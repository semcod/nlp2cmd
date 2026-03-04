"""Base classes for canvas planning."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class CanvasPlanResult:
    """Result of canvas planning."""
    steps: list[dict[str, Any]]
    confidence: float
    source: str
    estimated_time_ms: int
    success: bool = True
    error: str | None = None

    def to_action_steps(self) -> list:
        """Convert to ActionStep objects."""
        try:
            from nlp2cmd.automation.action_planner import ActionStep
            return [
                ActionStep(
                    action=s.get("action", ""),
                    params=s.get("params", {}),
                    description=s.get("description", ""),
                    store_as=s.get("store_as"),
                )
                for s in self.steps
            ]
        except ImportError:
            return []


class CanvasPlannerBase:
    """Base class for canvas planners."""
    
    def __init__(self, ollama_url: str | None = None, model: str | None = None):
        self.ollama_url = ollama_url
        self.model = model
    
    def plan(self, query: str, text: str, canvas_url: str = "https://jspaint.app") -> CanvasPlanResult | None:
        """Generate a drawing plan. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement plan()")
    
    def is_available(self) -> bool:
        """Check if this planner is available (dependencies, etc.)."""
        return True
    
    @staticmethod
    def _extract_object_name(text: str) -> str:
        """Extract object name from drawing query."""
        import re
        obj_match = re.search(
            r"(?:narysuj|rysuj|namaluj|maluj|naszkicuj|draw|paint|sketch)"
            r"\s+(.+?)(?:\s+na\s+|\s+w\s+|\s*$)",
            text,
        )
        object_name = obj_match.group(1).strip() if obj_match else "obiekt"
        # Remove trailing URL fragments
        object_name = re.sub(r"\s*https?://\S+", "", object_name).strip()
        if not object_name:
            object_name = "obiekt"
        return object_name
    
    @staticmethod
    def _extract_canvas_url(text: str, default: str = "https://jspaint.app") -> str:
        """Extract canvas URL from query."""
        import re
        url_match = re.search(
            r'\b([a-zA-Z0-9][\w\-]*\.(?:app|com|io))\b', text,
        )
        return f"https://{url_match.group(1)}" if url_match else default
