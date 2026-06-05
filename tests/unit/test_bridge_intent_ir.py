"""Tests for nlp2cmd ↔ nlp2dsl integration bridge."""

import pytest

from nlp2cmd.generation.keywords import DetectionResult, KeywordIntentDetector


@pytest.fixture
def detector() -> KeywordIntentDetector:
    return KeywordIntentDetector()


def test_detect_intent_ir_shell(detector: KeywordIntentDetector):
    pytest.importorskip("pact_ir")
    pytest.importorskip("nlp2cmd_intent")

    intent = detector.detect_intent_ir("znajdź pliki *.py w src")
    assert intent.intent in {"find", "file_search", "search"}
    assert intent.target_kind.value == "shell"
    assert intent.query == "znajdź pliki *.py w src"


def test_detect_intent_ir_browser(detector: KeywordIntentDetector):
    pytest.importorskip("pact_ir")
    pytest.importorskip("nlp2cmd_intent")

    intent = detector.detect_intent_ir("wejdź na jspaint.app")
    assert intent.target_kind.value == "browser"
    assert intent.intent == "navigate"


def test_plan_query_via_integration():
    pytest.importorskip("nlp2cmd_planner")
    pytest.importorskip("nlp2cmd_propact")

    from nlp2cmd.bridge.integration import plan_query_via_integration

    payload = plan_query_via_integration("znajdź pliki *.py")
    assert "propact_markdown" in payload
    assert "```propact:shell" in payload["propact_markdown"]
    assert payload["intent_ir"]["intent"] in {"find", "file_search", "search"}
    assert payload["intent_ir"]["format"] == "nlp2cmd.intent_ir.v1"
    assert "contract_check" not in payload


def test_plan_query_includes_contract_check_when_gate_enabled(monkeypatch):
    pytest.importorskip("nlp2cmd_planner")
    pytest.importorskip("nlp2cmd_propact")

    monkeypatch.setenv("NLP2CMD_INTRACT_GATE", "1")

    from nlp2cmd.bridge.integration import plan_query_via_integration

    payload = plan_query_via_integration("znajdź pliki *.py")
    assert payload["contract_check"]["passed"] is True
    assert payload["contract_check"]["steps"][0]["contract_id"] == "action.shell_find"
