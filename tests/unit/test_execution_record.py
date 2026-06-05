"""Tests for execution artifact persistence."""

from __future__ import annotations

from pathlib import Path

from nlp2cmd.automation.action_planner import ActionPlan, ActionStep
from nlp2cmd.plan_execution.execution_record import (
    build_dom_dsl_payload,
    build_planning_context,
    format_dom_dsl_text,
    save_execution_artifacts,
)


def test_build_dom_dsl_payload_from_canvas_plan():
    plan = ActionPlan(
        query="narysuj kota",
        source="canvas_blueprint",
        confidence=0.95,
        steps=[
            ActionStep("navigate", {"url": "https://jspaint.app"}, "Open"),
            ActionStep("set_color", {"color": "#808080"}, "Gray"),
            ActionStep("draw_filled_circle", {"radius": 45, "offset": [0, -35]}, "Head"),
        ],
    )
    payload = build_dom_dsl_payload(plan)
    assert payload["format"] == "canvas_dql.v1"
    assert payload["url"] == "https://jspaint.app"
    assert len(payload["steps"]) == 3


def test_format_dom_dsl_text_includes_actions():
    plan = ActionPlan(
        query="test",
        source="canvas_blueprint",
        steps=[
            ActionStep("navigate", {"url": "https://jspaint.app"}),
            ActionStep("draw_filled_circle", {"radius": 10}, "dot"),
        ],
    )
    text = format_dom_dsl_text(build_dom_dsl_payload(plan))
    assert "canvas_dql.v1" in text
    assert "draw_filled_circle" in text


def test_save_execution_artifacts_writes_files(tmp_path: Path):
    plan = ActionPlan(
        query="narysuj kota",
        source="canvas_blueprint",
        confidence=0.95,
        steps=[
            ActionStep("navigate", {"url": "https://jspaint.app"}),
            ActionStep("draw_filled_ellipse", {"rx": 80, "ry": 60}, "Body"),
            ActionStep("screenshot", {"suffix": "cat"}),
        ],
    )
    artifacts = save_execution_artifacts(
        plan,
        output_dir=tmp_path,
        execution_result={"success": True, "mode": "playwright"},
    )
    assert artifacts.record_path.exists()
    assert artifacts.dom_dsl_path.exists()
    assert artifacts.dom_dsl_text_path.exists()
    assert artifacts.vql_path.exists()
    summary = artifacts.to_summary_dict()
    assert summary["status"] == "execution_artifacts"
    assert "dom_dsl" in summary
    assert "vql" in summary


def test_planning_context_captures_source():
    plan = ActionPlan(query="q", source="canvas_llm", confidence=0.8, steps=[])
    ctx = build_planning_context(plan)
    assert ctx["source"] == "canvas_llm"
    assert "decision_path" in ctx
    assert "env" in ctx


def test_build_planning_preview():
    from nlp2cmd.plan_execution.execution_record import build_planning_preview

    plan = ActionPlan(
        query="narysuj kota",
        source="canvas_blueprint",
        confidence=0.95,
        steps=[ActionStep("navigate", {"url": "https://jspaint.app"})],
    )
    preview = build_planning_preview(plan)
    assert preview["source"] == "canvas_blueprint"
    assert preview["step_count"] == 1
    assert preview["decision_path"] == ["canvas_decomposition", "canvas_blueprint"]
