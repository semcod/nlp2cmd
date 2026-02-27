#!/usr/bin/env python3
"""
Demo 04: Advanced Patterns
Demonstracja zaawansowanych wzorców użycia.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from _demo_helpers import print_separator, print_rule


def main():
    print_separator("Zaawansowane Wzorce Użycia", leading_newline=True, width=80)
    
    print("🚀 Batch Processing (Python):")
    print("""
queries = [
    'Sprawdź status usług',
    'Znajdź duże pliki', 
    'Analizuj logi błędów',
    'Zoptymalizuj konfigurację'
]

results = await asyncio.gather(*[
    generator.generate(q) for q in queries
])
""")
    
    print("🔄 Pipeline (Shell):")
    print("   $ nlp2cmd --query 'Znajdź logi błędów' | grep 'CRITICAL' | wc -l")
    print()
    
    print("📁 Z pliku (Shell):")
    print("   $ echo 'Sprawdź CPU\\nSprawdź pamięć\\nSprawdź dysk' > queries.txt")
    print("   $ nlp2cmd --file queries.txt")
    print()
    
    print("🎯 Kontekstowe zapytania (Python):")
    print("""
context = {
    'environment': 'production',
    'available_tools': ['docker', 'kubectl'],
    'constraints': {'max_memory': '4GB'}
}

result = await generator.generate(
    'Zoptymalizuj deployment',
    context=context
)
""")
    
    print("\n✅ Koniec demo 04")
    print_rule(width=80, char="=")


if __name__ == "__main__":
    main()
