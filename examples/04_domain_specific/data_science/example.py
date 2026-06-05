"""
Data Science & ML - Optymalizacja procesów ML

Demonstruje użycie NLP2CMD do optymalizacji hiperparametrów,
planowania eksperymentów i wyboru cech.
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from nlp2cmd.generation.thermodynamic import OptimizationProblem

from _demo_helpers import (
    print_fallback_note,
    print_metrics,
    print_projected,
    project_sample,
    run_thermo_demo,
    print_separator,
)


async def demo_hyperparameter_optimization():
    """Optymalizacja hiperparametrów modelu ML."""
    # Problem optymalizacji hiperparametrów
    problem = OptimizationProblem(
        problem_type="hyperparameter",
        variables=["learning_rate", "batch_size", "num_layers", "dropout"],
        constraints=[
            {"type": "range", "var": "learning_rate", "min": 0.0001, "max": 0.1},
            {"type": "range", "var": "batch_size", "min": 16, "max": 256},
            {"type": "range", "var": "num_layers", "min": 2, "max": 10},
            {"type": "range", "var": "dropout", "min": 0.0, "max": 0.5},
        ],
        objective="minimize",  # minimize validation loss
        objective_field="val_loss",
    )
    
    result = await run_thermo_demo(
        "Data Science - Hyperparameter Optimization",
        "Znajdź optymalne hiperparametry dla modelu LSTM",
        problem=problem,
    )
    
    solution = result.solution
    if isinstance(solution, dict):
        raw_sample = solution.get("raw_sample", [])
    elif isinstance(solution, list) and solution:
        raw_sample = solution[0]
    else:
        raw_sample = []
    # Ensure plain Python floats (may come from numpy sampling)
    if hasattr(raw_sample, "tolist"):
        raw_sample = raw_sample.tolist()
    projected = project_sample(problem, raw_sample)

    print_projected("\n✅ Projected hyperparameters:", projected)
    print_metrics(result, energy=True, converged=True, indent="  ")
    print_fallback_note("hyperparameter")


async def demo_feature_selection():
    """Optymalizacja wyboru cech dla modelu ML."""
    start_time = time.time()
    # Optymalizacja wyboru cech
    result = await run_thermo_demo(
        "Data Science - Feature Selection",
        """
        Wybierz 10 najważniejszych cech z 50 dostępnych
        dla modelu predykcji churnu.
        Maksymalizuj AUC-ROC przy minimalnej korelacji między cechami.
    """,
        leading_newline=True,
    )
    elapsed = (time.time() - start_time) * 1000  # Convert to milliseconds
    
    print(f"\n📊 Feature selection result:")
    print(f"   {result.decoded_output}")
    print_metrics(result, energy=True, solution_quality=True)
    print(f"   ⚡ Latency: {elapsed:.1f}ms")


async def demo_experiment_scheduling():
    """Planowanie eksperymentów ML na klastrze GPU."""
    start_time = time.time()
    # Planowanie eksperymentów ML
    result = await run_thermo_demo(
        "Data Science - Experiment Scheduling",
        """
        Zaplanuj 20 eksperymentów ML na 4 GPU:
        - GPU A100: najszybsze, 2 dostępne
        - GPU V100: średnie, 2 dostępne
        
        Eksperymenty:
        - 5x large models (wymagają A100, 4h każdy)
        - 10x medium models (dowolne GPU, 2h każdy)
        - 5x small models (dowolne GPU, 1h każdy)
        
        Minimalizuj całkowity czas i koszt.
    """,
        leading_newline=True,
    )
    elapsed = (time.time() - start_time) * 1000  # Convert to milliseconds
    
    print(f"\n🧪 Experiment schedule:")
    print(f"   {result.decoded_output}")
    print_metrics(result, sampler_steps=True)
    print(f"   ⚡ Latency: {elapsed:.1f}ms")


async def demo_model_ensemble_optimization():
    """Optymalizacja ensemble modeli."""
    start_time = time.time()
    # Optymalizacja wag ensemble
    result = await run_thermo_demo(
        "Data Science - Model Ensemble Optimization",
        """
        Zoptymalizuj wagi dla ensemble 5 modeli:
        - Random Forest: accuracy 0.85, fast inference
        - XGBoost: accuracy 0.87, medium inference  
        - Neural Network: accuracy 0.89, slow inference
        - SVM: accuracy 0.84, medium inference
        - Logistic Regression: accuracy 0.82, very fast
        
        Maksymalizuj accuracy przy ograniczeniu:
        - Całkowity czas inference < 100ms
        - Max waga dla jednego modelu: 40%
    """,
        leading_newline=True,
    )
    elapsed = (time.time() - start_time) * 1000  # Convert to milliseconds
    
    print(f"\n🤖 Ensemble weights:")
    print(f"   {result.decoded_output}")
    print_metrics(result, energy_estimate=True, energy_estimate_label="Energy savings")
    print(f"   ⚡ Latency: {elapsed:.1f}ms")


async def main():
    """Uruchom wszystkie demonstracje Data Science."""
    await demo_hyperparameter_optimization()
    await demo_feature_selection()
    await demo_experiment_scheduling()
    await demo_model_ensemble_optimization()

    print_separator("Data Science demos completed!", leading_newline=True, width=70)


if __name__ == "__main__":
    asyncio.run(main())
