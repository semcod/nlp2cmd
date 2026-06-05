"""Query input layer: nlp2dsl structure at nlp2cmd entry."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class QueryInputAnalysis:
    query: str
    intent_ir: dict[str, Any] = field(default_factory=dict)
    execution_plan_ir: dict[str, Any] | None = None
    plan_error: str | None = None
    nlp2dsl_workflow: dict[str, Any] | None = None
    source: str = "nlp2cmd_intent"

    @property
    def intent(self) -> str:
        return str(self.intent_ir.get("intent", "unknown"))

    @property
    def target_kind(self) -> str:
        return str(self.intent_ir.get("target_kind", "unknown"))

    @property
    def confidence(self) -> float:
        try:
            return float(self.intent_ir.get("confidence", 0.0))
        except (TypeError, ValueError):
            return 0.0


def query_input_enabled() -> bool:
    flag = os.getenv("NLP2CMD_QUERY_INPUT", "1").strip().lower()
    return flag not in {"0", "false", "no", "off"}


def show_structure_enabled(*, explain: bool = False, verbose: bool = False) -> bool:
    if explain or verbose:
        return True
    return os.getenv("NLP2CMD_SHOW_STRUCTURE", "0").strip().lower() in {"1", "true", "yes", "on"}


def _try_nlp2dsl_workflow(query: str) -> dict[str, Any] | None:
    """Optional: fetch workflow DSL from nlp2dsl backend (invoice-style actions)."""
    try:
        from nlp2cmd_planner.workflow_backend import (
            fetch_workflow_from_text,
            workflow_backend_enabled,
        )
    except ImportError:
        return None

    if not workflow_backend_enabled():
        return None

    payload = fetch_workflow_from_text(query)
    if payload and payload.get("status") in {"complete", "executed"} and payload.get("dsl"):
        return payload
    return None


def analyze_query_input(
    query: str,
    *,
    include_plan: bool = False,
    try_workflow: bool = True,
) -> QueryInputAnalysis:
    """Run nlp2dsl input analysis (IntentIR) for an nlp2cmd query."""
    from nlp2cmd_intent.input import analyze_query

    payload = analyze_query(query, include_plan=include_plan)
    analysis = QueryInputAnalysis(
        query=query,
        intent_ir=payload.get("intent_ir") or {},
        execution_plan_ir=payload.get("execution_plan_ir"),
        plan_error=payload.get("plan_error"),
    )

    low_confidence = analysis.confidence < 0.5 or analysis.intent == "unknown"
    if try_workflow and low_confidence:
        workflow = _try_nlp2dsl_workflow(query)
        if workflow:
            analysis.nlp2dsl_workflow = workflow
            analysis.source = "nlp2dsl_backend"

    return analysis


def display_query_analysis(
    analysis: QueryInputAnalysis,
    *,
    console: Any = None,
    show_plan_hint: bool = False,
) -> None:
    """Print query structure (like nlp2dsl demo 'Analiza tekstu')."""
    lines = [
        f"Analiza tekstu: {analysis.query!r}",
        f"intent={analysis.intent} domain={analysis.intent_ir.get('domain', '?')} "
        f"target={analysis.target_kind} confidence={analysis.confidence:.2f}",
    ]
    if analysis.execution_plan_ir:
        steps = analysis.execution_plan_ir.get("steps") or []
        if steps:
            lines.append(f"plan (integration): {steps[0].get('dsl', steps[0].get('action', ''))}")
    elif show_plan_hint:
        lines.append(
            "plan (integration): n/d — uruchom ./scripts/setup-dev.sh i export NLP2CMD_INTEGRATION=1"
        )
    if analysis.plan_error:
        lines.append(f"plan_error: {analysis.plan_error}")
    if analysis.nlp2dsl_workflow:
        dsl = analysis.nlp2dsl_workflow.get("dsl")
        if dsl:
            lines.append("Wygenerowany DSL (nlp2dsl backend):")
            lines.append(json.dumps(dsl, ensure_ascii=False, indent=2))

    if console is not None:
        for line in lines:
            if line.startswith("{") or line.startswith("["):
                console.print(line)
            elif line.startswith("Wygenerowany"):
                console.print(f"[cyan]{line}[/cyan]")
            elif line.startswith("Analiza"):
                console.print(f"[bold]{line}[/bold]")
            else:
                console.print(f"[dim]{line}[/dim]")
        return

    for line in lines:
        print(line)


def _integration_plan_available() -> bool:
    """True when integration packages are enabled and planner is current."""
    try:
        from nlp2cmd.bridge.integration import integration_enabled

        if not integration_enabled():
            return False
        from nlp2cmd_planner.strategies.rule_shell import _parse_file_search  # noqa: F401

        return True
    except ImportError:
        return False


def attach_query_input(query: str, *, explain: bool = False, verbose: bool = False) -> QueryInputAnalysis | None:
    """Analyze query at nlp2cmd entry; display when configured."""
    if not query_input_enabled():
        return None
    try:
        include_plan = (explain or verbose) and _integration_plan_available()
        analysis = analyze_query_input(query, include_plan=include_plan)
    except ImportError:
        return None

    if show_structure_enabled(explain=explain, verbose=verbose):
        try:
            from nlp2cmd.cli.helpers import console as default_console
        except ImportError:
            default_console = None
        display_query_analysis(
            analysis,
            console=default_console,
            show_plan_hint=(explain or verbose) and not include_plan,
        )

    return analysis
