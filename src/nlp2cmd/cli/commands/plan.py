"""Integration plan command: NL → ExecutionPlanIR → Propact (nlp2cmd runner)."""

from __future__ import annotations

import json
import sys
from typing import Optional

from nlp2cmd.cli.helpers import console
from nlp2cmd.bridge.query_input import attach_query_input


def _require_integration() -> None:
    from nlp2cmd.bridge.integration import integration_enabled

    if not integration_enabled():
        msg = (
            "Integration packages not available. Install with:\n"
            "  pip install -e nlp2cmd[integration]\n"
            "  NLP2CMD_INTEGRATION=1 nlp2cmd plan \"your query\""
        )
        if console:
            console.print(f"[red]{msg}[/red]")
        else:
            print(msg, file=sys.stderr)
        raise SystemExit(2)


def cmd_plan(
    query: str,
    *,
    as_json: bool = False,
    execute: bool = False,
    dry_run: bool = False,
    explain: bool = False,
    verbose: bool = False,
) -> int:
    """Plan query via nlp2dsl integration packages and optionally execute."""
    attach_query_input(query, explain=explain, verbose=verbose)

    _require_integration()

    from nlp2cmd.bridge.integration import plan_query_via_integration
    from nlp2cmd_planner.router import UnsupportedIntentError
    from nlp2cmd_propact.executor import HybridPlanExecutor, execution_route
    from pact_ir import ExecutionPlanIR

    try:
        payload = plan_query_via_integration(query)
    except UnsupportedIntentError as exc:
        if console:
            console.print(f"[red]error:[/red] {exc}")
        else:
            print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        from nlp2cmd_intent import IntentClarificationRequired
        from nlp2cmd.intract.plan_gate import PlanContractViolation

        if isinstance(exc, (IntentClarificationRequired, PlanContractViolation)):
            if console:
                console.print(f"[red]error:[/red] {exc}")
            else:
                print(f"error: {exc}", file=sys.stderr)
            return 2
        raise

    plan = ExecutionPlanIR.model_validate(payload["plan"])
    payload["execution_routes"] = [
        {
            "step": step.id,
            "action": step.action,
            "target_kind": step.target_kind.value,
            "route": execution_route(step),
        }
        for step in plan.steps
    ]

    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    markdown = payload["propact_markdown"]
    print(markdown)

    if explain:
        for route in payload["execution_routes"]:
            line = (
                f"execution_route: {route['step']} -> {route['route']} "
                f"({route['target_kind']}, {route['action']})"
            )
            if console:
                console.print(f"[dim]{line}[/dim]")
            else:
                print(line)

    if execute:
        from pact_ir import IntentIR

        result = HybridPlanExecutor().run(plan, dry_run=dry_run)
        if dry_run and explain:
            hint = "dry-run: validated routes only (no execution)"
            if console:
                console.print(f"[dim]{hint}[/dim]")
            else:
                print(hint)
        elif result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        if execute and not dry_run:
            exit_code = 0 if result.success else 1
            if result.success:
                from nlp2cmd.post_execution.checker import (
                    PostCheckViolation,
                    validate_plan_outputs_if_enabled,
                )

                intent = IntentIR.model_validate(payload["intent_ir"])
                try:
                    post_check = validate_plan_outputs_if_enabled(plan, intent, result)
                except PostCheckViolation as exc:
                    if console:
                        console.print(f"[red]post-check failed:[/red] {exc}")
                    else:
                        print(f"post-check failed: {exc}", file=sys.stderr)
                    return 2
                if post_check is not None:
                    payload["post_check"] = post_check
                    if explain:
                        for step in post_check.get("steps") or []:
                            line = (
                                f"post_check: {step['step_id']} passed={step['passed']} "
                                f"lines={step.get('metadata', {}).get('line_count', '?')}"
                            )
                            if console:
                                console.print(f"[dim]{line}[/dim]")
                            else:
                                print(line)
                    if not post_check.get("passed"):
                        exit_code = 1
            return exit_code

    return 0
