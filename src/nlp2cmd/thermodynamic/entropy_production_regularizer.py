# EntropyProductionRegularizer - extracted from __init__.py
"""
Thermodynamic Computing Module for NLP2CMD.

Implements Whitelam's generative thermodynamic computing framework:
- Langevin dynamics sampling
- Energy-based models for constraints
- Entropy production regularization

Reference: Whitelam (2025) "Generative thermodynamic computing" arXiv:2506.15121
"""

from __future__ import annotations

import math
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
try:
    import numpy as np
except Exception:  # pragma: no cover
    class _NumpyStub:
        def __getattr__(self, name):
            raise ImportError(
                "numpy is not installed. Install it to use thermodynamic optimization features."
            )
        def array(self, obj, *args, **kwargs):
            raise ImportError(
                "numpy is not installed. Install it to use thermodynamic optimization features."
            )
        def zeros_like(self, *args, **kwargs):
            raise ImportError(
                "numpy is not installed. Install it to use thermodynamic optimization features."
            )
        def sum(self, *args, **kwargs):
            raise ImportError(
                "numpy is not installed. Install it to use thermodynamic optimization features."
            )
        def exp(self, *args, **kwargs):
            raise ImportError(
                "numpy is not installed. Install it to use thermodynamic optimization features."
            )
        def random(self, *args, **kwargs):
            raise ImportError(
                "numpy is not installed. Install it to use thermodynamic optimization features."
            )
        def sqrt(self, *args, **kwargs):
            raise ImportError(
                "numpy is not installed. Install it to use thermodynamic optimization features."
            )
        def mean(self, *args, **kwargs):
            raise ImportError(
                "numpy is not installed. Install it to use thermodynamic optimization features."
            )
        def std(self, *args, **kwargs):
            raise ImportError(
                "numpy is not installed. Install it to use thermodynamic optimization features."
            )
    np = _NumpyStub()


# =============================================================================
# Configuration
# =============================================================================
from nlp2cmd.thermodynamic.sampler_result import SamplerResult

class EntropyProductionRegularizer:
    """
    Regularizer based on Whitelam's principle:
    
    L = -E[log P(ω̃)] + λ E[Q(ω̃)]
    
    Where Q is heat (entropy production) along trajectory.
    Lower entropy production = more reversible = better generative quality.
    """
    
    def __init__(self, lambda_entropy: float = 0.1, kT: float = 1.0):
        self.lambda_entropy = lambda_entropy
        self.kT = kT
    
    def compute_regularization(self, result: SamplerResult) -> float:
        """
        Compute entropy production regularization term.
        
        Lower values indicate more reversible (thermodynamically efficient) sampling.
        """
        return self.lambda_entropy * result.entropy_production
    
    def estimate_heat_dissipation(self, result: SamplerResult) -> float:
        """
        Estimate heat dissipation Q during sampling.
        
        Q = kT * σ where σ is entropy production
        """
        return self.kT * result.entropy_production
