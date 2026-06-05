import os

import pytest

import nlp2cmd_intent.keywords as keywords_module
from nlp2cmd.generation.keywords import KeywordIntentDetector


def _empty_find_data_files(*, explicit_path, default_filename, alt_filenames=()):
    return []


def test_keyword_detector_missing_data_non_strict(monkeypatch):
    monkeypatch.delenv("NLP2CMD_STRICT_CONFIG", raising=False)
    monkeypatch.setattr(keywords_module, "find_data_files", _empty_find_data_files)

    detector = KeywordIntentDetector()

    # With missing data files, detector should still work in a limited mode.
    result = detector.detect("Pokaż użytkowników")
    assert result.domain == "unknown"

    # Explicit overrides should still work (not dependent on JSON config/patterns).
    override = detector.detect("pokaż adres ip")
    assert override.domain == "shell"
    assert override.intent == "network"
    assert override.confidence >= 0.9


def test_keyword_detector_missing_data_strict_raises(monkeypatch):
    monkeypatch.setenv("NLP2CMD_STRICT_CONFIG", "1")
    monkeypatch.setattr(keywords_module, "find_data_files", _empty_find_data_files)

    with pytest.raises(FileNotFoundError):
        KeywordIntentDetector()
