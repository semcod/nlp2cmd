# AllocationEnergy - extracted from thermodynamic.py
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
from nlp2cmd.thermodynamic.energy_models import (
    AllocationEnergy as ThermodynamicAllocationEnergy,
)

class AllocationEnergy(ThermodynamicAllocationEnergy):
    """Allocation energy model for thermodynamic optimization."""
    pass
