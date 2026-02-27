#!/usr/bin/env python3
"""
Demo 04: Search and Filter
Wyszukiwanie i filtrowanie komend TOON.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))


def main():
    print("=" * 60)
    print("Demo 04: Search and Filter")
    print("=" * 60)
    print()
    
    print("🔍 Wyszukiwanie komend:")
    print("""
from nlp2cmd.core.toon_integration import get_data_manager

manager = get_data_manager()

# Wyszukaj komendy po nazwie
results = manager.search_commands("docker")

# Wyszukaj komendy po opisie
desc_results = manager.search_commands("container")

# Wyszukaj w konkretnej kategorii
docker_cmds = manager.get_commands_by_category("docker")

# Filtrowanie po typie
shell_cmds = manager.get_shell_commands()
sql_cmds = manager.get_sql_commands()
k8s_cmds = manager.get_kubernetes_commands()
""")
    
    print("📋 Przykładowe wyniki wyszukiwania:")
    
    search_examples = [
        {"query": "docker", "results": ["docker", "docker-compose", "docker-build"]},
        {"query": "git", "results": ["git", "git-commit", "git-push", "git-clone"]},
        {"query": "sql", "results": ["sql", "sql-select", "sql-insert"]},
    ]
    
    for example in search_examples:
        print(f"\n   🔍 Zapytanie: '{example['query']}'")
        print(f"   📊 Znaleziono: {', '.join(example['results'])}")
    
    print()
    print("=" * 60)
    print("✅ Koniec demo 04")
    print("=" * 60)


if __name__ == "__main__":
    main()
