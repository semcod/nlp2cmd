# VRPSolver - extracted from termo2.py
"""
NLP2CMD - Przykłady zastosowań w różnych dziedzinach.

Ten moduł zawiera praktyczne przykłady użycia NLP2CMD
w IT, nauce i biznesie.
"""
import asyncio
from dataclasses import dataclass
from typing import Any, Optional
import numpy as np
from delivery_point import DeliveryPoint

class VRPSolver:
    """
    Solver dla Vehicle Routing Problem.

    Używa termodynamicznego samplowania do znajdowania
    optymalnych tras dla floty pojazdów.
    """

    def __init__(self, points: list[DeliveryPoint], vehicle_capacity: int = 100):
        self.points = points
        self.depot = points[0]  # Pierwszy punkt to depot
        self.customers = points[1:]
        self.capacity = vehicle_capacity

    def _distance(self, p1: DeliveryPoint, p2: DeliveryPoint) -> float:
        """Odległość euklidesowa między punktami."""
        return np.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)

    def _route_distance(self, route: list[DeliveryPoint]) -> float:
        """Całkowita długość trasy."""
        if not route:
            return 0

        dist = self._distance(self.depot, route[0])
        for i in range(len(route) - 1):
            dist += self._distance(route[i], route[i + 1])
        dist += self._distance(route[-1], self.depot)

        return dist

    def _route_demand(self, route: list[DeliveryPoint]) -> int:
        """Całkowite zapotrzebowanie na trasie."""
        return sum(p.demand for p in route)

    def solve(self, n_iterations: int = 100) -> list[list[DeliveryPoint]]:
        """Znajdź optymalne trasy."""
        best_routes = self._solve_with_iterations(n_iterations)
        return self._consolidate_routes(best_routes)
    
    def _solve_with_iterations(self, n_iterations: int) -> list[list[DeliveryPoint]]:
        """Znajdź optymalne trasy z iteracjami."""
        routes = self._initialize_routes()
        best_routes = routes.copy()
        best_distance = self._calculate_total_distance(routes)

        for _ in range(n_iterations):
            new_routes = self._perturb(routes)

            if self._is_feasible(new_routes):
                new_distance = self._calculate_total_distance(new_routes)

                if self._should_accept_solution(new_distance, best_distance):
                    routes = new_routes
                    if new_distance < best_distance:
                        best_routes = new_routes
                        best_distance = new_distance

        return best_routes
    
    def _initialize_routes(self) -> list[list[DeliveryPoint]]:
        """Inicjalizuj trasy - każdy klient w osobnej trasie."""
        return [[c] for c in self.customers]
    
    def _calculate_total_distance(self, routes: list[list[DeliveryPoint]]) -> float:
        """Oblicz całkowity dystans dla wszystkich tras."""
        return sum(self._route_distance(r) for r in routes)
    
    def _should_accept_solution(self, new_distance: float, best_distance: float) -> bool:
        """Sprawdź czy zaakceptować nowe rozwiązanie (Metropolis)."""
        return new_distance < best_distance or np.random.random() < 0.1

    def _perturb(self, routes: list[list[DeliveryPoint]]) -> list[list[DeliveryPoint]]:
        """Losowa modyfikacja tras."""
        new_routes = [r.copy() for r in routes]

        if len(new_routes) > 1 and np.random.random() < 0.5:
            # Przenieś klienta między trasami
            r1_idx = np.random.randint(len(new_routes))
            r2_idx = np.random.randint(len(new_routes))

            if new_routes[r1_idx] and r1_idx != r2_idx:
                customer = new_routes[r1_idx].pop(
                    np.random.randint(len(new_routes[r1_idx]))
                )
                pos = np.random.randint(len(new_routes[r2_idx]) + 1)
                new_routes[r2_idx].insert(pos, customer)

        # Usuń puste trasy
        new_routes = [r for r in new_routes if r]

        return new_routes

    def _is_feasible(self, routes: list[list[DeliveryPoint]]) -> bool:
        """Sprawdź czy rozwiązanie jest dopuszczalne."""
        for route in routes:
            if self._route_demand(route) > self.capacity:
                return False
        return True

    def _consolidate_routes(self, routes: list[list[DeliveryPoint]]) -> list[list[DeliveryPoint]]:
        """Połącz małe trasy jeśli możliwe."""
        consolidated = []
        remaining = routes.copy()

        while remaining:
            route = remaining.pop(0)

            # Próbuj połączyć z innymi
            merged = True
            while merged:
                merged = False
                for i, other in enumerate(remaining):
                    combined_demand = self._route_demand(route) + self._route_demand(other)
                    if combined_demand <= self.capacity:
                        route = route + other
                        remaining.pop(i)
                        merged = True
                        break

            consolidated.append(route)

        return consolidated
