"""
Text → Multi-DSL Generation Module.

This module provides iterative text-to-DSL generation capabilities:
- Rule-based intent detection (no LLM) - Iteration 1
- Regex entity extraction - Iteration 2
- Template-based generation - Iteration 3
- LLM integration (single/multi domain) - Iterations 4-5
- Structured JSON output - Iteration 6
- Validation & self-correction - Iteration 7
- Hybrid rule+LLM approach - Iteration 9
"""

# Iteration 1-3: Rule-based components
from nlp2cmd.generation.keywords.keyword_detector import KeywordIntentDetector, DetectionResult
from nlp2cmd.generation.regex import RegexEntityExtractor, ExtractionResult
from nlp2cmd.generation.template_generator import TemplateGenerator, TemplateResult
from nlp2cmd.generation.multi_command import (
    MultiCommandDetector,
    MultiCommandResult,
    detect_multi_commands,
    get_multi_command_detector,
)
from nlp2cmd.generation.pipeline import (
    RuleBasedPipeline,
    PipelineResult,
    PipelineMetrics,
)

import importlib
from typing import Any

__all__ = [
    # Iteration 1-3: Rule-based
    "KeywordIntentDetector",
    "DetectionResult",
    "RegexEntityExtractor",
    "ExtractionResult",
    "TemplateGenerator",
    "TemplateResult",
    "RuleBasedPipeline",
    "PipelineResult",
    "PipelineMetrics",
    # Multi-command detection
    "MultiCommandDetector",
    "MultiCommandResult",
    "detect_multi_commands",
    "get_multi_command_detector",
    # Iteration 4-5: LLM
    "LLMClient",
    "LLMConfig",
    "LLMGenerationResult",
    "BaseLLMGenerator",
    "SimpleLLMSQLGenerator",
    "SimpleLLMShellGenerator",
    "SimpleLLMDockerGenerator",
    "SimpleLLMKubernetesGenerator",
    "MockLLMClient",
    "LLMDomainRouter",
    "MultiDomainGenerator",
    "MultiDomainResult",
    "RoutingResult",
    "CachedMultiDomainGenerator",
    # Iteration 6: Structured
    "StructuredLLMPlanner",
    "StructuredPlan",
    "StructuredPlanResult",
    "MultiStepPlanner",
    "MultiStepPlan",
    "PLAN_SCHEMA",
    # Iteration 7: Validation
    "ValidatingGenerator",
    "ValidatingGeneratorResult",
    "ValidationResult",
    "SimpleSQLValidator",
    "SimpleShellValidator",
    "SimpleDockerValidator",
    "SimpleKubernetesValidator",
    "create_default_validators",
    # Iteration 9: Hybrid
    "HybridGenerator",
    "HybridResult",
    "HybridStats",
    "AdaptiveHybridGenerator",
    "create_hybrid_generator",
    # Iteration 10: Thermodynamic
    "ThermodynamicGenerator",
    "ThermodynamicResult",
    "OptimizationProblem",
    "SchedulingEnergy",
    "AllocationEnergy",
    "RoutingEnergy",
    "HybridThermodynamicGenerator",
    "create_thermodynamic_generator",
]


_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    # Iteration 4-5: LLM
    "LLMClient": ("nlp2cmd.generation.llm_simple", "LLMClient"),
    "LLMConfig": ("nlp2cmd.generation.llm_simple", "LLMConfig"),
    "LLMGenerationResult": ("nlp2cmd.generation.llm_simple", "LLMGenerationResult"),
    "BaseLLMGenerator": ("nlp2cmd.generation.llm_simple", "BaseLLMGenerator"),
    "SimpleLLMSQLGenerator": ("nlp2cmd.generation.llm_simple", "SimpleLLMSQLGenerator"),
    "SimpleLLMShellGenerator": ("nlp2cmd.generation.llm_simple", "SimpleLLMShellGenerator"),
    "SimpleLLMDockerGenerator": ("nlp2cmd.generation.llm_simple", "SimpleLLMDockerGenerator"),
    "SimpleLLMKubernetesGenerator": ("nlp2cmd.generation.llm_simple", "SimpleLLMKubernetesGenerator"),
    "MockLLMClient": ("nlp2cmd.generation.llm_simple", "MockLLMClient"),
    "LLMDomainRouter": ("nlp2cmd.generation.llm_multi", "LLMDomainRouter"),
    "MultiDomainGenerator": ("nlp2cmd.generation.llm_multi", "MultiDomainGenerator"),
    "MultiDomainResult": ("nlp2cmd.generation.llm_multi", "MultiDomainResult"),
    "RoutingResult": ("nlp2cmd.generation.llm_multi", "RoutingResult"),
    "CachedMultiDomainGenerator": ("nlp2cmd.generation.llm_multi", "CachedMultiDomainGenerator"),
    # Iteration 6: Structured
    "StructuredLLMPlanner": ("nlp2cmd.generation.structured", "StructuredLLMPlanner"),
    "StructuredPlan": ("nlp2cmd.generation.structured", "StructuredPlan"),
    "StructuredPlanResult": ("nlp2cmd.generation.structured", "StructuredPlanResult"),
    "MultiStepPlanner": ("nlp2cmd.generation.structured", "MultiStepPlanner"),
    "MultiStepPlan": ("nlp2cmd.generation.structured", "MultiStepPlan"),
    "PLAN_SCHEMA": ("nlp2cmd.generation.structured", "PLAN_SCHEMA"),
    # Iteration 7: Validation
    "ValidatingGenerator": ("nlp2cmd.generation.validating", "ValidatingGenerator"),
    "ValidatingGeneratorResult": ("nlp2cmd.generation.validating", "ValidatingGeneratorResult"),
    "ValidationResult": ("nlp2cmd.generation.validating", "ValidationResult"),
    "SimpleSQLValidator": ("nlp2cmd.generation.validating", "SimpleSQLValidator"),
    "SimpleShellValidator": ("nlp2cmd.generation.validating", "SimpleShellValidator"),
    "SimpleDockerValidator": ("nlp2cmd.generation.validating", "SimpleDockerValidator"),
    "SimpleKubernetesValidator": ("nlp2cmd.generation.validating", "SimpleKubernetesValidator"),
    "create_default_validators": ("nlp2cmd.generation.validating", "create_default_validators"),
    # Iteration 9: Hybrid
    "HybridGenerator": ("nlp2cmd.generation.hybrid", "HybridGenerator"),
    "HybridResult": ("nlp2cmd.generation.hybrid", "HybridResult"),
    "HybridStats": ("nlp2cmd.generation.hybrid", "HybridStats"),
    "AdaptiveHybridGenerator": ("nlp2cmd.generation.hybrid", "AdaptiveHybridGenerator"),
    "create_hybrid_generator": ("nlp2cmd.generation.hybrid", "create_hybrid_generator"),
    # Iteration 10: Thermodynamic
    "ThermodynamicGenerator": ("nlp2cmd.generation.thermodynamic", "ThermodynamicGenerator"),
    "ThermodynamicResult": ("nlp2cmd.generation.thermodynamic", "ThermodynamicResult"),
    "OptimizationProblem": ("nlp2cmd.generation.thermodynamic", "OptimizationProblem"),
    "SchedulingEnergy": ("nlp2cmd.generation.thermodynamic", "SchedulingEnergy"),
    "AllocationEnergy": ("nlp2cmd.generation.thermodynamic", "AllocationEnergy"),
    "RoutingEnergy": ("nlp2cmd.generation.thermodynamic", "RoutingEnergy"),
    "HybridThermodynamicGenerator": ("nlp2cmd.generation.thermodynamic", "HybridThermodynamicGenerator"),
    "create_thermodynamic_generator": ("nlp2cmd.generation.thermodynamic", "create_thermodynamic_generator"),
}


def __getattr__(name: str) -> Any:
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(name)
    module_name, attr_name = target
    module = importlib.import_module(module_name)
    return getattr(module, attr_name)


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + list(_LAZY_EXPORTS.keys()))
