from __future__ import annotations

from dataclasses import dataclass

import pytest


@dataclass
class _FakeExtractionResult:
    entities: dict


def test_rule_based_pipeline_captures_shadow_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NLP2CMD_ENTITY_EXTRACTOR_MODE", "shadow")

    from nlp2cmd.generation.pipeline import RuleBasedPipeline
    from nlp2cmd.generation import semantic_entities as sem_mod
    from nlp2cmd.generation.regex import RegexEntityExtractor

    class FakeSemanticEntityExtractor:
        def __init__(self):
            self.last_mode = "regex"
            self.last_semantic_entities = None
            self._regex = RegexEntityExtractor()

        def extract(self, text: str, domain: str):
            self.last_mode = "shadow"
            self.last_semantic_entities = {"semantic_only": "x"}
            return self._regex.extract(text, domain)

    monkeypatch.setattr(sem_mod, "SemanticEntityExtractor", FakeSemanticEntityExtractor)

    pipeline = RuleBasedPipeline()
    result = pipeline.process("Znajdź pliki *.py")

    assert result.metadata.get("entity_extractor_mode") == "shadow"
    assert result.metadata.get("shadow_entities") == {"semantic_only": "x"}
