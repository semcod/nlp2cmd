# QuadraticEnergy - extracted from __init__.py
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

class QuadraticEnergy(EnergyModel):
    """
    Simple quadratic energy for testing: V(z) = 0.5 * ||z - target||²
    """
    
    def __init__(self, target: Optional[np.ndarray] = None):
        self.target = target
    
    def energy(self, z: np.ndarray, condition: Dict[str, Any]) -> float:
        target = condition.get('target', self.target)
        if target is None:
            target = np.zeros_like(z)
        return 0.5 * np.sum((z - target) ** 2)
    
    def gradient(self, z: np.ndarray, condition: Dict[str, Any]) -> np.ndarray:
        target = condition.get('target', self.target)
        if target is None:
            target = np.zeros_like(z)
        return z - target
