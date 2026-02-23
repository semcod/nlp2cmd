"""
Iteration 10: Thermodynamic Optimization Integration (IMPROVED).

Integrate Langevin sampling for complex optimization problems:
- Scheduling, allocation, routing, planning
- Energy-based constraint satisfaction
- Hybrid LLM formalization + thermodynamic sampling

Based on Whitelam 2025 "Generative Thermodynamic Computing" (arXiv:2506.15121).

Key concepts:
- Langevin dynamics: dz = -μ∇V(z;c)dt + √(2μkT) dW
- Energy minimization for constraint satisfaction
- Majority voting across parallel samples
- Entropy production regularization

IMPROVEMENTS v1.2:
- [REFACTOR] Gradient computation uses base class numerical_gradient
- [FIX] Router now correctly identifies optimization problems (lowered threshold)
- [FIX] Allocation energy model uses correct number of resources from text
- [PERF] Adaptive n_steps based on problem size (smaller problems = fewer steps)
- [FIX] Polish UTF-8 keywords properly decoded
- [FIX] Better number extraction for "X zasobów do Y konsumentów"
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Optional

from nlp2cmd.thermodynamic import (
    LangevinConfig,
    LangevinSampler,
    SamplerResult,
    EnergyModel,
    ConstraintEnergy,
    MajorityVoter,
    ThermodynamicRouter,
    EnergyEstimator,
    EntropyProductionRegularizer,
)
from nlp2cmd.generation.structured import StructuredPlan, StructuredLLMPlanner
from nlp2cmd.generation.llm_simple import LLMClient, LLMConfig
from nlp2cmd.generation.thermodynamic_components import (
    OptimizationProblem,
    ThermodynamicResult,
    ThermodynamicProblemDetector,
    ThermodynamicConfig,
)


class ThermodynamicGenerator:
    """
    Generate solutions for optimization problems using Langevin sampling.
    
    This generator handles complex optimization problems that require
    constraint satisfaction and energy minimization.
    """
    
    def __init__(
        self,
        *,
        llm_client: Optional[LLMClient] = None,
        config: Optional[ThermodynamicConfig] = None,
    ):
        self.llm_client = llm_client
        self.config = config or ThermodynamicConfig()
        
        # Initialize components
        self.problem_detector = ThermodynamicProblemDetector()
        self.router = ThermodynamicRouter()
        self.energy_estimator = EnergyEstimator()
        
        # Initialize sampler (lazy loaded)
        self._sampler = None
    
    @property
    def sampler(self) -> LangevinSampler:
        """Get or create Langevin sampler."""
        if self._sampler is None:
            self._sampler = LangevinSampler()
        return self._sampler
    
    async def generate(
        self,
        text: str,
        problem: Optional[OptimizationProblem] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> ThermodynamicResult:
        """Generate solution using thermodynamic optimization."""
        start_time = time.time()
        
        try:
            # Detect or use provided problem
            if problem is None:
                problem = self.problem_detector.detect_problem(text)
                if problem is None:
                    return ThermodynamicResult(
                        decoded_output="# Not an optimization problem",
                        energy_estimate=float('inf'),
                        converged=False,
                        n_samples=0,
                        entropy_production=0.0,
                        latency_ms=(time.time() - start_time) * 1000,
                        errors=["No optimization problem detected"],
                    )
            
            # Adapt configuration to problem size
            config = self.config.adapt_to_problem_size(problem)
            
            # Create energy model
            energy_model = self._create_energy_model(problem)
            
            # Setup Langevin configuration
            langevin_config = LangevinConfig(
                n_samples=config.n_samples,
                n_steps=config.n_steps,
                temperature=config.temperature,
                step_size=config.step_size,
                convergence_threshold=config.convergence_threshold,
            )
            
            # Run Langevin sampling
            sampler_result = self.sampler.sample(
                energy_model=energy_model,
                config=langevin_config,
                context=context or {},
            )
            
            # Decode result
            decoded_output = self._decode_result(sampler_result, problem)
            
            # Calculate metrics
            energy_estimate = self.energy_estimator.estimate(sampler_result)
            entropy_production = self._calculate_entropy_production(sampler_result)
            
            return ThermodynamicResult(
                decoded_output=decoded_output,
                energy_estimate=energy_estimate,
                converged=sampler_result.converged,
                n_samples=config.n_samples,
                entropy_production=entropy_production,
                solution_quality=sampler_result.solution_quality,
                latency_ms=(time.time() - start_time) * 1000,
            )
            
        except Exception as e:
            return ThermodynamicResult(
                decoded_output="# Thermodynamic optimization failed",
                energy_estimate=float('inf'),
                converged=False,
                n_samples=0,
                entropy_production=0.0,
                latency_ms=(time.time() - start_time) * 1000,
                errors=[f"Generation error: {e}"],
            )
    
    def _create_energy_model(self, problem: OptimizationProblem) -> EnergyModel:
        """Create energy model for the problem."""
        # Create constraint energy
        constraint_energy = ConstraintEnergy()
        
        # Add constraints to energy model
        for constraint in problem.constraints:
            constraint_energy.add_constraint(constraint)
        
        # Create energy model with constraints
        energy_model = EnergyModel(constraint_energy=constraint_energy)
        
        # Set objective if specified
        if problem.objective and problem.objective_field:
            energy_model.set_objective(problem.objective, problem.objective_field)
        
        return energy_model
    
    def _decode_result(self, sampler_result: SamplerResult, problem: OptimizationProblem) -> str:
        """Decode sampler result to human-readable format."""
        if not sampler_result.samples:
            return "# No solution found"
        
        # Use majority voting to get best solution
        voter = MajorityVoter()
        best_solution = voter.vote(sampler_result.samples)
        
        # Format solution based on problem type
        if problem.problem_type == "schedule":
            return self._format_schedule_solution(best_solution, problem)
        elif problem.problem_type == "allocate":
            return self._format_allocation_solution(best_solution, problem)
        elif problem.problem_type == "route":
            return self._format_routing_solution(best_solution, problem)
        elif problem.problem_type == "assign":
            return self._format_assignment_solution(best_solution, problem)
        elif problem.problem_type == "balance":
            return self._format_balance_solution(best_solution, problem)
        else:
            return str(best_solution)
    
    def _format_schedule_solution(self, solution: Any, problem: OptimizationProblem) -> str:
        """Format scheduling solution."""
        # Simple formatting - could be enhanced
        return f"# Schedule: {solution}"
    
    def _format_allocation_solution(self, solution: Any, problem: OptimizationProblem) -> str:
        """Format allocation solution."""
        return f"# Allocation: {solution}"
    
    def _format_routing_solution(self, solution: Any, problem: OptimizationProblem) -> str:
        """Format routing solution."""
        return f"# Route: {solution}"
    
    def _format_assignment_solution(self, solution: Any, problem: OptimizationProblem) -> str:
        """Format assignment solution."""
        return f"# Assignment: {solution}"
    
    def _format_balance_solution(self, solution: Any, problem: OptimizationProblem) -> str:
        """Format balance solution."""
        return f"# Balance: {solution}"
    
    def _calculate_entropy_production(self, sampler_result: SamplerResult) -> float:
        """Calculate entropy production from sampler result."""
        if not sampler_result.samples:
            return 0.0
        
        # Simple entropy calculation
        regularizer = EntropyProductionRegularizer()
        return regularizer.calculate(sampler_result.samples)


class HybridThermodynamicGenerator:
    """
    Hybrid generator combining rule/LLM-based DSL with thermodynamic optimization.
    
    This generator first tries to use the standard pipeline, and if it detects
    an optimization problem, falls back to thermodynamic optimization.
    """
    
    def __init__(
        self,
        *,
        llm_client: Optional[LLMClient] = None,
        thermodynamic_config: Optional[ThermodynamicConfig] = None,
        optimization_threshold: float = 0.3,
    ):
        self.llm_client = llm_client
        self.thermodynamic_config = thermodynamic_config or ThermodynamicConfig()
        self.optimization_threshold = optimization_threshold
        
        # Initialize components
        self.problem_detector = ThermodynamicProblemDetector()
        self.router = ThermodynamicRouter()
        self.thermodynamic_generator = ThermodynamicGenerator(
            llm_client=llm_client,
            config=thermodynamic_config,
        )
        
        # Initialize standard pipeline (lazy loaded)
        self._pipeline = None
    
    @property
    def pipeline(self):
        """Get or create standard pipeline."""
        if self._pipeline is None:
            from nlp2cmd.generation.pipeline import RuleBasedPipeline
            self._pipeline = RuleBasedPipeline()
        return self._pipeline
    
    async def generate(
        self,
        text: str,
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Generate using hybrid approach."""
        # First, check if this is an optimization problem
        optimization_score = self.router.score_optimization(text)
        
        if optimization_score > self.optimization_threshold:
            # Use thermodynamic optimization
            result = await self.thermodynamic_generator.generate(text, context=context)
            return {
                "source": "thermodynamic",
                "result": result,
                "optimization_score": optimization_score,
            }
        else:
            # Use standard pipeline
            pipeline_result = self.pipeline.process(text)
            return {
                "source": "pipeline",
                "result": pipeline_result,
                "optimization_score": optimization_score,
            }
    
    def is_optimization_problem(self, text: str) -> bool:
        """Check if text describes an optimization problem."""
        optimization_score = self.router.score_optimization(text)
        return optimization_score > self.optimization_threshold
