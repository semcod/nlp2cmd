"""Tests for nlp2cmd.nlp.normalizer — Etap 1 of the refactoring plan."""

from __future__ import annotations

import unicodedata

import pytest

from nlp2cmd.nlp.normalizer import (
    NormalizedQuery,
    QueryNormalizer,
    correct_typos,
    detect_language,
    fold_accents,
    normalize_unicode,
    tokenize,
)


# ── NormalizedQuery dataclass ───────────────────────────────────────────

class TestNormalizedQuery:
    def test_immutable(self):
        nq = NormalizedQuery(original="x", text="x", lang="en", tokens=["x"])
        with pytest.raises(AttributeError):
            nq.text = "y"  # type: ignore[misc]

    def test_defaults(self):
        nq = NormalizedQuery(original="", text="", lang="en", tokens=[])
        assert nq.lemmas == []
        assert nq.corrections == {}


# ── Unicode normalization ───────────────────────────────────────────────

class TestNormalizeUnicode:
    def test_nfc_composition(self):
        # o + combining acute → ó (single codepoint)
        decomposed = "o\u0301"
        result = normalize_unicode(decomposed)
        assert result == "ó"
        assert len(result) == 1

    def test_already_nfc(self):
        text = "otwórz plik"
        assert normalize_unicode(text) == text

    def test_empty(self):
        assert normalize_unicode("") == ""


# ── Accent folding ──────────────────────────────────────────────────────

class TestFoldAccents:
    def test_polish_diacritics(self):
        assert fold_accents("otwórz przeglądarkę") == "otworz przegladarke"

    def test_german_umlaut(self):
        assert fold_accents("öffne") == "offne"

    def test_no_accents(self):
        assert fold_accents("docker ps") == "docker ps"

    def test_mixed(self):
        assert fold_accents("znajdź pliki w /tmp") == "znajdz pliki w /tmp"


# ── Language detection ──────────────────────────────────────────────────

class TestDetectLanguage:
    def test_polish_diacritics(self):
        assert detect_language("otwórz przeglądarkę i stronę") == "pl"

    def test_polish_keywords(self):
        assert detect_language("pokaż pliki w katalogu") == "pl"

    def test_english_pure(self):
        assert detect_language("show files in directory") == "en"

    def test_english_commands(self):
        assert detect_language("docker ps --all") == "en"

    def test_german_diacritics(self):
        assert detect_language("öffne die Datei und lösche den Ordner") == "de"

    def test_empty(self):
        assert detect_language("") == "unknown"

    def test_whitespace_only(self):
        assert detect_language("   ") == "unknown"

    def test_no_signals_defaults_english(self):
        # Pure ASCII with no language-specific words
        assert detect_language("xyz 123") == "en"

    def test_russian(self):
        assert detect_language("показать файлы в каталоге") == "ru"

    def test_mixed_pl_en(self):
        # Polish diacritics should dominate
        lang = detect_language("otwórz docker ps i pokaż kontenery")
        assert lang == "pl"


# ── Typo correction ─────────────────────────────────────────────────────

class TestCorrectTypos:
    def test_docker_typo_direct(self):
        text, corrections = correct_typos("dokcer ps")
        assert "docker" in text
        assert "dokcer" in corrections

    def test_doker_typo(self):
        text, corrections = correct_typos("doker images")
        assert text.startswith("docker")
        assert "doker" in corrections

    def test_kubernetes_typo(self):
        text, corrections = correct_typos("kubernets get pods")
        assert "kubernetes" in text

    def test_polish_diacritics_missing(self):
        text, corrections = correct_typos("pokaz pliki")
        assert "pokaż" in text
        assert "pokaz" in corrections

    def test_no_correction_needed(self):
        text, corrections = correct_typos("docker ps --all")
        assert text == "docker ps --all"
        assert corrections == {}

    def test_empty(self):
        text, corrections = correct_typos("")
        assert text == ""
        assert corrections == {}

    def test_preserves_case(self):
        text, _corr = correct_typos("Dokcer images")
        assert text.startswith("Docker")

    def test_multiple_corrections(self):
        text, corrections = correct_typos("pokaz dokcer kontenery")
        assert "pokaż" in text
        assert "docker" in text
        assert len(corrections) >= 2

    def test_browser_typos(self):
        text, corrections = correct_typos("otworz przegladarke")
        assert "otwórz" in text
        assert "przeglądarkę" in text

    def test_short_tokens_skip_fuzzy(self):
        # Tokens < 3 chars should not be fuzzed (avoid noise)
        text, corrections = correct_typos("ls -la")
        assert text == "ls -la"
        assert corrections == {}


# ── Tokenization ────────────────────────────────────────────────────────

class TestTokenize:
    def test_basic(self):
        tokens = tokenize("pokaż pliki")
        assert tokens == ["pokaż", "pliki"]

    def test_with_numbers(self):
        tokens = tokenize("znajdź pliki starsze niż 7 dni")
        assert "7" in tokens
        assert "znajdź" in tokens

    def test_version_number(self):
        tokens = tokenize("version 1.0.85")
        assert "1.0.85" in tokens

    def test_empty(self):
        assert tokenize("") == []

    def test_punctuation(self):
        tokens = tokenize("docker ps --all")
        assert "docker" in tokens
        assert "ps" in tokens
        # '--' gets split into individual punctuation chars
        assert "all" in tokens

    def test_unicode_words(self):
        tokens = tokenize("otwórz przeglądarkę i stronę openrouter.ai")
        assert "otwórz" in tokens
        assert "przeglądarkę" in tokens


# ── QueryNormalizer (integration) ───────────────────────────────────────

class TestQueryNormalizer:
    def setup_method(self):
        self.normalizer = QueryNormalizer()

    def test_full_pipeline_polish(self):
        nq = self.normalizer.normalize("pokaz pliki dokcer")
        assert nq.lang == "pl"
        assert "docker" in nq.text
        assert "pokaż" in nq.text
        assert nq.original == "pokaz pliki dokcer"
        assert len(nq.tokens) >= 3
        assert len(nq.corrections) >= 2

    def test_full_pipeline_english(self):
        nq = self.normalizer.normalize("show docker containers")
        assert nq.lang == "en"
        assert nq.text == "show docker containers"
        assert nq.corrections == {}

    def test_empty_input(self):
        nq = self.normalizer.normalize("")
        assert nq.lang == "unknown"
        assert nq.text == ""
        assert nq.tokens == []

    def test_unicode_combining_chars(self):
        # Simulate combining character input
        raw = "otwo\u0301rz plik"  # o + combining acute
        nq = self.normalizer.normalize(raw)
        assert "ó" in nq.text or "otwórz" in nq.text

    def test_typo_correction_disabled(self):
        normalizer = QueryNormalizer(enable_typo_correction=False)
        nq = normalizer.normalize("dokcer ps")
        assert nq.text == "dokcer ps"
        assert nq.corrections == {}

    def test_normalize_for_matching(self):
        result = self.normalizer.normalize_for_matching("Otwórz Przeglądarkę")
        assert result == "otworz przegladarke"

    def test_browser_automation_query(self):
        nq = self.normalizer.normalize(
            "otworz przegladarke i strone openrouter.ai, wyciągnij klucz API"
        )
        assert nq.lang == "pl"
        assert "otwórz" in nq.text
        assert "przeglądarkę" in nq.text

    def test_extra_vocabulary(self):
        normalizer = QueryNormalizer(extra_typo_map={"terrafrm": "terraform"})
        nq = normalizer.normalize("terrafrm plan")
        assert "terraform" in nq.text

    def test_performance(self):
        """Normalization should complete in < 5ms for typical queries."""
        import time
        normalizer = QueryNormalizer()
        query = "otwórz przeglądarkę i stronę openrouter.ai, wyciągnij klucz API i zapisz do .env"
        start = time.perf_counter()
        for _ in range(100):
            normalizer.normalize(query)
        elapsed_ms = (time.perf_counter() - start) * 1000 / 100
        assert elapsed_ms < 5.0, f"Normalization took {elapsed_ms:.2f}ms per query (target < 5ms)"
