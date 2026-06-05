"""Execute ExecutionPlanIR steps via nlp2cmd PipelineRunner."""

from __future__ import annotations

from typing import Any

from nlp2cmd.bridge.ir_convert import plan_step_to_action_ir
from nlp2cmd.pipeline_runner import PipelineRunner


def _runner_stdout(result: Any) -> str:
    data = getattr(result, "data", None) or {}
    if isinstance(data, dict):
        stdout = data.get("stdout")
        if stdout:
            return str(stdout)
    return ""


def run_plan_step(
    step: Any,
    plan: Any,
    *,
    dry_run: bool = False,
    headless: bool = True,
) -> dict[str, Any]:
    """Run a single plan step through nlp2cmd legacy runtime."""
    ir = plan_step_to_action_ir(
        step,
        query=getattr(plan, "query", ""),
        confidence=float(getattr(plan, "confidence", 0.0)),
    )
    runner = PipelineRunner(headless=headless)
    result = runner.run(ir, dry_run=dry_run, confirm=not dry_run)
    return {
        "success": result.success,
        "stdout": _runner_stdout(result),
        "stderr": result.error or "",
        "metadata": {
            "executor": "nlp2cmd",
            "kind": result.kind,
            "duration_ms": result.duration_ms,
            "data": result.data,
        },
    }
