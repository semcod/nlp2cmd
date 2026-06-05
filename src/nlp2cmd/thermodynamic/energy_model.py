# EnergyModel - extracted from __init__.py
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
class EnergyModel(ABC):
    """
    Abstract base class for energy models.
    
    Energy function V(z; c) defines the probability distribution:
    p(z | c) ∝ exp(-V(z; c) / kT)
    
    Based on Whitelam 2025 "Generative Thermodynamic Computing":
    - Lower energy = higher probability = better solution
    - Gradient guides Langevin dynamics toward minima
    """
    
    @abstractmethod
    def energy(self, z: np.ndarray, condition: Dict[str, Any]) -> float:
        """Compute energy V(z; c)."""
        raise NotImplementedError
    
    @abstractmethod
    def gradient(self, z: np.ndarray, condition: Dict[str, Any]) -> np.ndarray:
        """Compute energy gradient ∇V(z; c)."""
        raise NotImplementedError
    
    def numerical_gradient(
        self, z: np.ndarray, condition: Dict[str, Any], eps: float = 1e-5
    ) -> np.ndarray:
        """
        Compute gradient numerically via finite differences.
        
        Useful as fallback when analytical gradient is complex.
        Uses central differences for better accuracy.
        """
        grad = np.zeros_like(z)
        for i in range(len(z)):
            z_plus = z.copy()
            z_plus[i] += eps
            z_minus = z.copy()
            z_minus[i] -= eps
            grad[i] = (self.energy(z_plus, condition) - self.energy(z_minus, condition)) / (2 * eps)
        return grad
    
    def __call__(self, z: np.ndarray, condition: Dict[str, Any]) -> float:
        return self.energy(z, condition)
