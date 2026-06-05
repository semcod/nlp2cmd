# UnitCommitmentSolver - extracted from termo2.py
"""
NLP2CMD - Przykłady zastosowań w różnych dziedzinach.

Ten moduł zawiera praktyczne przykłady użycia NLP2CMD
w IT, nauce i biznesie.
"""
import asyncio
from dataclasses import dataclass
from typing import Any, Optional
import numpy as np
from power_plant import PowerPlant

class UnitCommitmentSolver:
    """
    Solver dla problemu Unit Commitment.

    Decyduje które elektrownie uruchomić i na jakim poziomie,
    aby zaspokoić zapotrzebowanie przy minimalnym koszcie.
    """

    def __init__(self, plants: list[PowerPlant]):
        self.plants = plants

    def solve(self, demand_profile: list[float]) -> list[dict[str, float]]:
        """
        Znajdź optymalne przydziały mocy.

        Args:
            demand_profile: Lista zapotrzebowania [MW] dla każdej godziny

        Returns:
            Lista słowników {plant_id: output_mw} dla każdej godziny
        """
        schedule = []

        for hour, demand in enumerate(demand_profile):
            # Sortuj wg kosztu (merit order)
            sorted_plants = sorted(self.plants, key=lambda p: p.cost_per_mwh)

            hour_schedule = {}
            remaining_demand = demand

            for plant in sorted_plants:
                if remaining_demand <= 0:
                    hour_schedule[plant.id] = 0
                    continue

                # Must-run dla nuklearnych
                if plant.type == 'nuclear':
                    output = plant.capacity_mw
                else:
                    output = min(plant.capacity_mw, remaining_demand)
                    output = max(output, plant.min_output_mw) if output > 0 else 0

                hour_schedule[plant.id] = output
                remaining_demand -= output

            schedule.append(hour_schedule)

        return schedule

    def calculate_cost(self, schedule: list[dict[str, float]]) -> dict:
        """Oblicz koszty i emisje."""
        total_cost = 0
        total_co2 = 0

        for hour_schedule in schedule:
            for plant in self.plants:
                output = hour_schedule.get(plant.id, 0)
                total_cost += output * plant.cost_per_mwh
                total_co2 += output * plant.co2_tons_per_mwh

        return {
            'total_cost': total_cost,
            'total_co2_tons': total_co2,
            'avg_cost_per_mwh': total_cost / sum(
                sum(h.values()) for h in schedule
            ) if schedule else 0,
        }
