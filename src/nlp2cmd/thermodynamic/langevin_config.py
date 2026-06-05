# LangevinConfig - extracted from __init__.py
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
@dataclass
class LangevinConfig:
    """Configuration for Langevin dynamics sampler."""
    
    mu: float = 1.0           # Mobility coefficient
    kT: float = 1.0           # Thermal energy (k_B * T)
    dt: float = 0.01          # Time step
    n_steps: int = 1000       # Number of integration steps
    dim: int = 64             # Latent dimension
    record_trajectory: bool = False  # Whether to record full trajectory
    seed: Optional[int] = None
    
    # Early stopping parameters
    early_stopping: bool = True    # Enable early stopping
    convergence_threshold: float = 0.01  # Energy threshold for convergence
    check_interval: int = 100
