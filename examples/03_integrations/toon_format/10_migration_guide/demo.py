#!/usr/bin/env python3
"""
Demo 10: Migration Guide
Przewodnik po migracji ze starego systemu do TOON.
"""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))


def show_old_structure():
    """Pokazuje strukturę starego systemu."""
    print("📁 Struktura starego systemu:")
    print("""
project/
├── command_schemas/
│   ├── commands/
│   │   ├── ls.json
│   │   ├── docker-ps.json
│   │   └── ... (wiele plików)
│   └── browser/
│       ├── navigate.json
│       └── ...
├── config.yaml
└── index.json  # Lista wszystkich komend
""")


def show_toon_structure():
    """Pokazuje strukturę TOON."""
    print("📁 Struktura TOON:")
    print("""
project/
└── commands.toon  # Jeden plik ze wszystkim
""")
    print()


def show_migration_steps():
    """Pokazuje kroki migracji."""
    print("🔄 Kroki migracji:\n")
    
    steps = [
        ("1. Krok 1: Zbierz wszystkie pliki JSON", [
            "Znajdź wszystkie pliki .json w command_schemas/",
            "Zidentyfikuj powiązane komendy i ich relacje"
        ]),
        ("2. Krok 2: Utwórz strukturę TOON", [
            "Utwórz główny obiekt z 'version' i 'commands'",
            "Przenieś komendy do 'commands' dict",
            "Dodaj aliasy jeśli istnieją"
        ]),
        ("3. Krok 3: Konwersja danych", [
            "Zmień 'command' na klucz w 'commands'",
            "Zachowaj wszystkie parametry",
            "Dodaj metadata jeśli potrzeba"
        ]),
        ("4. Krok 4: Walidacja", [
            "Sprawdź czy wszystkie komendy są obecne",
            "Testuj nowy format",
            "Porównaj wydajność"
        ])
    ]
    
    for title, items in steps:
        print(f"{title}")
        for item in items:
            print(f"   • {item}")
        print()


def show_conversion_example():
    """Pokazuje przykład konwersji."""
    print("💡 Przykład konwersji:\n")
    
    # Stary format
    old_format = {
        "command": "docker-ps",
        "description": "Lista kontenerów Docker",
        "template": "docker ps {{options}}"
    }
    
    print("Stary format (docker-ps.json):")
    print(json.dumps(old_format, indent=2))
    print()
    
    # Nowy format
    print("Nowy format (commands.toon):")
    print("""{
  "version": "1.0",
  "commands": {
    "docker-ps": {
      "description": "Lista kontenerów Docker",
      "template": "docker ps {{options}}"
    }
  }
}""")
    print()
    
    print("📝 Różnice:")
    print("   • Klucz 'command' → klucz w 'commands' dict")
    print("   • Osobny plik → część zintegrowanej struktury")
    print("   • Brak powtórzeń nazwy komendy")


def main():
    print("=" * 60)
    print("Demo 10: Migration Guide")
    print("=" * 60)
    print()
    
    show_old_structure()
    show_toon_structure()
    show_migration_steps()
    show_conversion_example()
    
    print()
    print("=" * 60)
    print("✅ Koniec demo 10")
    print("=" * 60)


if __name__ == "__main__":
    main()
