from __future__ import annotations

from unittest.mock import MagicMock

from nlp2cmd.pipeline_runner_plans import PlanExecutionMixin


def test_sanitize_drops_invalid_save_env_and_verify_env_steps():
    steps = [
        {"action": "save_env", "params": {"var_name": "", "value": "x", "file": ".env"}},
        {"action": "verify_env", "params": {"var_name": "UNKNOWN", "file": ".env"}},
        {"action": "save_env", "params": {"var_name": "OPENROUTER_API_KEY", "value": "x", "file": ".env"}},
        {"action": "wait", "params": {"ms": 1}},
    ]

    sanitized = PlanExecutionMixin._sanitize_replacement_steps(steps)

    actions = [s["action"] for s in sanitized]
    assert "wait" in actions
    assert actions.count("save_env") == 1
    assert "verify_env" not in actions
    assert any(s["params"].get("var_name") == "OPENROUTER_API_KEY" for s in sanitized if s["action"] == "save_env")


def test_execute_action_plan_dispatch_passes_pipeline_callbacks(monkeypatch):
    captured = {}

    class _DummyExecutor:
        def __init__(self, **kwargs):
            captured["init_kwargs"] = kwargs

        def execute(self, **kwargs):
            captured["execute_kwargs"] = kwargs
            return "dispatch-result"

    monkeypatch.setattr("nlp2cmd.pipeline_runner_plans.PlanExecutor", _DummyExecutor)

    class _Runner(PlanExecutionMixin):
        headless = False
        video_fmt = None
        video_dir = None

        def _execute_plan_step(self, page, context, step, variables):
            return "step-result"

        @staticmethod
        def _resolve_plan_variables(params, variables):
            return params

        def _execute_desktop_plan_step(self, step, variables):
            return "desktop-result"

    plan = MagicMock()
    plan.steps = []

    result = _Runner().execute_action_plan_dispatch(plan, dry_run=True)

    assert result == "dispatch-result"
    assert captured["init_kwargs"]["execute_step_fn"] is not None
    assert captured["init_kwargs"]["resolve_variables_fn"] is not None
    assert captured["init_kwargs"]["desktop_step_fn"] is not None
    assert captured["execute_kwargs"]["plan"] is plan
    assert captured["execute_kwargs"]["dry_run"] is True
