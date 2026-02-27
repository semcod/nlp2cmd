#!/usr/bin/env python3
"""
Demo 01: Basic TOON Usage
Podstawowe użycie formatu TOON.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))


def main():
    print("=" * 60)
    print("Demo 01: Basic TOON Usage")
    print("=" * 60)
    print()
    
    print("📚 TOON = Type-Object-Open-Notation")
    print("   Ujednolicony format dla wszystkich typów danych nlp2cmd")
    print()
    
    print("🔧 Inicjalizacja:")
    print("""
from nlp2cmd.core.toon_integration import get_data_manager

manager = get_data_manager()

# Pobierz wszystkie komendy
commands = manager.get_all_commands()

# Pobierz komendy shell
shell_commands = manager.get_shell_commands()

# Pobierz konfigurację
config = manager.get_config()
""")
    
    print("📊 Przykładowe dane TOON:")
    
    example_data = {
        "shell": {
            "type": "shell",
            "command": "docker ps -a",
            "description": "Pokaż wszystkie kontenery Docker"
        },
        "sql": {
            "type": "sql",
            "command": "SELECT * FROM users WHERE active = 1",
            "description": "Pobierz aktywnych użytkowników"
        },
        "kubernetes": {
            "type": "kubernetes",
            "command": "kubectl get pods",
            "description": "Pokaż pody Kubernetes"
        }
    }
    
    import json
    print(json.dumps(example_data, indent=2, ensure_ascii=False))
    
    print()
    print("=" * 60)
    print("✅ Koniec demo 01")
    print("=" * 60)


if __name__ == "__main__":
    main()
