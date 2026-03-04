"""Base classes for page analysis."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class FieldInfo:
    """Information about a form field."""
    tag: str = ""
    field_type: str = "text"
    name: str = ""
    field_id: str = ""
    placeholder: str = ""
    aria_label: str = ""
    is_contact: bool = False
    is_junk: bool = False


@dataclass
class PageAnalysisResult:
    """Result of page analysis."""
    url: str = ""
    title: str = ""
    has_form: bool = False
    form_count: int = 0
    contact_field_count: int = 0
    junk_field_count: int = 0
    fields: list[FieldInfo] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    score: float = 0.0
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "title": self.title,
            "has_form": self.has_form,
            "form_count": self.form_count,
            "contact_field_count": self.contact_field_count,
            "junk_field_count": self.junk_field_count,
            "fields": [
                {
                    "tag": f.tag,
                    "type": f.field_type,
                    "name": f.name,
                    "is_contact": f.is_contact,
                    "is_junk": f.is_junk,
                }
                for f in self.fields
            ],
            "links": self.links,
            "score": self.score,
        }
