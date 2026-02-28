from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import patch

import pytest

from nlp2cmd.pipeline_runner_plans import PlanExecutionMixin


@dataclass
class _Step:
    action: str
    params: dict


class _FakeLocator:
    def __init__(self) -> None:
        self.clicked = False

    @property
    def first(self):
        return self

    def wait_for(self, **_kw):
        return None

    def click(self, **_kw):
        self.clicked = True
        return None


class _FakePage:
    def __init__(self) -> None:
        self.clicked_text: str | None = None

    def wait_for_load_state(self, *_a, **_kw):
        return None

    def get_by_text(self, text: str, **_kw):
        self.clicked_text = text
        return _FakeLocator()

    def wait_for_selector(self, *_a, **_kw):
        return None

    def click(self, *_a, **_kw):
        raise AssertionError("page.click should not be used when selector is normalized to text")


class _Runner(PlanExecutionMixin):
    pass


def test_click_normalizes_contains_selector_to_text_click():
    runner = _Runner()
    page = _FakePage()
    step = _Step(
        action="click",
        params={"selector": "button:contains('Generate token')", "timeout": 1000, "retries": 1},
    )

    runner._execute_plan_step(page, context=None, step=step, variables={})
    assert page.clicked_text == "Generate token"


def test_check_clipboard_strict_when_key_pattern_provided():
    runner = _Runner()

    class _P:
        pass

    page = _P()  # not used
    step = _Step(
        action="check_clipboard",
        params={"key_pattern": r"hf_[A-Za-z0-9]{34,}", "env_var": "HF_TOKEN"},
    )

    with patch("nlp2cmd.automation.step_validator.StepValidator.get_clipboard", return_value="x" * 5000):
        val = runner._execute_plan_step(page, context=None, step=step, variables={})

    assert val is None
