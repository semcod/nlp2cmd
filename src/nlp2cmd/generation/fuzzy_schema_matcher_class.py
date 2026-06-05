# FuzzySchemaMatcher - extracted from fuzzy_schema_matcher.py
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
from nlp2cmd.generation.fuzzy_schema_matcher_config import FuzzySchemaMatcherConfig
from nlp2cmd.generation.match_result import MatchResult
from nlp2cmd.generation.phrase_schema import PhraseSchema

class FuzzySchemaMatcher:
    """
    Language-agnostic fuzzy matcher using JSON schemas.
    
    Works with any language by using character-level algorithms
    rather than language-specific dictionaries.
    """
    
    def __init__(
        self,
        schema_path: Optional[Path] = None,
        config: Optional[FuzzySchemaMatcherConfig] = None,
    ):
        self.config = config or FuzzySchemaMatcherConfig()
        self.phrases: list[PhraseSchema] = []
        self._phrase_index: dict[str, list[PhraseSchema]] = {}
        
        if schema_path:
            self.load_schema(schema_path)
    
    def load_schema(self, path: Path) -> None:
        """Load phrase schemas from JSON file."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.phrases = []
        for item in data.get("phrases", []):
            phrase = PhraseSchema(
                phrase=item["phrase"],
                domain=item.get("domain", "unknown"),
                intent=item.get("intent", "unknown"),
                language=item.get("language", "any"),
                aliases=item.get("aliases", []),
                phonetic_variants=item.get("phonetic_variants", []),
            )
            self.phrases.append(phrase)
        
        self._build_index()
    
    def add_phrase(self, phrase: PhraseSchema) -> None:
        """Add a phrase schema programmatically."""
        self.phrases.append(phrase)
        self._index_phrase(phrase)
    
    def add_phrases_from_dict(self, phrases_dict: dict[str, dict]) -> None:
        """
        Add phrases from a dictionary format.
        
        Format: {
            "domain": {
                "intent": ["phrase1", "phrase2", ...]
            }
        }
        """
        for domain, intents in phrases_dict.items():
            for intent, phrase_list in intents.items():
                for phrase_text in phrase_list:
                    phrase = PhraseSchema(
                        phrase=phrase_text,
                        domain=domain,
                        intent=intent,
                    )
                    self.add_phrase(phrase)
    
    def _build_index(self) -> None:
        """Build search index for phrases."""
        self._phrase_index = {}
        for phrase in self.phrases:
            self._index_phrase(phrase)
    
    def _index_phrase(self, phrase: PhraseSchema) -> None:
        """Index a single phrase."""
        # Index by first character (normalized)
        normalized = self._normalize(phrase.phrase)
        if normalized:
            key = normalized[0]
            if key not in self._phrase_index:
                self._phrase_index[key] = []
            self._phrase_index[key].append(phrase)
    
    def _normalize(self, text: str) -> str:
        """
        Normalize text for matching (language-agnostic).
        
        - Lowercase
        - Remove diacritics/accents
        - Normalize whitespace
        - Remove punctuation
        """
        # Lowercase
        text = text.lower()
        
        # Remove diacritics (works for any language with Latin-based script)
        text = unicodedata.normalize('NFKD', text)
        text = ''.join(c for c in text if not unicodedata.combining(c))
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        # Remove punctuation but keep spaces
        text = re.sub(r'[^\w\s]', '', text)
        
        return text.strip()
    
    def _remove_spaces(self, text: str) -> str:
        """Remove all spaces from text."""
        return text.replace(' ', '')
    
    def _get_ngrams(self, text: str, n: int = 2) -> set[str]:
        """Get character n-grams from text."""
        text = self._remove_spaces(text)
        if len(text) < n:
            return {text}
        return {text[i:i+n] for i in range(len(text) - n + 1)}
    
    def _ngram_similarity(self, text1: str, text2: str) -> float:
        """Calculate Jaccard similarity using n-grams."""
        n = self.config.ngram_size
        ngrams1 = self._get_ngrams(text1, n)
        ngrams2 = self._get_ngrams(text2, n)
        
        if not ngrams1 or not ngrams2:
            return 0.0
        
        intersection = ngrams1 & ngrams2
        union = ngrams1 | ngrams2
        
        return len(intersection) / len(union)
    
    def _levenshtein_similarity(self, text1: str, text2: str) -> float:
        """Calculate normalized Levenshtein similarity."""
        jf = _get_jellyfish()
        if jf:
            distance = jf.levenshtein_distance(text1, text2)
            max_len = max(len(text1), len(text2))
            if max_len == 0:
                return 1.0
            return 1.0 - (distance / max_len)
        
        # Fallback to rapidfuzz
        rf = _get_rapidfuzz()
        if rf:
            fuzz, _ = rf
            return fuzz.ratio(text1, text2) / 100.0
        
        # Basic fallback
        return 1.0 if text1 == text2 else 0.0
    
    def _jaro_winkler_similarity(self, text1: str, text2: str) -> float:
        """Calculate Jaro-Winkler similarity."""
        jf = _get_jellyfish()
        if jf:
            return jf.jaro_winkler_similarity(text1, text2)
        
        # Fallback to rapidfuzz
        rf = _get_rapidfuzz()
        if rf:
            fuzz, _ = rf
            return fuzz.ratio(text1, text2) / 100.0
        
        return 1.0 if text1 == text2 else 0.0
    
    def _phonetic_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate phonetic similarity using Metaphone.
        
        This helps with STT errors where words sound similar.
        """
        jf = _get_jellyfish()
        if not jf:
            return 0.0
        
        # Get metaphone codes for each word
        words1 = text1.split()
        words2 = text2.split()
        
        if not words1 or not words2:
            return 0.0
        
        # Compare metaphone codes
        codes1 = [jf.metaphone(w) for w in words1]
        codes2 = [jf.metaphone(w) for w in words2]
        
        # Join codes and compare
        code_str1 = ''.join(codes1)
        code_str2 = ''.join(codes2)
        
        if code_str1 == code_str2:
            return 1.0
        
        # Calculate similarity of phonetic codes
        return self._levenshtein_similarity(code_str1, code_str2)
    
    def _boundary_shift_similarity(self, text1: str, text2: str) -> float:
        """
        Handle word boundary shift errors from STT.
        
        E.g., "lista plików" -> "list aplików"
        
        Compares texts with spaces removed to detect shifted boundaries.
        """
        # Remove spaces and compare
        no_space1 = self._remove_spaces(text1)
        no_space2 = self._remove_spaces(text2)
        
        return self._levenshtein_similarity(no_space1, no_space2)
    
    def _combined_similarity(
        self, 
        input_text: str, 
        phrase_text: str,
    ) -> tuple[float, str]:
        """
        Calculate combined similarity using multiple algorithms.
        
        Returns (score, best_algorithm).
        """
        norm_input = self._normalize(input_text)
        norm_phrase = self._normalize(phrase_text)
        
        scores = {}
        
        # 1. Exact match after normalization
        if norm_input == norm_phrase:
            return (1.0, "exact")
        
        # 2. Levenshtein similarity
        scores["levenshtein"] = self._levenshtein_similarity(norm_input, norm_phrase)
        
        # 3. Jaro-Winkler similarity
        scores["jaro_winkler"] = self._jaro_winkler_similarity(norm_input, norm_phrase)
        
        # 4. N-gram similarity
        scores["ngram"] = self._ngram_similarity(norm_input, norm_phrase)
        
        # 5. Phonetic similarity
        scores["phonetic"] = self._phonetic_similarity(norm_input, norm_phrase)
        
        # 6. Boundary shift similarity (for STT errors)
        scores["boundary_shift"] = self._boundary_shift_similarity(norm_input, norm_phrase)
        
        # Find best score
        best_algo = max(scores, key=scores.get)
        best_score = scores[best_algo]
        
        # Calculate weighted combined score
        combined = (
            scores["levenshtein"] * 0.25 +
            scores["jaro_winkler"] * 0.25 +
            scores["ngram"] * 0.15 +
            scores["phonetic"] * self.config.phonetic_weight +
            scores["boundary_shift"] * 0.05
        )
        
        # Use best individual score if it's significantly better
        if best_score > combined + 0.1:
            return (best_score, best_algo)
        
        return (combined, "combined")
    
    def match(self, input_text: str) -> Optional[MatchResult]:
        """
        Match input text against all phrases in schema.
        
        Returns best match or None if no match above threshold.
        """
        if not input_text or not self.phrases:
            return None
        
        norm_input = self._normalize(input_text)
        best_result: Optional[MatchResult] = None
        best_score = 0.0
        
        for phrase in self.phrases:
            # Check main phrase
            score, algo = self._combined_similarity(input_text, phrase.phrase)
            
            if score > best_score:
                best_score = score
                best_result = MatchResult(
                    matched=score >= self.config.combined_threshold,
                    phrase=phrase.phrase,
                    domain=phrase.domain,
                    intent=phrase.intent,
                    confidence=score,
                    algorithm=algo,
                    original_input=input_text,
                    normalized_input=norm_input,
                )
            
            # Check aliases
            for alias in phrase.aliases:
                alias_score, alias_algo = self._combined_similarity(input_text, alias)
                if alias_score > best_score:
                    best_score = alias_score
                    best_result = MatchResult(
                        matched=alias_score >= self.config.combined_threshold,
                        phrase=phrase.phrase,
                        domain=phrase.domain,
                        intent=phrase.intent,
                        confidence=alias_score,
                        algorithm=alias_algo,
                        original_input=input_text,
                        normalized_input=norm_input,
                        details={"matched_alias": alias},
                    )
        
        if best_result and best_result.matched:
            return best_result
        
        return None
    
    def match_all(
        self, 
        input_text: str, 
        top_k: int = 5,
    ) -> list[MatchResult]:
        """
        Get top K matches for input text.
        
        Useful for disambiguation or suggestions.
        """
        if not input_text or not self.phrases:
            return []
        
        norm_input = self._normalize(input_text)
        results = []
        
        for phrase in self.phrases:
            score, algo = self._combined_similarity(input_text, phrase.phrase)
            
            result = MatchResult(
                matched=score >= self.config.combined_threshold,
                phrase=phrase.phrase,
                domain=phrase.domain,
                intent=phrase.intent,
                confidence=score,
                algorithm=algo,
                original_input=input_text,
                normalized_input=norm_input,
            )
            results.append(result)
            
            # Check aliases
            for alias in phrase.aliases:
                alias_score, alias_algo = self._combined_similarity(input_text, alias)
                if alias_score > score:
                    result = MatchResult(
                        matched=alias_score >= self.config.combined_threshold,
                        phrase=phrase.phrase,
                        domain=phrase.domain,
                        intent=phrase.intent,
                        confidence=alias_score,
                        algorithm=alias_algo,
                        original_input=input_text,
                        normalized_input=norm_input,
                        details={"matched_alias": alias},
                    )
                    results.append(result)
        
        # Sort by confidence and return top K
        results.sort(key=lambda r: r.confidence, reverse=True)
        return results[:top_k]
    
    def suggest_correction(self, input_text: str) -> Optional[str]:
        """
        Suggest corrected phrase for input with STT errors.
        
        Returns corrected phrase or None.
        """
        result = self.match(input_text)
        if result and result.matched:
            return result.phrase
        return None
    
    def export_schema(self, path: Path) -> None:
        """Export current phrases to JSON schema."""
        data = {
            "version": "1.0",
            "description": "Multilingual phrase schema for fuzzy matching",
            "phrases": [
                {
                    "phrase": p.phrase,
                    "domain": p.domain,
                    "intent": p.intent,
                    "language": p.language,
                    "aliases": p.aliases,
                    "phonetic_variants": p.phonetic_variants,
                }
                for p in self.phrases
            ]
        }
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
