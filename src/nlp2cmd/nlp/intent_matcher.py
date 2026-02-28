"""
Intent matcher — YAML-driven multilingual intent detection with fuzzy matching.

Loads intent definitions from data/intents/*.yaml and matches user queries
against multilingual keyword labels + examples using:
1. Exact keyword match (fastest)
2. Fuzzy match via rapidfuzz (typo-tolerant)
3. Example similarity (future: sentence embeddings)

Replaces hardcoded keyword lists scattered across adapters.

Usage:
    matcher = IntentMatcher()
    results = matcher.match("otwórz firefox")
    # → [IntentMatch(intent="open_app", domain="desktop", confidence=0.95, ...)]
"""

from __future__ import annotations

import logging
import os
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from nlp2cmd.utils.yaml_compat import yaml

log = logging.getLogger(__name__)

# Try package data dir first, then project root data dir
_PKG_DIR = Path(__file__).resolve().parent.parent
_INTENTS_DIR_CANDIDATES = [
    _PKG_DIR / "data" / "intents",
    _PKG_DIR.parent.parent / "data" / "intents",  # project root
]
_INTENTS_DIR = next((d for d in _INTENTS_DIR_CANDIDATES if d.is_dir()), _INTENTS_DIR_CANDIDATES[0])


@dataclass
class IntentDef:
    """Intent definition loaded from YAML."""
    intent: str
    domain: str
    description: str = ""
    labels: dict[str, list[str]] = field(default_factory=dict)
    entities: list[dict[str, Any]] = field(default_factory=list)
    examples: dict[str, list[str]] = field(default_factory=dict)

    def all_labels(self) -> list[str]:
        """Return all labels across all languages."""
        result: list[str] = []
        for lang_labels in self.labels.values():
            result.extend(lang_labels)
        return result

    def all_examples(self) -> list[str]:
        """Return all examples across all languages."""
        result: list[str] = []
        for lang_examples in self.examples.values():
            result.extend(lang_examples)
        return result


@dataclass
class IntentMatch:
    """Result of intent matching."""
    intent: str
    domain: str
    confidence: float
    matched_label: str = ""
    matched_lang: str = ""
    method: str = "keyword"  # "keyword", "fuzzy", "example", "semantic"


class IntentMatcher:
    """
    Multilingual intent matcher backed by YAML definitions.

    Matching pipeline (in order):
    1. Exact keyword match against labels (all languages)
    2. Fuzzy keyword match via rapidfuzz (handles typos)
    3. (Future) Sentence embedding similarity against examples
    """

    FUZZY_THRESHOLD = 80  # rapidfuzz score 0-100

    def __init__(self, intents_dir: Optional[Path] = None):
        self._intents_dir = intents_dir or _INTENTS_DIR
        self._intents: dict[str, IntentDef] = {}
        self._label_index: dict[str, tuple[str, str]] = {}  # label → (intent, lang)
        self.load()

    def load(self) -> None:
        """Load all intent YAML files from the intents directory."""
        self._intents.clear()
        self._label_index.clear()

        if not self._intents_dir.is_dir():
            log.warning("Intents directory not found: %s", self._intents_dir)
            return

        for yaml_path in sorted(self._intents_dir.glob("*.yaml")):
            try:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
            except Exception as e:
                log.warning("Failed to load %s: %s", yaml_path.name, e)
                continue

            intent_name = data.get("intent")
            if not intent_name:
                continue

            intent_def = IntentDef(
                intent=intent_name,
                domain=data.get("domain", "unknown"),
                description=data.get("description", ""),
                labels=data.get("labels", {}),
                entities=data.get("entities", []),
                examples=data.get("examples", {}),
            )
            self._intents[intent_name] = intent_def

            # Build label index for fast lookup
            for lang, labels in intent_def.labels.items():
                for label in labels:
                    normalized = self._normalize(label)
                    self._label_index[normalized] = (intent_name, lang)

        log.debug("IntentMatcher loaded %d intents from %s",
                  len(self._intents), self._intents_dir)

    def match(self, text: str, top_k: int = 3) -> list[IntentMatch]:
        """
        Match user query against all registered intents.

        Args:
            text: User query (any language)
            top_k: Maximum number of matches to return

        Returns:
            List of IntentMatch sorted by confidence (descending)
        """
        text_normalized = self._normalize(text)
        results: list[IntentMatch] = []
        seen_intents: set[str] = set()

        # Tier 1: Exact keyword match
        for label, (intent_name, lang) in self._label_index.items():
            if label in text_normalized and intent_name not in seen_intents:
                intent_def = self._intents[intent_name]
                results.append(IntentMatch(
                    intent=intent_name,
                    domain=intent_def.domain,
                    confidence=0.95,
                    matched_label=label,
                    matched_lang=lang,
                    method="keyword",
                ))
                seen_intents.add(intent_name)

        # Tier 2: Fuzzy match (for typos)
        if len(results) < top_k:
            fuzzy_results = self._fuzzy_match(text_normalized, exclude=seen_intents)
            results.extend(fuzzy_results[:top_k - len(results)])
            seen_intents.update(m.intent for m in fuzzy_results)

        # Sort by confidence descending
        results.sort(key=lambda m: m.confidence, reverse=True)
        return results[:top_k]

    def match_best(self, text: str) -> Optional[IntentMatch]:
        """Return the single best match, or None if no match found."""
        results = self.match(text, top_k=1)
        return results[0] if results else None

    def get_intent(self, name: str) -> Optional[IntentDef]:
        """Get intent definition by name."""
        return self._intents.get(name)

    def list_intents(self) -> list[str]:
        """Return sorted list of all intent names."""
        return sorted(self._intents.keys())

    def _fuzzy_match(
        self, text: str, exclude: set[str] | None = None
    ) -> list[IntentMatch]:
        """Fuzzy match text against intent labels using rapidfuzz."""
        exclude = exclude or set()
        results: list[IntentMatch] = []

        try:
            from rapidfuzz import fuzz
        except ImportError:
            return results

        # Extract words from query for matching
        words = text.split()

        for label, (intent_name, lang) in self._label_index.items():
            if intent_name in exclude:
                continue

            # Match each word and multi-word phrases against labels
            best_score = 0.0
            for i in range(len(words)):
                for j in range(i + 1, min(i + 5, len(words) + 1)):
                    phrase = " ".join(words[i:j])
                    score = fuzz.WRatio(phrase, label)
                    if score > best_score:
                        best_score = score

            if best_score >= self.FUZZY_THRESHOLD:
                intent_def = self._intents[intent_name]
                confidence = min(best_score / 100.0 * 0.85, 0.90)
                results.append(IntentMatch(
                    intent=intent_name,
                    domain=intent_def.domain,
                    confidence=confidence,
                    matched_label=label,
                    matched_lang=lang,
                    method="fuzzy",
                ))

        # Deduplicate by intent (keep highest confidence)
        best_per_intent: dict[str, IntentMatch] = {}
        for m in results:
            if m.intent not in best_per_intent or m.confidence > best_per_intent[m.intent].confidence:
                best_per_intent[m.intent] = m

        return sorted(best_per_intent.values(), key=lambda m: m.confidence, reverse=True)

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize text for matching: lowercase, strip diacritics for comparison."""
        text = text.lower().strip()
        # NFKD decomposition + strip combining marks for diacritic-insensitive matching
        nfkd = unicodedata.normalize("NFKD", text)
        stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
        return stripped
