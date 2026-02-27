#!/usr/bin/env python3
"""
Demo 04: Service Deployment
Wdrożenie usług z użyciem natural language.
"""

import sys
from pathlib import Path
from dataclasses import dataclass

sys.path.append(str(Path(__file__).resolve().parents[2]))


@dataclass
class DeployCommand:
    """Komenda wdrożenia."""
    natural_language: str
    expected_service: str
    expected_port: int
    expected_dependencies: list[str]


def main():
    print("=" * 60)
    print("Demo 04: Service Deployment")
    print("=" * 60)
    print()
    
    print("🚀 Przykładowe komendy deploymentu (natural language):")
    print()
    
    commands = [
        DeployCommand(
            "Uruchom serwis czatu na porcie 8080 z Redis jako backend",
            "chat-service", 8080, ["redis"]
        ),
        DeployCommand(
            "Skonfiguruj frontend na porcie 3000 z nginx",
            "frontend", 3000, []
        ),
        DeployCommand(
            "Wdróż API z PostgreSQL i Redis na portach 8080, 5432, 6379",
            "backend-api", 8080, ["postgres", "redis"]
        ),
        DeployCommand(
            "Skonfiguruj klienta email dla konta jan@example.com",
            "email-service", 587, []
        ),
    ]
    
    for cmd in commands:
        print(f"💬 {cmd.natural_language}")
        print(f"   → Usługa: {cmd.expected_service}")
        print(f"   → Port: {cmd.expected_port}")
        if cmd.expected_dependencies:
            print(f"   → Zależności: {', '.join(cmd.expected_dependencies)}")
        print()
    
    print("=" * 60)
    print("✅ Koniec demo 04")
    print("=" * 60)


if __name__ == "__main__":
    main()
