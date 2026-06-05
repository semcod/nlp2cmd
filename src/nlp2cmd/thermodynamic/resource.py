# Resource - extracted from energy_models.py
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
class Resource:
    """Represents a resource with capacity."""
    id: str
    capacity: float
    available_from: float = 0.0
    available_until: float = float('inf')
