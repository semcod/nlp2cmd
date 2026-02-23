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


@dataclass
class ThermodynamicResult:
    """Result of thermodynamic optimization."""
    
    decoded_output: str
    energy_estimate: float
    converged: bool
    n_samples: int
    entropy_production: float
    solution_quality: Optional[Any] = None
    latency_ms: float = 0.0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class ThermodynamicProblemDetector:
    """Detects optimization problems in natural language."""
    
    OPTIMIZATION_KEYWORDS = [
        "schedule", "allocate", "assign", "route", "balance", "optimize",
        "harmonogram", "przydziel", "rozdziel", "trasa", "zrównoważ", "optymalizuj",
        "minimalizuj", "maksymalizuj", "znajdź optymalne", "najlepsze rozwiązanie",
        "optymalny", "optymalna", "optymalne", "minimalny", "minimalna", "minimalne",
        "maksymalny", "maksymalna", "maksymalne", "koszt", "czas", "zasoby",
        "zadania", "pracownicy", "maszyny", "zasoby", "klienci", "dostawy",
        "produkcja", "dystrybucja", "logistyka", "planowanie", "harmonogramowanie"
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
            objective=objective.get("type"),
            objective_field=objective.get("field"),
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
            "route": ["route", "trasa", "droga", "ścieżka", "dostawa", "logistyka"],
            "assign": ["assign", "przypisz", "przydziel", "zadanie", "osoba", "rola"],
            "balance": ["balance", "zrównoważ", "równoważ", "obciążenie", "wydajność"],
        }
        
        for problem_type, keywords in type_keywords.items():
            if any(kw in text for kw in keywords):
                return problem_type
        
        return None
    
    def _extract_variables(self, text: str) -> list[str]:
        """Extract variables from text."""
        # Simple heuristic - look for nouns that could be variables
        # This could be enhanced with NLP
        import re
        
        # Look for patterns like "X do Y", "X dla Y", etc.
        patterns = [
            r'(\w+)\s+(?:do|dla|na)\s+(\w+)',
            r'(\w+)\s+(?:to|for)\s+(\w+)',
            r'(\w+)\s+(?:z|with)\s+(\w+)',
        ]
        
        variables = set()
        for pattern in patterns:
            matches = re.findall(pattern, text.lower())
            for match in matches:
                variables.update(match)
        
        return list(variables)
    
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
        
        # Resource constraints
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
                    "resource_type": pattern.split("(")[1].split("|")[0],
                })
        
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
        
        # Larger problems need more samples and steps
        adapted_config = ThermodynamicConfig(
            n_samples=max(50, min(500, n_vars * 20)),
            n_steps=max(20, min(100, n_vars * 10 + n_constraints * 5)),
            temperature=self.temperature,
            step_size=self.step_size,
            convergence_threshold=self.convergence_threshold,
            max_iterations=self.max_iterations,
        )
        
        return adapted_config
