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
    print(
        '# Komendy z ich aliasami\n'
        'results = manager.query("""\n'
        '    SELECT c.name, a.alias_name\n'
        '    FROM commands c\n'
        '    JOIN aliases a ON c.name = a.target\n'
        '""")'
    )
    
    print("3️⃣ Agregacje:")
    print(
        '# Liczba komend w każdej kategorii\n'
        'results = manager.query("""\n'
        '    SELECT category, COUNT(*) as count\n'
        '    FROM commands\n'
        '    GROUP BY category\n'
        '""")'
    )
    
    print("4️⃣ Sortowanie i limit:")
    print(
        '# Top 10 najczęściej używanych komend\n'
        'results = manager.query("""\n'
        '    SELECT name, usage_count\n'
        '    FROM commands\n'
        '    ORDER BY usage_count DESC\n'
        '    LIMIT 10\n'
        '""")'
    )
    
    print()
    print("=" * 60)
    print("✅ Koniec demo 13")
    print("=" * 60)


if __name__ == "__main__":
    main()
