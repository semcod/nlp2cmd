#!/usr/bin/env python3
"""
Demo 05: Infrastructure Management
Zarządzanie infrastrukturą web application.
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

sys.path.append(str(Path(__file__).resolve().parents[2]))


@dataclass
class InfraCommand:
    """Komenda zarządzania infrastrukturą."""
    action: str
    description: str
    example: str


def main():
    print("=" * 60)
    print("Demo 05: Infrastructure Management")
    print("=" * 60)
    print()
    
    print("🏗️ Zarządzanie infrastrukturą web application:")
    print()
    
    commands = [
        InfraCommand(
            "Skalowanie",
            "Skalowanie usług w górę lub w dół",
            "Skaluj deployment nginx do 5 replik"
        ),
        InfraCommand(
            "Monitorowanie",
            "Sprawdzanie statusu usług",
            "Sprawdź status wszystkich kontenerów"
        ),
        InfraCommand(
            "Aktualizacja",
            "Rolling update usług",
            "Zaktualizuj backend-api do wersji 2.0"
        ),
        InfraCommand(
            "Konfiguracja",
            "Zmiana konfiguracji w locie",
            "Zmień limit pamięci dla postgres na 2GB"
        ),
        InfraCommand(
            "Backup",
            "Tworzenie kopii zapasowych",
            "Wykonaj backup bazy danych postgres"
        ),
        InfraCommand(
            "Przywracanie",
            "Przywracanie z kopii zapasowej",
            "Przywróć postgres z backupu z wczoraj"
        ),
    ]
    
    for cmd in commands:
        print(f"🔧 {cmd.action}")
        print(f"   Opis: {cmd.description}")
        print(f"   Przykład: {cmd.example}")
        print()
    
    print("=" * 60)
    print("✅ Koniec demo 05")
    print("=" * 60)


if __name__ == "__main__":
    main()
