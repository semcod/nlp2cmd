"""Tests for nlp2dsl query input at nlp2cmd entry."""

import pytest


def test_analyze_query_input_shell():
    pytest.importorskip("nlp2cmd_intent")

    from nlp2cmd.bridge.query_input import analyze_query_input

    analysis = analyze_query_input("znajdź pliki *.py w src")
    assert analysis.intent in {"find", "file_search", "search"}
    assert analysis.target_kind == "shell"
    assert analysis.intent_ir["format"] == "nlp2cmd.intent_ir.v1"


def test_attach_query_input_respects_disable(monkeypatch, capsys):
    pytest.importorskip("nlp2cmd_intent")
    monkeypatch.setenv("NLP2CMD_QUERY_INPUT", "0")

    from nlp2cmd.bridge.query_input import attach_query_input

    assert attach_query_input("test query", verbose=True) is None
    assert capsys.readouterr().out == ""


def test_display_query_analysis(capsys):
    from nlp2cmd.bridge.query_input import QueryInputAnalysis, display_query_analysis

    display_query_analysis(
        QueryInputAnalysis(
            query="znajdź pliki",
            intent_ir={"intent": "find", "domain": "shell", "target_kind": "shell", "confidence": 0.9},
        )
    )
    out = capsys.readouterr().out
    assert "Analiza tekstu" in out
    assert "intent=find" in out
