# HybridThermodynamicGenerator - extracted from thermodynamic.py
"""
Iteration 10: Thermodynamic Optimization Integration (IMPROVED).

Integrate Langevin sampling for complex optimization problems:
- Scheduling, allocation, routing, planning
- Energy-based constraint satisfaction
- Hybrid LLM formalization + thermodynamic sampling

Based on Whitelam 2025 "Generative Thermodynamic Computing" (arXiv:2506.15121).

Key concepts:
- Langevin dynamics: dz = -μ∇V(z;c)dt + √(2μkT) dW
- Energy minimization for constraint satisfaction
- Majority voting across parallel samples
- Entropy production regularization

IMPROVEMENTS v1.2:
- [REFACTOR] Gradient computation uses base class numerical_gradient
- [FIX] Router now correctly identifies optimization problems (lowered threshold)
- [FIX] Allocation energy model uses correct number of resources from text
- [PERF] Adaptive n_steps based on problem size (smaller problems = fewer steps)
- [FIX] Polish UTF-8 keywords properly decoded
- [FIX] Better number extraction for "X zasobów do Y konsumentów"
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Optional

try:
    import numpy as np
except Exception:  # pragma: no cover
    class _NumpyStub:
        def __getattr__(self, name):
            raise ImportError(
                "numpy is not installed. Install it to use thermodynamic optimization features."
            )
    np = _NumpyStub()

from nlp2cmd.thermodynamic import (
    LangevinConfig,
    LangevinSampler,
    SamplerResult,
    EnergyModel,
    ConstraintEnergy,
    MajorityVoter,
    ThermodynamicRouter,
    EnergyEstimator,
    EntropyProductionRegularizer,
)
from nlp2cmd.generation.structured import StructuredPlan, StructuredLLMPlanner
from nlp2cmd.generation.llm_simple import LLMClient, LLMConfig
from nlp2cmd.generation.thermodynamic_components import (
    OptimizationProblem,
    ThermodynamicResult,
    ThermodynamicProblemDetector,
    ThermodynamicConfig,
)
from nlp2cmd.generation.thermodynamic_generator import ThermodynamicGenerator

class HybridThermodynamicGenerator:
    """
    Hybrid generator combining rule/LLM-based DSL with thermodynamic optimization.
    
    This generator first tries to use the standard pipeline, and if it detects
    an optimization problem, falls back to thermodynamic optimization.
    """
    
    def __init__(
        self,
        *,
        llm_client: Optional[LLMClient] = None,
        thermodynamic_config: Optional[ThermodynamicConfig] = None,
        optimization_threshold: float = 0.3,
    ):
        self.llm_client = llm_client
        self.thermodynamic_config = thermodynamic_config or ThermodynamicConfig()
        self.optimization_threshold = optimization_threshold
        
        # Initialize components
        self.problem_detector = ThermodynamicProblemDetector()
        self.router = ThermodynamicRouter()
        self.thermodynamic_generator = ThermodynamicGenerator(
            llm_client=llm_client,
            config=thermodynamic_config,
        )
        
        # Initialize standard pipeline (lazy loaded)
        self._pipeline = None
    
    @property
    def pipeline(self):
        """Get or create standard pipeline."""
        if self._pipeline is None:
            from nlp2cmd.generation.pipeline import RuleBasedPipeline
            self._pipeline = RuleBasedPipeline()
        return self._pipeline
    
    async def generate(
        self,
        text: str,
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Generate using hybrid approach."""
        # First, check if this is an optimization problem
        optimization_score = self.router.score_optimization(text)
        
        if optimization_score > self.optimization_threshold:
            # Use thermodynamic optimization
            result = await self.thermodynamic_generator.generate(text, context=context)
            return {
                "source": "thermodynamic",
                "result": result,
                "optimization_score": optimization_score,
            }
        else:
            # Use standard pipeline
            pipeline_result = self.pipeline.process(text)
            return {
                "source": "pipeline",
                "result": pipeline_result,
                "optimization_score": optimization_score,
            }
    
    def is_optimization_problem(self, text: str) -> bool:
        """Check if text describes an optimization problem."""
        optimization_score = self.router.score_optimization(text)
        return optimization_score > self.optimization_threshold
