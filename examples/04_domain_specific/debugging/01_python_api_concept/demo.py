#!/usr/bin/env python3
"""
Demo 01: Python API Concept
Pokazuje koncepcję użycia nlp2cmd przez Python API.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from _demo_helpers import print_separator, print_rule


def main():
    print_separator("Python API - Koncepcja użycia", leading_newline=True, width=80)
    
    print("🐍 Import i inicjalizacja:")
    print("""
from nlp2cmd.generation import HybridThermodynamicGenerator

generator = HybridThermodynamicGenerator()

# Proste zapytanie → DSL generation
result = await generator.generate("Pokaż użytkowników")
# → {'source': 'dsl', 'result': HybridResult(...)}

# Optymalizacja → Thermodynamic sampling  
result = await generator.generate("Zoptymalizuj przydzielanie zasobów")
# → {'source': 'thermodynamic', 'result': ThermodynamicResult(...)}
""")
    
    print("📝 Przykładowe zapytania:")
    
    examples = [
        ("Pokaż użytkowników", "dsl", "who, cut -d: -f1 /etc/passwd"),
        ("Znajdź pliki .log większe niż 10MB", "dsl", "find . -name '*.log' -size +10M"),
        ("Zoptymalizuj zużycie pamięci", "thermodynamic", "free -h && echo 'Optimization: clear caches'"),
        ("Sprawdź status Docker", "dsl", "systemctl status docker"),
        ("Minimalizuj koszty transportu", "thermodynamic", "Linear programming solution"),
    ]
    
    for query, expected_type, sample_output in examples:
        print(f"\n🔍 Zapytanie: {query}")
        print(f"📊 Typ: {expected_type}")
        print(f"⚡ Przykładowy wynik: {sample_output}")
    
    print("\n✅ Koniec demo 01")
    print_rule(width=80, char="=")


if __name__ == "__main__":
    main()
