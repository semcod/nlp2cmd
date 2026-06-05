"""Re-exports from split termo2.py module."""

import asyncio

import numpy as np

from delivery_point import DeliveryPoint
from genomic_pipeline_scheduler import GenomicPipelineScheduler
from genomic_sample import GenomicSample
from hyperparameter_optimizer import HyperparameterOptimizer
from hyperparameter_space import HyperparameterSpace
from operating_room import OperatingRoom
from or_scheduler import ORScheduler
from pipeline_step import PipelineStep
from power_plant import PowerPlant
from surgery import Surgery
from unit_commitment_solver import UnitCommitmentSolver
from vrp_solver import VRPSolver

__all__ = [
    "HyperparameterSpace",
    "HyperparameterOptimizer",
    "DeliveryPoint",
    "VRPSolver",
    "Surgery",
    "OperatingRoom",
    "ORScheduler",
    "PowerPlant",
    "UnitCommitmentSolver",
    "GenomicSample",
    "PipelineStep",
    "GenomicPipelineScheduler",
]


async def demo_devops_automation():
    """Demonstracja automatyzacji DevOps."""
    print("=" * 70)
    print("  DevOps Automation Demo")
    print("=" * 70)

    # Symulacja NLP2CMD (w produkcji użyj prawdziwego generatora)
    queries_and_commands = [
        ("Pokaż wszystkie pody w namespace production",
         "kubectl get pods -n production"),
        ("Skaluj deployment api-server do 5 replik",
         "kubectl scale deployment api-server --replicas=5"),
        ("Znajdź logi z błędami z ostatniej godziny",
         "kubectl logs -l app=api --since=1h | grep -i error"),
        ("Pokaż wykorzystanie zasobów przez pody",
         "kubectl top pods --sort-by=memory"),
        ("Wykonaj rolling restart deployment web",
         "kubectl rollout restart deployment/web"),
    ]

    for query, expected_cmd in queries_and_commands:
        print(f"\n📝 Query: {query}")
        print(f"   Command: {expected_cmd}")

    print("\n" + "-" * 70)
    print("✅ DevOps queries translated to kubectl commands")

async def demo_hyperparameter_optimization():
    """Demonstracja optymalizacji hiperparametrów."""
    print("\n" + "=" * 70)
    print("  Hyperparameter Optimization Demo")
    print("=" * 70)

    space = HyperparameterSpace()
    optimizer = HyperparameterOptimizer(space, n_samples=50)

    print("\n🔍 Searching hyperparameter space...")
    best_params, best_loss = optimizer.optimize()

    print(f"\n✅ Optimal hyperparameters found:")
    print(f"   Learning rate: {best_params['learning_rate']:.6f}")
    print(f"   Batch size: {best_params['batch_size']}")
    print(f"   Num layers: {best_params['num_layers']}")
    print(f"   Dropout: {best_params['dropout']:.3f}")
    print(f"   Hidden dim: {best_params['hidden_dim']}")
    print(f"\n   Final loss: {best_loss:.4f}")

async def demo_vehicle_routing():
    """Demonstracja optymalizacji tras dostaw."""
    print("\n" + "=" * 70)
    print("  Vehicle Routing Problem Demo")
    print("=" * 70)

    # Generuj punkty dostawy
    np.random.seed(42)
    points = [DeliveryPoint("Depot", 50, 50, 0)]  # Depot w centrum

    for i in range(15):
        points.append(DeliveryPoint(
            id=f"C{i + 1}",
            x=np.random.uniform(0, 100),
            y=np.random.uniform(0, 100),
            demand=np.random.randint(10, 30),
        ))

    print(f"\n📍 {len(points) - 1} delivery points generated")
    print(f"   Vehicle capacity: 100 units")

    solver = VRPSolver(points, vehicle_capacity=100)
    routes = solver.solve(n_iterations=200)

    print(f"\n✅ Optimal routes found: {len(routes)} vehicles needed")

    total_distance = 0
    for i, route in enumerate(routes):
        dist = solver._route_distance(route)
        demand = solver._route_demand(route)
        total_distance += dist

        route_str = " → ".join([p.id for p in route])
        print(f"\n   Vehicle {i + 1}: Depot → {route_str} → Depot")
        print(f"      Distance: {dist:.1f} km, Load: {demand}/{solver.capacity}")

    print(f"\n   Total distance: {total_distance:.1f} km")

async def demo_or_scheduling():
    """Demonstracja harmonogramowania sal operacyjnych."""
    print("\n" + "=" * 70)
    print("  Operating Room Scheduling Demo")
    print("=" * 70)

    # Definiuj sale
    rooms = [
        OperatingRoom("OR-1", ["general", "laparoscopy"]),
        OperatingRoom("OR-2", ["general", "cardiac"]),
        OperatingRoom("OR-3", ["general", "neuro", "microscope"]),
    ]

    # Definiuj operacje
    surgeries = [
        Surgery("Appendectomy", 60, 2, ["general"], "Dr. Smith"),
        Surgery("Cardiac bypass", 240, 1, ["cardiac"], "Dr. Johnson"),
        Surgery("Brain tumor", 300, 1, ["neuro", "microscope"], "Dr. Williams"),
        Surgery("Knee replacement", 120, 3, ["general"], "Dr. Brown"),
        Surgery("Hernia repair", 45, 4, ["general"], "Dr. Davis"),
        Surgery("Cholecystectomy", 90, 3, ["laparoscopy"], "Dr. Smith"),
        Surgery("Hip replacement", 150, 2, ["general"], "Dr. Brown"),
        Surgery("Spinal fusion", 180, 2, ["general"], "Dr. Williams"),
    ]

    print(f"\n🏥 {len(rooms)} operating rooms")
    print(f"   {len(surgeries)} surgeries to schedule")

    scheduler = ORScheduler(rooms, surgeries)
    schedule = scheduler.schedule()

    print("\n✅ Optimal schedule:")
    scheduler.print_schedule(schedule)

    # Statystyki
    total_surgeries = sum(len(s) for s in schedule.values())
    total_time = sum(
        sum(end - start for _, start, end in surgeries)
        for surgeries in schedule.values()
    )

    print(f"\n   Scheduled: {total_surgeries}/{len(surgeries)} surgeries")
    print(f"   Total OR time: {total_time // 60}h {total_time % 60}min")

async def demo_unit_commitment():
    """Demonstracja harmonogramowania elektrowni."""
    print("\n" + "=" * 70)
    print("  Unit Commitment Problem Demo")
    print("=" * 70)

    # Definiuj elektrownie
    plants = [
        PowerPlant("Nuclear-1", "nuclear", 1000, 800, 15, 0, 100000, 0.0),
        PowerPlant("Coal-1", "coal", 500, 200, 45, 50, 20000, 0.9),
        PowerPlant("Coal-2", "coal", 500, 200, 48, 50, 20000, 0.95),
        PowerPlant("Gas-1", "gas", 300, 50, 65, 150, 5000, 0.4),
        PowerPlant("Gas-2", "gas", 300, 50, 68, 150, 5000, 0.42),
        PowerPlant("Hydro-1", "hydro", 200, 0, 5, 200, 0, 0.0),
    ]

    # Profil zapotrzebowania (24h)
    demand_profile = [
        1200, 1100, 1050, 1000, 1000, 1100,  # 0-5: noc
        1300, 1500, 1800, 2000, 2100, 2200,  # 6-11: poranek
        2100, 2000, 1900, 1800, 1900, 2100,  # 12-17: popołudnie
        2400, 2500, 2300, 2000, 1700, 1400,  # 18-23: wieczór
    ]

    print(f"\n⚡ {len(plants)} power plants")
    print(f"   Total capacity: {sum(p.capacity_mw for p in plants)} MW")
    print(f"   Peak demand: {max(demand_profile)} MW")

    solver = UnitCommitmentSolver(plants)
    schedule = solver.solve(demand_profile)

    print("\n✅ Optimal dispatch schedule:")

    # Pokaż kilka godzin
    for hour in [6, 12, 19, 23]:
        print(f"\n   Hour {hour:02d}:00 (demand: {demand_profile[hour]} MW)")
        for plant in plants:
            output = schedule[hour][plant.id]
            if output > 0:
                print(f"      {plant.id}: {output:.0f} MW "
                      f"({output / plant.capacity_mw * 100:.0f}%)")

    # Podsumowanie kosztów
    costs = solver.calculate_cost(schedule)
    print(f"\n   📊 Daily summary:")
    print(f"      Total cost: ${costs['total_cost']:,.0f}")
    print(f"      Avg cost: ${costs['avg_cost_per_mwh']:.2f}/MWh")
    print(f"      CO2 emissions: {costs['total_co2_tons']:,.0f} tons")

async def demo_genomic_pipeline():
    """Demonstracja harmonogramowania pipeline'u genomicznego."""
    print("\n" + "=" * 70)
    print("  Genomic Pipeline Scheduling Demo")
    print("=" * 70)

    # Definiuj kroki pipeline'u
    steps = [
        PipelineStep("FastQC", 2.0, 4, 2, []),
        PipelineStep("Trimming", 5.0, 8, 4, ["FastQC"]),
        PipelineStep("Alignment", 15.0, 32, 8, ["Trimming"]),
        PipelineStep("Sorting", 3.0, 16, 4, ["Alignment"]),
        PipelineStep("MarkDuplicates", 4.0, 16, 2, ["Sorting"]),
        PipelineStep("VariantCalling", 20.0, 32, 8, ["MarkDuplicates"]),
        PipelineStep("Annotation", 5.0, 8, 2, ["VariantCalling"]),
    ]

    # Definiuj próbki
    samples = [
        GenomicSample("Sample_001", 50.0, 1),  # 50GB, high priority
        GenomicSample("Sample_002", 45.0, 2),
        GenomicSample("Sample_003", 55.0, 2),
        GenomicSample("Sample_004", 40.0, 3),
        GenomicSample("Sample_005", 48.0, 3),
    ]

    print(f"\n🧬 {len(samples)} samples to process")
    print(f"   Pipeline steps: {len(steps)}")
    print(f"   Total data: {sum(s.size_gb for s in samples):.0f} GB")

    scheduler = GenomicPipelineScheduler(samples, steps)
    schedule = scheduler.schedule()

    print("\n✅ Pipeline schedule:")

    for sample_sched in schedule[:2]:  # Pokaż pierwsze 2 próbki
        print(f"\n   {sample_sched['sample']}:")
        for step_info in sample_sched['steps']:
            print(f"      {step_info['step']:20s} "
                  f"{step_info['start']:6.0f} - {step_info['end']:6.0f} min "
                  f"({step_info['duration']:.0f} min)")

    # Całkowity czas
    total_time = max(
        max(s['end'] for s in sample['steps'])
        for sample in schedule
    )
    print(f"\n   Total pipeline time: {total_time / 60:.1f} hours")

async def main():
    """Uruchom wszystkie demonstracje."""
    print("=" * 70)
    print("  NLP2CMD - Use Cases Demo")
    print("  Przykłady zastosowań w IT, nauce i biznesie")
    print("=" * 70)

    await demo_devops_automation()
    await demo_hyperparameter_optimization()
    await demo_vehicle_routing()
    await demo_or_scheduling()
    await demo_unit_commitment()
    await demo_genomic_pipeline()

    print("\n" + "=" * 70)
    print("  All demos completed!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
