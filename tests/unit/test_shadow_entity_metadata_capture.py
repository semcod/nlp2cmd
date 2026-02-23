from __future__ import annotations

from dataclasses import dataclass

import pytest


@dataclass
class _FakeExtractionResult:
    entities: dict


def test_transform_captures_shadow_entity_metadata_from_rule_based_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NLP2CMD_ENTITY_EXTRACTOR_MODE", "shadow")

    from nlp2cmd.adapters.shell import ShellAdapter
    from nlp2cmd.core import NLP2CMD, RuleBasedBackend
    from nlp2cmd.generation import semantic_entities as sem_mod
    from nlp2cmd.generation.regex import RegexEntityExtractor

    class FakeSemanticEntityExtractor:
        def __init__(self):
            self.last_mode = "shadow"
            self.last_semantic_entities = {"semantic_only": "x"}
            self._regex = RegexEntityExtractor()

        def extract(self, text: str, domain: str):
            return self._regex.extract(text, domain)

    monkeypatch.setattr(sem_mod, "SemanticEntityExtractor", FakeSemanticEntityExtractor)

    adapter = ShellAdapter()
    rules = {k: list(v.get("patterns", [])) for k, v in adapter.INTENTS.items()}
    backend = RuleBasedBackend(rules=rules, config={"dsl": "shell"})

    nlp2cmd = NLP2CMD(adapter=adapter, nlp_backend=backend)

    result = nlp2cmd.transform("Znajdź pliki *.py")

    assert result.plan.metadata.get("entity_extractor_mode") == "shadow"
    assert result.plan.metadata.get("shadow_entities") == {"semantic_only": "x"}

    assert result.metadata.get("entity_extractor_mode") == "shadow"
    assert result.metadata.get("shadow_entities") == {"semantic_only": "x"}
