#!/usr/bin/env python3
"""
Demo 09: Format Comparison
Porównanie struktury formatów: JSON vs YAML vs TOON.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))


def show_json_format():
    """Pokazuje przykład formatu JSON."""
    example = {
        "command": "docker-ps",
        "description": "Lista kontenerów Docker",
        "template": "docker ps {{options}}",
        "parameters": {
            "options": {
                "type": "string",
                "default": "-a"
            }
        }
    }
    
    import json
    print("📝 Format JSON (stary system):")
    print(json.dumps(example, indent=2))
    print()
    
    print("  ✅ Zalety: szeroko wspierany, łatwy do parsowania")
    print("  ❌ Wady: sztywna składnia, brak komentarzy")
    print()


def show_yaml_format():
    """Pokazuje przykład formatu YAML."""
    example = """
command: docker-ps
description: Lista kontenerów Docker
template: docker ps {{options}}
parameters:
  options:
    type: string
    default: -a
"""
    
    print("📝 Format YAML (stary system):")
    print(example)
    print()
    
    print("  ✅ Zalety: czytelny dla ludzi, komentarze")
    print("  ❌ Wady: skomplikowana specyfikacja, błędy wcięć")
    print()


def show_toon_format():
    """Pokazuje przykład formatu TOON."""
    example = {
        "version": "1.0",
        "commands": {
            "docker-ps": {
                "description": "Lista kontenerów Docker",
                "template": "docker ps {{options}}",
                "parameters": {
                    "options": {"type": "string", "default": "-a"}
                }
            },
            "docker-run": {
                "description": "Uruchom kontener",
                "template": "docker run {{image}} {{cmd}}"
            }
        },
        "aliases": {
            "containers": "docker-ps"
        }
    }
    
    import json
    print("📝 Format TOON:")
    print(json.dumps(example, indent=2))
    print()
    
    print("  ✅ Zalety:")
    print("     - Jedna zintegrowana struktura")
    print("     - Aliasy i relacje między komendami")
    print("     - Wspólna metadata")
    print("     - Łatwe rozszerzanie")
    print()


def main():
    print("=" * 60)
    print("Demo 09: Format Comparison")
    print("=" * 60)
    print()
    
    show_json_format()
    show_yaml_format()
    show_toon_format()
    
    print("💡 Porównanie:")
    print("   JSON: Dobry dla maszyn, sztywny")
    print("   YAML: Dobry dla ludzi, podatny na błędy")
    print("   TOON: Najlepszy z obu - struktura + elastyczność")
    
    print()
    print("=" * 60)
    print("✅ Koniec demo 09")
    print("=" * 60)


if __name__ == "__main__":
    main()
