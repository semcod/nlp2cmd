from __future__ import annotations

import math
from typing import Dict, Iterable, List, Optional

from nlp2cmd.generation.thermodynamic import ThermodynamicGenerator


def print_separator(
    title: str,
    *,
    leading_newline: bool = False,
    width: int = 70,
) -> None:
    prefix = "\n" if leading_newline else ""
    print(f"{prefix}{'=' * width}")
    print(f"  {title}")
    print("=" * width)


def print_rule(
    *,
    width: int = 70,
    char: str = "-",
    indent: str = "",
    leading_newline: bool = False,
) -> None:
    prefix = "\n" if leading_newline else ""
    print(f"{prefix}{indent}{char * width}")


def rule_line(*, width: int = 70, char: str = "-") -> str:
    return char * width


def print_demo_header(title: str, *, leading_newline: bool = False) -> None:
    print_separator(title, leading_newline=leading_newline, width=70)


async def run_thermo_demo(
    title: str,
    prompt: str,
    *,
    leading_newline: bool = False,
    **generate_kwargs,
):
    print_demo_header(title, leading_newline=leading_newline)
    thermo = ThermodynamicGenerator()
    return await thermo.generate(prompt, **generate_kwargs)


def print_metrics(
    result,
    *,
    indent: str = "   ",
    energy: bool = False,
    converged: bool = False,
    solution_quality: bool = False,
    solution_feasible: bool = False,
    latency: bool = False,
    sampler_steps: bool = False,
    energy_estimate: bool = False,
    energy_estimate_label: str = "Energy savings",
) -> None:
    if energy:
        print(f"{indent}Energy: {result.energy:.4f}")
    if converged:
        print(f"{indent}Converged: {result.converged}")
    if solution_quality:
        sq = result.solution_quality
        explanation = getattr(sq, 'explanation', None) or f"score={getattr(sq, 'quality_score', 'N/A')}"
        print(f"{indent}Solution quality: {explanation}")
    if solution_feasible:
        sq = result.solution_quality
        print(f"{indent}Solution feasible: {getattr(sq, 'is_feasible', 'N/A')}")
    if latency:
        print(f"{indent}Latency: {result.latency_ms:.1f}ms")
    if sampler_steps:
        print(f"{indent}Sampler steps: {getattr(result, 'sampler_steps', 'N/A')}")
    if energy_estimate:
        estimate = getattr(result, "energy_estimate", None)
        if isinstance(estimate, dict):
            savings = estimate.get("savings_digital_percent", 0)
            print(f"{indent}{energy_estimate_label}: {savings:.1f}%")
        elif isinstance(estimate, (int, float)):
            print(f"{indent}{energy_estimate_label}: {estimate:.4f}")
        else:
            print(f"{indent}{energy_estimate_label}: N/A")


def print_simple_result(query: str, result: dict, elapsed_ms: float) -> None:
    print(f"\n📝 Query: {query}")

    if result["source"] == "dsl":
        print(f"   Command: {result['result'].command}")
    elif result["source"] == "pipeline":
        print(f"   Command: {result['result'].command}")
    else:
        print(f"   Solution: {result['result'].decoded_output}")

    print(f"   ⚡ Latency: {elapsed_ms:.1f}ms")


def print_full_result(
    query: str,
    result: dict,
    elapsed_ms: float,
    *,
    source: str = "Python API",
) -> None:
    print(f"\n📝 Zapytanie: {query}")
    print(f"🔧 Źródło: {source}")

    if result["source"] == "dsl":
        print(f"⚡ Komenda: {result['result'].command}")
        print(f"🎯 Domena: {result['result'].domain}")
        print(f"📊 Pewność: {result['result'].confidence:.2f}")
    else:
        print(f"🧪 Rozwiązanie: {result['result'].decoded_output}")
        if result["result"].solution_quality:
            print(f"✅ Wykonalne: {result['result'].solution_quality.is_feasible}")
            print(
                f"📈 Jakość: {result['result'].solution_quality.optimality_gap:.2f}"
            )

    print(f"⏱️  Latencja: {elapsed_ms:.1f}ms")


def sigmoid(value: float) -> float:
    import numpy as np
    if hasattr(value, "item"):
        v = value.item()
    else:
        v = float(value)
    return 1.0 / (1.0 + math.exp(-v))


def project_sample(problem, raw_sample: List[float]) -> Dict[str, float]:
    if not raw_sample:
        return {}

    constraint_map = {
        c.get("var"): c
        for c in problem.constraints
        if c.get("type") == "range" and c.get("var")
    }

    projected: Dict[str, float] = {}
    for idx, var in enumerate(problem.variables):
        raw_value = raw_sample[idx] if idx < len(raw_sample) else 0.0
        constraint = constraint_map.get(var)
        if constraint and "min" in constraint and "max" in constraint:
            min_val = float(constraint["min"])
            max_val = float(constraint["max"])
            projected[var] = min_val + (max_val - min_val) * sigmoid(raw_value)
        else:
            projected[var] = raw_value

    return projected


def print_projected(
    title: str,
    projected: Dict[str, float],
    *,
    precision: int = 4,
    empty_message: Optional[str] = "(no projected values)",
) -> None:
    print(title)
    if not projected:
        if empty_message:
            print(f"  {empty_message}")
        return
    for key, value in projected.items():
        print(f"  {key}: {value:.{precision}f}")


def print_fallback_note(problem_name: str) -> None:
    print(
        f"\n⚠️  Uwaga: brak dedykowanego modelu energii dla '{problem_name}'. "
        "Wyniki bazują na surowej próbce (raw_sample) rzutowanej na zakresy."
    )
