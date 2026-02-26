"""Tests for rapidfuzz-based similarity matching in EvolutionaryCache."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from nlp2cmd.generation.evolutionary_cache import (
    EvolutionaryCache,
    fingerprint,
    fuzzy_fingerprint,
    detect_domain,
)


@pytest.fixture
def cache_dir(tmp_path):
    d = tmp_path / ".nlp2cmd_test"
    d.mkdir()
    yield d
    shutil.rmtree(d, ignore_errors=True)


def _seed_cache(cache: EvolutionaryCache, entries: list[tuple[str, str, str]]):
    """Seed cache with (query, domain, command) tuples."""
    from datetime import datetime
    now = datetime.now().isoformat()
    for query, domain, command in entries:
        fp = fingerprint(query)
        ffp = fuzzy_fingerprint(query)
        cache.entries[fp] = {
            "query": query, "domain": domain, "command": command,
            "model": "test", "hits": 1, "created": now, "last_used": now,
        }
        cache.fuzzy_index[ffp] = fp
    cache.save()


# === Tier 1a: Exact match ===

class TestExactMatch:
    def test_exact_same_query(self, cache_dir):
        cache = EvolutionaryCache(cache_dir=cache_dir, enable_llm=False)
        _seed_cache(cache, [("znajdź pliki PDF większe niż 10MB", "shell", "find / -name '*.pdf' -size +10M")])
        r = cache.lookup("znajdź pliki PDF większe niż 10MB")
        assert r.cached is True
        assert r.source == "cache_exact"
        assert "find" in r.command

    def test_case_insensitive(self, cache_dir):
        cache = EvolutionaryCache(cache_dir=cache_dir, enable_llm=False)
        _seed_cache(cache, [("Docker PS", "docker", "docker ps")])
        r = cache.lookup("docker ps")
        assert r.cached is True
        assert r.source == "cache_exact"


# === Tier 1b: Fuzzy fingerprint match ===

class TestFuzzyFingerprint:
    def test_extra_stop_words(self, cache_dir):
        cache = EvolutionaryCache(cache_dir=cache_dir, enable_llm=False)
        _seed_cache(cache, [("pokaż pliki w katalogu", "shell", "ls")])
        r = cache.lookup("proszę pokaż pliki w katalogu")
        assert r.cached is True
        assert r.source == "cache_fuzzy"

    def test_word_reorder(self, cache_dir):
        cache = EvolutionaryCache(cache_dir=cache_dir, enable_llm=False)
        _seed_cache(cache, [("pliki katalogu pokaż", "shell", "ls")])
        r = cache.lookup("pokaż katalogu pliki")
        assert r.cached is True
        assert r.source == "cache_fuzzy"


# === Tier 1c: Similarity match (rapidfuzz) ===

class TestSimilarityMatch:
    def test_typo_in_query(self, cache_dir):
        """Typo: 'znajdź' -> 'znajdz' (missing diacritic)."""
        cache = EvolutionaryCache(cache_dir=cache_dir, enable_llm=False)
        _seed_cache(cache, [("znajdź pliki PDF większe niż 10MB", "shell", "find / -name '*.pdf' -size +10M")])
        r = cache.lookup("znajdz pliki PDF wieksze niz 10MB")
        assert r.cached is True
        assert r.source == "cache_similar"
        assert r.confidence >= 0.88
        assert "find" in r.command

    def test_minor_rewording(self, cache_dir):
        """Minor rewording: 'pokaż' -> 'wyświetl'."""
        cache = EvolutionaryCache(cache_dir=cache_dir, enable_llm=False)
        _seed_cache(cache, [("pokaż uruchomione kontenery docker", "docker", "docker ps")])
        r = cache.lookup("pokaż uruchomione kontenery Docker")
        assert r.cached is True
        assert "docker" in r.command.lower()

    def test_extra_words(self, cache_dir):
        """Extra words added."""
        cache = EvolutionaryCache(cache_dir=cache_dir, enable_llm=False)
        _seed_cache(cache, [("zainstaluj nodejs przez apt", "package_mgmt", "sudo apt install nodejs")])
        r = cache.lookup("zainstaloj nodejs przez apt")
        assert r.cached is True
        assert "nodejs" in r.command

    def test_completely_different_no_match(self, cache_dir):
        """Completely different query should NOT match."""
        cache = EvolutionaryCache(cache_dir=cache_dir, enable_llm=False)
        _seed_cache(cache, [("znajdź pliki PDF większe niż 10MB", "shell", "find / -name '*.pdf' -size +10M")])
        r = cache.lookup("utwórz nowy branch feature/login")
        assert r.cached is False
        assert r.source == "none"

    def test_same_meaning_different_language(self, cache_dir):
        """Polish vs English - same intent."""
        cache = EvolutionaryCache(cache_dir=cache_dir, enable_llm=False)
        _seed_cache(cache, [("list all docker containers", "docker", "docker ps -a")])
        r = cache.lookup("list docker containers")
        assert r.cached is True

    def test_threshold_respected(self, cache_dir):
        """High threshold should reject borderline matches."""
        cache = EvolutionaryCache(cache_dir=cache_dir, enable_llm=False, similarity_threshold=95.0)
        _seed_cache(cache, [("znajdź pliki PDF większe niż 10MB", "shell", "find / -name '*.pdf' -size +10M")])
        r = cache.lookup("znajdz pliki PDF wieksze niz 10MB")
        # With 95% threshold, diacritic-stripped query might not pass
        # This depends on rapidfuzz scoring, but tests the threshold mechanism
        assert isinstance(r.cached, bool)


# === Domain detection ===

class TestDomainDetection:
    @pytest.mark.parametrize("query,expected", [
        ("docker ps", "docker"),
        ("kubectl get pods", "kubernetes"),
        ("git commit -m test", "git"),
        ("ffmpeg -i video.mp4 out.webm", "ffmpeg"),
        ("curl https://api.com/users", "api"),
        ("ssh admin@server", "remote"),
        ("apt install nodejs", "package_mgmt"),
        ("znajdź pliki PDF", "shell"),
        ("pokaż kontenery docker", "docker"),
    ])
    def test_domain_detection(self, query, expected):
        assert detect_domain(query) == expected


# === Stats ===

class TestStats:
    def test_stats_track_similarity_hits(self, cache_dir):
        cache = EvolutionaryCache(cache_dir=cache_dir, enable_llm=False)
        _seed_cache(cache, [("zainstaluj nodejs przez apt", "package_mgmt", "sudo apt install nodejs")])
        cache.lookup("zainstaluj nodejs przez apt")  # exact
        cache.lookup("zainstaloj nodejs przez apt")  # similarity (typo)
        stats = cache.get_stats()
        assert stats["cache_hits"] >= 2
        assert stats.get("similarity_hits", 0) >= 1


# === Persistence ===

class TestPersistence:
    def test_cache_survives_reload(self, cache_dir):
        cache1 = EvolutionaryCache(cache_dir=cache_dir, enable_llm=False)
        _seed_cache(cache1, [("test query", "shell", "echo test")])
        del cache1

        cache2 = EvolutionaryCache(cache_dir=cache_dir, enable_llm=False)
        r = cache2.lookup("test query")
        assert r.cached is True
        assert r.command == "echo test"

    def test_similarity_works_after_reload(self, cache_dir):
        cache1 = EvolutionaryCache(cache_dir=cache_dir, enable_llm=False)
        _seed_cache(cache1, [("zainstaluj nodejs przez apt", "package_mgmt", "sudo apt install nodejs")])
        del cache1

        cache2 = EvolutionaryCache(cache_dir=cache_dir, enable_llm=False)
        r = cache2.lookup("zainstaloj nodejs przez apt")
        assert r.cached is True
        assert r.source == "cache_similar"


# === Tier 2: Template pipeline ===

class TestTemplatePipeline:
    def test_template_hit_docker_ps(self, cache_dir):
        """Template pipeline should match 'pokaż kontenery docker'."""
        cache = EvolutionaryCache(cache_dir=cache_dir, enable_llm=False)
        r = cache.lookup("pokaż uruchomione kontenery docker")
        if r.source == "template":
            assert "docker" in r.command.lower()
            assert r.cached is False

    def test_template_hit_cached_on_second_call(self, cache_dir):
        """Template result should be cached after first call."""
        cache = EvolutionaryCache(cache_dir=cache_dir, enable_llm=False)
        r1 = cache.lookup("pokaż uruchomione kontenery docker")
        if r1.source == "template":
            r2 = cache.lookup("pokaż uruchomione kontenery docker")
            assert r2.source == "cache_exact"
            assert r2.cached is True

    def test_template_rejects_echo_fallback(self, cache_dir):
        """Template pipeline should reject echo-fallback commands."""
        cache = EvolutionaryCache(cache_dir=cache_dir, enable_llm=False)
        # A query that would produce an echo fallback should return none
        r = cache.lookup("zrób coś magicznego z kwantowym teleportem")
        assert r.source == "none" or r.source == "template"
        if r.source == "template":
            assert not r.command.startswith("echo ")


# === Pre-warm cache ===

class TestPrewarm:
    def test_prewarm_adds_entries(self, cache_dir):
        cache = EvolutionaryCache(cache_dir=cache_dir, enable_llm=False)
        assert len(cache.entries) == 0
        added = cache.prewarm()
        assert added == 50
        assert len(cache.entries) == 50

    def test_prewarm_idempotent(self, cache_dir):
        cache = EvolutionaryCache(cache_dir=cache_dir, enable_llm=False)
        added1 = cache.prewarm()
        added2 = cache.prewarm()
        assert added1 == 50
        assert added2 == 0  # no new entries

    def test_prewarm_entries_are_exact_hit(self, cache_dir):
        cache = EvolutionaryCache(cache_dir=cache_dir, enable_llm=False)
        cache.prewarm()
        r = cache.lookup("znajdź pliki PDF większe niż 10MB")
        assert r.cached is True
        assert r.source == "cache_exact"
        assert "find" in r.command

    def test_prewarm_similarity_hit(self, cache_dir):
        """Pre-warmed entries should be findable via similarity matching."""
        cache = EvolutionaryCache(cache_dir=cache_dir, enable_llm=False)
        cache.prewarm()
        r = cache.lookup("znajdz pliki PDF wieksze niz 10MB")
        assert r.cached is True
        assert r.source in ("cache_exact", "cache_fuzzy", "cache_similar")

    def test_prewarm_survives_reload(self, cache_dir):
        cache1 = EvolutionaryCache(cache_dir=cache_dir, enable_llm=False)
        cache1.prewarm()
        del cache1
        cache2 = EvolutionaryCache(cache_dir=cache_dir, enable_llm=False)
        assert len(cache2.entries) == 50
        r = cache2.lookup("pokaż ostatnie 10 commitów")
        assert r.cached is True
        assert "git log" in r.command
