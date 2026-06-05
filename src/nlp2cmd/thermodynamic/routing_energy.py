# RoutingEnergy - extracted from energy_models.py
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
class RoutingEnergy(EnergyModel):
    """
    Energy model for routing problems (TSP, VRP).
    
    Encodes z as permutation relaxation: z[i,j] = probability that city j is visited at position i
    
    Uses doubly stochastic matrix representation with entropy regularization.
    
    V(z; c) = total_distance + λ_row * row_constraint + λ_col * col_constraint
    """
    
    def __init__(
        self,
        lambda_row: float = 10.0,
        lambda_col: float = 10.0,
        lambda_entropy: float = 0.1,
        n_cities: Optional[int] = None,
        **kwargs
    ):
        self.lambda_row = lambda_row
        self.lambda_col = lambda_col
        self.lambda_entropy = lambda_entropy
        self.n_cities = n_cities  # Store for backward compatibility
    
    def energy(self, z: np.ndarray, condition: Dict[str, Any]) -> float:
        """
        Compute routing energy.
        
        Args:
            z: Permutation matrix flattened (shape: [n_cities^2])
            condition: Contains 'distances' matrix
        
        Returns:
            Total energy
        """
        n_cities = condition.get('n_cities', int(math.sqrt(len(z))))
        distances = np.array(condition.get('distances', np.zeros((n_cities, n_cities))))
        
        # Reshape to matrix and apply softmax for soft assignment
        Z = z.reshape(n_cities, n_cities)
        P = self._softmax_matrix(Z)
        
        total_energy = 0.0
        
        # 1. Total distance (expected under soft assignment)
        # For TSP: sum of distances for consecutive visits
        for i in range(n_cities - 1):
            for j in range(n_cities):
                for k in range(n_cities):
                    total_energy += P[i, j] * P[i+1, k] * distances[j, k]
        
        # Return to start
        for j in range(n_cities):
            for k in range(n_cities):
                total_energy += P[n_cities-1, j] * P[0, k] * distances[j, k]
        
        # 2. Row sum = 1 constraint (each position has exactly one city)
        row_sums = P.sum(axis=1)
        row_violation = np.sum((row_sums - 1) ** 2)
        total_energy += self.lambda_row * row_violation
        
        # 3. Column sum = 1 constraint (each city visited exactly once)
        col_sums = P.sum(axis=0)
        col_violation = np.sum((col_sums - 1) ** 2)
        total_energy += self.lambda_col * col_violation
        
        # 4. Entropy regularization (encourage discrete assignment)
        entropy = -np.sum(P * np.log(P + 1e-10))
        total_energy -= self.lambda_entropy * entropy
        
        return total_energy
    
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
    
    def _softmax_matrix(self, Z: np.ndarray) -> np.ndarray:
        """Apply softmax to make soft assignment matrix."""
        exp_Z = np.exp(Z - Z.max())
        return exp_Z / exp_Z.sum()
    
    def decode_route(self, z: np.ndarray) -> list[int]:
        """
        Decode flattened permutation matrix to route.
        
        Args:
            z: Flattened permutation matrix (shape: [n_cities^2])
            
        Returns:
            List of city indices in visitation order
        """
        n_cities = int(np.sqrt(len(z)))
        Z = z.reshape(n_cities, n_cities)
        
        # Use Hungarian algorithm for optimal assignment
        try:
            from scipy.optimize import linear_sum_assignment
            # Find assignment that maximizes the soft assignments
            row_ind, col_ind = linear_sum_assignment(-Z)
            route = col_ind.tolist()
        except ImportError:
            # Fallback: greedy assignment
            route = []
            used = set()
            for i in range(n_cities):
                # Find best unused city for position i
                best_city = None
                best_score = -float('inf')
                for j in range(n_cities):
                    if j not in used and Z[i, j] > best_score:
                        best_score = Z[i, j]
                        best_city = j
                if best_city is not None:
                    route.append(best_city)
                    used.add(best_city)
                else:
                    # Fallback: add any unused city
                    for j in range(n_cities):
                        if j not in used:
                            route.append(j)
                            used.add(j)
                            break
        
        return route
