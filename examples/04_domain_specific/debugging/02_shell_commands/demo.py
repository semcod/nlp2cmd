#!/usr/bin/env python3
"""
Demo 02: Shell Commands
Demonstracja komend shell nlp2cmd.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from _demo_helpers import print_separator, print_rule


def main():
    print_separator("Shell Commands - Bezpośrednie użycie", leading_newline=True, width=80)
    
    print("💻 Instalacja:")
    print("pip install nlp2cmd")
    print()
    
    print("🚀 Podstawowe użycie:")
    shell_examples = [
        ("Proste zapytanie", "nlp2cmd --query 'Pokaż użytkowników'"),
        ("Określony DSL", "nlp2cmd --dsl shell --query 'Znajdź pliki .tmp'"),
        ("SQL", "nlp2cmd --dsl sql --query 'SELECT * FROM users WHERE city = \"Warsaw\"'"),
        ("Docker", "nlp2cmd --dsl docker --query 'Pokaż wszystkie kontenery'"),
        ("Kubernetes", "nlp2cmd --dsl kubernetes --query 'Skaluj deployment nginx'"),
        ("Z wyjaśnieniem", "nlp2cmd --explain --query 'Sprawdź status systemu'"),
        ("Auto-repair", "nlp2cmd --auto-repair --query 'Napraw konfigurację'"),
        ("Interaktywny", "nlp2cmd --interactive"),
    ]
    
    for description, command in shell_examples:
        print(f"\n📋 {description}:")
        print(f"   {command}")
    
    print("\n🔍 Analiza środowiska:")
    print("   nlp2cmd analyze-env")
    print("   nlp2cmd analyze-env --output environment.json")
    
    print("\n✅ Walidacja i naprawa:")
    print("   nlp2cmd validate config.json")
    print("   nlp2cmd repair docker-compose.yml --backup")
    
    print("\n✅ Koniec demo 02")
    print_rule(width=80, char="=")


if __name__ == "__main__":
    main()
