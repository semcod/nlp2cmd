"""
Drug Discovery - Optymalizacja cząsteczek i profilu ADMET.

Demonstruje użycie NLP2CMD do wielokryterialnej optymalizacji
w procesie odkrywania leków (lead optimization).
"""

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from nlp2cmd.generation.thermodynamic import (
    OptimizationProblem,
)

from _demo_helpers import (
    print_fallback_note,
    print_metrics,
    print_projected,
    project_sample,
    run_thermo_demo,
)




async def demo_lead_optimization() -> None:
    """Optymalizacja leadu z ograniczeniami fizykochemicznymi."""
    problem = OptimizationProblem(
        problem_type="drug_discovery",
        variables=[
            "molecular_weight",
            "logP",
            "tpsa",
            "hbd",
            "hba",
            "rotatable_bonds",
        ],
        constraints=[
            {"type": "range", "var": "molecular_weight", "min": 250, "max": 450},
            {"type": "range", "var": "logP", "min": 1.5, "max": 3.5},
            {"type": "range", "var": "tpsa", "min": 40, "max": 90},
            {"type": "range", "var": "hbd", "min": 0, "max": 3},
            {"type": "range", "var": "hba", "min": 2, "max": 8},
            {"type": "range", "var": "rotatable_bonds", "min": 0, "max": 6},
        ],
        objective="maximize",
        objective_field="binding_affinity",
    )

    result = await run_thermo_demo(
        "Drug Discovery - Lead Optimization",
        "Zoptymalizuj lead: wysokie powinowactwo do celu, dobry profil ADMET.",
        problem=problem,
    )

    solution = result.solution
    if isinstance(solution, dict):
        raw_sample = solution.get("raw_sample", [])
    elif isinstance(solution, list) and solution:
        raw_sample = solution[0]
    else:
        raw_sample = []
    if hasattr(raw_sample, "tolist"):
        raw_sample = raw_sample.tolist()
    projected = project_sample(problem, raw_sample)

    print(result.decoded_output)
    print_projected("\n🔬 Projected physicochemical profile:", projected, precision=3)
    print_metrics(result, energy=True, converged=True)
    print_fallback_note("drug_discovery")


async def demo_admet_balancing() -> None:
    """Wielokryterialna optymalizacja ADMET."""
    problem = OptimizationProblem(
        problem_type="drug_discovery",
        variables=[
            "solubility",
            "clearance",
            "toxicity_score",
            "bioavailability",
            "cyp_inhibition",
        ],
        constraints=[
            {"type": "range", "var": "solubility", "min": 0.2, "max": 1.0},
            {"type": "range", "var": "clearance", "min": 0.1, "max": 0.8},
            {"type": "range", "var": "toxicity_score", "min": 0.0, "max": 0.3},
            {"type": "range", "var": "bioavailability", "min": 0.4, "max": 0.9},
            {"type": "range", "var": "cyp_inhibition", "min": 0.0, "max": 0.4},
        ],
        objective="maximize",
        objective_field="admet_score",
    )

    result = await run_thermo_demo(
        "Drug Discovery - ADMET Balancing",
        "Zbalansuj ADMET: wysoka biodostępność, niska toksyczność, stabilność metaboliczna.",
        problem=problem,
        leading_newline=True,
    )

    solution = result.solution
    if isinstance(solution, dict):
        raw_sample = solution.get("raw_sample", [])
    elif isinstance(solution, list) and solution:
        raw_sample = solution[0]
    else:
        raw_sample = []
    if hasattr(raw_sample, "tolist"):
        raw_sample = raw_sample.tolist()
    projected = project_sample(problem, raw_sample)

    print(result.decoded_output)
    print_projected("\n🧪 Projected ADMET profile:", projected, precision=3)
    print_metrics(result, energy=True, latency=True)
    print_fallback_note("drug_discovery")


async def main() -> None:
    """Uruchom demonstracje Drug Discovery."""
    await demo_lead_optimization()
    await demo_admet_balancing()

    from _demo_helpers import print_separator

    print_separator("Drug Discovery demos completed!", leading_newline=True, width=70)


if __name__ == "__main__":
    asyncio.run(main())
