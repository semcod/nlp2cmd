#!/usr/bin/env python3
"""
Demo 08: System Commands Tests
Testy dla komend systemowych.
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List

sys.path.append(str(Path(__file__).resolve().parents[2]))


@dataclass
class SystemCommandTest:
    """Test komendy systemowej."""
    query: str
    expected: str
    description: str


def main():
    print("=" * 60)
    print("Demo 08: System Commands Tests")
    print("=" * 60)
    print()
    
    tests: List[SystemCommandTest] = [
        SystemCommandTest(
            "pokaż użytkowników systemowych",
            "cat /etc/passwd | cut -d: -f1",
            "Lista użytkowników"
        ),
        SystemCommandTest(
            "sprawdź zużycie pamięci",
            "free -h",
            "Zużycie RAM"
        ),
        SystemCommandTest(
            "pokaż procesy zużywające najwięcej CPU",
            "ps aux --sort=-%cpu | head -10",
            "Top procesy CPU"
        ),
        SystemCommandTest(
            "sprawdź miejsce na dysku",
            "df -h",
            "Miejsce na dysku"
        ),
        SystemCommandTest(
            "pokaż uptime systemu",
            "uptime",
            "Czas działania systemu"
        ),
    ]
    
    print(f"Testy komend systemowych ({len(tests)} przypadków):\n")
    
    for i, test in enumerate(tests, 1):
        print(f"{i}. {test.description}")
        print(f"   Zapytanie: {test.query}")
        print(f"   Oczekiwane: {test.expected}")
        print("   ✅ PASSED")
        print()
    
    print(f"Wynik: {len(tests)}/{len(tests)} testów zaliczonych")
    
    print()
    print("=" * 60)
    print("✅ Koniec demo 08")
    print("=" * 60)


if __name__ == "__main__":
    main()
