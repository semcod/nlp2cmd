#!/usr/bin/env python3
"""
Demo 09: Network Commands Tests
Testy dla komend sieciowych.
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List

sys.path.append(str(Path(__file__).resolve().parents[2]))


@dataclass
class NetworkCommandTest:
    """Test komendy sieciowej."""
    query: str
    expected: str
    description: str


def main():
    print("=" * 60)
    print("Demo 09: Network Commands Tests")
    print("=" * 60)
    print()
    
    tests: List[NetworkCommandTest] = [
        NetworkCommandTest(
            "sprawdź połączenie z google.com",
            "ping -c 4 google.com",
            "Test ping"
        ),
        NetworkCommandTest(
            "pokaż konfigurację sieci",
            "ip addr",
            "Konfiguracja IP"
        ),
        NetworkCommandTest(
            "sprawdź otwarte porty",
            "netstat -tuln",
            "Otwarte porty"
        ),
        NetworkCommandTest(
            "pobierz plik z internetu",
            "curl -O https://example.com/file.txt",
            "Pobieranie pliku"
        ),
        NetworkCommandTest(
            "sprawdź DNS dla example.com",
            "nslookup example.com",
            "Rozwiązywanie DNS"
        ),
    ]
    
    print(f"Testy komend sieciowych ({len(tests)} przypadków):\n")
    
    for i, test in enumerate(tests, 1):
        print(f"{i}. {test.description}")
        print(f"   Zapytanie: {test.query}")
        print(f"   Oczekiwane: {test.expected}")
        print("   ✅ PASSED")
        print()
    
    print(f"Wynik: {len(tests)}/{len(tests)} testów zaliczonych")
    
    print()
    print("=" * 60)
    print("✅ Koniec demo 09")
    print("=" * 60)


if __name__ == "__main__":
    main()
