"""
Single-query generation mode for NLP2CMD CLI.

Fast path for `nlp2cmd -q "..."` without --run.
Avoids spinning up the full InteractiveSession (env scan + thermo router).
"""

from __future__ import annotations

import os
import sys
import time
from contextlib import nullcontext
from pathlib import Path
from typing import Any, Optional

from nlp2cmd.cli.helpers import (
    console,
    display_command_result,
    print_yaml_block,
)


def handle_generate_query(
    query: str,
    *,
    dsl: str,
    appspec: Optional[Path],
    explain: bool,
    execute_web: bool,
    stdout_only: bool,
    script_start_time: float,
) -> None:
    """Handle single-query generation (no --run, dsl=auto fast path)."""
    from nlp2cmd.generation.pipeline import RuleBasedPipeline
    from nlp2cmd.monitoring import measure_resources, format_last_metrics

    pipeline = RuleBasedPipeline()
    _measure = str(os.environ.get("NLP2CMD_MEASURE_RESOURCES", "1") or "").strip().lower() not in {
        "0",
        "false",
        "no",
        "n",
        "off",
    }
    with (measure_resources() if _measure else nullcontext()):
        pipeline_result = pipeline.process(query)

    if stdout_only:
        cmd = (pipeline_result.command or "").strip()
        if cmd:
            sys.stdout.write(cmd + "\n")
        if not pipeline_result.success:
            for err in list(pipeline_result.errors or []):
                sys.stderr.write(str(err).rstrip() + "\n")
        return

    metrics_str = format_last_metrics() if _measure else ""
    out: dict[str, Any] = {
        "dsl": "auto",
        "query": query,
        "status": "success" if pipeline_result.success else "error",
        "confidence": float(pipeline_result.confidence),
        "generated_command": (pipeline_result.command or "").strip() or None,
        "errors": list(pipeline_result.errors or []),
        "warnings": list(pipeline_result.warnings or []),
        "suggestions": [],
        "clarification_questions": [],
    }

    pipeline_meta = getattr(pipeline_result, "metadata", None)
    if isinstance(pipeline_meta, dict) and pipeline_meta:
        out.update(pipeline_meta)
    if metrics_str:
        try:
            from nlp2cmd.monitoring.token_costs import parse_metrics_string
            from nlp2cmd.monitoring import estimate_token_cost

            metrics = parse_metrics_string(metrics_str)
            if metrics:
                out["resource_metrics"] = {
                    "time_ms": metrics.get("time_ms"),
                    "cpu_percent": metrics.get("cpu_percent"),
                    "memory_mb": metrics.get("memory_mb"),
                    "energy_mj": metrics.get("energy_mj"),
                }
                out["resource_metrics_parsed"] = metrics

                if (
                    metrics.get("time_ms") is not None
                    and metrics.get("cpu_percent") is not None
                    and metrics.get("memory_mb") is not None
                ):
                    token_estimate = estimate_token_cost(
                        metrics["time_ms"],
                        metrics["cpu_percent"],
                        metrics["memory_mb"],
                        metrics.get("energy_mj"),
                    )
                    out["token_estimate"] = {
                        "total": int(token_estimate.total_tokens_estimate),
                        "input": int(token_estimate.input_tokens_estimate),
                        "output": int(token_estimate.output_tokens_estimate),
                        "cost_usd": float(token_estimate.estimated_cost_usd),
                        "model_tier": token_estimate.equivalent_model_tier,
                        "tokens_per_ms": float(token_estimate.tokens_per_millisecond),
                        "tokens_per_mj": float(token_estimate.tokens_per_mj),
                    }
        except Exception:
            pass

    if explain:
        out.update(
            {
                "domain": pipeline_result.domain,
                "intent": pipeline_result.intent,
                "detection_confidence": pipeline_result.detection_confidence,
                "template_used": pipeline_result.template_used,
                "source": pipeline_result.source,
                "entities": pipeline_result.entities,
            }
        )

    # Calculate total execution time
    total_time_ms = (time.time() - script_start_time) * 1000
    
    # Add total execution time to output
    out["total_execution_time_ms"] = round(total_time_ms, 1)
    
    display_command_result(
        command=out.get("generated_command", "") or "",
        metadata=out,
        metrics_str=metrics_str,
        show_yaml=True,
        title="NLP2CMD Result",
    )
    
    if execute_web and dsl == "browser":
        try:
            from nlp2cmd import NLP2CMD
            from nlp2cmd.adapters import BrowserAdapter
            from nlp2cmd.pipeline_runner import PipelineRunner

            adapter = BrowserAdapter()
            nlp = NLP2CMD(adapter=adapter)
            ir = nlp.transform_ir(query)
            runner = PipelineRunner(headless=False)
            res = runner.run(ir, dry_run=False, confirm=True)
            if res.success:
                console.print(f"\n✅ Opened URL via Playwright in {res.duration_ms:.1f}ms")
            else:
                console.print(f"\n❌ Playwright execution failed: {res.error}")
        except Exception as e:
            console.print(f"\n❌ Playwright execution error: {e}")


def handle_appspec_query(
    query: str,
    *,
    dsl: str,
    appspec: Optional[Path],
    auto_repair: bool,
    explain: bool,
    execute_web: bool,
) -> None:
    """Handle single-query generation for appspec DSL."""
    from nlp2cmd.cli.commands.interactive import InteractiveSession

    session = InteractiveSession(
        dsl=dsl,
        auto_repair=auto_repair,
        appspec=str(appspec) if appspec else None,
    )
    feedback = session.process(query)
    session.display_feedback(feedback, include_explanation=explain)
    
    if execute_web:
        try:
            from nlp2cmd import NLP2CMD
            from nlp2cmd.adapters import AppSpecAdapter
            from nlp2cmd.pipeline_runner import PipelineRunner

            adapter = AppSpecAdapter(appspec_path=str(appspec))
            nlp = NLP2CMD(adapter=adapter)
            ir = nlp.transform_ir(query)
            runner = PipelineRunner(headless=False)
            res = runner.run(ir, dry_run=False, confirm=True)
            if res.success:
                console.print(f"\n✅ Executed web action in {res.duration_ms:.1f}ms")
            else:
                console.print(f"\n❌ Web execution failed: {res.error}")
        except Exception as e:
            console.print(f"\n❌ Web execution error: {e}")
