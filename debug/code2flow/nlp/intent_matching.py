"""Intent Matching - Steps 2a-2e.

2a. Fuzzy matching threshold (0.0-1.0)
2b. Semantic similarity threshold
2c. Keyword matching weight
2d. Context window size
2e. Multi-intent resolution strategy
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher

from .config import IntentMatchingConfig


@dataclass
class IntentMatch:
    """Single intent match result."""
    intent: str
    confidence: float
    matched_phrase: str
    match_type: str  # exact, fuzzy, keyword, semantic
    context_score: float = 0.0


@dataclass
class IntentMatchingResult:
    """Result of intent matching."""
    query: str
    primary_intent: Optional[IntentMatch] = None
    all_matches: List[IntentMatch] = field(default_factory=list)
    strategy_used: str = "best_match"
    
    def get_best_intent(self) -> Optional[str]:
        """Get the best matching intent name."""
        if self.primary_intent:
            return self.primary_intent.intent
        return None
    
    def get_confidence(self) -> float:
        """Get confidence of best match."""
        if self.primary_intent:
            return self.primary_intent.confidence
        return 0.0


class IntentMatcher:
    """Match queries to intents using fuzzy and keyword matching."""
    
    # Predefined intent patterns
    DEFAULT_INTENTS = {
        "find_function": [
            "find function", "lookup function", "search function",
            "znajdź funkcję", "szukaj funkcji", "gdzie jest funkcja"
        ],
        "find_class": [
            "find class", "lookup class", "search class",
            "znajdź klasę", "szukaj klasy", "gdzie jest klasa"
        ],
        "analyze_flow": [
            "analyze flow", "show flow", "trace flow",
            "analizuj przepływ", "pokaż przepływ", "śledź przepływ"
        ],
        "show_call_graph": [
            "show call graph", "display call graph", "call graph",
            "pokaż graf wywołań", "graf wywołań"
        ],
        "find_dependencies": [
            "find dependencies", "show dependencies", "what depends on",
            "znajdź zależności", "pokaż zależności"
        ],
        "explain_code": [
            "explain code", "explain function", "what does",
            "wyjaśnij kod", "wyjaśnij funkcję", "co robi"
        ],
    }
    
    def __init__(
        self,
        config: Optional[IntentMatchingConfig] = None,
        intents: Optional[Dict[str, List[str]]] = None
    ):
        self.config = config or IntentMatchingConfig()
        self.intents = intents or self.DEFAULT_INTENTS
    
    def match(
        self,
        query: str,
        context: Optional[List[str]] = None
    ) -> IntentMatchingResult:
        """Match query to intents (steps 2a-2e)."""
        result = IntentMatchingResult(query=query)
        
        # 2a. Fuzzy matching
        fuzzy_matches = self._fuzzy_match(query)
        
        # 2c. Keyword matching
        keyword_matches = self._keyword_match(query)
        
        # 2d. Context scoring
        if context:
            self._apply_context(query, fuzzy_matches + keyword_matches, context)
        
        # Combine and deduplicate
        all_matches = self._combine_matches(fuzzy_matches + keyword_matches)
        result.all_matches = all_matches
        
        # 2e. Multi-intent resolution
        result.primary_intent = self._resolve_multi_intent(all_matches)
        result.strategy_used = self.config.multi_intent_strategy
        
        return result
    
    def _fuzzy_match(self, query: str) -> List[IntentMatch]:
        """2a. Fuzzy matching with configurable threshold."""
        matches = []
        threshold = self.config.fuzzy_threshold
        
        for intent, phrases in self.intents.items():
            for phrase in phrases:
                similarity = self._calculate_similarity(query, phrase)
                if similarity >= threshold:
                    matches.append(IntentMatch(
                        intent=intent,
                        confidence=similarity,
                        matched_phrase=phrase,
                        match_type="fuzzy"
                    ))
        
        return matches
    
    def _keyword_match(self, query: str) -> List[IntentMatch]:
        """2c. Keyword matching with configurable weight."""
        matches = []
        query_words = set(query.lower().split())
        
        for intent, phrases in self.intents.items():
            best_score = 0.0
            best_phrase = ""
            
            for phrase in phrases:
                phrase_words = set(phrase.lower().split())
                
                # Calculate Jaccard similarity
                intersection = len(query_words & phrase_words)
                union = len(query_words | phrase_words)
                
                if union > 0:
                    score = intersection / union
                    if score > best_score:
                        best_score = score
                        best_phrase = phrase
            
            # Apply keyword weight
            weighted_score = best_score * self.config.keyword_weight
            
            if weighted_score > 0:
                matches.append(IntentMatch(
                    intent=intent,
                    confidence=weighted_score,
                    matched_phrase=best_phrase,
                    match_type="keyword"
                ))
        
        return matches
    
    def _apply_context(
        self,
        query: str,
        matches: List[IntentMatch],
        context: List[str]
    ) -> None:
        """2d. Apply context window scoring."""
        window_size = self.config.context_window
        context_text = ' '.join(context[-window_size:]).lower()
        
        for match in matches:
            # Boost confidence if intent keywords appear in context
            intent_phrases = self.intents.get(match.intent, [])
            context_score = 0.0
            
            for phrase in intent_phrases:
                phrase_words = phrase.lower().split()
                for word in phrase_words:
                    if word in context_text:
                        context_score += 0.1
            
            match.context_score = min(context_score, 0.5)  # Cap at 0.5
            match.confidence = min(1.0, match.confidence + match.context_score)
    
    def _combine_matches(self, matches: List[IntentMatch]) -> List[IntentMatch]:
        """Combine and deduplicate matches, keeping highest confidence per intent."""
        best_by_intent: Dict[str, IntentMatch] = {}
        
        for match in matches:
            if match.intent not in best_by_intent:
                best_by_intent[match.intent] = match
            elif match.confidence > best_by_intent[match.intent].confidence:
                best_by_intent[match.intent] = match
        
        # Sort by confidence descending
        return sorted(best_by_intent.values(), key=lambda m: m.confidence, reverse=True)
    
    def _resolve_multi_intent(self, matches: List[IntentMatch]) -> Optional[IntentMatch]:
        """2e. Multi-intent resolution strategy."""
        if not matches:
            return None
        
        strategy = self.config.multi_intent_strategy
        
        if strategy == "best_match":
            return matches[0]
        
        elif strategy == "combine":
            # Combine top matches if close in confidence
            if len(matches) >= 2:
                gap = matches[0].confidence - matches[1].confidence
                if gap < 0.1:  # Within 0.1 confidence
                    # Return combined intent
                    combined = IntentMatch(
                        intent=f"{matches[0].intent}+{matches[1].intent}",
                        confidence=(matches[0].confidence + matches[1].confidence) / 2,
                        matched_phrase=f"{matches[0].matched_phrase} | {matches[1].matched_phrase}",
                        match_type="combined"
                    )
                    return combined
            return matches[0]
        
        elif strategy == "sequential":
            # Return list of intents to process sequentially
            return matches[0]  # For now, just return best
        
        return matches[0]
    
    def _calculate_similarity(self, a: str, b: str) -> float:
        """Calculate string similarity using configured algorithm."""
        algorithm = self.config.fuzzy_algorithm
        
        if algorithm == "ratio":
            return SequenceMatcher(None, a.lower(), b.lower()).ratio()
        
        elif algorithm == "partial_ratio":
            # Check if one is substring of other
            a_lower = a.lower()
            b_lower = b.lower()
            
            if a_lower in b_lower or b_lower in a_lower:
                return 0.9  # High score for partial match
            
            return SequenceMatcher(None, a_lower, b_lower).ratio()
        
        elif algorithm == "token_sort_ratio":
            # Sort tokens and compare
            a_sorted = ' '.join(sorted(a.lower().split()))
            b_sorted = ' '.join(sorted(b.lower().split()))
            return SequenceMatcher(None, a_sorted, b_sorted).ratio()
        
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()
    
    # Individual step methods
    def step_2a_fuzzy_match(self, query: str, phrase: str) -> float:
        """Step 2a: Calculate fuzzy match score."""
        return self._calculate_similarity(query, phrase)
    
    def step_2b_semantic_match(self, query: str, phrase: str) -> float:
        """Step 2b: Semantic similarity (placeholder for embeddings)."""
        # Placeholder - would use sentence embeddings in production
        return self._calculate_similarity(query, phrase)
    
    def step_2c_keyword_match(self, query: str, phrase: str) -> float:
        """Step 2c: Keyword matching score."""
        query_words = set(query.lower().split())
        phrase_words = set(phrase.lower().split())
        
        if not phrase_words:
            return 0.0
        
        intersection = len(query_words & phrase_words)
        return intersection / len(phrase_words)
    
    def step_2d_context_score(self, query: str, context: List[str]) -> float:
        """Step 2d: Calculate context relevance score."""
        window = ' '.join(context[-self.config.context_window:]).lower()
        query_words = query.lower().split()
        
        score = 0.0
        for word in query_words:
            if word in window:
                score += 0.1
        
        return min(score, 0.5)
    
    def step_2e_resolve_intents(self, matches: List[IntentMatch]) -> Optional[IntentMatch]:
        """Step 2e: Resolve multiple intent matches."""
        return self._resolve_multi_intent(matches)
