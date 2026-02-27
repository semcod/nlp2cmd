#!/usr/bin/env python3
"""
Demo 03: Data Manager
Użycie Data Manager do zarządzania danymi TOON.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))


def main():
    print("=" * 60)
    print("Demo 03: Data Manager")
    print("=" * 60)
    print()
    
    print("📊 Operacje Data Manager:")
    print("""
from nlp2cmd.core.toon_integration import get_data_manager

manager = get_data_manager()

# Pobierz wszystkie komendy
all_commands = manager.get_all_commands()

# Pobierz tylko komendy shell
shell_commands = manager.get_shell_commands()

# Pobierz tylko komendy SQL
sql_commands = manager.get_sql_commands()

# Pobierz komendę po nazwie
git_cmd = manager.get_command_by_name('git')

# Pobierz konfigurację
config = manager.get_config()

# Pobierz ustawienia LLM
llm_config = manager.get_llm_config()
""")
    
    print("🔍 Przykładowe struktury danych:")
    
    examples = {
        "command_structure": {
            "name": "docker",
            "type": "shell",
            "description": "Zarządzanie kontenerami Docker",
            "category": "containerization",
            "examples": [
                "docker ps -a",
                "docker images",
                "docker run -d nginx"
            ]
        },
        "llm_config_structure": {
            "model": "llama3.1",
            "temperature": 0.7,
            "max_tokens": 2048,
            "provider": "ollama"
        }
    }
    
    import json
    print(json.dumps(examples, indent=2, ensure_ascii=False))
    
    print()
    print("=" * 60)
    print("✅ Koniec demo 03")
    print("=" * 60)


if __name__ == "__main__":
    main()
