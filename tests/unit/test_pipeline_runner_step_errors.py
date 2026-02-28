from __future__ import annotations

import pytest


class _DummyPage:
    def __init__(self, *, raise_on: str = "evaluate"):
        self.raise_on = raise_on

    def evaluate(self, _js: str):  # noqa: ANN001
        if self.raise_on == "evaluate":
            raise RuntimeError("boom")
        return None

    def wait_for_timeout(self, _ms: int):  # noqa: ANN001
        return None


class _DummyStep:
    def __init__(self, action: str, params: dict | None = None):
        self.action = action
        self.params = params or {}


def test_execute_plan_step_set_color_raises_on_evaluate_error():
    from nlp2cmd.pipeline_runner import PipelineRunner

    runner = PipelineRunner(headless=True)
    page = _DummyPage()
    step = _DummyStep("set_color", {"color": "#ff0000"})

    with pytest.raises(RuntimeError):
        runner._execute_plan_step(page, None, step, {})


def test_execute_plan_step_draw_filled_circle_raises_on_evaluate_error():
    from nlp2cmd.pipeline_runner import PipelineRunner

    runner = PipelineRunner(headless=True)
    page = _DummyPage()
    step = _DummyStep("draw_filled_circle", {"radius": 10, "offset": [0, 0]})

    with pytest.raises(RuntimeError):
        runner._execute_plan_step(page, None, step, {})
