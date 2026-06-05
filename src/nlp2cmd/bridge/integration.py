"""High-level integration: NL query → IntentIR → ExecutionPlanIR → Propact markdown."""

from __future__ import annotations

from typing import Any


def plan_query_via_integration(query: str) -> dict[str, Any]:
    """
    Run nlp2dsl integration pipeline when packages are installed.

    Returns dict with intent_ir, plan, and propact markdown.
    """
    from nlp2cmd_intent import IntentPipeline, ensure_intent_clear
    from nlp2cmd_planner import PlanningPipeline
    from nlp2cmd_propact import plan_to_propact_markdown

    intent_pipeline = IntentPipeline()
    intent = intent_pipeline.run(query)
    ensure_intent_clear(intent, enforced=True)
    plan = PlanningPipeline(intent_pipeline=intent_pipeline).run(query)

    payload: dict[str, Any] = {
        "intent_ir": intent.model_dump(mode="json"),
        "plan": plan.model_dump(mode="json"),
        "propact_markdown": plan_to_propact_markdown(plan),
    }

    from nlp2cmd.intract.plan_gate import validate_plan_contracts_if_enabled

    contract_check = validate_plan_contracts_if_enabled(plan, intent)
    if contract_check is not None:
        payload["contract_check"] = contract_check
        if not contract_check["passed"]:
            from nlp2cmd.intract.plan_gate import PlanContractViolation

            raise PlanContractViolation(contract_check["steps"])

    return payload


def integration_enabled() -> bool:
    import os

    if os.getenv("NLP2CMD_INTEGRATION", "0").strip().lower() not in {"1", "true", "yes", "on"}:
        return False
    try:
        import pact_ir  # noqa: F401
        import nlp2cmd_planner  # noqa: F401
        import nlp2cmd_propact  # noqa: F401

        return True
    except ImportError:
        return False
