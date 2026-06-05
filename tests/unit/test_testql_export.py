"""Tests for TestQL scenario export from execution records."""

from __future__ import annotations

from pathlib import Path

import pytest

from nlp2cmd.automation.action_planner import ActionPlan, ActionStep
from nlp2cmd.intract.color_validation import is_valid_hex_color
from nlp2cmd.plan_execution.execution_record import save_execution_artifacts
from nlp2cmd.plan_execution.testql_export import build_testql_scenario_text


@pytest.mark.parametrize(
    ("color", "expected"),
    [
        ("#fff", True),
        ("#FF8040", True),
        ("#ff8040aa", True),
        ("red", False),
        ("#gggggg", False),
        ("808080", False),
    ],
)
def test_is_valid_hex_color(color: str, expected: bool) -> None:
    assert is_valid_hex_color(color) is expected


def test_build_testql_scenario_text_from_record() -> None:
    record = {
        "dom_dql": {
            "url": "https://jspaint.app",
            "query": "narysuj kota",
            "source": "canvas_blueprint",
            "steps": [
                {"action": "navigate", "params": {"url": "https://jspaint.app"}},
                {"action": "draw_filled_circle", "params": {"radius": 10}},
            ],
        },
        "planning": {"query": "narysuj kota", "source": "canvas_blueprint"},
        "execution": {"success": True},
        "artifacts": {"execution_record": "/tmp/action_plan_record_1.record.yaml"},
    }
    text = build_testql_scenario_text(record)
    assert "TYPE: gui" in text
    assert "target_url,  https://jspaint.app" in text
    assert "expected_draw_steps,  1" in text
    assert "GUI_START ${target_url}" in text
    assert "NAVIGATE[1]{path, wait_ms}:" in text


def test_save_execution_artifacts_emits_testql_when_enabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NLP2CMD_EMIT_TESTQL", "1")
    plan = ActionPlan(
        query="narysuj kota",
        source="canvas_blueprint",
        steps=[ActionStep("navigate", {"url": "https://jspaint.app"})],
    )
    artifacts = save_execution_artifacts(plan, output_dir=tmp_path, execution_result={"success": True})
    testql_files = list(tmp_path.glob("*.testql.toon.yaml"))
    assert len(testql_files) == 1
    assert artifacts.to_summary_dict()["testql"] == str(testql_files[0])
    assert "testql" in artifacts.record["integrations"]
    assert "doql" in artifacts.record["integrations"]
