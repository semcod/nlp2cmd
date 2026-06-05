# MajorityVoter - extracted from __init__.py
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
from nlp2cmd.thermodynamic.sampler_result import SamplerResult

class MajorityVoter:
    """
    Select best sample from multiple candidates.
    
    Strategies:
    - 'energy': Select lowest energy sample
    - 'entropy': Select lowest entropy production
    - 'cluster': Cluster similar solutions, select from largest cluster
    """
    
    def __init__(self, strategy: str = 'energy'):
        self.strategy = strategy
    
    def vote(self, results: List[SamplerResult]) -> SamplerResult:
        """Select best result based on voting strategy."""
        if not results:
            raise ValueError("No results to vote on")
        
        if len(results) == 1:
            return results[0]
        
        if self.strategy == 'energy':
            return min(results, key=lambda r: r.energy)
        
        elif self.strategy == 'entropy':
            return min(results, key=lambda r: r.entropy_production)
        
        elif self.strategy == 'combined':
            # Weighted combination of energy and entropy
            def score(r):
                return r.energy + 0.1 * r.entropy_production
            return min(results, key=score)
        
        elif self.strategy == 'cluster':
            return self._cluster_vote(results)
        
        else:
            raise ValueError(f"Unknown strategy: {self.strategy}")
    
    def _cluster_vote(self, results: List[SamplerResult], threshold: float = 0.1) -> SamplerResult:
        """Cluster similar samples and select from largest cluster."""
        # Simple clustering by sample similarity
        clusters = []
        
        for result in results:
            added = False
            for cluster in clusters:
                # Check similarity to cluster centroid
                centroid = np.mean([r.sample for r in cluster], axis=0)
                dist = np.linalg.norm(result.sample - centroid)
                if dist < threshold:
                    cluster.append(result)
                    added = True
                    break
            
            if not added:
                clusters.append([result])
        
        # Select from largest cluster
        largest_cluster = max(clusters, key=len)
        
        # Return lowest energy from largest cluster
        return min(largest_cluster, key=lambda r: r.energy)
