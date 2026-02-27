#!/usr/bin/env python3
"""
Demo 14: Batch Processing
Przetwarzanie wsadowe komend TOON.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))


def batch_validate(commands: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Walidacja wsadowa komend."""
    results = {"valid": [], "invalid": []}
    for cmd in commands:
        if "name" in cmd and "template" in cmd:
            results["valid"].append(cmd["name"])
        else:
            results["invalid"].append(cmd.get("name", "unknown"))
    return results


def batch_export(commands: List[Dict[str, Any]], format: str = "json") -> str:
    """Eksport wsadowy komend."""
    if format == "json":
        import json
        return json.dumps(commands, indent=2)
    elif format == "csv":
        lines = ["name,description,template"]
        for cmd in commands:
            lines.append(f"{cmd.get('name','')},{cmd.get('description','')},{cmd.get('template','')}")
        return "\n".join(lines)
    return ""


def main():
    print("=" * 60)
    print("Demo 14: Batch Processing")
    print("=" * 60)
    print()
    
    print("🚀 Przetwarzanie wsadowe:\n")
    
    # Przykładowe komendy
    sample_commands = [
        {"name": "docker-ps", "template": "docker ps", "description": "Lista kontenerów"},
        {"name": "git-status", "template": "git status", "description": "Status git"},
        {"name": "invalid-cmd", "description": "Brak template"},  # Invalid
    ]
    
    print("1️⃣ Walidacja wsadowa:")
    validation = batch_validate(sample_commands)
    print(f"   ✅ Poprawne: {', '.join(validation['valid'])}")
    print(f"   ❌ Niepoprawne: {', '.join(validation['invalid'])}")
    print()
    
    print("2️⃣ Eksport wsadowy:")
    json_output = batch_export(sample_commands[:2], "json")
    print("   Format JSON:")
    print("   " + json_output.replace("\n", "\n   "))
    print()
    
    csv_output = batch_export(sample_commands[:2], "csv")
    print("   Format CSV:")
    print("   " + csv_output.replace("\n", "\n   "))
    print()
    
    print("3️⃣ Wzorzec Pipeline:")
    print("""
   commands = manager.get_all_commands()
   
   # Krok 1: Filtrowanie
   filtered = [c for c in commands if c.get('category') == 'shell']
   
   # Krok 2: Transformacja
   transformed = [{**c, 'name': c['name'].upper()} for c in filtered]
   
   # Krok 3: Eksport
   output = batch_export(transformed, "json")
""")
    
    print()
    print("=" * 60)
    print("✅ Koniec demo 14")
    print("=" * 60)


if __name__ == "__main__":
    main()
