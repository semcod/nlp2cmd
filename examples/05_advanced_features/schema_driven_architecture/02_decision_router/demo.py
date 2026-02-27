#!/usr/bin/env python3
"""
Demo 02: Decision Router
Demonstracja Decision Router - decyzja czy potrzebny LLM.
"""

import sys
from pathlib import Path
from enum import Enum

sys.path.append(str(Path(__file__).resolve().parents[2]))


class RoutingDecision(Enum):
    """Decyzja routingu."""
    USE_RULE = "use_rule"
    USE_LLM = "use_llm"
    NEEDS_CLARIFICATION = "needs_clarification"


class DecisionRouter:
    """Prosty router decyzji."""
    
    def __init__(self):
        self.rule_patterns = {
            "docker": ["docker ps", "docker run", "docker build"],
            "git": ["git status", "git commit", "git push"],
            "ls": ["ls", "ls -la", "ls -lh"],
        }
    
    def route(self, query: str, intent: str, entities: dict) -> RoutingDecision:
        """Decyduje jak obsłużyć zapytanie."""
        # Sprawdź czy pasuje do znanej reguły
        for category, patterns in self.rule_patterns.items():
            if category in query.lower():
                for pattern in patterns:
                    if pattern in query.lower():
                        return RoutingDecision.USE_RULE
        
        # Sprawdź złożoność
        if len(entities) > 3:
            return RoutingDecision.USE_LLM
        
        # Domyślnie użyj LLM dla nieznanych zapytań
        return RoutingDecision.USE_LLM


def main():
    print("=" * 60)
    print("Demo 02: Decision Router")
    print("=" * 60)
    print()
    
    router = DecisionRouter()
    
    test_cases = [
        ("docker ps", "list", {"type": "containers"}),
        ("git status", "check", {"target": "repo"}),
        ("pokaż procesy zużywające najwięcej pamięci", "analyze", {
            "target": "processes", 
            "metric": "memory", 
            "sort": "desc",
            "limit": "10"
        }),
        ("ustaw webhook dla repozytorium", "configure", {
            "service": "webhook",
            "target": "repo",
            "url": "https://example.com/webhook"
        }),
    ]
    
    print("🚦 Decyzje routingu:\n")
    
    for query, intent, entities in test_cases:
        decision = router.route(query, intent, entities)
        
        icon = "📋" if decision == RoutingDecision.USE_RULE else "🧠"
        print(f"{icon} Zapytanie: {query}")
        print(f"   Intencja: {intent}")
        print(f"   Encje: {entities}")
        print(f"   Decyzja: {decision.value}")
        print()
    
    print("💡 Logika decyzji:")
    print("   📋 USE_RULE - gdy zapytanie pasuje do znanej reguły")
    print("   🧠 USE_LLM - gdy zapytanie jest złożone lub nieznane")
    print("   ❓ NEEDS_CLARIFICATION - gdy potrzeba dodatkowych informacji")
    
    print()
    print("=" * 60)
    print("✅ Koniec demo 02")
    print("=" * 60)


if __name__ == "__main__":
    main()
