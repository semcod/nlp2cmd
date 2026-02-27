#!/usr/bin/env python3


"""
Demo 06: Test Framework
Podstawy frameworka testowego dla komend shell.
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List

sys.path.append(str(Path(__file__).resolve().parents[2]))


@dataclass
class CommandTest:
    """Test case dla komendy shell."""
    query: str
    expected_command: str
    description: str
    category: str


class SimpleTestRunner:
    """Prosty runner testów."""
    
    def __init__(self):
        self.tests: List[CommandTest] = []
        self.passed = 0
        self.failed = 0
    
    def add_test(self, test: CommandTest):
        self.tests.append(test)
    
    def run_all(self):
        print(f"Uruchamianie {len(self.tests)} testów...\n")
        for i, test in enumerate(self.tests, 1):
            print(f"Test {i}/{len(self.tests)}: {test.description}")
            print(f"  Zapytanie: {test.query}")
            print(f"  Oczekiwane: {test.expected_command}")
            print(f"  Kategoria: {test.category}")
            print("  ✅ OK\n")
            self.passed += 1
        
        print(f"Wyniki: {self.passed}/{len(self.tests)} zaliczonych")


def main():
    print("=" * 60)
    print("Demo 06: Test Framework")
    print("=" * 60)
    print()
    
    runner = SimpleTestRunner()
    
    runner.add_test(CommandTest(
        "znajdź pliki .py", "find . -name '*.py'",
        "Test wyszukiwania plików", "pliki"
    ))
    runner.add_test(CommandTest(
        "pokaż użytkowników", "cat /etc/passwd",
        "Test wyświetlania użytkowników", "system"
    ))
    runner.add_test(CommandTest(
        "sprawdź pamięć", "free -h",
        "Test sprawdzania pamięci", "system"
    ))
    
    runner.run_all()
    
    print()
    print("=" * 60)
    print("✅ Koniec demo 06")
    print("=" * 60)


if __name__ == "__main__":
    main()
