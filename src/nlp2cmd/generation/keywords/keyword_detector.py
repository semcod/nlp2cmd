"""
Keyword-based intent detection logic.

This module contains the core detection algorithms and logic
for matching keywords to intents and domains.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Optional

from .keyword_patterns import KeywordPatterns

logger = logging.getLogger(__name__)

# Lazy imports for heavy dependencies
_polish_support = None
_fuzzy_schema_matcher = None
_ml_classifier = None
_semantic_matcher = None
_spacy = None
_nlp_model = None
_nlp_model_loaded = False


def _get_polish_support():
    """Lazy load Polish support to avoid circular imports."""
    global _polish_support
    if _polish_support is None:
        try:
            from nlp2cmd.polish_support import polish_support
            _polish_support = polish_support
        except ImportError:
            _polish_support = False
    return _polish_support if _polish_support else None


def _get_fuzzy_schema_matcher():
    """Lazy load FuzzySchemaMatcher with multilingual phrases."""
    global _fuzzy_schema_matcher
    if _fuzzy_schema_matcher is None:
        try:
            from nlp2cmd.generation.fuzzy_schema_matcher import FuzzySchemaMatcher
            from pathlib import Path
            
            schema_paths = [
                Path(__file__).parent.parent.parent.parent / "data" / "multilingual_phrases.json",
                Path("data/multilingual_phrases.json"),
                Path("multilingual_phrases.json"),
            ]
            
            matcher = FuzzySchemaMatcher()
            for path in schema_paths:
                if path.exists():
                    matcher.load_schema(path)
                    break
            
            if not matcher.phrases:
                from nlp2cmd.generation.fuzzy_schema_matcher import create_multilingual_matcher
                matcher = create_multilingual_matcher()
            
            _fuzzy_schema_matcher = matcher
        except ImportError:
            _fuzzy_schema_matcher = False
    return _fuzzy_schema_matcher if _fuzzy_schema_matcher else None


def _get_ml_classifier():
    """Lazy load ML intent classifier for high-accuracy predictions."""
    global _ml_classifier
    enable_ml = str(
        os.environ.get("NLP2CMD_ENABLE_ML_CLASSIFIER")
        or os.environ.get("NLP2CMD_ENABLE_HEAVY_NLP")
        or ""
    ).strip().lower() in {"1", "true", "yes", "y", "on"}
    
    if not enable_ml:
        return None
    
    if _ml_classifier is None:
        try:
            from nlp2cmd.generation.ml_intent_classifier import get_ml_classifier
            _ml_classifier = get_ml_classifier()
            if _ml_classifier is None:
                _ml_classifier = False
        except ImportError:
            _ml_classifier = False
    return _ml_classifier if _ml_classifier else None


def _get_semantic_matcher():
    """Lazy load semantic matcher for high-accuracy predictions."""
    global _semantic_matcher
    enable_semantic = str(
        os.environ.get("NLP2CMD_ENABLE_SEMANTIC_MATCHING")
        or os.environ.get("NLP2CMD_ENABLE_HEAVY_NLP")
        or ""
    ).strip().lower() in {"1", "true", "yes", "y", "on"}
    
    if not enable_semantic:
        return None
    
    if _semantic_matcher is None:
        try:
            from nlp2cmd.generation.semantic_matcher_optimized import OptimizedSemanticMatcher
            _semantic_matcher = OptimizedSemanticMatcher()
        except ImportError:
            _semantic_matcher = False
    return _semantic_matcher if _semantic_matcher else None


def _get_spacy_model():
    """Lazy load spaCy model for lemmatization."""
    global _spacy, _nlp_model, _nlp_model_loaded
    enable_spacy = str(
        os.environ.get("NLP2CMD_ENABLE_SPACY_LEMMATIZATION")
        or os.environ.get("NLP2CMD_ENABLE_HEAVY_NLP")
        or ""
    ).strip().lower() in {"1", "true", "yes", "y", "on"}
    
    if not enable_spacy:
        return None
    
    if _nlp_model_loaded:
        return _nlp_model
    
    try:
        import spacy
        _spacy = spacy
        
        # Try to load Polish model first, fall back to English
        try:
            _nlp_model = spacy.load("pl_core_news_sm")
        except OSError:
            try:
                _nlp_model = spacy.load("en_core_web_sm")
            except OSError:
                logger.warning("No spaCy model available, falling back to basic tokenization")
                _nlp_model = None
        
        _nlp_model_loaded = True
        return _nlp_model
        
    except ImportError:
        logger.debug("spaCy not available")
        _nlp_model_loaded = True
        return None


@dataclass
class DetectionResult:
    """Result of intent detection."""
    
    domain: str
    intent: str
    confidence: float
    entities: dict[str, str] = None
    metadata: dict[str, any] = None
    matched: bool = True  # Whether detection was successful
    
    def __post_init__(self):
        if self.entities is None:
            self.entities = {}
        if self.metadata is None:
            self.metadata = {}


class KeywordIntentDetector:
    """
    Rule-based intent detection using keyword matching.
    
    No LLM needed - uses predefined keyword patterns to detect
    domain (sql, shell, docker, kubernetes) and intent.
    
    Example:
        detector = KeywordIntentDetector()
        result = detector.detect("Pokaż wszystkich użytkowników z tabeli users")
        # result.domain == 'sql', result.intent == 'select'
    """
    
    def __init__(
        self,
        patterns: Optional[KeywordPatterns] = None,
        confidence_threshold: float = 0.5,
    ):
        """
        Initialize keyword detector.
        
        Args:
            patterns: KeywordPatterns instance or None to create default
            confidence_threshold: Minimum confidence to return a match
        """
        self.patterns = patterns or KeywordPatterns()
        self.confidence_threshold = confidence_threshold
    
    def detect(self, text: str) -> DetectionResult:
        """
        Detect domain and intent from text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            DetectionResult with detected domain, intent, and confidence
        """
        if not text or not text.strip():
            return DetectionResult(domain="", intent="", confidence=0.0, matched=False)
        
        text_lower = text.lower()
        
        # Fast path checks for browser and search
        fast_result = self._fast_path_detection(text_lower)
        if fast_result:
            return fast_result
        
        # Enhanced detection with fuzzy matching
        fuzzy_result = self._fuzzy_detection(text)
        if fuzzy_result and fuzzy_result.confidence >= self.confidence_threshold:
            return fuzzy_result
        
        # ML-based detection if available
        ml_result = self._ml_detection(text)
        if ml_result and ml_result.confidence >= self.confidence_threshold:
            return ml_result
        
        # Semantic matching if available
        semantic_result = self._semantic_detection(text)
        if semantic_result and semantic_result.confidence >= self.confidence_threshold:
            return semantic_result
        
        # Traditional keyword matching
        result = self._keyword_detection(text, text_lower)
        
        # Set matched based on confidence threshold
        result.matched = result.confidence >= self.confidence_threshold
        
        return result
    
    def detect_all(self, text: str) -> list[DetectionResult]:
        """
        Detect all matching domains and intents.
        
        Args:
            text: Natural language input
            
        Returns:
            List of DetectionResult, sorted by confidence descending
        """
        if not text or not text.strip():
            return []
        
        text_lower = text.lower()
        results: list[DetectionResult] = []
        seen: set[tuple[str, str]] = set()
        
        # Get all possible matches from patterns
        for domain, intents in self.patterns.patterns.items():
            for intent, keywords in intents.items():
                for kw in keywords:
                    if self._match_keyword(text_lower, kw):
                        key = (domain, intent)
                        if key not in seen:
                            seen.add(key)
                            confidence = 0.7  # Base confidence for keyword matches
                            results.append(DetectionResult(
                                domain=domain,
                                intent=intent,
                                confidence=confidence
                            ))
        
        # Sort by confidence descending
        results.sort(key=lambda x: x.confidence, reverse=True)
        return results
    
    def _match_keyword(self, text_lower: str, keyword: str) -> bool:
        """Simple keyword matching."""
        return keyword.lower() in text_lower
    
    def _fast_path_detection(self, text_lower: str) -> Optional[DetectionResult]:
        """Fast path detection for common patterns."""
        # URL detection
        # IMPORTANT:
        # - Prefer explicit URLs (https?://...) over bare domain matches.
        # - Preserve the full path/query when present.
        # - If the user provides a bare domain (e.g. prototypowanie.pl),
        #   default to https:// so xdg-open doesn't treat it like a local file.

        def _normalize_url(raw: str) -> str:
            u = (raw or "").strip().strip("'\"")
            if not u:
                return u
            if u.startswith("http://") or u.startswith("https://") or u.startswith("file://"):
                return u
            if u.startswith("www."):
                return f"https://{u}"
            # If it looks like a domain[/path], default to https
            if re.match(r"^[a-zA-Z0-9][\w\-]*\.[a-zA-Z]{2,}(?:/[^\s'\"]*)?$", u):
                return f"https://{u}"
            return u

        # 1) Full explicit URLs
        url_match = re.search(r"\b(https?://[^\s'\"]+)", text_lower)
        if url_match:
            return DetectionResult(
                domain="browser",
                intent="navigate",
                confidence=0.95,
                entities={"url": _normalize_url(url_match.group(1))},
            )

        # 2) www.* URLs
        www_match = re.search(r"\b(www\.[^\s'\"]+)", text_lower)
        if www_match:
            return DetectionResult(
                domain="browser",
                intent="navigate",
                confidence=0.92,
                entities={"url": _normalize_url(www_match.group(1))},
            )

        # 3) Bare domains (optionally with a path)
        domain_match = re.search(
            r"\b([a-zA-Z0-9][\w\-]*\.(?:com|org|net|io|dev|pl|de|uk|eu|gov|edu|tv|co)(?:/[^\s'\"]*)?)\b",
            text_lower,
        )
        if domain_match:
            return DetectionResult(
                domain="browser",
                intent="navigate",
                confidence=0.9,
                entities={"url": _normalize_url(domain_match.group(1))},
            )
        
        # Browser keywords
        browser_keywords = self.patterns.fast_path_browser_keywords
        if any(kw in text_lower for kw in browser_keywords):
            return DetectionResult(
                domain="browser",
                intent="web_action",
                confidence=0.8,
            )
        
        # Search keywords
        search_keywords = self.patterns.fast_path_search_keywords
        if any(kw in text_lower for kw in search_keywords):
            return DetectionResult(
                domain="shell",
                intent="search_web",
                confidence=0.8,
            )
        
        return None
    
    def _fuzzy_detection(self, text: str) -> Optional[DetectionResult]:
        """Detection using fuzzy schema matching."""
        matcher = _get_fuzzy_schema_matcher()
        if not matcher:
            return None
        
        try:
            result = matcher.match(text)
            if result and result.confidence >= self.confidence_threshold:
                return DetectionResult(
                    domain=result.domain,
                    intent=result.intent,
                    confidence=result.confidence,
                    entities=result.entities or {},
                )
        except Exception as e:
            logger.debug(f"Fuzzy matching failed: {e}")
        
        return None
    
    def _ml_detection(self, text: str) -> Optional[DetectionResult]:
        """ML-based detection using trained classifier."""
        classifier = _get_ml_classifier()
        if not classifier:
            return None
        
        try:
            result = classifier.predict(text)
            if result and result.confidence >= self.confidence_threshold:
                return DetectionResult(
                    domain=result.domain,
                    intent=result.intent,
                    confidence=result.confidence,
                    entities=result.entities or {},
                )
        except Exception as e:
            logger.debug(f"ML detection failed: {e}")
        
        return None
    
    def _semantic_detection(self, text: str) -> Optional[DetectionResult]:
        """Semantic detection using sentence embeddings."""
        matcher = _get_semantic_matcher()
        if not matcher:
            return None
        
        try:
            result = matcher.match(text)
            if result and result.confidence >= self.confidence_threshold:
                return DetectionResult(
                    domain=result.domain,
                    intent=result.intent,
                    confidence=result.confidence,
                    entities=result.entities or {},
                )
        except Exception as e:
            logger.debug(f"Semantic matching failed: {e}")
        
        return None
    
    def _keyword_detection(self, text: str, text_lower: str) -> DetectionResult:
        """Traditional keyword-based detection."""
        best_match = DetectionResult(domain="", intent="", confidence=0.0, matched=False)
        
        # Check priority intents first
        for domain in self.patterns.list_domains():
            priority_intents = self.patterns.get_priority_intents(domain)
            for intent in priority_intents:
                patterns = self.patterns.get_intent_patterns(domain, intent)
                confidence = self._calculate_keyword_confidence(text_lower, patterns)
                
                if confidence > best_match.confidence:
                    best_match = DetectionResult(
                        domain=domain,
                        intent=intent,
                        confidence=confidence,
                    )
        
        # Check all intents if no priority match found
        if best_match.confidence < self.confidence_threshold:
            for domain in self.patterns.list_domains():
                for intent in self.patterns.list_intents(domain):
                    # Skip if already checked as priority
                    if intent in self.patterns.get_priority_intents(domain):
                        continue
                    
                    patterns = self.patterns.get_intent_patterns(domain, intent)
                    confidence = self._calculate_keyword_confidence(text_lower, patterns)
                    
                    if confidence > best_match.confidence:
                        best_match = DetectionResult(
                            domain=domain,
                            intent=intent,
                            confidence=confidence,
                        )
        
        # Apply domain boosters
        if best_match.domain:
            boosters = self.patterns.get_domain_boosters(best_match.domain)
            booster_confidence = self._calculate_keyword_confidence(text_lower, boosters)
            if booster_confidence > 0:
                best_match.confidence = min(1.0, best_match.confidence + 0.1)
        
        return best_match
    
    def _calculate_keyword_confidence(self, text: str, keywords: list[str]) -> float:
        """Calculate confidence based on keyword matches."""
        if not keywords:
            return 0.0
        
        matches = 0
        total_keywords = len(keywords)
        
        # Use enhanced tokenization if available
        tokens = self._tokenize_text(text)
        token_set = set(tokens)
        
        for keyword in keywords:
            if self._keyword_matches(keyword, text, token_set):
                matches += 1
        
        if matches == 0:
            return 0.0
        
        # Base confidence from keyword matches
        base_confidence = matches / total_keywords
        
        # Boost for multiple matches
        if matches >= 2:
            base_confidence = min(1.0, base_confidence + 0.2)
        
        return base_confidence
    
    def _tokenize_text(self, text: str) -> list[str]:
        """Tokenize text using available tools."""
        # Try spaCy first
        nlp = _get_spacy_model()
        if nlp:
            try:
                doc = nlp(text)
                tokens = []
                polish_support = _get_polish_support()
                
                for token in doc:
                    if polish_support and hasattr(polish_support, '_is_important_token'):
                        if polish_support._is_important_token(token):
                            original_text = token.text.lower()
                            lemma = (token.lemma_ or "").lower()
                            important_keywords = {
                                'restartuj', 'uruchom', 'zrestartuj', 'startuj', 'wystartuj',
                                'zatrzymaj', 'stopuj', 'usuń', 'skopiuj', 'przenieś', 'znajdź',
                                'pokaż', 'sprawdź', 'utwórz', 'zmień', 'restart', 'docker', 'ps',
                                'kill', 'run', 'stop', 'start', 'create', 'delete', 'remove',
                                'katalog', 'katalogi', 'usługa', 'usługi', 'usługę', 'serwis',
                                'komputer', 'system', 'proces', 'procesy'
                            }
                            if original_text in important_keywords or not lemma or len(lemma) <= 1:
                                tokens.append(original_text)
                            else:
                                tokens.append(lemma)
                    else:
                        tokens.append(token.text.lower())
                return tokens
            except Exception as e:
                logger.debug(f"spaCy tokenization failed: {e}")
        
        # Fallback to basic tokenization
        return re.findall(r'\b\w+\b', text.lower())
    
    def _keyword_matches(self, keyword: str, text: str, tokens: set[str]) -> bool:
        """Check if a keyword matches the text."""
        # Direct token match
        if keyword in tokens:
            return True
        
        # Multi-word keyword matching
        if ' ' in keyword:
            pattern = r'\s+'.join(map(re.escape, keyword.split()))
            return re.search(pattern, text) is not None
        
        # Special patterns for single keywords
        if len(keyword) <= 3 and re.fullmatch(r"[a-z0-9]+", keyword):
            return re.search(rf"(?<![a-z0-9_]){re.escape(keyword)}(?![a-z0-9_])", text) is not None
        
        # General substring search
        return keyword in text
