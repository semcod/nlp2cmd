"""Persist reproducible execution artifacts (DOM DSL, VQL, planning context)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nlp2cmd.pipeline_runner_utils import get_timestamp


def _extract_canvas_url(steps: list[Any]) -> str:
    for step in steps:
        action = getattr(step, "action", "") or (step.get("action") if isinstance(step, dict) else "")
        params = getattr(step, "params", None) or (step.get("params") if isinstance(step, dict) else {}) or {}
        if action == "navigate":
            return str(params.get("url") or "https://jspaint.app")
    return "https://jspaint.app"


def _step_to_dict(step: Any) -> dict[str, Any]:
    if hasattr(step, "to_dict"):
        return step.to_dict()
    if isinstance(step, dict):
        return step
    return {
        "action": getattr(step, "action", ""),
        "params": getattr(step, "params", {}) or {},
        "description": getattr(step, "description", ""),
    }


def build_dom_dsl_payload(plan: Any) -> dict[str, Any]:
    """Build canvas_dql.v1 payload from an ActionPlan."""
    steps = getattr(plan, "steps", None) or []
    url = _extract_canvas_url(steps)
    app = "jspaint"
    if "jspaint" in url:
        app = "jspaint"
    return {
        "format": "canvas_dql.v1",
        "query": getattr(plan, "query", ""),
        "app": app,
        "url": url,
        "source": getattr(plan, "source", ""),
        "confidence": getattr(plan, "confidence", 0.0),
        "steps": [_step_to_dict(s) for s in steps],
    }


def execution_record_enabled() -> bool:
    return os.getenv("NLP2CMD_SAVE_EXECUTION_RECORD", "1").strip().lower() in {
        "1", "true", "yes", "on",
    }


def _infer_decision_path(plan: Any) -> list[str]:
    source = str(getattr(plan, "source", "") or "")
    if not source:
        return ["unknown"]
    if source.startswith("canvas_"):
        return ["canvas_decomposition", source]
    if source == "rule_decomposer":
        return ["rule_decomposition"]
    return [source]


def build_planning_context(plan: Any, *, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Capture transparent planning variables for post-hoc analysis."""
    ctx: dict[str, Any] = {
        "query": getattr(plan, "query", ""),
        "source": getattr(plan, "source", ""),
        "confidence": getattr(plan, "confidence", 0.0),
        "estimated_time_ms": getattr(plan, "estimated_time_ms", 0),
        "step_count": len(getattr(plan, "steps", None) or []),
        "env": {
            "LLM_MODEL": os.getenv("LLM_MODEL"),
            "LITELLM_MODEL": os.getenv("LITELLM_MODEL"),
            "NLP2CMD_PLANNER_MODEL": os.getenv("NLP2CMD_PLANNER_MODEL"),
            "CANVAS_MIN_DRAW_STEPS": os.getenv("CANVAS_MIN_DRAW_STEPS", "4"),
            "CANVAS_USE_BLUEPRINTS": os.getenv("CANVAS_USE_BLUEPRINTS", "0"),
            "NLP2CMD_INTRACT_GATE": os.getenv("NLP2CMD_INTRACT_GATE", "0"),
            "NLP2CMD_EMIT_TESTQL": os.getenv("NLP2CMD_EMIT_TESTQL", "0"),
            "OPENROUTER_MODEL": os.getenv("OPENROUTER_MODEL"),
        },
        "decision_path": _infer_decision_path(plan),
    }
    if extra:
        ctx.update(extra)
    return ctx


def build_planning_preview(plan: Any) -> dict[str, Any]:
    """Lightweight planning snapshot for multistep_plan_detected."""
    ctx = build_planning_context(plan)
    return {
        "source": ctx.get("source"),
        "confidence": ctx.get("confidence"),
        "step_count": ctx.get("step_count"),
        "decision_path": ctx.get("decision_path"),
        "model": ctx.get("env", {}).get("LLM_MODEL") or ctx.get("env", {}).get("LITELLM_MODEL"),
    }


def build_vql_program_from_plan(plan: Any):
    """Best-effort VQLProgram from canvas action steps (analysis / replay metadata)."""
    from nlp2cmd.vql.adapters.canvas_to_vql import action_plan_to_vql_program

    return action_plan_to_vql_program(plan)


def format_dom_dsl_text(payload: dict[str, Any]) -> str:
    """Human-readable DOM DSL lines for shell markdown."""
    lines = [
        f"# canvas_dql.v1 query={payload.get('query', '')!r}",
        f"# source={payload.get('source')} confidence={payload.get('confidence')}",
        f"navigate {payload.get('url', '')}",
    ]
    for step in payload.get("steps", []):
        action = step.get("action", "")
        params = step.get("params") or {}
        desc = step.get("description") or action
        if action == "navigate":
            continue
        if not params:
            lines.append(f"{action}  # {desc}")
            continue
        flat = " ".join(f"{k}={json.dumps(v, ensure_ascii=False)}" for k, v in params.items())
        lines.append(f"{action} {flat}  # {desc}")
    return "\n".join(lines)


@dataclass
class ExecutionArtifacts:
    """Paths and inline payloads for a completed plan run."""

    record_path: Path
    dom_dsl_path: Path
    dom_dsl_text_path: Path
    vql_path: Path
    record: dict[str, Any] = field(default_factory=dict)

    def to_summary_dict(self) -> dict[str, Any]:
        artifacts = self.record.get("artifacts", {})
        return {
            "status": "execution_artifacts",
            "execution_record": str(self.record_path),
            "dom_dsl": str(self.dom_dsl_path),
            "dom_dsl_text": str(self.dom_dsl_text_path),
            "vql": str(self.vql_path),
            "screenshot": artifacts.get("screenshot"),
            "video": artifacts.get("video"),
            "testql": artifacts.get("testql"),
            "integrations": self.record.get("integrations"),
            "planning": self.record.get("planning"),
            "execution": self.record.get("execution"),
        }


def save_execution_artifacts(
    plan: Any,
    *,
    output_dir: str | Path,
    execution_result: dict[str, Any] | None = None,
    planning_extra: dict[str, Any] | None = None,
    prefix: str = "action_plan",
) -> ExecutionArtifacts:
    """Write DOM DSL, VQL, and execution record YAML/JSON files."""
    from nlp2cmd.utils.yaml_compat import yaml

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = get_timestamp()
    base = out / f"{prefix}_record_{stamp}"

    dom_payload = build_dom_dsl_payload(plan)
    dom_dsl_path = base.with_suffix(".dom.yaml")
    dom_dsl_text_path = base.with_suffix(".dom.dsl")
    vql_path = base.with_suffix(".vql.yaml")
    record_path = base.with_suffix(".record.yaml")

    dom_dsl_text = format_dom_dsl_text(dom_payload)
    dom_dsl_text_path.write_text(dom_dsl_text + "\n", encoding="utf-8")
    dom_dsl_path.write_text(
        yaml.safe_dump(dom_payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    vql_program = build_vql_program_from_plan(plan)
    vql_payload = {
        "format": "vql.program.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "query": getattr(plan, "query", ""),
        "program": vql_program.to_dict(),
    }
    vql_path.write_text(
        yaml.safe_dump(vql_payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    record = {
        "format": "nlp2cmd.execution_record.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "planning": build_planning_context(plan, extra=planning_extra),
        "execution": execution_result or {},
        "artifacts": {
            "dom_dsl": str(dom_dsl_path),
            "dom_dsl_text": str(dom_dsl_text_path),
            "vql": str(vql_path),
            "execution_record": str(record_path),
            **{
                k: v
                for k, v in (execution_result or {}).items()
                if k in {"screenshot", "video", "mode"}
            },
        },
        "dom_dql": dom_payload,
        "vql": vql_payload,
    }

    from nlp2cmd.plan_execution.testql_export import (
        build_integrations_metadata,
        build_testql_scenario_text,
        testql_export_enabled,
    )

    testql_path = None
    if testql_export_enabled():
        testql_path = base.with_suffix(".testql.toon.yaml")
        testql_path.write_text(build_testql_scenario_text(record), encoding="utf-8")
        record["artifacts"]["testql"] = str(testql_path)

    record["integrations"] = build_integrations_metadata(record, testql_path=testql_path)
    record_path.write_text(
        yaml.safe_dump(record, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    return ExecutionArtifacts(
        record_path=record_path,
        dom_dsl_path=dom_dsl_path,
        dom_dsl_text_path=dom_dsl_text_path,
        vql_path=vql_path,
        record=record,
    )
