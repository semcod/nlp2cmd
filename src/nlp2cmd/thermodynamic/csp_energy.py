# CSPEnergy - extracted from energy_models.py
"""
Domain-specific Energy Models for NLP2CMD Thermodynamic Computing.

Provides energy functions V(z; c) for specific problem domains:
- Scheduling (job shop, task assignment)
- Resource Allocation
- Routing (TSP, VRP)
- Planning with constraints
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from . import EnergyModel


# =============================================================================
# Scheduling Energy Model
# =============================================================================
class CSPEnergy(EnergyModel):
    """
    Generic Constraint Satisfaction Problem energy model.
    
    Supports arbitrary constraint functions with learnable weights.
    """
    
    def __init__(self):
        self.constraints: List[Tuple[str, callable, float]] = []
    
    def add_constraint(
        self, 
        name: str, 
        constraint_fn: callable,
        weight: float = 1.0
    ):
        """
        Add a constraint.
        
        Args:
            name: Constraint name
            constraint_fn: Function (z, condition) -> violation (float, 0 = satisfied)
            weight: Penalty weight
        """
        self.constraints.append((name, constraint_fn, weight))
    
    def energy(self, z: np.ndarray, condition: Dict[str, Any]) -> float:
        """Compute total constraint violation energy."""
        total = 0.0
        for name, fn, weight in self.constraints:
            violation = fn(z, condition)
            total += weight * violation
        return total
    
    def gradient(self, z: np.ndarray, condition: Dict[str, Any]) -> np.ndarray:
        """Compute gradient numerically."""
        eps = 1e-5
        grad = np.zeros_like(z)
        
        for i in range(len(z)):
            z_plus = z.copy()
            z_plus[i] += eps
            z_minus = z.copy()
            z_minus[i] -= eps
            
            grad[i] = (self.energy(z_plus, condition) - self.energy(z_minus, condition)) / (2 * eps)
        
        return grad
