#!/usr/bin/env python3
"""
Demo 05: Real World Examples
Demonstracja rzeczywistych przypadków użycia.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from _demo_helpers import print_separator, print_rule


def main():
    print_separator("Rzeczywiste Przypadki Użycia", leading_newline=True, width=80)
    
    use_cases = [
        {
            "title": "DevOps Automation",
            "python": """
# Monitorowanie i optymalizacja
status = await generator.generate("Sprawdź status wszystkich usług")
optimization = await generator.generate("Zoptymalizuj konfigurację nginx")
""",
            "shell": "nlp2cmd 'Deploy aplikacji i sprawdź status'"
        },
        {
            "title": "Data Science",
            "python": """
# Analiza danych
analysis = await generator.generate("Znajdź outliery w zbiorze danych")
visualization = await generator.generate("Stwórz wykres rozkładu")
""",
            "shell": "nlp2cmd --dsl sql 'Analizuj trendy sprzedaży z ostatniego miesiąca'"
        },
        {
            "title": "System Administration",
            "python": """
# Zarządzanie systemem
cleanup = await generator.generate("Wyczyść stare logi i pliki tymczasowe")
security = await generator.generate("Sprawdź bezpieczeństwo systemu")
""",
            "shell": "nlp2cmd 'Wykonaj pełną konserwację systemu'"
        }
    ]
    
    for use_case in use_cases:
        print(f"\n🎯 {use_case['title']}:")
        print("Python API:")
        print(use_case['python'])
        print("Shell:")
        print(f"   {use_case['shell']}")
    
    print("\n✅ Koniec demo 05")
    print_rule(width=80, char="=")


if __name__ == "__main__":
    main()
