"""Convert nlp2cmd execution records into TestQL TestTOON scenarios."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


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


def build_testql_scenario_text(record: dict[str, Any]) -> str:
    """Build a minimal GUI smoke TestTOON scenario from execution_record.v1."""
    dom = record.get("dom_dql") or {}
    planning = record.get("planning") or {}
    execution = record.get("execution") or {}
    artifacts = record.get("artifacts") or {}

    url = str(dom.get("url") or "https://jspaint.app")
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else url
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    query = _csv_cell(dom.get("query") or planning.get("query") or "")
    source = _csv_cell(dom.get("source") or planning.get("source") or "")
    record_path = _csv_cell(artifacts.get("execution_record") or "")
    draw_steps = _count_draw_steps(dom.get("steps") or [])
    success = "true" if execution.get("success") else "false"
    screenshot = _csv_cell(artifacts.get("screenshot") or "-")

    config_rows = [
        ("target_url", base_url),
        ("browser.base_url", base_url),
        ("browser.engine", "chromium"),
        ("browser.headless", "true"),
        ("nlp2cmd_query", query),
        ("nlp2cmd_source", source),
        ("expected_draw_steps", str(draw_steps)),
        ("execution_success", success),
        ("source_record", record_path),
    ]
    if screenshot != "-":
        config_rows.append(("screenshot_path", screenshot))

    config_lines = "\n".join(
        f"  {key},  {value}" for key, value in config_rows
    )

    return f"""# SCENARIO: nlp2cmd-replay-from-execution-record
# TYPE: gui
# VERSION: 1.0
# SOURCE: nlp2cmd.execution_record.v1
# DOQL: doql adopt . --format less --output app.doql.less --force

CONFIG[{len(config_rows)}]{{key, value}}:
{config_lines}

COMMANDS[1]{{command}}:
  GUI_START ${{target_url}}

NAVIGATE[1]{{path, wait_ms}}:
  /,  2000

WAIT[1]{{ms}}:
  500

COMMANDS[1]{{command}}:
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
    }
    if testql_path is not None:
        meta["testql"] = {
            "scenario": str(testql_path),
            "run_command": f"testql run {testql_path} --url {url or '${{TARGET_URL}}'}",
            "generate_from_page_command": (
                f"testql generate-from-page {url} -o recordings/smoke.testql.toon.yaml"
                if url
                else None
            ),
        }
    return meta
