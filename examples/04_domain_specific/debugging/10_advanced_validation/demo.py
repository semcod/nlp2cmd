#!/usr/bin/env python3
"""
Demo 10: Advanced Validation
Zaawansowane techniki walidacji komend.
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple

sys.path.append(str(Path(__file__).resolve().parents[2]))


@dataclass
class ValidationResult:
    """Wynik walidacji."""
    query: str
    generated: str
    expected: str
    similarity: float
    passed: bool


class AdvancedValidator:
    """Zaawansowany walidator komend."""
    
    def __init__(self):
        self.results: List[ValidationResult] = []
    
    def validate(self, query: str, generated: str, expected: str) -> ValidationResult:
        # Prosta metryka podobieństwa
        similarity = self._calculate_similarity(generated, expected)
        passed = similarity > 0.7
        
        result = ValidationResult(
            query=query,
            generated=generated,
            expected=expected,
            similarity=similarity,
            passed=passed
        )
        self.results.append(result)
        return result
    
    def _calculate_similarity(self, a: str, b: str) -> float:
        # Uproszczona metryka
        a_words = set(a.lower().split())
        b_words = set(b.lower().split())
        if not a_words or not b_words:
            return 0.0
        intersection = len(a_words & b_words)
        union = len(a_words | b_words)
        return intersection / union if union > 0 else 0.0
    
    def summary(self) -> Tuple[int, int]:
        passed = sum(1 for r in self.results if r.passed)
        return passed, len(self.results)


def main():
    print("=" * 60)
    print("Demo 10: Advanced Validation")
    print("=" * 60)
    print()
    
    validator = AdvancedValidator()
    
    test_cases = [
        ("pokaż pliki", "ls -la", "ls -la"),
        ("znajdź pliki .py", "find . -name '*.py'", "find . -name '*.py'"),
        ("sprawdź pamięć", "free -h", "free -h"),
    ]
    
    print("Zaawansowana walidacja:\n")
    
    for query, generated, expected in test_cases:
        result = validator.validate(query, generated, expected)
        status = "✅ PASSED" if result.passed else "❌ FAILED"
        print(f"Zapytanie: {query}")
        print(f"Wygenerowane: {generated}")
        print(f"Oczekiwane: {expected}")
        print(f"Podobieństwo: {result.similarity:.2%}")
        print(f"Status: {status}")
        print()
    
    passed, total = validator.summary()
    print(f"Podsumowanie: {passed}/{total} ({passed/total*100:.1f}%)")
    
    print()
    print("=" * 60)
    print("✅ Koniec demo 10")
    print("=" * 60)


if __name__ == "__main__":
    main()
