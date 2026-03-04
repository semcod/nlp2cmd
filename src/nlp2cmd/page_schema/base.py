"""Base classes for page schema extraction."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class PageSchema:
    """Schema of actionable elements extracted from a page."""
    buttons: list[dict[str, str]] = field(default_factory=list)
    forms: list[dict[str, str]] = field(default_factory=list)
    radio_buttons: list[dict[str, str]] = field(default_factory=list)
    tokens: list[dict[str, str]] = field(default_factory=list)
    copy_buttons: list[dict[str, str]] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, list[dict[str, str]]]:
        """Convert to dictionary format."""
        return {
            "buttons": self.buttons,
            "forms": self.forms,
            "radio_buttons": self.radio_buttons,
            "tokens": self.tokens,
            "copy_buttons": self.copy_buttons,
        }


class ExtractorBase(Protocol):
    """Base protocol for element extractors."""
    
    def extract(self, page: Any) -> list[dict[str, str]]:
        """Extract elements from the page."""
        ...
    
    def is_available(self, page: Any) -> bool:
        """Check if this extractor can run on the page."""
        return True
