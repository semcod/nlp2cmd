"""
QueryNormalizer — Etap 1 of the NLP refactoring plan.

Provides Unicode normalization, typo correction (rapidfuzz), heuristic
language detection, and basic tokenization.  Every user query passes through
this layer *before* intent detection so downstream components receive
clean, language-tagged input instead of raw strings.

Design goals:
  • Zero heavy ML deps — stdlib + rapidfuzz only (rapidfuzz is already used
    elsewhere in the project).
  • Fast — target < 1 ms per query on commodity hardware.
  • Extensible — vocabulary files can be swapped / extended via YAML later
    (Etap 2).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional

try:
    from rapidfuzz import fuzz, process as rfprocess
except ImportError:  # pragma: no cover
    fuzz = None  # type: ignore[assignment]
    rfprocess = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class NormalizedQuery:
    """Immutable result of normalizing a raw user query."""

    original: str
    text: str
    lang: str
    tokens: list[str]
    lemmas: list[str] = field(default_factory=list)
    corrections: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Language detection — lightweight heuristic (no heavy deps)
# ---------------------------------------------------------------------------

# Character-set markers per language → (charset, weight)
_CHAR_LANG_TABLE: list[tuple[str, set[str], float]] = [
    ("pl", set("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ"), 2.0),
    ("de", set("äöüßÄÖÜẞ"), 2.0),
    ("fr", set("àâæçéèêëîïôùûüÿœÀÂÆÇÉÈÊËÎÏÔÙÛÜŸŒ"), 2.0),
    ("es", set("áéíóúñüÁÉÍÓÚÑÜ¿¡"), 2.0),
    ("cs", set("áčďéěíňóřšťúůýžÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ"), 1.5),
    ("uk", set("іїєґІЇЄҐ"), 3.0),
    ("ru", set("абвгдежзийклмнопрстуфхцчшщъыьэюяАБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"), 1.5),
]

# High-frequency short words per language (top ~20 function words)
_PL_WORDS = frozenset({
    "i", "w", "na", "z", "do", "nie", "to", "co", "jak", "jest",
    "się", "ale", "za", "od", "po", "tak", "ten", "jej", "ich", "czy",
    "dla", "lub", "bez", "tego", "przez", "albo", "też",
    "pokaż", "pokaz", "znajdź", "znajdz", "otwórz", "otworz", "usuń", "usun",
    "stwórz", "stworz", "uruchom", "zatrzymaj", "wejdź", "wejdz",
})
_EN_WORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "have",
    "has", "do", "does", "did", "will", "would", "can", "could", "should",
    "of", "in", "to", "for", "with", "on", "at", "from", "by", "about",
    "show", "find", "open", "delete", "create", "run", "stop", "list",
    "get", "set", "move", "copy", "search", "kill", "start", "build",
})
_DE_WORDS = frozenset({
    "der", "die", "das", "ein", "eine", "ist", "sind", "war", "haben",
    "und", "oder", "nicht", "mit", "von", "zu", "auf", "für", "aus",
    "zeige", "finde", "öffne", "lösche", "erstelle",
})


# Word-frequency lookup: lang → frozenset
_WORD_LANG_TABLE: list[tuple[str, frozenset[str]]] = [
    ("pl", _PL_WORDS),
    ("en", _EN_WORDS),
    ("de", _DE_WORDS),
]

_WORD_RE = re.compile(r"[\w]+", re.UNICODE)


def _score_chars(text: str, scores: dict[str, float]) -> None:
    """Accumulate character-set language scores."""
    for ch in text:
        for lang, charset, weight in _CHAR_LANG_TABLE:
            if ch in charset:
                scores[lang] += weight


def _score_words(text: str, scores: dict[str, float]) -> None:
    """Accumulate word-frequency language scores."""
    words_lower = set(_WORD_RE.findall(text.lower()))
    for lang, wordset in _WORD_LANG_TABLE:
        for w in words_lower:
            if w in wordset:
                scores[lang] += 1.0


def detect_language(text: str) -> str:
    """Heuristic language detection based on character sets and word frequency.

    Returns ISO 639-1 code: ``"pl"``, ``"en"``, ``"de"``, ``"fr"``, ``"es"``,
    ``"cs"``, ``"uk"``, ``"ru"``, or ``"unknown"``.

    The heuristic is intentionally simple and fast (<0.05 ms).  For
    production-grade detection on very short inputs, swap in ``lingua-py``
    behind the same interface later (Etap 2+).
    """
    if not text or not text.strip():
        return "unknown"

    scores: dict[str, float] = {
        "pl": 0.0, "de": 0.0, "fr": 0.0, "es": 0.0,
        "cs": 0.0, "uk": 0.0, "ru": 0.0, "en": 0.0,
    }
    _score_chars(text, scores)
    _score_words(text, scores)

    best_lang = max(scores, key=scores.get)  # type: ignore[arg-type]
    if scores[best_lang] < 0.01:
        return "en"

    # If PL and CS are very close (shared diacritics), prefer PL as project default
    if best_lang == "cs" and scores["pl"] >= scores["cs"] * 0.8:
        return "pl"

    return best_lang


# ---------------------------------------------------------------------------
# Unicode normalization
# ---------------------------------------------------------------------------

def normalize_unicode(text: str) -> str:
    """Apply NFC normalization so combining characters are composed.

    For example, ``'ó'`` as ``o + combining acute`` → single ``ó`` codepoint.
    """
    return unicodedata.normalize("NFC", text)


def fold_accents(text: str) -> str:
    """Strip diacritical marks, producing ASCII-like text for fuzzy matching.

    ``"otwórz przeglądarkę"`` → ``"otworz przegladarke"``

    This is used *only* for matching — the original accented text is preserved
    in ``NormalizedQuery.text``.
    """
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if unicodedata.category(ch) != "Mn")


# ---------------------------------------------------------------------------
# Typo correction via rapidfuzz
# ---------------------------------------------------------------------------

# Known vocabulary — canonical forms of domain-specific terms.
# This list is used both as a rapidfuzz reference set and as a
# direct-lookup correction dictionary.
_TYPO_MAP: dict[str, str] = {
    # Docker
    "dokcer": "docker",
    "doker": "docker",
    "dcoker": "docker",
    "dockre": "docker",
    "docekr": "docker",
    "dokker": "docker",
    # Kubernetes
    "kubernetse": "kubernetes",
    "kuberntes": "kubernetes",
    "kuberneets": "kubernetes",
    "kubernates": "kubernetes",
    "kuberentes": "kubernetes",
    "kubernets": "kubernetes",
    # kubectl
    "kubeclt": "kubectl",
    "kubctl": "kubectl",
    "kubetcl": "kubectl",
    # Git
    "gti": "git",
    "igt": "git",
    # Common shell commands
    "systemclt": "systemctl",
    "systmctl": "systemctl",
    "systemtcl": "systemctl",
    # Polish command words
    "pokaz": "pokaż",
    "pokż": "pokaż",
    "znajdz": "znajdź",
    "znajź": "znajdź",
    "otworz": "otwórz",
    "otwozr": "otwórz",
    "usun": "usuń",
    "utworz": "utwórz",
    "stworz": "stwórz",
    "przenies": "przenieś",
    "skopiój": "skopiuj",
    "urucho": "uruchom",
    "zatrzym": "zatrzymaj",
    # Browser
    "przegladarka": "przeglądarka",
    "przegladark": "przeglądark",
    "przegladarke": "przeglądarkę",
    "strone": "stronę",
}

# Full vocabulary set for fuzzy matching (canonical forms)
_VOCABULARY: list[str] = sorted(set(_TYPO_MAP.values()) | {
    # Additional canonical terms not in typo map
    "docker", "kubernetes", "kubectl", "git", "systemctl",
    "pokaż", "znajdź", "otwórz", "usuń", "utwórz", "stwórz",
    "przenieś", "skopiuj", "uruchom", "zatrzymaj",
    "przeglądarka", "przeglądarkę", "stronę",
    "pliki", "plik", "katalog", "folder", "proces", "procesy",
    "kontener", "kontenery", "obraz", "obrazy", "sieć",
    "usługa", "usługi", "klucz", "token", "api",
    "lista", "status", "informacje", "pamięć", "dysk",
    "serwer", "baza", "danych", "tabela", "kolumna",
    "files", "file", "directory", "process", "processes",
    "container", "containers", "image", "images", "network",
    "service", "services", "key", "server", "database",
    "table", "column", "memory", "disk", "space",
    "show", "find", "open", "delete", "create", "run", "stop",
    "list", "get", "set", "move", "copy", "search", "kill",
    "start", "build", "push", "pull", "restart", "install",
})

# Minimum score for rapidfuzz to consider a match (0–100).
# Set high (96) to avoid correcting valid inflected forms like
# "kontenera", "obrazów", "foldery" which are not typos.
# The direct _TYPO_MAP lookup handles curated typos regardless of this threshold.
_FUZZY_THRESHOLD = 96


def _preserve_case(original: str, corrected: str) -> str:
    """Apply the casing style of *original* to *corrected*."""
    if original[0].isupper() and corrected[0].islower():
        return corrected[0].upper() + corrected[1:]
    return corrected


def _try_direct_lookup(token_lower: str) -> Optional[str]:
    """Return corrected form from the direct typo map, or None."""
    return _TYPO_MAP.get(token_lower)


def _try_fuzzy_match(token_lower: str, threshold: int) -> Optional[str]:
    """Return best fuzzy match from vocabulary, or None."""
    if fuzz is None or len(token_lower) < 3:
        return None
    match = rfprocess.extractOne(
        token_lower, _VOCABULARY, scorer=fuzz.ratio, score_cutoff=threshold,
    )
    if match is not None:
        candidate, _score, _idx = match
        if candidate != token_lower:
            return candidate
    return None


def correct_typos(text: str, threshold: int = _FUZZY_THRESHOLD) -> tuple[str, dict[str, str]]:
    """Correct known typos in *text* using direct lookup + rapidfuzz fallback.

    Returns ``(corrected_text, {original_token: corrected_token, ...})``.
    """
    if not text:
        return text, {}

    corrections: dict[str, str] = {}
    result_tokens: list[str] = []

    for token in text.split():
        token_lower = token.lower()
        corrected = _try_direct_lookup(token_lower) or _try_fuzzy_match(token_lower, threshold)

        if corrected is not None:
            corrected = _preserve_case(token, corrected)
            corrections[token] = corrected
            result_tokens.append(corrected)
        else:
            result_tokens.append(token)

    return " ".join(result_tokens), corrections


# ---------------------------------------------------------------------------
# Tokenization
# ---------------------------------------------------------------------------

# Token pattern: word chars (incl. Unicode letters), numbers, or punctuation groups
_TOKEN_RE = re.compile(
    r"""
    [a-zA-Z\u00C0-\u024F\u0400-\u04FF]+  # Latin/Cyrillic word
    (?:[-'][a-zA-Z\u00C0-\u024F\u0400-\u04FF]+)*  # hyphenated / apostrophe
    | \d+(?:\.\d+)*                        # numbers (incl. version-like 1.0.85)
    | \.(?:com|org|net|io|ai|dev|pl|app|co|de|uk|eu|env)\b  # TLD / .env
    | [^\s]                                # single punctuation
    """,
    re.VERBOSE | re.UNICODE,
)


def tokenize(text: str) -> list[str]:
    """Split *text* into tokens suitable for downstream NLP processing.

    Preserves URLs, dotted identifiers, and version numbers as single tokens
    where possible.
    """
    if not text:
        return []
    return _TOKEN_RE.findall(text)


# ---------------------------------------------------------------------------
# QueryNormalizer — main API
# ---------------------------------------------------------------------------

class QueryNormalizer:
    """Normalize a raw user query into a ``NormalizedQuery``.

    Usage::

        normalizer = QueryNormalizer()
        nq = normalizer.normalize("pokaz pliki dokcer")
        assert nq.lang == "pl"
        assert "docker" in nq.text
        assert nq.corrections == {"dokcer": "docker"}
    """

    def __init__(
        self,
        *,
        enable_typo_correction: bool = True,
        fuzzy_threshold: int = _FUZZY_THRESHOLD,
        extra_vocabulary: Optional[list[str]] = None,
        extra_typo_map: Optional[dict[str, str]] = None,
    ) -> None:
        self.enable_typo_correction = enable_typo_correction
        self.fuzzy_threshold = fuzzy_threshold

        # Allow callers (or YAML config later) to extend vocabulary
        if extra_vocabulary:
            _VOCABULARY.extend(extra_vocabulary)
        if extra_typo_map:
            _TYPO_MAP.update(extra_typo_map)

    def normalize(self, raw: str) -> NormalizedQuery:
        """Full normalization pipeline: unicode → typo correction → lang → tokenize."""
        if not raw:
            return NormalizedQuery(
                original="", text="", lang="unknown", tokens=[], lemmas=[]
            )

        # Step 1: Unicode NFC normalization
        text = normalize_unicode(raw.strip())

        # Step 2: Detect language (on original text, before correction)
        lang = detect_language(text)

        # Step 3: Typo correction
        corrections: dict[str, str] = {}
        if self.enable_typo_correction:
            text, corrections = correct_typos(text, threshold=self.fuzzy_threshold)

        # Step 4: Tokenize
        tokens = tokenize(text)

        # Step 5: Lemmas — placeholder for future stanza/spaCy integration
        lemmas: list[str] = []

        return NormalizedQuery(
            original=raw,
            text=text,
            lang=lang,
            tokens=tokens,
            lemmas=lemmas,
            corrections=corrections,
        )

    def normalize_for_matching(self, raw: str) -> str:
        """Return accent-folded, lowercased text for fuzzy/keyword matching.

        This does NOT replace the original text — it's a secondary view used
        by keyword_detector and similar components.
        """
        nq = self.normalize(raw)
        return fold_accents(nq.text).lower()
