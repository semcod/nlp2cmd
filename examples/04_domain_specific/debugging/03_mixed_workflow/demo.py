#!/usr/bin/env python3
"""
Demo 03: Mixed Workflow
Demonstracja mieszanego workflow Python + Shell.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from _demo_helpers import print_separator, print_rule


def main():
    print_separator("Mieszany Workflow - Python + Shell", leading_newline=True, width=80)
    
    print("🔄 Scenariusz: Optymalizacja systemu")
    print()
    
    print("1️⃣ Krok 1: Analiza środowiska (shell)")
    print("   $ nlp2cmd analyze-env")
    print("   📊 Wynik: System Linux, 8GB RAM, Docker dostępny")
    print()
    
    print("2️⃣ Krok 2: Generowanie rozwiązań (Python)")
    print("""
import asyncio
from nlp2cmd.generation import HybridThermodynamicGenerator

async def optimize_system():
    generator = HybridThermodynamicGenerator()
    
    # Analiza zasobów
    resource_analysis = await generator.generate(
        "Zoptymalizuj zużycie pamięci i CPU"
    )
    
    # Generowanie komend
    cleanup_commands = await generator.generate(
        "Wyczyść niepotrzebne pliki i cache"
    )
    
    return resource_analysis, cleanup_commands
""")
    
    print("3️⃣ Krok 3: Wykonanie komend (shell)")
    print("   $ nlp2cmd 'Wyczyść cache systemowy'")
    print("   $ nlp2cmd 'Uruchom garbage collection'")
    print()
    
    print("4️⃣ Krok 4: Walidacja (shell)")
    print("   $ nlp2cmd analyze-env")
    print("   ✅ Poprawa: 20% mniej zużycia pamięci")
    
    print("\n✅ Koniec demo 03")
    print_rule(width=80, char="=")


if __name__ == "__main__":
    main()
