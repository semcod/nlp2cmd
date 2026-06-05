# Task - extracted from energy_models.py
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
