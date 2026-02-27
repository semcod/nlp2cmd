#!/usr/bin/env python3
"""
Demo 12: Advanced Integration
Zaawansowana integracja z systemem TOON.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))


def main():
    print("=" * 60)
    print("Demo 12: Advanced Integration")
    print("=" * 60)
    print()
    
    print("🚀 Zaawansowana integracja z TOON:\n")
    
    print("1️⃣ Cache'owanie i optymalizacja:")
    print("""
# Wbudowane cache'owanie wyników
manager = get_data_manager(cache_enabled=True)

# Ręczne odświeżenie cache
manager.refresh_cache()

# Czyszczenie cache
manager.clear_cache()
""")
    
    print("2️⃣ Wielowątkowy dostęp:")
    print("""
# Thread-safe singleton
with manager.get_lock():
    commands = manager.get_all_commands()

# Atomowe operacje
manager.atomic_update(commands_data)
""")
    
    print("3️⃣ Rozszerzone filtrowanie:")
    print("""
# Filtrowanie po tagach
results = manager.filter_commands(tags=["docker", "system"])

# Filtrowanie po złożoności
simple_commands = manager.filter_commands(max_complexity=3)

# Filtrowanie po wymaganych uprawnieniach
admin_commands = manager.filter_commands(requires_admin=True)
""")
    
    print("4️⃣ Dynamiczne ładowanie:")
    print("""
# Lazy loading - ładuj tylko potrzebne kategorie
manager = get_data_manager(
    categories=["shell", "browser"],  # Tylko te
    lazy=True
)

# Doładuj dodatkowe kategorie w runtime
manager.load_category("database")
""")
    
    print()
    print("=" * 60)
    print("✅ Koniec demo 12")
    print("=" * 60)


if __name__ == "__main__":
    main()
