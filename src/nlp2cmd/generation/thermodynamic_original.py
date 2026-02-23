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

from dataclasses import dataclass, field
from typing import Any, Callable, Optional
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
        def pad(self, *args, **kwargs):
            raise ImportError(
                "numpy is not installed. Install it to use thermodynamic optimization features."
            )
        def var(self, *args, **kwargs):
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
        def argmax(self, *args, **kwargs):
            raise ImportError(
                "numpy is not installed. Install it to use thermodynamic optimization features."
            )
        def max(self, *args, **kwargs):
            raise ImportError(
                "numpy is not installed. Install it to use thermodynamic optimization features."
            )
    np = _NumpyStub()
import re
import json
from pathlib import Path

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


@dataclass
class OptimizationProblem:
    """Structured optimization problem definition."""

    problem_type: str  # schedule, allocate, route, assign, balance
    variables: list[str]
    constraints: list[dict[str, Any]]
    objective: Optional[str] = None  # minimize, maximize
    objective_field: Optional[str] = None
    bounds: Optional[dict[str, tuple[float, float]]] = None

    # Optional sizing hints (used by energy models / output formatting)
    n_tasks: Optional[int] = None
    n_slots: Optional[int] = None
    n_resources: Optional[int] = None
    n_consumers: Optional[int] = None

    def to_condition(self) -> dict[str, Any]:
        """Convert to condition dict for Langevin sampler."""
        return {
            "problem_type": self.problem_type,
            "constraints": self.constraints,
            "objective": self.objective,
            "bounds": self.bounds,
        }


@dataclass
class ThermodynamicResult:
    """Result of thermodynamic optimization."""

    problem: OptimizationProblem
    solution: dict[str, Any]
    energy: float
    entropy_production: float
    n_samples: int
    converged: bool
    latency_ms: float

    sampler_steps: Optional[int] = None

    # Decoded solution
    decoded_output: Optional[str] = None

    # Energy estimation
    energy_estimate: Optional[dict[str, float]] = None

    solution_quality: Optional["SolutionQuality"] = None

    errors: list[str] = field(default_factory=list)


@dataclass
class SolutionQuality:
    is_feasible: bool
    constraint_violations: list[str]
    optimality_gap: float
    explanation: str


class SchedulingEnergy(EnergyModel):
    """
    Energy model for scheduling problems.

    Penalizes:
    - Task overlaps
    - Deadline violations
    - Resource overallocation
    """

    OVERLAP_PENALTY = 100.0
    DEADLINE_PENALTY = 50.0
    PREFERENCE_PENALTY = 10.0

    def __init__(self, n_tasks: int, n_slots: int):
        self.n_tasks = n_tasks
        self.n_slots = n_slots

    def energy(self, z: np.ndarray, condition: dict[str, Any]) -> float:
        """Compute scheduling energy."""
        # Decode z into task-slot assignments
        assignments = self._decode_assignments(z)

        total_energy = 0.0
        constraints = condition.get("constraints", [])

        # Overlap penalty
        for slot in range(self.n_slots):
            tasks_in_slot = sum(1 for a in assignments if a == slot)
            if tasks_in_slot > 1:
                total_energy += self.OVERLAP_PENALTY * (tasks_in_slot - 1)

        # Deadline constraints
        for c in constraints:
            if c.get("type") == "deadline":
                task_idx = c.get("task", 0)
                deadline_slot = c.get("slot", self.n_slots)
                if task_idx < len(assignments):
                    if assignments[task_idx] > deadline_slot:
                        violation = assignments[task_idx] - deadline_slot
                        total_energy += self.DEADLINE_PENALTY * violation

        return total_energy

    def gradient(self, z: np.ndarray, condition: dict[str, Any]) -> np.ndarray:
        """Compute gradient using central differences from base class."""
        return self.numerical_gradient(z, condition)

    def _decode_assignments(self, z: np.ndarray) -> list[int]:
        """Decode continuous z to discrete slot assignments."""
        # Each task gets n_slots values, softmax to get assignment
        assignments = []
        chunk_size = self.n_slots

        for i in range(self.n_tasks):
            start = i * chunk_size
            end = start + chunk_size
            if end <= len(z):
                probs = self._softmax(z[start:end])
                assignments.append(int(np.argmax(probs)))
            else:
                assignments.append(0)

        return assignments

    def _softmax(self, x: np.ndarray) -> np.ndarray:
        """Stable softmax."""
        e_x = np.exp(x - np.max(x))
        return e_x / e_x.sum()


class AllocationEnergy(EnergyModel):
    """
    Energy model for resource allocation problems.

    Penalizes:
    - Capacity violations
    - Unmet demands
    - Imbalanced allocation
    """

    CAPACITY_PENALTY = 100.0
    DEMAND_PENALTY = 50.0
    BALANCE_PENALTY = 5.0

    def __init__(self, n_resources: int, n_consumers: int):
        self.n_resources = n_resources
        self.n_consumers = n_consumers

    def energy(self, z: np.ndarray, condition: dict[str, Any]) -> float:
        """Compute allocation energy."""
        # Decode z into allocation matrix
        allocation = self._decode_allocation(z)

        total_energy = 0.0
        constraints = condition.get("constraints", [])

        # Capacity constraints
        for c in constraints:
            if c.get("type") == "capacity":
                resource_idx = c.get("resource", 0)
                capacity = c.get("value", float("inf"))
                if resource_idx < self.n_resources:
                    usage = allocation[:, resource_idx].sum()
                    if usage > capacity:
                        total_energy += self.CAPACITY_PENALTY * (usage - capacity)

        # Demand constraints
        for c in constraints:
            if c.get("type") == "demand":
                consumer_idx = c.get("consumer", 0)
                demand = c.get("value", 0)
                if consumer_idx < self.n_consumers:
                    allocated = allocation[consumer_idx, :].sum()
                    if allocated < demand:
                        total_energy += self.DEMAND_PENALTY * (demand - allocated)

        # Balance penalty (variance in allocation)
        resource_usage = allocation.sum(axis=0)
        if len(resource_usage) > 1:
            total_energy += self.BALANCE_PENALTY * np.var(resource_usage)

        return total_energy

    def gradient(self, z: np.ndarray, condition: dict[str, Any]) -> np.ndarray:
        """Compute gradient using central differences from base class."""
        return self.numerical_gradient(z, condition)

    def _decode_allocation(self, z: np.ndarray) -> np.ndarray:
        """Decode continuous z to allocation matrix."""
        # Reshape and apply softmax per consumer
        size = self.n_consumers * self.n_resources
        z_resized = z[:size] if len(z) >= size else np.pad(z, (0, size - len(z)))

        matrix = z_resized.reshape(self.n_consumers, self.n_resources)

        # Apply sigmoid to get [0, 1] allocation values
        return 1 / (1 + np.exp(-matrix))


class RoutingEnergy(EnergyModel):
    """
    Energy model for routing problems (TSP, VRP).

    Encodes z as permutation relaxation using doubly stochastic matrix.
    Uses softmax for soft assignment with entropy regularization.

    Penalizes:
    - Total route distance
    - Row/column constraint violations (each city visited once)
    """

    DISTANCE_WEIGHT = 1.0
    ROW_PENALTY = 10.0
    COL_PENALTY = 10.0

    def __init__(self, n_cities: int):
        self.n_cities = n_cities

    def energy(self, z: np.ndarray, condition: dict[str, Any]) -> float:
        """Compute routing energy."""
        distances = condition.get("distances", np.zeros((self.n_cities, self.n_cities)))
        if isinstance(distances, list):
            distances = np.array(distances)

        # Reshape to matrix and apply softmax
        Z = z[: self.n_cities ** 2].reshape(self.n_cities, self.n_cities)
        P = self._softmax_matrix(Z)

        total_energy = 0.0

        # Distance cost (expected under soft assignment)
        for i in range(self.n_cities - 1):
            for j in range(self.n_cities):
                for k in range(self.n_cities):
                    total_energy += self.DISTANCE_WEIGHT * P[i, j] * P[i + 1, k] * distances[j, k]

        # Row sum = 1 constraint
        row_sums = P.sum(axis=1)
        total_energy += self.ROW_PENALTY * np.sum((row_sums - 1) ** 2)

        # Column sum = 1 constraint
        col_sums = P.sum(axis=0)
        total_energy += self.COL_PENALTY * np.sum((col_sums - 1) ** 2)

        return total_energy

    def gradient(self, z: np.ndarray, condition: dict[str, Any]) -> np.ndarray:
        """Compute gradient using central differences from base class."""
        return self.numerical_gradient(z, condition)

    def _softmax_matrix(self, Z: np.ndarray) -> np.ndarray:
        """Apply softmax to make soft assignment matrix."""
        exp_Z = np.exp(Z - np.max(Z))
        return exp_Z / (exp_Z.sum() + 1e-10)

    def decode_route(self, z: np.ndarray) -> list[int]:
        """Decode z to route (permutation of cities)."""
        Z = z[: self.n_cities ** 2].reshape(self.n_cities, self.n_cities)
        P = self._softmax_matrix(Z)
        # Greedy assignment
        route = []
        available = set(range(self.n_cities))
        for i in range(self.n_cities):
            probs = P[i].copy()
            for j in range(self.n_cities):
                if j not in available:
                    probs[j] = -np.inf
            city = int(np.argmax(probs))
            route.append(city)
            available.discard(city)
        return route


class ThermodynamicGenerator:
    """
    Generate solutions for optimization problems using Langevin sampling.

    Workflow:
    1. Parse NL problem description (via LLM or rules)
    2. Build energy model for problem type
    3. Run Langevin sampling
    4. Decode solution and format output

    Example:
        generator = ThermodynamicGenerator()
        result = await generator.generate(
            "Zaplanuj 5 zadań w 10 slotach, zadanie 3 musi być przed slotem 5"
        )
    """

    # Problem type to energy model mapping
    ENERGY_MODELS: dict[str, type[EnergyModel]] = {
        "schedule": SchedulingEnergy,
        "allocate": AllocationEnergy,
        "route": RoutingEnergy,
    }

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        langevin_config: Optional[LangevinConfig] = None,
        n_samples: int = 5,
        voting_strategy: str = "energy",
        adaptive_steps: bool = True,  # NEW: adaptively reduce steps for small problems
        parallel_sampling: bool = False,  # Use parallel thread pool for sampling
        max_workers: int = 4,  # Max threads for parallel sampling
    ):
        self.llm = llm_client
        self.base_langevin_config = langevin_config or LangevinConfig(
            n_steps=500,
            kT=0.5,
            mu=1.0,
        )
        self.langevin_config = self.base_langevin_config
        self.n_samples = n_samples
        self.voter = MajorityVoter(strategy=voting_strategy)
        self.router = ThermodynamicRouter()
        self.energy_estimator = EnergyEstimator()
        self.regularizer = EntropyProductionRegularizer()
        self.adaptive_steps = adaptive_steps
        self.parallel_sampling = parallel_sampling
        self.max_workers = max_workers

        if llm_client:
            self.planner = StructuredLLMPlanner(llm_client)
        else:
            self.planner = None

    def _get_adaptive_config(self, problem: OptimizationProblem) -> LangevinConfig:
        """
        IMPROVEMENT: Adjust Langevin steps based on problem complexity.
        
        Small problems (< 10 variables) need fewer steps.
        """
        if not self.adaptive_steps:
            return self.base_langevin_config

        n_vars = len(problem.variables)
        
        # Adaptive step count based on problem size
        if n_vars <= 3:
            n_steps = 100  # Very small - fast convergence
            threshold = 0.05  # Higher threshold for early stopping
        elif n_vars <= 5:
            n_steps = 200  # Small
            threshold = 0.02
        elif n_vars <= 10:
            n_steps = 300  # Medium
            threshold = 0.01
        else:
            n_steps = self.base_langevin_config.n_steps  # Large - use default
            threshold = 0.01

        return LangevinConfig(
            n_steps=n_steps,
            kT=self.base_langevin_config.kT,
            mu=self.base_langevin_config.mu,
            dim=self.base_langevin_config.dim,
            early_stopping=True,
            convergence_threshold=threshold,
            check_interval=min(100, n_steps // 4),  # Check more frequently for small problems
        )

    def _get_sampling_config(self, problem: OptimizationProblem) -> tuple[LangevinConfig, int]:
        """Return (LangevinConfig, n_samples) adapted to problem size."""
        config = self._get_adaptive_config(problem)

        n_vars = len(problem.variables)
        if n_vars <= 3:
            n_samples = min(self.n_samples, 3)
        elif n_vars <= 8:
            n_samples = min(self.n_samples, 5)
        else:
            n_samples = self.n_samples

        return config, n_samples

    async def generate(
        self,
        text: str,
        problem: Optional[OptimizationProblem] = None,
    ) -> ThermodynamicResult:
        """
        Generate solution for optimization problem.

        Args:
            text: Natural language problem description
            problem: Pre-parsed problem (optional)

        Returns:
            ThermodynamicResult with solution
        """
        import time
        start = time.time()

        try:
            # Parse problem if not provided
            if problem is None:
                problem = await self._parse_problem(text)

            # IMPROVEMENT: Get adaptive config based on problem size
            config, n_samples = self._get_sampling_config(problem)

            # Get or create energy model
            energy_model = self._create_energy_model(problem)

            # Configure sampler with adaptive config
            sampler = LangevinSampler(energy_model, config)

            # Sample multiple solutions (parallel or sequential)
            condition = problem.to_condition()
            if self.parallel_sampling and n_samples > 1:
                results = sampler.sample_parallel(
                    condition, n_samples=n_samples, max_workers=self.max_workers
                )
            else:
                results = sampler.sample(condition, n_samples=n_samples)

            if not isinstance(results, list):
                results = [results]

            # Vote for best solution
            best = self.voter.vote(results)

            # Decode solution
            solution = self._decode_solution(best, problem, energy_model)

            # Format output
            decoded_output = self._format_output(solution, problem)

            solution_quality = self.validate_solution(solution, problem, best_energy=best.energy)

            # Estimate energy savings
            energy_estimate = self.energy_estimator.estimate(
                llm_input_tokens=len(text.split()),
                llm_output_tokens_classic=100,
                llm_output_tokens_hybrid=30,
                langevin_steps=config.n_steps,
            )

            latency = (time.time() - start) * 1000

            return ThermodynamicResult(
                problem=problem,
                solution=solution,
                energy=best.energy,
                entropy_production=best.entropy_production,
                n_samples=len(results),
                converged=best.converged,
                latency_ms=latency,
                sampler_steps=getattr(best, "n_steps", None),
                decoded_output=decoded_output,
                energy_estimate=energy_estimate,
                solution_quality=solution_quality,
            )

        except Exception as e:
            latency = (time.time() - start) * 1000
            return ThermodynamicResult(
                problem=problem or OptimizationProblem("unknown", [], []),
                solution={},
                energy=float("inf"),
                entropy_production=0.0,
                n_samples=0,
                converged=False,
                latency_ms=latency,
                errors=[str(e)],
            )

    async def _parse_problem(self, text: str) -> OptimizationProblem:
        """Parse problem from natural language."""
        # Try LLM if available
        if self.planner:
            result = await self.planner.plan(text)
            if result.success and result.plan:
                return self._plan_to_problem(result.plan)

        # Fallback: rule-based parsing
        return self._rule_based_parse(text)

    def _plan_to_problem(self, plan: StructuredPlan) -> OptimizationProblem:
        """Convert structured plan to optimization problem."""
        entities = plan.entities

        return OptimizationProblem(
            problem_type=plan.intent,
            variables=entities.get("variables", []),
            constraints=entities.get("constraints", []),
            objective=entities.get("objective"),
            objective_field=entities.get("objective_field"),
            bounds=entities.get("bounds"),
            n_tasks=entities.get("n_tasks"),
            n_slots=entities.get("n_slots"),
            n_resources=entities.get("n_resources"),
            n_consumers=entities.get("n_consumers"),
        )

    def _rule_based_parse(self, text: str) -> OptimizationProblem:
        """
        IMPROVED: Rule-based problem parsing with better Polish support.

        Fixes:
        - Proper UTF-8 handling for Polish characters
        - Better extraction of "X zasobów do Y konsumentów"
        - Correct number of resources/consumers
        """
        text_lower = text.lower()

        # Polish keywords (properly encoded)
        schedule_keywords = [
            "zaplanuj", "schedule", "zadań", "zadania", "harmonogram",
            "rozplanuj", "ułóż", "zadan"  # fallback for encoding issues
        ]
        allocate_keywords = [
            "przydziel", "allocate", "zasobów", "zasoby", "alokuj",
            "rozdziel", "podziel", "zasobow"  # fallback for encoding issues
        ]
        routing_keywords = [
            "trasa", "route", "routing", "tsp", "vrp", "miasta", "city",
            "odwiedź", "visit", "podróż", "travel", "komiwojażer"
        ]

        # Detect problem type
        if any(kw in text_lower for kw in routing_keywords):
            problem_type = "route"
        elif "przydziel" in text_lower or "allocate" in text_lower or "zasob" in text_lower:
            problem_type = "allocate"
        elif "zaplanuj" in text_lower or "schedule" in text_lower or "zad" in text_lower:
            problem_type = "schedule"
        else:
            problem_type = "schedule"  # default

        # IMPROVED: Better number extraction with context
        import re
        numbers = [int(n) for n in re.findall(r'\d+', text)]

        n_tasks: Optional[int] = None
        n_slots: Optional[int] = None
        n_resources: Optional[int] = None
        n_consumers: Optional[int] = None

        # Heuristic sizing extraction
        if problem_type == "schedule":
            # Examples:
            # - "Zaplanuj 5 zadań w 10 slotach"
            # - "Zaplanuj 3 zadania"
            m = re.search(r'(\d+)\s+(?:zada\w*)', text_lower)
            if m:
                n_tasks = int(m.group(1))
            m = re.search(r'(\d+)\s+(?:slot\w*|okn\w*|termin\w*)', text_lower)
            if m:
                n_slots = int(m.group(1))
        elif problem_type == "allocate":
            # IMPROVED: Better patterns for allocation
            # - "Przydziel 3 zasoby do 4 konsumentów"
            # - "Allocate 5 resources to 3 consumers"
            m = re.search(r'(\d+)\s+(?:zasob\w*|resource\w*)\s+do\s+(\d+)\s+(?:konsument\w*|consumer\w*|odbiorc\w*)', text_lower)
            if m:
                n_resources = int(m.group(1))
                n_consumers = int(m.group(2))
            else:
                # Fallback patterns
                m = re.search(r'(\d+)\s+(?:zasob\w*|resource\w*)', text_lower)
                if m:
                    n_resources = int(m.group(1))
                m = re.search(r'(\d+)\s+(?:konsument\w*|consumer\w*|odbiorc\w*)', text_lower)
                if m:
                    n_consumers = int(m.group(1))

        # Defaults (only if missing)
        if n_resources is None:
            n_resources = 5
        if n_consumers is None:
            n_consumers = 5
        if n_tasks is None:
            n_tasks = 5
        if n_slots is None:
            n_slots = 10

        # Build constraints from text
        constraints = []

        if "przed" in text_lower or "before" in text_lower:
            # Deadline constraint
            deadline_match = re.search(r'(?:zadanie|task)\s*(\d+).*(?:przed|before).*(?:slot|czas)?\s*(\d+)', text_lower)
            if deadline_match:
                constraints.append({
                    "type": "deadline",
                    "task": int(deadline_match.group(1)),
                    "slot": int(deadline_match.group(2)),
                })
            elif len(numbers) >= 2:
                constraints.append({
                    "type": "deadline",
                    "task": numbers[0] if len(numbers) > 0 else 0,
                    "slot": numbers[1] if len(numbers) > 1 else 5,
                })

        if problem_type == "schedule":
            task_count = n_tasks or (numbers[0] if numbers else 5)
            slot_count = n_slots or 10
            return OptimizationProblem(
                problem_type=problem_type,
                variables=[f"task_{i}" for i in range(task_count)],
                constraints=constraints,
                n_tasks=task_count,
                n_slots=slot_count,
            )

        if problem_type == "route":
            # Extract number of cities from text
            m = re.search(r'(\d+)\s+(?:miast\w*|cit\w*|punkt\w*|lokal\w*)', text_lower)
            n_cities = int(m.group(1)) if m else (numbers[0] if numbers else 5)
            return OptimizationProblem(
                problem_type=problem_type,
                variables=[f"city_{i}" for i in range(n_cities)],
                constraints=constraints,
            )

        consumer_count = n_consumers or (numbers[1] if len(numbers) > 1 else (numbers[0] if numbers else 3))
        resource_count = n_resources or (numbers[0] if numbers else 2)
        
        # CRITICAL FIX: For allocation, variables represent resources, not consumers
        return OptimizationProblem(
            problem_type=problem_type,
            variables=[f"resource_{i}" for i in range(resource_count)],  # FIXED: was consumer_i
            constraints=constraints,
            n_resources=resource_count,
            n_consumers=consumer_count,
        )

    def _create_energy_model(self, problem: OptimizationProblem) -> EnergyModel:
        """Create appropriate energy model for problem."""
        n_vars = len(problem.variables) or 5

        if problem.problem_type == "schedule":
            # Default: 10 time slots
            n_slots = problem.n_slots or 10
            n_tasks = problem.n_tasks or n_vars
            return SchedulingEnergy(n_tasks=n_tasks, n_slots=n_slots)

        elif problem.problem_type == "allocate":
            # Default: 5 resources
            n_resources = problem.n_resources or 5
            n_consumers = problem.n_consumers or n_vars
            return AllocationEnergy(n_resources=n_resources, n_consumers=n_consumers)

        elif problem.problem_type == "route":
            # Routing/TSP problems
            n_cities = len(problem.variables) or 5
            return RoutingEnergy(n_cities=n_cities)

        else:
            # Generic constraint energy
            return ConstraintEnergy()

    def _decode_solution(
        self,
        result: SamplerResult,
        problem: OptimizationProblem,
        energy_model: EnergyModel,
    ) -> dict[str, Any]:
        """Decode sampler result to solution dict."""
        z = result.sample

        if isinstance(energy_model, SchedulingEnergy):
            assignments = energy_model._decode_assignments(z)
            return {
                "assignments": {
                    var: slot
                    for var, slot in zip(problem.variables, assignments)
                },
                "raw_sample": z.tolist(),
            }

        elif isinstance(energy_model, AllocationEnergy):
            allocation = energy_model._decode_allocation(z)
            return {
                "allocation": allocation.tolist(),
                "n_resources": energy_model.n_resources,  # Store for formatting
                "raw_sample": z.tolist(),
            }

        elif isinstance(energy_model, RoutingEnergy):
            route = energy_model.decode_route(z)
            return {
                "route": route,
                "n_cities": energy_model.n_cities,
                "raw_sample": z.tolist(),
            }

        return {"raw_sample": z.tolist()}

    def _format_output(
        self,
        solution: dict[str, Any],
        problem: OptimizationProblem,
    ) -> str:
        """Format solution as readable output."""
        if problem.problem_type == "schedule":
            assignments = solution.get("assignments", {})
            lines = ["# Schedule:"]
            for task, slot in sorted(assignments.items(), key=lambda x: x[1]):
                lines.append(f"  Slot {slot}: {task}")
            return "\n".join(lines)

        elif problem.problem_type == "allocate":
            allocation = solution.get("allocation", [])
            n_resources = solution.get("n_resources", len(allocation[0]) if allocation else 0)
            lines = ["# Allocation:"]
            for i, row in enumerate(allocation):
                row = row[:n_resources] if n_resources else row
                resources = ", ".join(f"R{j}={v:.2f}" for j, v in enumerate(row))
                lines.append(f"  Consumer {i}: {resources}")
            return "\n".join(lines)

        elif problem.problem_type == "route":
            route = solution.get("route", [])
            lines = ["# Route (TSP):"]
            route_str = " → ".join(f"City_{c}" for c in route)
            lines.append(f"  {route_str}")
            if route:
                lines.append(f"  (Return to City_{route[0]})")
            return "\n".join(lines)

        return f"# Solution:\n{solution}"

    def validate_solution(
        self,
        solution: dict[str, Any],
        problem: OptimizationProblem,
        best_energy: Optional[float] = None,
    ) -> SolutionQuality:
        violations: list[str] = []

        if problem.problem_type == "schedule":
            assignments: dict[str, int] = solution.get("assignments", {})

            slot_to_tasks: dict[int, list[str]] = {}
            for task, slot in assignments.items():
                slot_to_tasks.setdefault(int(slot), []).append(task)
            for slot, tasks in slot_to_tasks.items():
                if len(tasks) > 1:
                    violations.append(f"Overlap in slot {slot}: {', '.join(sorted(tasks))}")

            for c in problem.constraints:
                if c.get("type") == "deadline":
                    task_idx = c.get("task")
                    deadline = c.get("slot")
                    if task_idx is None or deadline is None:
                        continue
                    task_key = f"task_{task_idx}"
                    assigned = assignments.get(task_key)
                    if assigned is not None and int(assigned) > int(deadline):
                        violations.append(
                            f"{task_key} assigned to slot {assigned}, deadline was {deadline}"
                        )

        elif problem.problem_type == "allocate":
            allocation = solution.get("allocation")
            if isinstance(allocation, list) and allocation:
                try:
                    mat = np.array(allocation, dtype=float)
                except Exception:
                    mat = None
                if mat is not None:
                    for c in problem.constraints:
                        if c.get("type") == "capacity":
                            resource_idx = c.get("resource")
                            capacity = c.get("value")
                            if resource_idx is None or capacity is None:
                                continue
                            if 0 <= int(resource_idx) < mat.shape[1]:
                                usage = float(mat[:, int(resource_idx)].sum())
                                if usage > float(capacity):
                                    violations.append(
                                        f"Resource {resource_idx} usage {usage:.2f} exceeds capacity {capacity}"
                                    )
                        if c.get("type") == "demand":
                            consumer_idx = c.get("consumer")
                            demand = c.get("value")
                            if consumer_idx is None or demand is None:
                                continue
                            if 0 <= int(consumer_idx) < mat.shape[0]:
                                allocated = float(mat[int(consumer_idx), :].sum())
                                if allocated < float(demand):
                                    violations.append(
                                        f"Consumer {consumer_idx} allocated {allocated:.2f} below demand {demand}"
                                    )

        elif problem.problem_type == "route":
            route = solution.get("route", [])
            n_cities = solution.get("n_cities", len(route))
            
            # Check all cities visited exactly once
            if len(route) != n_cities:
                violations.append(f"Route has {len(route)} cities, expected {n_cities}")
            
            visited = set(route)
            if len(visited) != len(route):
                duplicates = [c for c in route if route.count(c) > 1]
                violations.append(f"Duplicate cities in route: {set(duplicates)}")
            
            expected_cities = set(range(n_cities))
            missing = expected_cities - visited
            if missing:
                violations.append(f"Missing cities: {missing}")

        is_feasible = len(violations) == 0

        if best_energy is None or not np.isfinite(best_energy):
            optimality_gap = 1.0
        elif best_energy <= 0:
            optimality_gap = 0.0
        else:
            optimality_gap = float(min(1.0, best_energy / (best_energy + 1.0)))

        if is_feasible:
            explanation = "All constraints satisfied"
        else:
            explanation = f"Constraints violated: {len(violations)}"

        return SolutionQuality(
            is_feasible=is_feasible,
            constraint_violations=violations,
            optimality_gap=optimality_gap,
            explanation=explanation,
        )


class HybridThermodynamicGenerator:
    """
    Hybrid generator combining rule/LLM-based DSL with thermodynamic optimization.

    Routes:
    - Simple queries → Rule-based or LLM generation
    - Optimization problems → Thermodynamic sampling

    IMPROVEMENTS:
    - Lower threshold for optimization detection (0.3 instead of 0.4)
    - Better keyword matching for Polish
    - Explicit check for optimization keywords before DSL routing
    """

    # IMPROVED: More comprehensive optimization keywords
    OPTIMIZATION_KEYWORDS = [
        # Polish
        "zaplanuj", "przydziel", "optymalizuj", "rozłóż", "harmonogram",
        "alokuj", "rozdziel", "zbalansuj", "minimalizuj", "maksymalizuj",
        # Fallback (encoding issues)
        "zaplanu", "przydziel", "optymali", "rozloz", "aloku",
        # English
        "schedule", "allocate", "optimize", "balance", "distribute",
        "assign", "plan", "minimize", "maximize",
        # Routing (TSP/VRP)
        "trasa", "route", "routing", "tsp", "vrp", "miasta",
        "odwiedź", "komiwojażer", "travel",
    ]

    @staticmethod
    def _load_optimization_schema() -> dict[str, Any]:
        def _candidate_paths() -> list[Path]:
            yield Path("data") / "optimization_schema.json"
            yield Path("./data") / "optimization_schema.json"
            try:
                repo_root = Path(__file__).resolve().parents[4]
                yield repo_root / "data" / "optimization_schema.json"
            except Exception:
                return

        for p in _candidate_paths():
            try:
                if p.exists() and p.is_file():
                    raw = json.loads(p.read_text(encoding="utf-8"))
                    if isinstance(raw, dict):
                        return raw
            except Exception:
                continue
        return {}

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        langevin_config: Optional[LangevinConfig] = None,
    ):
        from nlp2cmd.generation.hybrid import HybridGenerator, create_hybrid_generator

        self.dsl_generator = create_hybrid_generator(llm_client)
        self.thermo_generator = ThermodynamicGenerator(
            llm_client=llm_client,
            langevin_config=langevin_config,
            adaptive_steps=True,  # Enable adaptive steps
        )
        self.router = ThermodynamicRouter()

    def _is_optimization_query(self, text: str) -> bool:
        """
        IMPROVED: Check if query is an optimization problem.

        Uses comprehensive keyword matching with Polish support.
        """
        text_lower = text.lower()
        schema = self._load_optimization_schema()
        kws = schema.get("optimization_keywords")
        if isinstance(kws, list) and kws:
            keywords = [k for k in kws if isinstance(k, str) and k.strip()]
        else:
            keywords = self.OPTIMIZATION_KEYWORDS
        return any(kw in text_lower for kw in keywords)

    async def generate(
        self,
        text: str,
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Route and generate based on problem type.

        Returns dict with:
        - source: 'dsl' or 'thermodynamic'
        - result: Generation result

        IMPROVED routing logic:
        1. First check for explicit optimization keywords
        2. If found, use thermodynamic regardless of complexity
        3. Otherwise, use DSL generator
        """

        if self._is_optimization_query(text):
            result = await self.thermo_generator.generate(text)
            return {'source': 'thermodynamic', 'result': result}

        # DSL fallback
        result = await self.dsl_generator.generate(text, context)
        return {'source': 'dsl', 'result': result}


def create_thermodynamic_generator(
    llm_client: Optional[LLMClient] = None,
    n_samples: int = 5,
    n_steps: int = 500,
    adaptive_steps: bool = True,
    parallel_sampling: bool = False,
    max_workers: int = 4,
) -> ThermodynamicGenerator:
    """
    Factory function for thermodynamic generator.

    Based on Whitelam 2025 "Generative Thermodynamic Computing" (arXiv:2506.15121).

    Args:
        llm_client: Optional LLM client for problem parsing
        n_samples: Number of samples for voting (default: 5)
        n_steps: Base number of Langevin steps (default: 500)
        adaptive_steps: If True, reduce steps for small problems (default: True)
        parallel_sampling: If True, use thread pool for parallel sampling (default: False)
        max_workers: Max threads for parallel sampling (default: 4)

    Returns:
        ThermodynamicGenerator configured for optimization problems

    Example:
        >>> generator = create_thermodynamic_generator(n_samples=5)
        >>> result = await generator.generate("Zaplanuj 5 zadań w 10 slotach")
        >>> print(result.decoded_output)
    """
    config = LangevinConfig(
        n_steps=n_steps,
        kT=0.5,
        mu=1.0,
        dim=64,
    )

    return ThermodynamicGenerator(
        llm_client=llm_client,
        langevin_config=config,
        n_samples=n_samples,
        adaptive_steps=adaptive_steps,
        parallel_sampling=parallel_sampling,
        max_workers=max_workers,
    )