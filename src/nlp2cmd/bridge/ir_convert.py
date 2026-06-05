"""Convert pact-ir PlanStep to nlp2cmd ActionIR."""

from __future__ import annotations

from pact_ir import PlanStep, TargetKind

from nlp2cmd.ir import ActionIR, DSLKind


_TARGET_TO_DSL: dict[TargetKind, DSLKind] = {
    TargetKind.SHELL: "shell",
    TargetKind.REST: "http",
    TargetKind.BROWSER: "dom",
    TargetKind.SQL: "sql",
    TargetKind.DESKTOP: "gui",
    TargetKind.MCP: "http",
    TargetKind.WS: "http",
    TargetKind.UNKNOWN: "shell",
}


def plan_step_to_action_ir(
    step: PlanStep,
    *,
    query: str = "",
    confidence: float = 0.0,
) -> ActionIR:
    """Map ExecutionPlanIR step to legacy nlp2cmd ActionIR."""
    dsl_kind = _TARGET_TO_DSL.get(step.target_kind, "shell")
    dsl = step.dsl.strip()
    if not dsl and step.target_kind == TargetKind.SHELL:
        dsl = str(step.params.get("command", "")).strip()

    metadata = dict(step.metadata)
    metadata.setdefault("intent", step.action)
    if step.target_kind == TargetKind.BROWSER:
        metadata.setdefault("dom_action", step.params.get("dom_action", step.action))
        metadata.setdefault("registry_action", step.params.get("registry_action", step.action))

    return ActionIR(
        action_id=step.action,
        dsl=dsl,
        dsl_kind=dsl_kind,
        params=dict(step.params),
        confidence=confidence,
        explanation=step.description or query,
        metadata=metadata,
    )
