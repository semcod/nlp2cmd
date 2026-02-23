from __future__ import annotations

import pytest


def test_service_query_returns_shadow_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")

    monkeypatch.setenv("NLP2CMD_ENTITY_EXTRACTOR_MODE", "shadow")

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

    from nlp2cmd.service import create_app

    app = create_app()

    from fastapi.testclient import TestClient

    client = TestClient(app)

    resp = client.post("/query", json={"query": "Znajdź pliki *.py"})
    assert resp.status_code == 200

    payload = resp.json()
    assert payload.get("success") in {True, False}

    meta = payload.get("metadata")
    assert isinstance(meta, dict)
    assert meta.get("entity_extractor_mode") == "shadow"
    assert meta.get("shadow_entities") == {"semantic_only": "x"}
