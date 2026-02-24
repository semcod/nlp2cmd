"""
Thermodynamic optimization components for NLP2CMD.

Contains core classes and utilities for thermodynamic optimization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

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


@dataclass
class OptimizationProblem:
    """Structured optimization problem definition."""

    problem_type: str  # schedule, allocate, route, assign, balance
    variables: list[str]
    constraints: list[dict[str, Any]]
    objective: Optional[str] = None  # minimize, maximize
    objective_field: Optional[str] = None
    bounds: Optional[dict[str, tuple[float, float]]] = None
    
    # Legacy parameters for backward compatibility
    n_tasks: Optional[int] = None
    n_slots: Optional[int] = None
    n_resources: Optional[int] = None
    n_cities: Optional[int] = None
    n_consumers: Optional[int] = None
    
    def __post_init__(self):
        """Extract legacy parameters from variables if not provided."""
        if self.n_tasks is None or self.n_slots is None or self.n_resources is None or self.n_consumers is None:
            # Extract numbers from variables
            import re
            
            # For scheduling problems, count task variables
            if self.problem_type == "schedule" and self.n_tasks is None:
                task_vars = [v for v in self.variables if v.startswith('t') and v[1:].isdigit()]
                if task_vars:
                    self.n_tasks = len(task_vars)
                else:
                    # Fallback to looking for "task" in variable names
                    for var in self.variables:
                        if 'task' in var.lower():
                            match = re.search(r'(\d+)', var)
                            if match:
                                self.n_tasks = int(match.group())
                                break
            
            # Extract other parameters
            for var in self.variables:
                if 'slot' in var.lower() and self.n_slots is None:
                    match = re.search(r'(\d+)', var)
                    if match:
                        self.n_slots = int(match.group())
                elif 'resource' in var.lower() and self.n_resources is None:
                    match = re.search(r'(\d+)', var)
                    if match:
                        self.n_resources = int(match.group())
                elif 'city' in var.lower() and self.n_cities is None:
                    match = re.search(r'(\d+)', var)
                    if match:
                        self.n_cities = int(match.group())
                elif 'consumer' in var.lower() and self.n_consumers is None:
                    match = re.search(r'(\d+)', var)
                    if match:
                        self.n_consumers = int(match.group())
                elif 'konsument' in var.lower() and self.n_consumers is None:
                    match = re.search(r'(\d+)', var)
                    if match:
                        self.n_consumers = int(match.group())
        
        # Also extract from constraints (for allocation patterns)
        if self.n_resources is None or self.n_consumers is None:
            for constraint in self.constraints:
                if constraint.get('type') == 'allocation':
                    if self.n_resources is None and 'n_resources' in constraint:
                        self.n_resources = constraint['n_resources']
                    if self.n_consumers is None and 'n_consumers' in constraint:
                        self.n_consumers = constraint['n_consumers']
    
    def to_condition(self) -> dict[str, Any]:
        """Convert to condition dictionary for energy models."""
        return {
            "problem_type": self.problem_type,
            "variables": self.variables,
            "constraints": self.constraints,
            "objective": self.objective,
            "objective_field": self.objective_field,
            "bounds": self.bounds,
        }


class ThermodynamicResult:
    """Result of thermodynamic optimization."""
    
    def __init__(
        self,
        decoded_output: Optional[str] = None,
        energy_estimate: Optional[float] = None,
        energy: Optional[float] = None,  # Backward compatibility
        converged: bool = False,
        n_samples: int = 0,
        entropy_production: float = 0.0,
        solution_quality: Optional[Any] = None,
        latency_ms: float = 0.0,
        errors: list[str] = None,
        warnings: list[str] = None,
        problem: Optional["OptimizationProblem"] = None,
        solution: Optional[Any] = None,
        **kwargs  # Allow additional keyword arguments for backward compatibility
    ):
        # Handle backward compatibility for decoded_output
        if decoded_output is None:
            decoded_output = kwargs.get('decoded_output', '# Solution generated')
        
        self.decoded_output = decoded_output
        
        # Handle energy_estimate - can be float or dict
        if energy is not None and energy_estimate is None:
            self.energy_estimate = energy
        elif energy_estimate is not None:
            self.energy_estimate = energy_estimate
        else:
            self.energy_estimate = float('inf')
        
        self.converged = converged
        self.n_samples = n_samples
        self.entropy_production = entropy_production
        self.solution_quality = solution_quality
        self.latency_ms = latency_ms
        self.errors = errors or []
        self.warnings = warnings or []
        self.problem = problem
        self.solution = solution
    
    @property
    def energy(self) -> float:
        """Backward compatibility property."""
        if isinstance(self.energy_estimate, dict):
            # Extract the main energy value from dict, or return inf if not found
            return self.energy_estimate.get('energy', float('inf'))
        return self.energy_estimate


class ThermodynamicProblemDetector:
    """Detects optimization problems in natural language."""
    
    OPTIMIZATION_KEYWORDS = [
        "schedule", "allocate", "assign", "route", "balance", "optimize",
        "harmonogram", "przydziel", "rozdziel", "trasa", "zrównoważ", "optymalizuj",
        "minimalizuj", "maksymalizuj", "znajdź optymalne", "najlepsze rozwiązanie",
        "optymalny", "optymalna", "optymalne", "minimalny", "minimalna", "minimalne",
        "maksymalny", "maksymalna", "maksymalne", "koszt", "czas", "zasoby",
        "zadania", "pracownicy", "maszyny", "zasoby", "klienci", "dostawy",
        "produkcja", "dystrybucja", "logistyka", "planowanie", "harmonogramowanie",
        "zaplanuj", "rozplanuj", "ugrupuj", "zorganizuj", "znajdź",
    ]
    
    def detect_problem(self, text: str) -> Optional[OptimizationProblem]:
        """Detect optimization problem in text."""
        text_lower = text.lower()
        
        # Check if this looks like an optimization problem
        if not self._is_optimization_problem(text_lower):
            return None
        
        # Try to extract problem structure
        problem_type = self._detect_problem_type(text_lower)
        if not problem_type:
            return None
        
        variables = self._extract_variables(text)
        constraints = self._extract_constraints(text)
        objective = self._extract_objective(text_lower)
        
        return OptimizationProblem(
            problem_type=problem_type,
            variables=variables,
            constraints=constraints,
            objective=objective.get("type") if objective else None,
            objective_field=objective.get("field") if objective else None,
        )
    
    def _is_optimization_problem(self, text: str) -> bool:
        """Check if text contains optimization keywords."""
        keywords = self.OPTIMIZATION_KEYWORDS
        return any(kw in text for kw in keywords)
    
    def _detect_problem_type(self, text: str) -> Optional[str]:
        """Detect the type of optimization problem."""
        type_keywords = {
            "schedule": ["schedule", "harmonogram", "czas", "plan", "termin", "kolejność"],
            "allocate": ["allocate", "przydziel", "rozdziel", "zasoby", "pracownicy", "maszyny"],
            "route": ["route", "trasa", "trasę", "droga", "ścieżka", "dostawa", "logistyka"],
            "assign": ["assign", "przypisz", "przydziel", "zadanie", "osoba", "rola"],
            "balance": ["balance", "zrównoważ", "równoważ", "obciążenie", "wydajność"],
        }
        
        for problem_type, keywords in type_keywords.items():
            if any(kw in text for kw in keywords):
                return problem_type
        
        return None
    
    def _extract_variables(self, text: str) -> list[str]:
        """Extract variables from text."""
        import re
        
        variables = []
        
        # Extract numbers and their associated items
        # Pattern: "X zadania" (X tasks), "Y slotach" (Y slots)
        task_matches = re.findall(r'(\d+)\s+(?:zadanie|zadania|zadań|task|tasks)', text.lower())
        slot_matches = re.findall(r'(\d+)\s+(?:slot|slotach|slots)', text.lower())
        resource_matches = re.findall(r'(\d+)\s+(?:zasób|zasoby|zasobów|resource|resources)', text.lower())
        city_matches = re.findall(r'(\d+)\s+(?:miasto|miasta|miast|city|cities)', text.lower())
        consumer_matches = re.findall(r'(\d+)\s+(?:konsument|konsumenci|consumer|consumers)', text.lower())
        
        # Check problem type for appropriate variable handling
        problem_type = self._detect_problem_type(text.lower())
        
        for match in task_matches:
            if problem_type == "schedule":
                # For scheduling, create individual task variables
                n_tasks = int(match)
                variables = [f"t{i}" for i in range(n_tasks)]
            else:
                # For other problems, use aggregated variable
                variables.append(f"{match} tasks")
        for match in slot_matches:
            variables.append(f"{match} slots")
        for match in resource_matches:
            variables.append(f"{match} resources")
        for match in city_matches:
            variables.append(f"{match} cities")
        for match in consumer_matches:
            variables.append(f"{match} consumers")
        
        # Special handling for routing: if we have "route through X cities", create X city variables
        if problem_type == "route" and city_matches:
            n_cities = int(city_matches[0])
            # For routing problems, we need individual city variables only
            variables = [v for v in variables if not v.endswith(" cities")]
            for i in range(n_cities):
                variables.append(f"city_{i}")
        
        # Look for patterns like "X do Y", "X dla Y", etc.
        patterns = [
            r'(\d+)\s+(?:do|dla|na)\s+(\w+)',
            r'(\d+)\s+(?:to|for)\s+(\w+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text.lower())
            for match in matches:
                variables.extend(list(match))
        
        # If no variables found, add defaults based on problem type
        if not variables:
            variables = ["3 tasks", "5 slots"]  # Default for scheduling
        
        return variables
    
    def _extract_constraints(self, text: str) -> list[dict[str, Any]]:
        """Extract constraints from text."""
        constraints = []
        
        # Look for constraint patterns
        import re
        
        # Time constraints
        time_patterns = [
            r'(\d+)\s*(?:godzin|hour|godziny|hours|minut|minute|minuty|minutes)',
            r'(\d+)\s*(?:dni|day|dni|days)',
        ]
        
        for pattern in time_patterns:
            matches = re.findall(pattern, text.lower())
            for match in matches:
                constraints.append({
                    "type": "time",
                    "value": int(match),
                    "unit": "hours" if "hour" in pattern else "days",
                })
        
        # Resource constraints (including Polish)
        resource_patterns = [
            r'(\d+)\s*(?:zasobów|resource|zasoby|resources)',
            r'(\d+)\s*(?:pracowników|worker|pracownicy|workers)',
            r'(\d+)\s*(?:maszyn|machine|maszyny|machines)',
        ]
        
        for pattern in resource_patterns:
            matches = re.findall(pattern, text.lower())
            for match in matches:
                constraints.append({
                    "type": "resource",
                    "value": int(match),
                    "resource_type": pattern.split("(")[1].split("|")[0] if "(" in pattern else "resource",
                })
        
        # Special handling for allocation: "X resources to Y consumers"
        allocation_pattern = r'(\d+)\s*(?:zasoby|resources|zasobów|resource)\s+(?:do|dla|to|for)\s+(\d+)\s*(?:konsument|consumer|konsumenci|consumers)'
        allocation_matches = re.findall(allocation_pattern, text.lower())
        for match in allocation_matches:
            n_resources, n_consumers = match
            constraints.append({
                "type": "allocation",
                "n_resources": int(n_resources),
                "n_consumers": int(n_consumers),
            })
        
        # If no constraints found, add default
        if not constraints:
            constraints.append({"type": "resource", "value": 3})
        
        return constraints
    
    def _extract_objective(self, text: str) -> Optional[dict[str, str]]:
        """Extract optimization objective."""
        objectives = {
            "minimize": ["minimalizuj", "zmniejsz", "zminimalizuj", "minimize", "reduce"],
            "maximize": ["maksymalizuj", "zwiększ", "zmaksymalizuj", "maximize", "increase"],
        }
        
        for obj_type, keywords in objectives.items():
            if any(kw in text for kw in keywords):
                # Try to find what to optimize
                obj_field = None
                
                # Look for cost, time, efficiency, etc.
                field_keywords = {
                    "cost": ["koszt", "cena", "cost", "price"],
                    "time": ["czas", "duration", "time", "termin"],
                    "efficiency": ["wydajność", "efektywność", "efficiency", "effectiveness"],
                    "profit": ["zysk", "przychód", "profit", "revenue"],
                }
                
                for field, field_kws in field_keywords.items():
                    if any(kw in text for kw in field_kws):
                        obj_field = field
                        break
                
                return {"type": obj_type, "field": obj_field}
        
        return None


class ThermodynamicConfig:
    """Configuration for thermodynamic optimization."""
    
    def __init__(
        self,
        n_samples: int = 100,
        n_steps: int = 50,
        temperature: float = 1.0,
        step_size: float = 0.1,
        convergence_threshold: float = 1e-6,
        max_iterations: int = 1000,
    ):
        self.n_samples = n_samples
        self.n_steps = n_steps
        self.temperature = temperature
        self.step_size = step_size
        self.convergence_threshold = convergence_threshold
        self.max_iterations = max_iterations
    
    def adapt_to_problem_size(self, problem: OptimizationProblem) -> "ThermodynamicConfig":
        """Adapt configuration based on problem size."""
        n_vars = len(problem.variables)
        n_constraints = len(problem.constraints)
        
        # For very small problems (n_vars <= 2), use minimal configuration
        if n_vars <= 2:
            adapted_n_steps = 20
            adapted_n_samples = 3
        elif n_vars <= 5:
            adapted_n_steps = 100
            adapted_n_samples = 10
        else:
            # Larger problems need more samples and steps
            adapted_n_samples = max(50, min(500, n_vars * 20))
            adapted_n_steps = max(300, min(1000, n_vars * 50 + n_constraints * 20))
        
        adapted_config = ThermodynamicConfig(
            n_samples=adapted_n_samples,
            n_steps=adapted_n_steps,
            temperature=self.temperature,
            step_size=self.step_size,
            convergence_threshold=self.convergence_threshold,
            max_iterations=self.max_iterations,
        )
        
        return adapted_config
