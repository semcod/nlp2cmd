# SchedulingEnergy - extracted from energy_models.py
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
from nlp2cmd.thermodynamic.resource import Resource
from nlp2cmd.thermodynamic.task import Task

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
        n_slots: Optional[int] = None,
        **kwargs
    ):
        self.lambda_overlap = lambda_overlap
        self.lambda_deadline = lambda_deadline
        self.lambda_precedence = lambda_precedence
        self.lambda_makespan = lambda_makespan
        self.n_tasks = n_tasks  # Store for backward compatibility
        self.n_slots = n_slots  # Store for backward compatibility
    
    def energy(self, z: np.ndarray, condition: Dict[str, Any]) -> float:
        """
        Compute scheduling energy.
        
        Args:
            z: Start times for each task (shape: [n_tasks]) or assignment matrix (n_tasks * n_slots)
            condition: Contains 'tasks', 'resources', optional 'assignments' OR legacy format
        
        Returns:
            Total energy (lower = better schedule)
        """
        # Handle legacy format for backward compatibility
        if 'tasks' not in condition and self.n_tasks is not None:
            # Legacy format: z is assignment matrix, n_tasks * n_slots
            n_tasks = self.n_tasks
            n_slots = self.n_slots or condition.get('n_slots', 5)  # Use constructor value or default
            
            # Create dummy tasks for backward compatibility
            tasks = []
            for i in range(n_tasks):
                task = Task(
                    id=f"task_{i}",
                    duration=1.0,
                    deadline=n_slots
                )
                tasks.append(task)
            
            # Convert assignment matrix to start times
            if len(z) == n_tasks * n_slots:
                # z is assignment matrix, find max position for each task
                z_reshaped = z.reshape(n_tasks, n_slots)
                start_times = np.argmax(z_reshaped, axis=1).astype(float)
                z = start_times
            
            resources = []
            assignments = {}
        else:
            # New format
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
    
    def _decode_assignments(self, z: np.ndarray) -> list[int]:
        """
        Decode assignment matrix to slot assignments.
        
        Args:
            z: Assignment matrix flattened (shape: [n_tasks * n_slots])
            
        Returns:
            List of slot indices for each task
        """
        # Infer dimensions from z length
        n_slots = int(np.sqrt(len(z))) if int(np.sqrt(len(z))) ** 2 == len(z) else 5
        n_tasks = len(z) // n_slots
        
        # Reshape to assignment matrix
        Z = z.reshape(n_tasks, n_slots)
        
        # For each task, find the slot with maximum assignment
        assignments = []
        for i in range(n_tasks):
            # Find slot with highest value for task i
            slot = np.argmax(Z[i])
            assignments.append(int(slot))
        
        return assignments
    
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
                
                # For legacy format with no assignments, assume all tasks share same resource
                same_resource = (res_i is not None and res_i == res_j) or (not assignments and len(tasks) > 1)
                
                if same_resource:
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
