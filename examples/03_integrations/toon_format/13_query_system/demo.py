#!/usr/bin/env python3
"""
Demo 13: Query System
System zapytań SQL-like dla TOON.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))


def main():
    print("=" * 60)
    print("Demo 13: Query System")
    print("=" * 60)
    print()
    
    print("🚀 System zapytań SQL-like:\n")
    
    print("1️⃣ Podstawowe zapytania:")
    print("""
# SELECT * FROM commands WHERE category='shell'
results = manager.query("SELECT * FROM commands WHERE category='shell'")

# SELECT name, description WHERE template LIKE '%docker%'
results = manager.query(
    "SELECT name, description FROM commands "
    "WHERE template LIKE '%docker%'"
)
""")
    
    print("2️⃣ Zapytania z JOIN:")
    print("""
# Komendy z ich aliasami
results = manager.query("""
    SELECT c.name, a.alias_name
    FROM commands c
    JOIN aliases a ON c.name = a.target
""")
""")
    
    print("3️⃣ Agregacje:")
    print("""
# Liczba komend w każdej kategorii
results = manager.query("""
    SELECT category, COUNT(*) as count
    FROM commands
    GROUP BY category
""")
""")
    
    print("4️⃣ Sortowanie i limit:")
    print("""
# Top 10 najczęściej używanych komend
results = manager.query("""
    SELECT name, usage_count
    FROM commands
    ORDER BY usage_count DESC
    LIMIT 10
""")
""")
    
    print()
    print("=" * 60)
    print("✅ Koniec demo 13")
    print("=" * 60)


if __name__ == "__main__":
    main()
