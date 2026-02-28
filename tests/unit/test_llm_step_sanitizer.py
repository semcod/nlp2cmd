from __future__ import annotations

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
