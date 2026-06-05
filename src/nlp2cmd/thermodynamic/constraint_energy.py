# ConstraintEnergy - extracted from __init__.py
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
from nlp2cmd.thermodynamic.energy_model import EnergyModel

class ConstraintEnergy(EnergyModel):
    """
    Energy model for constraint satisfaction problems.
    
    V(z; c) = Σ_a λ_a φ_a(z; c)
    
    Where:
    - φ_a: penalty functions for constraint violations
    - λ_a: weights
    """
    
    def __init__(self):
        self.penalties: Dict[str, Callable] = {}
        self.lambdas: Dict[str, float] = {}
    
    def add_penalty(
        self, 
        name: str, 
        penalty_fn: Callable[[np.ndarray, Any], float],
        gradient_fn: Callable[[np.ndarray, Any], np.ndarray],
        weight: float = 1.0
    ):
        """Add a penalty function."""
        self.penalties[name] = (penalty_fn, gradient_fn)
        self.lambdas[name] = weight
    
    def energy(self, z: np.ndarray, condition: Dict[str, Any]) -> float:
        total = 0.0
        constraints = condition.get('constraints', {})
        for name, (penalty_fn, _) in self.penalties.items():
            if name in constraints:
                violation = penalty_fn(z, constraints[name])
                total += self.lambdas[name] * violation
        return total
    
    def gradient(self, z: np.ndarray, condition: Dict[str, Any]) -> np.ndarray:
        grad = np.zeros_like(z)
        constraints = condition.get('constraints', {})
        for name, (_, gradient_fn) in self.penalties.items():
            if name in constraints:
                g = gradient_fn(z, constraints[name])
                grad += self.lambdas[name] * g
        return grad
