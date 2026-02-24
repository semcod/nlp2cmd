"""
Iteration 10: Thermodynamic Optimization Tests.

Test Langevin sampling for optimization problems.
"""

import pytest

np = pytest.importorskip("numpy")

from nlp2cmd.generation.thermodynamic import (
    ThermodynamicGenerator,
    ThermodynamicResult,
    OptimizationProblem,
    SchedulingEnergy,
    AllocationEnergy,
    HybridThermodynamicGenerator,
    create_thermodynamic_generator,
)
from nlp2cmd.thermodynamic import (
    LangevinConfig,
    LangevinSampler,
    SamplerResult,
    MajorityVoter,
    ThermodynamicRouter,
    EnergyEstimator,
)


class TestOptimizationProblem:
    """Test OptimizationProblem dataclass."""
    
    def test_create_scheduling_problem(self):
        """Test creating scheduling problem."""
        problem = OptimizationProblem(
            problem_type="schedule",
            variables=["task_0", "task_1", "task_2"],
            constraints=[
                {"type": "deadline", "task": 0, "slot": 5}
            ],
        )
        
        assert problem.problem_type == "schedule"
        assert len(problem.variables) == 3
        assert len(problem.constraints) == 1
    
    def test_to_condition(self):
        """Test conversion to condition dict."""
        problem = OptimizationProblem(
            problem_type="allocate",
            variables=["consumer_0"],
            constraints=[{"type": "capacity", "resource": 0, "value": 10}],
            objective="minimize",
        )
        
        condition = problem.to_condition()
        
        assert condition["problem_type"] == "allocate"
        assert condition["objective"] == "minimize"
        assert len(condition["constraints"]) == 1


class TestSchedulingEnergy:
    """Test scheduling energy model."""
    
    @pytest.fixture
    def energy(self) -> SchedulingEnergy:
        return SchedulingEnergy(n_tasks=3, n_slots=5, lambda_overlap=40.0)
    
    def test_no_overlap_low_energy(self, energy):
        """Test that non-overlapping schedule has low energy."""
        # z that decodes to tasks in different slots
        z = np.zeros(15)  # 3 tasks * 5 slots
        z[0] = 10   # task 0 -> slot 0
        z[6] = 10   # task 1 -> slot 1
        z[12] = 10  # task 2 -> slot 2
        
        e = energy.energy(z, {"constraints": []})
        
        # Should be low (no overlap)
        assert e < 50
    
    def test_overlap_high_energy(self, energy):
        """Test that overlapping schedule has high energy."""
        # z that decodes to all tasks in same slot
        z = np.zeros(15)
        z[0] = 10   # task 0 -> slot 0
        z[5] = 10   # task 1 -> slot 0
        z[10] = 10  # task 2 -> slot 0
        
        e = energy.energy(z, {"constraints": []})
        
        # Should be high (overlap penalty)
        assert e >= 100
    
    def test_deadline_violation_penalty(self, energy):
        """Test deadline violation increases energy."""
        z = np.zeros(15)
        z[4] = 10  # task 0 -> slot 4 (after deadline)
        
        constraints = [{"type": "deadline", "task": 0, "slot": 2}]
        
        e = energy.energy(z, {"constraints": constraints})
        
        # Should include deadline penalty
        assert e > 0
    
    def test_gradient_shape(self, energy):
        """Test gradient has correct shape."""
        z = np.random.randn(15)
        grad = energy.gradient(z, {"constraints": []})
        
        assert grad.shape == z.shape
    
    def test_decode_assignments(self, energy):
        """Test decoding z to assignments."""
        z = np.zeros(15)
        z[2] = 10   # task 0 -> slot 2
        z[8] = 10   # task 1 -> slot 3
        z[14] = 10  # task 2 -> slot 4
        
        assignments = energy._decode_assignments(z)
        
        assert len(assignments) == 3
        assert assignments[0] == 2
        assert assignments[1] == 3
        assert assignments[2] == 4


class TestAllocationEnergy:
    """Test allocation energy model."""
    
    @pytest.fixture
    def energy(self) -> AllocationEnergy:
        return AllocationEnergy(n_resources=3, n_consumers=2)
    
    def test_feasible_low_energy(self, energy):
        """Test feasible allocation has low energy."""
        z = np.zeros(6)  # 2 consumers * 3 resources
        
        constraints = [
            {"type": "capacity", "resource": 0, "value": 100}
        ]
        
        e = energy.energy(z, {"constraints": constraints})
        
        # Feasible, should be low
        assert e < 100
    
    def test_capacity_violation_high_energy(self, energy):
        """Test capacity violation increases energy."""
        z = np.ones(6) * 5  # High allocation
        
        constraints = [
            {"type": "capacity", "resource": 0, "value": 0.1}  # Very low capacity
        ]
        
        e = energy.energy(z, {"constraints": constraints})
        
        # Should include capacity penalty
        assert e > 0
    
    def test_decode_allocation(self, energy):
        """Test decoding z to allocation matrix."""
        z = np.zeros(6)
        
        allocation = energy._decode_allocation(z)
        
        assert allocation.shape == (2, 3)
        assert np.all(allocation >= 0)
        assert np.all(allocation <= 1)


class TestThermodynamicGenerator:
    """Test thermodynamic generator."""
    
    @pytest.fixture
    def generator(self) -> ThermodynamicGenerator:
        return create_thermodynamic_generator(n_samples=3, n_steps=100, adaptive_steps=False)
    
    @pytest.mark.asyncio
    async def test_generate_scheduling(self, generator):
        """Test generating scheduling solution."""
        result = await generator.generate(
            "Zaplanuj 3 zadania w 5 slotach"
        )
        
        assert isinstance(result, ThermodynamicResult)
        assert result.problem.problem_type == "schedule"
        assert result.n_samples == 3
    
    @pytest.mark.asyncio
    async def test_generate_with_problem(self, generator):
        """Test generating with pre-parsed problem."""
        problem = OptimizationProblem(
            problem_type="schedule",
            variables=["t0", "t1"],
            constraints=[],
        )
        
        result = await generator.generate("", problem=problem)
        
        assert result.problem == problem
    
    @pytest.mark.asyncio
    async def test_result_has_energy_estimate(self, generator):
        """Test result includes energy estimate."""
        result = await generator.generate("Zaplanuj zadania")
        
        assert result.energy_estimate is not None
        assert "savings_digital_percent" in result.energy_estimate
    
    def test_rule_based_parse(self, generator):
        """Test rule-based problem parsing."""
        problem = generator._rule_based_parse(
            "Zaplanuj 5 zadań, zadanie 2 przed slotem 3"
        )
        
        assert problem.problem_type == "schedule"
        assert len(problem.variables) == 5
    
    def test_format_output_scheduling(self, generator):
        """Test output formatting for scheduling."""
        problem = OptimizationProblem("schedule", ["t0", "t1"], [])
        solution = {"assignments": {"t0": 2, "t1": 5}}
        
        output = generator._format_output(solution, problem)
        
        assert "Schedule" in output
        assert "t0" in output


class TestThermodynamicResult:
    """Test ThermodynamicResult dataclass."""
    
    def test_create_result(self):
        """Test creating result."""
        problem = OptimizationProblem("schedule", [], [])
        
        result = ThermodynamicResult(
            problem=problem,
            solution={"assignments": {}},
            energy=1.5,
            entropy_production=0.3,
            n_samples=5,
            converged=True,
            latency_ms=150.0,
        )
        
        assert result.energy == 1.5
        assert result.n_samples == 5
        assert result.converged
    
    def test_result_with_errors(self):
        """Test result with errors."""
        problem = OptimizationProblem("unknown", [], [])
        
        result = ThermodynamicResult(
            problem=problem,
            solution={},
            energy=float("inf"),
            entropy_production=0.0,
            n_samples=0,
            converged=False,
            latency_ms=10.0,
            errors=["Parse error"],
        )
        
        assert not result.converged
        assert len(result.errors) == 1


class TestLangevinSamplerIntegration:
    """Test Langevin sampler with generation energy models."""
    
    def test_sampling_scheduling(self):
        """Test sampling with scheduling energy."""
        energy = SchedulingEnergy(n_tasks=2, n_slots=4)
        config = LangevinConfig(n_steps=100, dim=8, kT=1.0)
        sampler = LangevinSampler(energy, config)
        
        result = sampler.sample({"constraints": []})
        
        assert isinstance(result, SamplerResult)
        assert result.sample.shape == (8,)
    
    def test_multiple_samples_voting(self):
        """Test sampling multiple and voting."""
        energy = SchedulingEnergy(n_tasks=2, n_slots=4)
        config = LangevinConfig(n_steps=50, dim=8)
        sampler = LangevinSampler(energy, config)
        
        results = sampler.sample({"constraints": []}, n_samples=5)
        
        voter = MajorityVoter(strategy="energy")
        best = voter.vote(results)
        
        # Best should have lowest energy
        assert best.energy == min(r.energy for r in results)


class TestThermodynamicRouter:
    """Test routing between DSL and thermodynamic."""
    
    @pytest.fixture
    def router(self) -> ThermodynamicRouter:
        return ThermodynamicRouter()
    
    def test_route_scheduling_to_langevin(self, router):
        """Test scheduling routes to Langevin."""
        result = router.route("schedule", complexity=0.7)
        assert result == "langevin"
    
    def test_route_query_to_classic(self, router):
        """Test query routes to classic."""
        result = router.route("query", complexity=0.3)
        assert result == "classic"
    
    def test_complexity_estimation(self, router):
        """Test complexity estimation."""
        complexity = router.estimate_complexity(
            "Zoptymalizuj przydzielanie zasobów",
            {"constraints": [1, 2, 3]}
        )
        
        assert complexity > 0.3  # Should be at least moderately complex


class TestEnergyEstimator:
    """Test energy estimation."""
    
    def test_estimate_savings(self):
        """Test energy savings estimation."""
        estimator = EnergyEstimator()
        
        estimate = estimator.estimate(
            llm_input_tokens=100,
            llm_output_tokens_classic=500,
            llm_output_tokens_hybrid=50,
            langevin_steps=1000,
        )
        
        assert "savings_digital_percent" in estimate
        assert estimate["savings_digital_percent"] > 0


class TestCreateThermodynamicGenerator:
    """Test factory function."""
    
    def test_create_default(self):
        """Test creating with defaults."""
        gen = create_thermodynamic_generator()
        
        assert gen.n_samples == 5
        assert gen.langevin_config.n_steps == 500
    
    def test_create_custom(self):
        """Test creating with custom params."""
        gen = create_thermodynamic_generator(
            n_samples=10,
            n_steps=200,
        )
        
        assert gen.n_samples == 10
        assert gen.langevin_config.n_steps == 200


class TestThermodynamicPerformance:
    """Test performance characteristics."""
    
    @pytest.fixture
    def generator(self) -> ThermodynamicGenerator:
        return create_thermodynamic_generator(n_samples=3, n_steps=50)
    
    @pytest.mark.asyncio
    async def test_latency_reasonable(self, generator):
        """Test latency is reasonable (<1s for small problems)."""
        result = await generator.generate("Zaplanuj 3 zadania")
        
        assert result.latency_ms < 1000
    
    @pytest.mark.asyncio
    async def test_convergence(self, generator):
        """Test that sampler converges."""
        result = await generator.generate("Zaplanuj 2 zadania w 5 slotach")
        
        # Should converge for simple problems
        assert result.converged or result.energy < float("inf")
