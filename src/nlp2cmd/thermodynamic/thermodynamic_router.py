# ThermodynamicRouter - extracted from __init__.py
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
class ThermodynamicRouter:
    """
    Routes problems to appropriate solver:
    - Classic DSL agents for simple queries
    - Langevin/EBM for constraint satisfaction
    """
    
    THERMODYNAMIC_INTENTS = {
        'schedule',         # Scheduling problems
        'allocate',         # Resource allocation
        'optimize',         # General optimization
        'sample',           # Bayesian sampling
        'plan',             # Planning with constraints
        'route',            # Routing/TSP problems
        'assign',           # Assignment problems
        'balance',          # Load balancing
    }
    
    CLASSIC_INTENTS = {
        'query',            # SQL queries
        'execute',          # Shell commands
        'deploy',           # Docker/K8s
        'transform',        # Data transformation
        'list',             # Listing resources
        'get',              # Getting information
        'create',           # Creating resources
        'delete',           # Deleting resources
    }
    
    def __init__(self, complexity_threshold: float = 0.5):
        self.complexity_threshold = complexity_threshold
    
    def route(self, intent: str, complexity: float = 0.5) -> str:
        """
        Decide solver type based on intent and complexity.
        
        Args:
            intent: Detected intent
            complexity: Estimated problem complexity (0-1)
        
        Returns:
            'classic' | 'langevin' | 'hybrid'
        """
        # Normalize intent
        intent_lower = intent.lower().strip()
        
        if intent_lower in self.THERMODYNAMIC_INTENTS:
            if complexity > self.complexity_threshold:
                return 'langevin'
            else:
                return 'hybrid'  # LLM formalization + Langevin sampling
        
        elif intent_lower in self.CLASSIC_INTENTS:
            return 'classic'
        
        else:
            # Unknown intent - default to hybrid for safety
            return 'hybrid' if complexity > self.complexity_threshold else 'classic'
    
    def estimate_complexity(self, problem_description: str, entities: Dict[str, Any]) -> float:
        """
        Estimate problem complexity based on description and entities.
        
        Heuristics:
        - Number of constraints
        - Number of variables
        - Problem size indicators
        """
        complexity = 0.3  # Base complexity
        
        # Count constraints
        n_constraints = len(entities.get('constraints', []))
        complexity += min(0.3, n_constraints * 0.05)
        
        # Check for optimization keywords
        opt_keywords = ['minimize', 'maximize', 'optimal', 'best', 'efficient']
        if any(kw in problem_description.lower() for kw in opt_keywords):
            complexity += 0.2
        
        # Check for combinatorial keywords
        comb_keywords = ['schedule', 'assign', 'allocate', 'route', 'plan']
        if any(kw in problem_description.lower() for kw in comb_keywords):
            complexity += 0.15
        
        return min(1.0, complexity)
