"""Re-exports from split engine.py module."""

import json

from nlp2cmd.orchestration.step_status import StepStatus
from nlp2cmd.orchestration.step_def import StepDef
from nlp2cmd.orchestration.step_result import StepResult
from nlp2cmd.orchestration.task_schema import TaskSchema
from nlp2cmd.orchestration.task_result import TaskResult
from nlp2cmd.orchestration.orchestrator import Orchestrator

__all__ = ['StepStatus', 'StepDef', 'StepResult', 'TaskSchema', 'TaskResult', 'Orchestrator']



# ── Helpers ──────────────────────────────────────────────────────────

def _parse_json(text: str) -> dict:
    """Robust JSON extraction from LLM output."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip markdown fences
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        try:
            return json.loads("\n".join(lines))
        except json.JSONDecodeError:
            pass

    # Find first { and match
    start = text.find("{")
    if start >= 0:
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(text)):
            c = text[i]
            if esc:
                esc = False
                continue
            if c == "\\":
                esc = True
                continue
            if c == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    break

    raise ValueError(f"Cannot parse JSON from: {text[:200]}")
