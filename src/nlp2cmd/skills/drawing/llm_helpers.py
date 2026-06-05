"""Shared LLM helpers for drawing skills."""

from __future__ import annotations

import json
import re
from typing import Any


def get_drawing_router():
    """Lazy-init LLM router for drawing skills."""
    try:
        from nlp2cmd.llm.router import get_router
        return get_router()
    except ImportError:
        return None


def parse_llm_json_object(text: str) -> dict[str, Any] | None:
    """Robustly parse a JSON object from LLM output."""
    clean = text.strip()
    if "```json" in clean:
        clean = clean.split("```json")[1].split("```")[0]
    elif "```" in clean:
        clean = clean.split("```")[1].split("```")[0]

    if not clean.startswith("{"):
        start = clean.find("{")
        end = clean.rfind("}")
        if start >= 0 and end > start:
            clean = clean[start:end + 1]

    try:
        clean = re.sub(r",\s*}", "}", clean)
        clean = re.sub(r",\s*]", "]", clean)
        data = json.loads(clean)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None
