#!/usr/bin/env python3
"""
Demo 03: LLM Planner
Demonstracja LLM Planner - generowanie wieloetapowego planu.
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List

sys.path.append(str(Path(__file__).resolve().parents[2]))


@dataclass
class PlanStep:
    """Pojedynczy krok planu."""
    step_number: int
    action: str
    params: dict
    description: str


class LLMPlanner:
    """Mock LLM Planner."""
    
    def generate_plan(self, query: str, entities: dict) -> List[PlanStep]:
        """Generuje plan wieloetapowy."""
        
        # Symulacja planowania dla złożonego zapytania
        if "backup" in query.lower() and "database" in query.lower():
            return [
                PlanStep(1, "check_disk_space", {}, "Sprawdź dostępne miejsce"),
                PlanStep(2, "lock_database", {"mode": "read_only"}, "Zablokuj bazę danych"),
                PlanStep(3, "create_backup", {"type": "full"}, "Utwórz backup"),
                PlanStep(4, "verify_backup", {}, "Zweryfikuj backup"),
                PlanStep(5, "unlock_database", {}, "Odblokuj bazę danych"),
            ]
        
        elif "deploy" in query.lower():
            return [
                PlanStep(1, "run_tests", {}, "Uruchom testy"),
                PlanStep(2, "build_image", {}, "Zbuduj obraz Docker"),
                PlanStep(3, "push_image", {}, "Push do registry"),
                PlanStep(4, "update_k8s", {}, "Zaktualizuj Kubernetes"),
            ]
        
        else:
            return [PlanStep(1, "execute_command", {"cmd": query}, "Wykonaj komendę")]


def main():
    print("=" * 60)
    print("Demo 03: LLM Planner")
    print("=" * 60)
    print()
    
    planner = LLMPlanner()
    
    test_queries = [
        ("Utwórz backup bazy danych", {"target": "database", "action": "backup"}),
        ("Deploy aplikacji na produkcję", {"target": "app", "action": "deploy", "env": "prod"}),
        ("Pokaż logi serwera", {"target": "logs", "source": "server"}),
    ]
    
    print("🧠 Generowanie planów przez LLM:\n")
    
    for query, entities in test_queries:
        plan = planner.generate_plan(query, entities)
        
        print(f"📝 Zapytanie: {query}")
        print(f"   Encje: {entities}")
        print(f"   Liczba kroków: {len(plan)}")
        print()
        
        for step in plan:
            print(f"   {step.step_number}. {step.action}")
            print(f"      {step.description}")
            if step.params:
                print(f"      Parametry: {step.params}")
        
        print()
    
    print("💡 Kiedy używać LLM Planner:")
    print("   • Złożone zadania wieloetapowe")
    print("   • Kompozycja wielu akcji")
    print("   • Warunkowe wykonanie")
    print("   • Optymalizacja sekwencji")
    
    print()
    print("=" * 60)
    print("✅ Koniec demo 03")
    print("=" * 60)


if __name__ == "__main__":
    main()
