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

@dataclass
class Task:
    """Represents a task to be scheduled."""
    id: str
    duration: float
    earliest_start: float = 0.0
    deadline: Optional[float] = None
    resource_requirements: Dict[str, float] = None
    predecessors: List[str] = None


@dataclass 
class Resource:
    """Represents a resource with capacity."""
    id: str
    capacity: float
    available_from: float = 0.0
    available_until: float = float('inf')


class SchedulingEnergy(EnergyModel):
    """
    Energy model for scheduling problems.
    
    Encodes z as a vector of start times for each task.
    
    Constraints encoded as energy penalties:
    - No overlap on same resource
    - Respect deadlines
    - Respect precedence
    - Resource capacity limits
    
    V(z; c) = λ_overlap * Σ overlap_penalty 
            + λ_deadline * Σ deadline_violation
            + λ_precedence * Σ precedence_violation
            + λ_makespan * makespan
    """
    
    def __init__(
        self,
        lambda_overlap: float = 10.0,
        lambda_deadline: float = 5.0,
        lambda_precedence: float = 10.0,
        lambda_makespan: float = 1.0,
        n_tasks: Optional[int] = None,
        **kwargs
    ):
        self.lambda_overlap = lambda_overlap
        self.lambda_deadline = lambda_deadline
        self.lambda_precedence = lambda_precedence
        self.lambda_makespan = lambda_makespan
        self.n_tasks = n_tasks  # Store for backward compatibility
    
    def energy(self, z: np.ndarray, condition: Dict[str, Any]) -> float:
        """
        Compute scheduling energy.
        
        Args:
            z: Start times for each task (shape: [n_tasks])
            condition: Contains 'tasks', 'resources', optional 'assignments'
        
        Returns:
            Total energy (lower = better schedule)
        """
        tasks = condition.get('tasks', [])
        resources = condition.get('resources', [])
        assignments = condition.get('assignments', {})  # task_id -> resource_id
        
        if len(z) != len(tasks):
            raise ValueError(f"z length {len(z)} != n_tasks {len(tasks)}")
        
        total_energy = 0.0
        
        # 1. Overlap penalty
        total_energy += self.lambda_overlap * self._overlap_penalty(z, tasks, assignments)
        
        # 2. Deadline violations
        total_energy += self.lambda_deadline * self._deadline_penalty(z, tasks)
        
        # 3. Precedence violations
        total_energy += self.lambda_precedence * self._precedence_penalty(z, tasks, condition)
        
        # 4. Makespan (completion time of last task)
        total_energy += self.lambda_makespan * self._makespan(z, tasks)
        
        return total_energy
    
    def gradient(self, z: np.ndarray, condition: Dict[str, Any]) -> np.ndarray:
        """
        Compute gradient of scheduling energy.
        
        Uses numerical differentiation for simplicity.
        """
        eps = 1e-5
        grad = np.zeros_like(z)
        
        for i in range(len(z)):
            z_plus = z.copy()
            z_plus[i] += eps
            z_minus = z.copy()
            z_minus[i] -= eps
            
            grad[i] = (self.energy(z_plus, condition) - self.energy(z_minus, condition)) / (2 * eps)
        
        return grad
    
    def _overlap_penalty(
        self, 
        z: np.ndarray, 
        tasks: List[Task],
        assignments: Dict[str, str]
    ) -> float:
        """Penalty for overlapping tasks on same resource."""
        penalty = 0.0
        
        for i, task_i in enumerate(tasks):
            for j, task_j in enumerate(tasks):
                if i >= j:
                    continue
                
                # Check if on same resource
                res_i = assignments.get(task_i.id)
                res_j = assignments.get(task_j.id)
                
                if res_i is not None and res_i == res_j:
                    # Check overlap
                    start_i, end_i = z[i], z[i] + task_i.duration
                    start_j, end_j = z[j], z[j] + task_j.duration
                    
                    overlap = max(0, min(end_i, end_j) - max(start_i, start_j))
                    penalty += overlap ** 2
        
        return penalty
    
    def _deadline_penalty(self, z: np.ndarray, tasks: List[Task]) -> float:
        """Penalty for missing deadlines."""
        penalty = 0.0
        
        for i, task in enumerate(tasks):
            if task.deadline is not None:
                end_time = z[i] + task.duration
                violation = max(0, end_time - task.deadline)
                penalty += violation ** 2
        
        return penalty
    
    def _precedence_penalty(
        self, 
        z: np.ndarray, 
        tasks: List[Task],
        condition: Dict[str, Any]
    ) -> float:
        """Penalty for violating precedence constraints."""
        penalty = 0.0
        precedence = condition.get('precedence', {})  # task_id -> list of predecessor ids
        
        task_idx = {t.id: i for i, t in enumerate(tasks)}
        
        for task_id, predecessors in precedence.items():
            if task_id not in task_idx:
                continue
            
            task_i = task_idx[task_id]
            start_i = z[task_i]
            
            for pred_id in predecessors:
                if pred_id not in task_idx:
                    continue
                
                pred_i = task_idx[pred_id]
                pred_end = z[pred_i] + tasks[pred_i].duration
                
                # Task must start after predecessor ends
                violation = max(0, pred_end - start_i)
                penalty += violation ** 2
        
        return penalty
    
    def _makespan(self, z: np.ndarray, tasks: List[Task]) -> float:
        """Total completion time (makespan)."""
        end_times = [z[i] + tasks[i].duration for i in range(len(tasks))]
        return max(end_times) if end_times else 0.0


# =============================================================================
# Resource Allocation Energy Model
# =============================================================================

class AllocationEnergy(EnergyModel):
    """
    Energy model for resource allocation problems.
    
    Encodes z as allocation amounts: z[i,j] = amount of resource j allocated to request i
    
    Constraints:
    - Capacity: total allocation ≤ resource capacity
    - Demand: allocation ≥ minimum demand
    - Balance: fair distribution across requests
    - Cost: minimize total cost
    
    V(z; c) = λ_capacity * capacity_violation
            + λ_demand * unmet_demand
            + λ_balance * imbalance
            + λ_cost * total_cost
    """
    
    def __init__(
        self,
        lambda_capacity: float = 10.0,
        lambda_demand: float = 5.0,
        lambda_balance: float = 1.0,
        lambda_cost: float = 1.0,
        n_resources: Optional[int] = None,
        **kwargs
    ):
        self.lambda_capacity = lambda_capacity
        self.lambda_demand = lambda_demand
        self.lambda_balance = lambda_balance
        self.lambda_cost = lambda_cost
        self.n_resources = n_resources  # Store for backward compatibility
    
    def energy(self, z: np.ndarray, condition: Dict[str, Any]) -> float:
        """
        Compute allocation energy.
        
        Args:
            z: Allocation matrix flattened (shape: [n_requests * n_resources])
            condition: Contains 'capacities', 'demands', 'costs'
        
        Returns:
            Total energy
        """
        n_requests = condition.get('n_requests', 1)
        n_resources = condition.get('n_resources', 1)
        capacities = np.array(condition.get('capacities', [1.0] * n_resources))
        demands = np.array(condition.get('demands', [0.0] * n_requests))
        costs = np.array(condition.get('costs', np.ones((n_requests, n_resources))))
        
        # Reshape z to matrix
        Z = z.reshape(n_requests, n_resources)
        
        total_energy = 0.0
        
        # 1. Capacity violation
        total_per_resource = Z.sum(axis=0)
        capacity_violation = np.sum(np.maximum(0, total_per_resource - capacities) ** 2)
        total_energy += self.lambda_capacity * capacity_violation
        
        # 2. Demand satisfaction
        total_per_request = Z.sum(axis=1)
        demand_violation = np.sum(np.maximum(0, demands - total_per_request) ** 2)
        total_energy += self.lambda_demand * demand_violation
        
        # 3. Balance (variance of allocations)
        if n_requests > 1:
            imbalance = np.var(total_per_request)
            total_energy += self.lambda_balance * imbalance
        
        # 4. Cost
        total_cost = np.sum(Z * costs)
        total_energy += self.lambda_cost * total_cost
        
        # 5. Non-negativity (soft constraint)
        negative_penalty = np.sum(np.minimum(0, Z) ** 2)
        total_energy += 100.0 * negative_penalty
        
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


# =============================================================================
# Routing Energy Model (TSP-like)
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


# =============================================================================
# Generic Constraint Satisfaction Energy
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


# =============================================================================
# Module exports
# =============================================================================

__all__ = [
    'Task',
    'Resource',
    'SchedulingEnergy',
    'AllocationEnergy',
    'RoutingEnergy',
    'CSPEnergy',
]
