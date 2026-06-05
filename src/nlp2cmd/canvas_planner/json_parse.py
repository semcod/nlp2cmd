"""Parse and salvage JSON step arrays from canvas LLM responses."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

log = logging.getLogger("nlp2cmd.canvas_planner.json_parse")


def clean_llm_json_text(raw: str) -> str:
    """Strip markdown fences and common formatting noise."""
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)
    raw = raw.strip()
    if raw.startswith("```json"):
        raw = raw[7:]
    if raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()
    raw = re.sub(r",(\s*[\}\]])", r"\1", raw)
    return raw


def _salvage_truncated_json_array(text: str) -> list[dict[str, Any]] | None:
    """Recover a usable prefix when the model truncates mid-array."""
    start = text.find("[")
    if start < 0:
        return None

    chunk = text[start:]
    last_obj_end = -1
    depth = 0
    in_string = False
    escape = False

    for i, ch in enumerate(chunk):
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                try:
                    data = json.loads(chunk[: i + 1])
                    if isinstance(data, list) and len(data) >= 2:
                        return data
                except json.JSONDecodeError:
                    pass
        elif ch == "}" and depth == 1:
            last_obj_end = i

    if last_obj_end > 0:
        candidate = chunk[: last_obj_end + 1].rstrip().rstrip(",") + "]"
        try:
            data = json.loads(candidate)
            if isinstance(data, list) and len(data) >= 2:
                log.info("Salvaged truncated canvas LLM JSON (%d steps)", len(data))
                return data
        except json.JSONDecodeError:
            pass

    return None


def parse_canvas_steps_json(raw: str, *, min_steps: int = 2) -> list[dict[str, Any]] | None:
    """Parse a canvas LLM response into a list of step dicts."""
    cleaned = clean_llm_json_text(raw)
    if not cleaned:
        return None

    try:
        steps_data = json.loads(cleaned)
        if isinstance(steps_data, list) and len(steps_data) >= min_steps:
            return steps_data
    except json.JSONDecodeError:
        pass

    salvaged = _salvage_truncated_json_array(cleaned)
    if salvaged and len(salvaged) >= min_steps:
        return salvaged

    log.warning("Failed to parse canvas LLM JSON response")
    return None
