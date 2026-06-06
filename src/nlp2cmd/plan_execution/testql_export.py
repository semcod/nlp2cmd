"""Convert nlp2cmd execution records into TestQL TestTOON scenarios."""

from __future__ import annotations

import json
import os
import platform
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    from testql.export.scenario_builder import ScenarioBuilder
except ImportError:
    ScenarioBuilder = None  # type: ignore[misc, assignment]


def testql_export_enabled() -> bool:
    return os.getenv("NLP2CMD_EMIT_TESTQL", "0").strip().lower() in {
        "1", "true", "yes", "on",
    }


def _csv_cell(value: Any) -> str:
    text = str(value if value is not None else "-").strip()
    return text.replace(",", ";") or "-"


def _count_draw_steps(steps: list[dict[str, Any]]) -> int:
    return sum(
        1
        for step in steps
        if str(step.get("action", "")).startswith("draw_")
        or step.get("action") in {"fill_at", "click_canvas"}
    )


def _detect_environment(record: dict[str, Any]) -> dict[str, str]:
    dom = record.get("dom_dql") or {}
    planning = record.get("planning") or {}
    session = os.environ.get("XDG_SESSION_TYPE", "").strip().lower()
    display = "wayland" if session == "wayland" or os.environ.get("WAYLAND_DISPLAY") else "x11"
    app = str(dom.get("app") or "browser")
    return {
        "os": platform.system().lower(),
        "os_release": platform.release(),
        "session": session or display,
        "display": display,
        "browser.engine": "chromium",
        "browser.headless": os.environ.get("NLP2CMD_HEADLESS", "true"),
        "app.type": "canvas" if app == "jspaint" else "web",
        "app.id": app,
        "runtime.source": "nlp2cmd",
        "runtime.planner": _csv_cell(planning.get("source")),
    }


def _map_dom_step_to_gui_row(step: dict[str, Any]) -> dict[str, Any] | None:
    action = str(step.get("action") or "").strip().lower()
    params = step.get("params") or {}
    if action == "navigate":
        return {"action": "navigate", "selector": "-", "value": params.get("url"), "wait_ms": 1500}
    if action == "click":
        return {
            "action": "click",
            "selector": params.get("selector") or params.get("text") or "body",
            "value": "-",
            "wait_ms": 500,
        }
    if action in {"type_text", "fill", "input"}:
        return {
            "action": "input",
            "selector": params.get("selector") or "input",
            "value": params.get("text") or params.get("value") or "",
            "wait_ms": 300,
        }
    if action in {"wait", "sleep"}:
        return {"action": "log", "selector": "wait", "value": params.get("ms", 500), "wait_ms": params.get("ms", 500)}
    return None


def _map_dom_step_to_flow_row(step: dict[str, Any]) -> dict[str, Any]:
    action = str(step.get("action") or "").strip()
    params = step.get("params") or {}
    if action.startswith("draw_") or action in {"fill_at", "click_canvas", "select_tool"}:
        return {
            "command": "LOG",
            "target": action,
            "value": json.dumps(params, ensure_ascii=False),
        }
    return {"command": action.upper() or "LOG", "target": "-", "value": json.dumps(params, ensure_ascii=False)}


def build_testql_scenario_text(record: dict[str, Any]) -> str:
    """Build TestTOON scenario with environment profile + replay steps."""
    dom = record.get("dom_dql") or {}
    planning = record.get("planning") or {}
    execution = record.get("execution") or {}
    artifacts = record.get("artifacts") or {}

    url = str(dom.get("url") or "https://jspaint.app")
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else url
    steps = dom.get("steps") or []
    draw_steps = _count_draw_steps(steps)
    dom_dsl_text = artifacts.get("dom_dsl_text") or artifacts.get("dom_dsl") or ""

    if ScenarioBuilder is not None:
        builder = (
            ScenarioBuilder(
                name="nlp2cmd-replay-from-execution-record",
                scenario_type="gui" if draw_steps else "e2e",
                meta={"SOURCE": "nlp2cmd.execution_record.v1"},
            )
            .environment(_detect_environment(record))
            .config({
                "target_url": base_url,
                "browser.base_url": base_url,
                "nlp2cmd_query": _csv_cell(dom.get("query") or planning.get("query")),
                "nlp2cmd_source": _csv_cell(dom.get("source") or planning.get("source")),
                "expected_draw_steps": str(draw_steps),
                "execution_success": "true" if execution.get("success") else "false",
                "source_record": _csv_cell(artifacts.get("execution_record")),
                "dom_dsl_text": _csv_cell(dom_dsl_text),
            })
        )

        gui_rows: list[dict[str, Any]] = []
        flow_rows: list[dict[str, Any]] = []
        for step in steps:
            if str(step.get("action")) == "navigate":
                continue
            gui_row = _map_dom_step_to_gui_row(step)
            if gui_row and gui_row.get("action") != "log":
                gui_rows.append(gui_row)
            else:
                flow_rows.append(_map_dom_step_to_flow_row(step))

        builder.commands([f"GUI_START ${'{'}target_url{'}'}", "CONTEXT_DETECT source=nlp2cmd"])
        if gui_rows:
            builder.gui(gui_rows)
        if flow_rows:
            builder.flow(flow_rows)
        if dom_dsl_text:
            builder.shell([f"test -f {dom_dsl_text} || test -f ${{source_record}}"], exit_code=0)
        builder.commands(["GUI_STOP"])
        return builder.build()

    return _legacy_build_testql_scenario_text(record)


def _legacy_build_testql_scenario_text(record: dict[str, Any]) -> str:
    """Fallback when testql is not installed."""
    dom = record.get("dom_dql") or {}
    planning = record.get("planning") or {}
    execution = record.get("execution") or {}
    artifacts = record.get("artifacts") or {}
    url = str(dom.get("url") or "https://jspaint.app")
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else url
    draw_steps = _count_draw_steps(dom.get("steps") or [])
    env = _detect_environment(record)
    env_lines = "\n".join(f"  {k},  {v}" for k, v in env.items())
    return f"""# SCENARIO: nlp2cmd-replay-from-execution-record
# TYPE: gui
# VERSION: 1.0
# SOURCE: nlp2cmd.execution_record.v1

ENVIRONMENT[{len(env)}]{{key, value}}:
{env_lines}

CONFIG[6]{{key, value}}:
  target_url,  {base_url}
  browser.base_url,  {base_url}
  nlp2cmd_query,  {_csv_cell(dom.get('query') or planning.get('query'))}
  nlp2cmd_source,  {_csv_cell(dom.get('source') or planning.get('source'))}
  expected_draw_steps,  {draw_steps}
  execution_success,  {'true' if execution.get('success') else 'false'}

COMMANDS[2]{{command}}:
  GUI_START ${{target_url}}
  GUI_STOP
"""


def build_integrations_metadata(
    record: dict[str, Any],
    *,
    testql_path: Path | None = None,
) -> dict[str, Any]:
    """Sidecar metadata for DOQL/TestQL tooling."""
    dom = record.get("dom_dql") or {}
    url = str(dom.get("url") or "")
    meta: dict[str, Any] = {
        "doql": {
            "adopt_command": "doql adopt . --format less --output app.doql.less --force",
            "echo_command": "testql echo --toon-path ./recordings --doql-path app.doql.less",
        },
        "testql": {
            "direct_run": f"testql run {testql_path} --url {url or '${{TARGET_URL}}'}" if testql_path else None,
            "dry_run": f"testql run {testql_path} --dry-run" if testql_path else None,
        },
    }
    if testql_path is not None:
        meta["testql"]["scenario"] = str(testql_path)
        meta["testql"]["run_command"] = f"testql run {testql_path} --url {url or '${{TARGET_URL}}'}"
    return meta
