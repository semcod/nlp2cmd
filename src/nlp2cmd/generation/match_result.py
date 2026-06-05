# MatchResult - extracted from fuzzy_schema_matcher.py
"""
Language-Agnostic Fuzzy Schema Matcher.

Uses multiple algorithms to match input text against JSON schema-defined phrases,
independent of specific language or dictionary words.

Algorithms used:
- Levenshtein/Damerau-Levenshtein: Edit distance for typos
- Jaro-Winkler: Good for similar word beginnings  
- Metaphone: Phonetic matching for STT errors
- N-gram Jaccard: Fragment-based matching for word boundary errors
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any

# Lazy imports for optional dependencies
_jellyfish = None
_rapidfuzz = None


def _get_jellyfish():
    """Lazy load jellyfish library."""
    global _jellyfish
    if _jellyfish is None:
        try:
            import jellyfish
            _jellyfish = jellyfish
        except ImportError:
            _jellyfish = False
    return _jellyfish if _jellyfish else None


def _get_rapidfuzz():
    """Lazy load rapidfuzz library."""
    global _rapidfuzz
    if _rapidfuzz is None:
        try:
            from rapidfuzz import fuzz, process
            _rapidfuzz = (fuzz, process)
        except ImportError:
            _rapidfuzz = False
    return _rapidfuzz if _rapidfuzz else None
@dataclass
class MatchResult:
    """Result of fuzzy schema matching."""
    matched: bool
    phrase: str
    domain: str
    intent: str
    confidence: float
    algorithm: str
    original_input: str
    normalized_input: str
    details: dict = field(default_factory=dict)
