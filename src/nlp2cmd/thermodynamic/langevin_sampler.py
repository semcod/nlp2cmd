# LangevinSampler - extracted from __init__.py
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
from nlp2cmd.thermodynamic.langevin_config import LangevinConfig
from nlp2cmd.thermodynamic.sampler_result import SamplerResult

class LangevinSampler:
    """
    Thermodynamic sampler using overdamped Langevin dynamics.
    
    Implements: dz = -μ∇V(z;c)dt + √(2μkT) dW
    
    Discretized (Euler-Maruyama):
    z_{k+1} = z_k - μ∇V(z_k;c)Δt + √(2μkTΔt) η_k
    
    Where:
    - z: latent state
    - c: condition from LLM
    - V: energy function
    - η: standard normal noise
    """
    
    def __init__(self, energy_model: EnergyModel, config: Optional[LangevinConfig] = None):
        self.energy = energy_model
        self.config = config or LangevinConfig()
    
    def sample(
        self,
        condition: Dict[str, Any],
        n_samples: int = 1,
        initial_state: Optional[np.ndarray] = None,
    ) -> Union[SamplerResult, List[SamplerResult]]:
        """
        Generate samples via Langevin dynamics.
        
        Args:
            condition: Conditioning information (constraints, targets, etc.)
            n_samples: Number of independent samples
            initial_state: Starting point (default: random noise)
        
        Returns:
            SamplerResult or list of SamplerResult if n_samples > 1
        """
        if n_samples == 1:
            return self._sample_single(condition, initial_state)
        else:
            return [self._sample_single(condition, initial_state) for _ in range(n_samples)]
    
    def _sample_single(
        self,
        condition: Dict[str, Any],
        initial_state: Optional[np.ndarray] = None,
    ) -> SamplerResult:
        """Generate a single sample."""
        cfg = self.config
        
        # Set random seed if specified
        if cfg.seed is not None:
            np.random.seed(cfg.seed)
        
        # Initialize from noise or given state
        if initial_state is not None:
            z = initial_state.copy()
        else:
            z = np.random.randn(cfg.dim)
        
        # Precompute noise scaling
        noise_scale = math.sqrt(2 * cfg.mu * cfg.kT * cfg.dt)
        
        # Track trajectory if requested
        trajectory = [z.copy()] if cfg.record_trajectory else None
        
        # Track entropy production
        entropy_prod = 0.0
        
        # Langevin integration
        converged = False
        actual_steps = cfg.n_steps

        for step in range(cfg.n_steps):
            # Compute energy gradient
            grad_V = self.energy.gradient(z, condition)
            
            # Generate noise
            eta = np.random.randn(cfg.dim)
            
            # Langevin update: z_{k+1} = z_k - μ∇V·dt + √(2μkT·dt)·η
            dz = -cfg.mu * grad_V * cfg.dt + noise_scale * eta
            z = z + dz
            
            # Accumulate entropy production: σ ≈ Σ (∇V · Δz) / kT
            entropy_prod += np.dot(grad_V, dz) / cfg.kT
            
            if cfg.record_trajectory:
                trajectory.append(z.copy())

            # Convergence / early stopping
            if cfg.early_stopping and (step + 1) % cfg.check_interval == 0:
                current_energy = self.energy.energy(z, condition)
                if current_energy <= cfg.convergence_threshold:
                    converged = True
                    actual_steps = step + 1
                    break
        
        # Final energy
        final_energy = self.energy.energy(z, condition)

        if cfg.early_stopping and not converged:
            converged = final_energy <= cfg.convergence_threshold

        return SamplerResult(
            sample=z,
            energy=final_energy,
            trajectory=np.array(trajectory) if trajectory else None,
            entropy_production=entropy_prod,
            n_steps=actual_steps,
            converged=converged,
            metadata={'condition': condition}
        )
    
    def sample_parallel(
        self,
        condition: Dict[str, Any],
        n_samples: int,
        max_workers: int = 4,
    ) -> List[SamplerResult]:
        """Sample in parallel using thread pool."""
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(self._sample_single, condition, None)
                for _ in range(n_samples)
            ]
            results = [f.result() for f in as_completed(futures)]
        return results
