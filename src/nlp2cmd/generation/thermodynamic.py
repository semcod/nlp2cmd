"""Re-exports from split thermodynamic.py module."""

from nlp2cmd.generation.allocation_energy import AllocationEnergy
from nlp2cmd.generation.hybrid_thermodynamic_generator import HybridThermodynamicGenerator
from nlp2cmd.generation.routing_energy import RoutingEnergy
from nlp2cmd.generation.scheduling_energy import SchedulingEnergy
from nlp2cmd.generation.thermodynamic_components import OptimizationProblem, ThermodynamicResult
from nlp2cmd.generation.thermodynamic_generator import ThermodynamicGenerator

__all__ = [
    "ThermodynamicGenerator",
    "HybridThermodynamicGenerator",
    "SchedulingEnergy",
    "AllocationEnergy",
    "RoutingEnergy",
    "OptimizationProblem",
    "ThermodynamicResult",
    "create_thermodynamic_generator",
]



def create_thermodynamic_generator(
    n_samples: int = 5,
    n_steps: int = 500,
    adaptive_steps: bool = True,
    parallel_sampling: bool = False,
    **kwargs
) -> ThermodynamicGenerator:
    """Create a thermodynamic generator with default configuration."""
    from nlp2cmd.generation.thermodynamic_components import ThermodynamicConfig
    
    # Create ThermodynamicConfig with correct parameters
    config = ThermodynamicConfig(
        n_samples=n_samples,
        n_steps=n_steps,
        temperature=kwargs.get('kT', 1.0),
        step_size=kwargs.get('mu', 0.1),
        convergence_threshold=kwargs.get('convergence_threshold', 1e-6),
        max_iterations=kwargs.get('max_iterations', 1000)
    )
    
    return ThermodynamicGenerator(
        config=config,
        adaptive_steps=adaptive_steps,
        parallel_sampling=parallel_sampling,
        **kwargs
    )
