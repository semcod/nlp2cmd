#!/usr/bin/env python3
"""
Demo 11: Basic Integration
Podstawowa integracja z systemem TOON.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))


def main():
    print("=" * 60)
    print("Demo 11: Basic Integration")
    print("=" * 60)
    print()
    
    print("🚀 Podstawowa integracja z TOON:\n")
    
    print("1️⃣ Inicjalizacja systemu:")
    print("""
from nlp2cmd.core.toon_integration import get_data_manager

# Załaduj menedżer danych
manager = get_data_manager()

# Lub z konkretnym plikiem
manager = get_data_manager("project.unified.toon")
""")
    
    print("2️⃣ Pobieranie wszystkich komend:")
    print("""
# Wszystkie komendy z wszystkich kategorii
all_commands = manager.get_all_commands()

# Komendy shell
shell_commands = manager.get_shell_commands()

# Komendy przeglądarki
browser_commands = manager.get_browser_commands()
""")
    
    print("3️⃣ Pobieranie konfiguracji:")
    print("""
# Cała konfiguracja
config = manager.get_config()

# Konkretna wartość konfiguracji
batch_size = manager.get_config('schema_generation.batch_size')
llm_model = manager.get_config('schema_generation.llm.model')
""")
    
    print("4️⃣ Wyszukiwanie komend:")
    print("""
# Wyszukaj we wszystkich kategoriach
results = manager.search_commands("git")

# Wyszukaj w konkretnej kategorii
shell_results = manager.search_commands("docker", category="shell")
""")
    
    print()
    print("=" * 60)
    print("✅ Koniec demo 11")
    print("=" * 60)


if __name__ == "__main__":
    main()
