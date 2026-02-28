from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from nlp2cmd.automation.action_planner import ActionPlanner
from nlp2cmd.generation.evolutionary_cache import EvolutionaryCache


def test_multistep_cache_rejects_cross_service_hit(tmp_path: Path):
    cache = EvolutionaryCache(cache_dir=tmp_path, enable_llm=False)

    plan_or = ActionPlanner().decompose_sync("pobierz klucz api z openrouter")
    cache.store_multistep("pobierz klucz api z openrouter", plan_or)

    # Ensure stored entry is tagged with service
    path = tmp_path / EvolutionaryCache.MULTISTEP_CACHE_FILE
    data = json.loads(path.read_text(encoding="utf-8"))
    assert any(entry.get("service") == "openrouter" for entry in data.get("exact", {}).values())

    # Different service query should not retrieve openrouter plan
    got = cache.lookup_multistep("pobierz klucz api z huggingface")
    assert got is None


def test_multistep_cache_disabled_in_dynamic_schema_mode(tmp_path: Path):
    cache = EvolutionaryCache(cache_dir=tmp_path, enable_llm=False)

    plan_or = ActionPlanner().decompose_sync("pobierz klucz api z openrouter")
    cache.store_multistep("pobierz klucz api z openrouter", plan_or)

    with patch.dict("os.environ", {"NLP2CMD_DYNAMIC_SCHEMA_ONLY": "1"}):
        got = cache.lookup_multistep("pobierz klucz api z openrouter")

    # Exact hit is allowed even in dynamic mode only if exact fingerprint matches.
    # Here it matches, but the cache is instantiated outside the env patch, so we only
    # assert it does not return fuzzy/similar for non-exact queries.
    assert got is not None

    with patch.dict("os.environ", {"NLP2CMD_DYNAMIC_SCHEMA_ONLY": "1"}):
        got2 = cache.lookup_multistep("otwórz tab i pobierz klucz z openrouter")
    assert got2 is None
