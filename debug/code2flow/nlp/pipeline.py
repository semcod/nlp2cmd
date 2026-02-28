"""Main NLP Pipeline - Integration of all components (Steps 4a-4e).

4a. Pipeline orchestration
4b. Result aggregation
4c. Confidence scoring
4d. Fallback handling
4e. Output formatting
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path

from .config import NLPConfig, FAST_NLP_CONFIG
from .normalization import QueryNormalizer, NormalizationResult
from .intent_matching import IntentMatcher, IntentMatchingResult
from .entity_resolution import EntityResolver, EntityResolutionResult, Entity


@dataclass
class PipelineStage:
    """Single pipeline stage result."""
    stage_name: str
    success: bool
    result: Any
    execution_time_ms: float = 0.0
    error: Optional[str] = None


@dataclass
class NLPPipelineResult:
    """Complete NLP pipeline result (4b-4e aggregation)."""
    # 4b. Aggregated results
    original_query: str
    normalized_query: NormalizationResult
    intent_result: IntentMatchingResult
    entity_result: EntityResolutionResult
    
    # 4c. Confidence scoring
    overall_confidence: float = 0.0
    stage_confidences: Dict[str, float] = field(default_factory=dict)
    
    # 4d. Fallback information
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    
    # 4e. Formatted output
    formatted_response: Optional[str] = None
    action_recommendation: Optional[str] = None
    
    # Execution metadata
    stages: List[PipelineStage] = field(default_factory=list)
    total_execution_time_ms: float = 0.0
    
    def is_successful(self) -> bool:
        """Check if pipeline produced actionable result."""
        return (
            self.overall_confidence >= 0.5
            and self.intent_result.primary_intent is not None
            and not self.fallback_used
        )
    
    def get_intent(self) -> Optional[str]:
        """Get resolved intent."""
        if self.intent_result.primary_intent:
            return self.intent_result.primary_intent.intent
        return None
    
    def get_entities(self) -> List[Entity]:
        """Get resolved entities."""
        return self.entity_result.entities
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "original_query": self.original_query,
            "normalized": self.normalized_query.normalized,
            "intent": self.get_intent(),
            "intent_confidence": self.intent_result.get_confidence(),
            "entities": [
                {
                    "name": e.name,
                    "type": e.entity_type,
                    "confidence": e.confidence,
                }
                for e in self.entity_result.entities[:5]
            ],
            "overall_confidence": self.overall_confidence,
            "fallback_used": self.fallback_used,
            "action": self.action_recommendation,
        }


class NLPPipeline:
    """Main NLP processing pipeline (4a-4e)."""
    
    def __init__(self, config: Optional[NLPConfig] = None):
        self.config = config or FAST_NLP_CONFIG
        
        # Initialize components
        self.normalizer = QueryNormalizer(self.config.normalization)
        self.intent_matcher = IntentMatcher(self.config.intent_matching)
        self.entity_resolver = EntityResolver(self.config.entity_resolution)
        
        # Execution history for context
        self.query_history: List[str] = []
    
    def process(self, query: str, language: str = "en") -> NLPPipelineResult:
        """Process query through full pipeline (4a-4e)."""
        import time
        
        start_time = time.time()
        stages = []
        
        # 4a. Pipeline orchestration - Step 1: Normalization
        norm_start = time.time()
        normalized = self._step_normalize(query, language)
        norm_time = (time.time() - norm_start) * 1000
        
        stages.append(PipelineStage(
            stage_name="normalization",
            success=True,
            result=normalized,
            execution_time_ms=norm_time
        ))
        
        # Step 2: Intent Matching
        intent_start = time.time()
        intent_result = self._step_match_intent(normalized.normalized)
        intent_time = (time.time() - intent_start) * 1000
        
        intent_success = intent_result.primary_intent is not None
        stages.append(PipelineStage(
            stage_name="intent_matching",
            success=intent_success,
            result=intent_result,
            execution_time_ms=intent_time
        ))
        
        # Step 3: Entity Resolution
        entity_start = time.time()
        
        # Determine expected entity types from intent
        expected_types = self._infer_entity_types(intent_result)
        
        entity_result = self._step_resolve_entities(
            normalized.normalized,
            expected_types=expected_types,
            context=normalized.normalized
        )
        entity_time = (time.time() - entity_start) * 1000
        
        entity_success = len(entity_result.entities) > 0
        stages.append(PipelineStage(
            stage_name="entity_resolution",
            success=entity_success,
            result=entity_result,
            execution_time_ms=entity_time
        ))
        
        # 4b. Result aggregation
        total_time = (time.time() - start_time) * 1000
        
        result = NLPPipelineResult(
            original_query=query,
            normalized_query=normalized,
            intent_result=intent_result,
            entity_result=entity_result,
            stages=stages,
            total_execution_time_ms=total_time,
        )
        
        # 4c. Confidence scoring
        result.overall_confidence = self._calculate_overall_confidence(result)
        result.stage_confidences = {
            "normalization": 1.0,  # Normalization is deterministic
            "intent": intent_result.get_confidence(),
            "entity": self._calculate_entity_confidence(entity_result),
        }
        
        # 4d. Fallback handling
        if result.overall_confidence < 0.5:
            result = self._apply_fallback(result)
        
        # 4e. Output formatting
        result.action_recommendation = self._format_action(result)
        result.formatted_response = self._format_response(result)
        
        # Update history
        self.query_history.append(query)
        if len(self.query_history) > 10:
            self.query_history.pop(0)
        
        return result
    
    def _step_normalize(self, query: str, language: str) -> NormalizationResult:
        """Step 1: Query normalization."""
        if not self.config.enable_normalization:
            # Skip normalization, return identity
            return NormalizationResult(
                original=query,
                normalized=query,
                tokens=query.split(),
                language=language,
                steps_applied=["skipped"]
            )
        
        return self.normalizer.normalize(query, language)
    
    def _step_match_intent(self, normalized_query: str) -> IntentMatchingResult:
        """Step 2: Intent matching."""
        if not self.config.enable_intent_matching:
            return IntentMatchingResult(query=normalized_query)
        
        return self.intent_matcher.match(
            normalized_query,
            context=self.query_history[-3:] if self.query_history else None
        )
    
    def _step_resolve_entities(
        self,
        normalized_query: str,
        expected_types: Optional[List[str]] = None,
        context: Optional[str] = None
    ) -> EntityResolutionResult:
        """Step 3: Entity resolution."""
        if not self.config.enable_entity_resolution:
            return EntityResolutionResult(query=normalized_query)
        
        return self.entity_resolver.resolve(
            normalized_query,
            context=context,
            expected_types=expected_types
        )
    
    def _infer_entity_types(
        self,
        intent_result: IntentMatchingResult
    ) -> Optional[List[str]]:
        """Infer expected entity types from matched intent."""
        if not intent_result.primary_intent:
            return None
        
        intent = intent_result.primary_intent.intent
        
        # Map intents to expected entity types
        intent_to_entities = {
            "find_function": ["function"],
            "find_class": ["class"],
            "analyze_flow": ["function", "class"],
            "show_call_graph": ["function", "class", "module"],
            "find_dependencies": ["module", "file"],
            "explain_code": ["function", "class"],
        }
        
        return intent_to_entities.get(intent)
    
    def _calculate_overall_confidence(self, result: NLPPipelineResult) -> float:
        """4c. Calculate overall pipeline confidence."""
        weights = {
            "intent": 0.5,
            "entity": 0.3,
            "normalization": 0.2,
        }
        
        intent_conf = result.intent_result.get_confidence()
        entity_conf = self._calculate_entity_confidence(result.entity_result)
        norm_conf = 1.0  # Normalization is reliable
        
        overall = (
            weights["intent"] * intent_conf +
            weights["entity"] * entity_conf +
            weights["normalization"] * norm_conf
        )
        
        return round(overall, 3)
    
    def _calculate_entity_confidence(self, entity_result: EntityResolutionResult) -> float:
        """Calculate aggregate entity confidence."""
        if not entity_result.entities:
            return 0.0
        
        # Use best entity confidence
        best = max(e.confidence for e in entity_result.entities)
        return best
    
    def _apply_fallback(self, result: NLPPipelineResult) -> NLPPipelineResult:
        """4d. Apply fallback strategies when confidence is low."""
        result.fallback_used = True
        
        # Try keyword-only matching as fallback
        if result.intent_result.get_confidence() < 0.3:
            # Re-run with lower thresholds
            self.intent_matcher.config.fuzzy_threshold = 0.5
            fallback_intent = self.intent_matcher.match(
                result.normalized_query.normalized
            )
            
            if fallback_intent.get_confidence() > result.intent_result.get_confidence():
                result.intent_result = fallback_intent
                result.fallback_reason = "lowered_threshold"
            
            # Restore original threshold
            self.intent_matcher.config.fuzzy_threshold = self.config.intent_matching.fuzzy_threshold
        
        # If still no intent, default to generic search
        if result.intent_result.get_confidence() < 0.2:
            from .intent_matching import IntentMatch
            result.intent_result.primary_intent = IntentMatch(
                intent="generic_search",
                confidence=0.3,
                matched_phrase=result.normalized_query.normalized,
                match_type="fallback"
            )
            result.fallback_reason = "generic_search"
        
        return result
    
    def _format_action(self, result: NLPPipelineResult) -> Optional[str]:
        """4e. Format action recommendation."""
        intent = result.get_intent()
        entities = result.get_entities()
        
        if not intent:
            return "Unable to determine action. Please clarify your query."
        
        # Format based on intent type
        if intent == "find_function":
            if entities:
                return f"Search for function: {entities[0].name}"
            return "Search for functions"
        
        elif intent == "find_class":
            if entities:
                return f"Search for class: {entities[0].name}"
            return "Search for classes"
        
        elif intent == "analyze_flow":
            if entities:
                return f"Analyze control flow of: {entities[0].name}"
            return "Analyze control flow"
        
        elif intent == "show_call_graph":
            return "Generate call graph visualization"
        
        elif intent == "generic_search":
            return f"Search for: {result.normalized_query.normalized}"
        
        return f"Execute: {intent}"
    
    def _format_response(self, result: NLPPipelineResult) -> str:
        """4e. Format human-readable response."""
        lines = [
            f"Query: {result.original_query}",
            f"Intent: {result.get_intent() or 'unknown'} (confidence: {result.overall_confidence:.2f})",
        ]
        
        if result.entity_result.entities:
            lines.append("Entities:")
            for e in result.entity_result.entities[:3]:
                lines.append(f"  - {e.name} ({e.entity_type}, {e.confidence:.2f})")
        
        if result.fallback_used:
            lines.append(f"[Fallback used: {result.fallback_reason}]")
        
        return "\n".join(lines)
    
    # Individual step methods for 4a-4e
    def step_4a_orchestrate(self, query: str) -> List[PipelineStage]:
        """Step 4a: Pipeline orchestration."""
        return self.process(query).stages
    
    def step_4b_aggregate(self, stages: List[PipelineStage]) -> NLPPipelineResult:
        """Step 4b: Result aggregation."""
        # This is done in process() method
        pass
    
    def step_4c_confidence(self, result: NLPPipelineResult) -> float:
        """Step 4c: Confidence scoring."""
        return self._calculate_overall_confidence(result)
    
    def step_4d_fallback(self, result: NLPPipelineResult) -> NLPPipelineResult:
        """Step 4d: Fallback handling."""
        return self._apply_fallback(result)
    
    def step_4e_format(self, result: NLPPipelineResult) -> str:
        """Step 4e: Output formatting."""
        return self._format_response(result)
