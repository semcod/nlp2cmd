"""
Pipeline components for NLP2CMD generation.

Contains core classes and utilities for the generation pipeline.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional


# Simple execution plan to avoid circular import
@dataclass
class SimpleExecutionPlan:
    """Simple execution plan for adapters."""
    intent: str
    entities: dict[str, Any]
    confidence: float
    text: str


@dataclass
class PipelineResult:
    """Result of the complete pipeline."""
    
    # Input
    input_text: str = ""
    
    # Detection
    domain: str = "unknown"
    intent: str = "unknown"
    confidence: float = 0.0
    detection_confidence: float = 0.0
    
    # Extraction
    entities: dict[str, Any] = field(default_factory=dict)
    
    # Generation
    command: str = ""
    template_used: str = ""
    
    # Metadata
    success: bool = False
    source: str = "rules"  # "rules" or "llm"
    latency_ms: float = 0.0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.confidence == 0.0 and self.detection_confidence != 0.0:
            self.confidence = self.detection_confidence
        if self.detection_confidence == 0.0 and self.confidence != 0.0:
            self.detection_confidence = self.confidence
    
    def to_plan(self) -> SimpleExecutionPlan:
        """Convert to execution plan format for adapters."""
        conf = self.confidence if self.confidence != 0.0 else self.detection_confidence
        return SimpleExecutionPlan(intent=self.intent, entities=self.entities, confidence=conf, text=self.input_text)


class PipelineMetrics:
    """Track pipeline metrics for evaluation."""
    
    def __init__(self):
        self.total_processed = 0
        self.successful = 0
        self.failed = 0
        self.total_latency_ms = 0.0
        self.domain_counts: dict[str, int] = {}
        self.intent_counts: dict[str, int] = {}
        self.error_counts: dict[str, int] = {}
    
    def record_result(self, result_or_success, latency_ms=0.0) -> None:
        """Record a pipeline result.
        
        Can accept either a PipelineResult object or legacy parameters (success, latency_ms).
        """
        # Handle legacy call signature: record_result(success, latency_ms)
        if isinstance(result_or_success, bool):
            # Create a dummy PipelineResult from legacy parameters
            from nlp2cmd.generation.pipeline import PipelineResult
            result = PipelineResult(
                success=result_or_success,
                latency_ms=latency_ms,
                domain="unknown",
                intent="unknown",
                command="",
                entities={},
                errors=[] if result_or_success else ["Unknown error"]
            )
        else:
            result = result_or_success
        
        self.total_processed += 1
        self.total_latency_ms += result.latency_ms
        
        if result.success:
            self.successful += 1
        else:
            self.failed += 1
        
        # Count domains and intents
        self.domain_counts[result.domain] = self.domain_counts.get(result.domain, 0) + 1
        self.intent_counts[result.intent] = self.intent_counts.get(result.intent, 0) + 1
        
        # Count errors
        for error in result.errors:
            self.error_counts[error] = self.error_counts.get(error, 0) + 1
    
    def get_success_rate(self) -> float:
        """Get success rate as percentage."""
        if self.total_processed == 0:
            return 0.0
        return (self.successful / self.total_processed) * 100.0
    
    def get_average_latency(self) -> float:
        """Get average latency in milliseconds."""
        if self.total_processed == 0:
            return 0.0
        return self.total_latency_ms / self.total_processed
    
    def get_summary(self) -> dict[str, Any]:
        """Get metrics summary."""
        return {
            "total_processed": self.total_processed,
            "successful": self.successful,
            "failed": self.failed,
            "success_rate": self.get_success_rate(),
            "average_latency_ms": self.get_average_latency(),
            "domain_counts": self.domain_counts,
            "intent_counts": self.intent_counts,
            "error_counts": self.error_counts,
        }


# Enhanced context detector is imported lazily (it can pull heavy deps like torch).
ENHANCED_CONTEXT_AVAILABLE: bool | None = None

_DEFAULT_USE_ENHANCED_CONTEXT = str(os.environ.get("NLP2CMD_USE_ENHANCED_CONTEXT") or "").strip().lower() in {
    "1",
    "true",
    "yes",
    "y",
    "on",
}

_SEMANTIC_ENTITY_MODES = {"semantic", "shadow", "ab"}


def _should_use_semantic_extractor() -> bool:
    mode = os.environ.get("NLP2CMD_ENTITY_EXTRACTOR_MODE")
    if not isinstance(mode, str):
        return False
    return mode.strip().lower() in _SEMANTIC_ENTITY_MODES


def _create_default_extractor() -> Any:
    if _should_use_semantic_extractor():
        from nlp2cmd.generation.semantic_entities import SemanticEntityExtractor
        return SemanticEntityExtractor()
    
    from nlp2cmd.generation.regex import RegexEntityExtractor
    return RegexEntityExtractor()
