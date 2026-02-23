"""
Iteration 9: Hybrid Rule+LLM Generator.

Optimizes costs by using rules first, LLM as fallback only when needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
import time

from nlp2cmd.generation.pipeline import RuleBasedPipeline, PipelineResult
from nlp2cmd.generation.llm_multi import MultiDomainGenerator, MultiDomainResult
from nlp2cmd.generation.llm_simple import LLMClient, LLMConfig


@dataclass
class HybridResult:
    """Result of hybrid generation."""
    
    command: str
    domain: str
    source: str  # "rules" or "llm"
    confidence: float
    latency_ms: float
    success: bool
    
    # Detailed results
    rule_result: Optional[PipelineResult] = None
    llm_result: Optional[MultiDomainResult] = None
    
    # Cost tracking
    llm_calls: int = 0
    estimated_cost: float = 0.0
    
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class HybridStats:
    """Statistics for hybrid generator."""
    
    total_requests: int = 0
    rule_hits: int = 0
    llm_fallbacks: int = 0
    total_llm_calls: int = 0
    total_latency_ms: float = 0.0
    estimated_total_cost: float = 0.0
    
    @property
    def rule_hit_rate(self) -> float:
        """Calculate rule hit rate."""
        if self.total_requests == 0:
            return 0.0
        return self.rule_hits / self.total_requests
    
    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency."""
        if self.total_requests == 0:
            return 0.0
        return self.total_latency_ms / self.total_requests
    
    @property
    def cost_savings_percent(self) -> float:
        """Estimate cost savings vs pure LLM."""
        if self.total_requests == 0:
            return 0.0
        # Assuming all requests would need LLM otherwise
        return self.rule_hit_rate * 100
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_requests": self.total_requests,
            "rule_hits": self.rule_hits,
            "llm_fallbacks": self.llm_fallbacks,
            "rule_hit_rate": f"{self.rule_hit_rate:.1%}",
            "avg_latency_ms": f"{self.avg_latency_ms:.2f}",
            "estimated_cost": f"${self.estimated_total_cost:.4f}",
            "cost_savings": f"{self.cost_savings_percent:.1f}%",
        }


class HybridGenerator:
    """
    Use rules first, LLM as fallback.
    
    Optimizes for cost and latency by attempting rule-based
    generation first, only falling back to LLM when:
    - Rule confidence is below threshold
    - Required entities are missing
    - Domain cannot be determined
    
    Example:
        generator = HybridGenerator(
            rule_pipeline=RuleBasedPipeline(),
            llm_generator=MultiDomainGenerator(llm_client),
            confidence_threshold=0.7
        )
        result = await generator.generate("Pokaż użytkowników")
        # Uses rules (fast, free) if confident enough
        # Falls back to LLM if rules fail
    """
    
    # Estimated cost per LLM call (GPT-4)
    COST_PER_LLM_CALL = 0.01
    
    # Required entities per domain/intent for rule-based generation
    REQUIRED_ENTITIES: dict[tuple[str, str], list[str]] = {
        ("sql", "select"): ["table"],
        ("sql", "insert"): ["table", "values"],
        ("sql", "update"): ["table", "values"],
        ("sql", "delete"): ["table"],
        ("shell", "find"): ["path"],
        ("shell", "grep"): ["pattern"],
        ("docker", "logs"): ["container"],
        ("docker", "exec"): ["container"],
        ("kubernetes", "get"): ["resource_type"],
        ("kubernetes", "logs"): ["pod"],
        ("kubernetes", "scale"): ["resource_name", "replicas"],
    }
    
    def __init__(
        self,
        rule_pipeline: RuleBasedPipeline,
        llm_generator: Optional[MultiDomainGenerator] = None,
        llm_client: Optional[LLMClient] = None,
        confidence_threshold: float = 0.7,
        always_validate_with_llm: bool = False,
    ):
        """
        Initialize hybrid generator.
        
        Args:
            rule_pipeline: Rule-based pipeline for fast generation
            llm_generator: LLM generator for fallback (or created from client)
            llm_client: LLM client (if llm_generator not provided)
            confidence_threshold: Minimum confidence to use rule result
            always_validate_with_llm: Also validate rule results with LLM
        """
        self.rules = rule_pipeline
        self.confidence_threshold = confidence_threshold
        self.always_validate = always_validate_with_llm
        
        if llm_generator:
            self.llm = llm_generator
        elif llm_client:
            self.llm = MultiDomainGenerator(llm_client)
        else:
            self.llm = None
        
        self.stats = HybridStats()
    
    async def generate(
        self,
        text: str,
        context: Optional[dict[str, Any]] = None,
        force_llm: bool = False,
    ) -> HybridResult:
        """
        Generate DSL using hybrid approach.
        
        Args:
            text: Natural language input
            context: Additional context
            force_llm: Skip rules, go directly to LLM
            
        Returns:
            HybridResult with generated command
        """
        start_time = time.time()
        self.stats.total_requests += 1
        
        # Force LLM if requested
        if force_llm and self.llm:
            return await self._generate_with_llm(text, context, start_time)
        
        # Try rules first
        rule_result = self.rules.process(text)
        
        # Check if rules succeeded with high confidence
        if self._should_use_rule_result(rule_result):
            self.stats.rule_hits += 1
            latency = (time.time() - start_time) * 1000
            self.stats.total_latency_ms += latency
            
            return HybridResult(
                command=rule_result.command,
                domain=rule_result.domain,
                source="rules",
                confidence=rule_result.detection_confidence,
                latency_ms=latency,
                success=rule_result.success,
                rule_result=rule_result,
                llm_calls=0,
                estimated_cost=0.0,
                metadata=dict(getattr(rule_result, "metadata", {}) or {}),
            )
        
        # Fallback to LLM
        if self.llm is None:
            # No LLM available - return rule result anyway
            latency = (time.time() - start_time) * 1000
            self.stats.total_latency_ms += latency
            
            return HybridResult(
                command=rule_result.command,
                domain=rule_result.domain,
                source="rules",
                confidence=rule_result.detection_confidence,
                latency_ms=latency,
                success=rule_result.success,
                rule_result=rule_result,
                errors=["LLM fallback not available"],
                metadata=dict(getattr(rule_result, "metadata", {}) or {}),
            )
        
        return await self._generate_with_llm(text, context, start_time, rule_result)
    
    def _should_use_rule_result(self, result: PipelineResult) -> bool:
        """Determine if rule result is good enough."""
        # Must be successful
        if not result.success:
            return False
        
        # Must have sufficient confidence
        if result.detection_confidence < self.confidence_threshold:
            return False
        
        # Must have required entities
        required = self.REQUIRED_ENTITIES.get(
            (result.domain, result.intent), []
        )
        for entity in required:
            if entity not in result.entities:
                return False
        
        return True
    
    async def _generate_with_llm(
        self,
        text: str,
        context: Optional[dict[str, Any]],
        start_time: float,
        rule_result: Optional[PipelineResult] = None,
    ) -> HybridResult:
        """Generate using LLM."""
        self.stats.llm_fallbacks += 1
        self.stats.total_llm_calls += 1
        
        llm_result = await self.llm.generate(text, context)
        
        latency = (time.time() - start_time) * 1000
        self.stats.total_latency_ms += latency
        self.stats.estimated_total_cost += self.COST_PER_LLM_CALL
        
        return HybridResult(
            command=llm_result.command,
            domain=llm_result.domain,
            source="llm",
            confidence=llm_result.routing_confidence,
            latency_ms=latency,
            success=llm_result.success,
            rule_result=rule_result,
            llm_result=llm_result,
            llm_calls=1,
            estimated_cost=self.COST_PER_LLM_CALL,
            errors=[llm_result.error] if llm_result.error else [],
            metadata=dict(getattr(rule_result, "metadata", {}) or {}),
        )
    
    async def generate_batch(
        self,
        texts: list[str],
        context: Optional[dict[str, Any]] = None,
    ) -> list[HybridResult]:
        """Generate for multiple inputs."""
        import asyncio
        tasks = [self.generate(text, context) for text in texts]
        return await asyncio.gather(*tasks)
    
    def get_stats(self) -> HybridStats:
        """Get generation statistics."""
        return self.stats
    
    def reset_stats(self) -> None:
        """Reset statistics."""
        self.stats = HybridStats()
    
    def set_confidence_threshold(self, threshold: float) -> None:
        """Update confidence threshold."""
        self.confidence_threshold = threshold


class AdaptiveHybridGenerator(HybridGenerator):
    """
    Hybrid generator with adaptive threshold.
    
    Automatically adjusts confidence threshold based on
    LLM validation of rule results.
    """
    
    def __init__(
        self,
        rule_pipeline: RuleBasedPipeline,
        llm_generator: Optional[MultiDomainGenerator] = None,
        llm_client: Optional[LLMClient] = None,
        initial_threshold: float = 0.7,
        min_threshold: float = 0.5,
        max_threshold: float = 0.95,
        adaptation_rate: float = 0.1,
    ):
        super().__init__(
            rule_pipeline,
            llm_generator,
            llm_client,
            initial_threshold,
        )
        self.min_threshold = min_threshold
        self.max_threshold = max_threshold
        self.adaptation_rate = adaptation_rate
        
        # Track validation results for adaptation
        self._validation_history: list[bool] = []
    
    def _adapt_threshold(self, rule_was_correct: bool) -> None:
        """Adapt threshold based on validation."""
        self._validation_history.append(rule_was_correct)
        
        # Keep last 100 results
        if len(self._validation_history) > 100:
            self._validation_history = self._validation_history[-100:]
        
        # Calculate recent accuracy
        if len(self._validation_history) >= 10:
            recent_accuracy = sum(self._validation_history[-10:]) / 10
            
            if recent_accuracy > 0.9:
                # Rules are very accurate - lower threshold
                self.confidence_threshold = max(
                    self.min_threshold,
                    self.confidence_threshold - self.adaptation_rate
                )
            elif recent_accuracy < 0.7:
                # Rules are less accurate - raise threshold
                self.confidence_threshold = min(
                    self.max_threshold,
                    self.confidence_threshold + self.adaptation_rate
                )


def create_hybrid_generator(
    llm_client: Optional[LLMClient] = None,
    confidence_threshold: float = 0.7,
) -> HybridGenerator:
    """
    Factory function to create a hybrid generator.
    
    Args:
        llm_client: Optional LLM client for fallback
        confidence_threshold: Threshold for rule acceptance
        
    Returns:
        Configured HybridGenerator
    """
    from nlp2cmd.generation.pipeline import RuleBasedPipeline
    
    rule_pipeline = RuleBasedPipeline()
    
    llm_generator = None
    if llm_client:
        llm_generator = MultiDomainGenerator(llm_client)
    
    return HybridGenerator(
        rule_pipeline=rule_pipeline,
        llm_generator=llm_generator,
        confidence_threshold=confidence_threshold,
    )
