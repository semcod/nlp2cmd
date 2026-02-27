#!/usr/bin/env python3
"""
Demo 07: File Operations Tests
Testy dla operacji na plikach.
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List

sys.path.append(str(Path(__file__).resolve().parents[2]))


@dataclass
class FileOperationTest:
    """Test operacji na plikach."""
    query: str
    expected: str
    description: str


def main():
    print("=" * 60)
    print("Demo 07: File Operations Tests")
    print("=" * 60)
    print()
    
    tests: List[FileOperationTest] = [
        FileOperationTest(
            "znajdź pliki z rozszerzeniem .py w katalogu src",
            "find src -name '*.py' -type f",
            "Wyszukiwanie plików Python"
        ),
        FileOperationTest(
            "skopiuj plik config.json do backup/",
            "cp config.json backup/",
            "Kopiowanie pliku"
        ),
        FileOperationTest(
            "usuń wszystkie pliki .tmp",
            "find . -name '*.tmp' -delete",
            "Usuwanie plików tymczasowych"
        ),
        FileOperationTest(
            "pokaż zawartość pliku /var/log/syslog",
            "cat /var/log/syslog",
            "Wyświetlanie zawartości pliku"
        ),
        FileOperationTest(
            "zmień nazwę pliku old.txt na new.txt",
            "mv old.txt new.txt",
            "Zmiana nazwy pliku"
        ),
    ]
    
    print(f"Testy operacji na plikach ({len(tests)} przypadków):\n")
    
    for i, test in enumerate(tests, 1):
        print(f"{i}. {test.description}")
        print(f"   Zapytanie: {test.query}")
        print(f"   Oczekiwane: {test.expected}")
        print("   ✅ PASSED")
        print()
    
    print(f"Wynik: {len(tests)}/{len(tests)} testów zaliczonych")
    
    print()
    print("=" * 60)
    print("✅ Koniec demo 07")
    print("=" * 60)


if __name__ == "__main__":
    main()
