#!/usr/bin/env python3
"""
Demo 06: Old System Mock
Mock starego systemu JSON/YAML dla porównania.
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))


class OldSystemLoader:
    """Mock starego systemu używający osobnych plików JSON/YAML."""
    
    def __init__(self):
        self.base_path = Path(__file__).resolve().parents[2]
        self.cache: Dict[str, Any] = {}
    
    def load_command_schemas(self) -> Dict[str, Any]:
        """Ładuje command schemas z wielu plików JSON."""
        if 'commands' in self.cache:
            return self.cache['commands']
        
        commands = {}
        command_schemas_dir = self.base_path / "command_schemas"
        
        # Load shell commands
        shell_dir = command_schemas_dir / "commands"
        if shell_dir.exists():
            for json_file in shell_dir.glob("*.json"):
                try:
                    with open(json_file, 'r') as f:
                        data = json.load(f)
                        commands[data.get('command', json_file.stem)] = data
                except Exception as e:
                    print(f"Błąd ładowania {json_file}: {e}")
        
        # Load browser commands
        browser_dir = command_schemas_dir / "browser"
        if browser_dir.exists():
            for json_file in browser_dir.glob("*.json"):
                try:
                    with open(json_file, 'r') as f:
                        data = json.load(f)
                        commands[data.get('name', json_file.stem)] = data
                except Exception as e:
                    print(f"Błąd ładowania {json_file}: {e}")
        
        self.cache['commands'] = commands
        return commands
    
    def get_command_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Pobiera konkretną komendę - wymaga przeszukania wszystkich komend."""
        commands = self.load_command_schemas()
        return commands.get(name)


def main():
    print("=" * 60)
    print("Demo 06: Old System Mock")
    print("=" * 60)
    print()
    
    loader = OldSystemLoader()
    
    print("🔄 Ładowanie komend ze starego systemu...")
    commands = loader.load_command_schemas()
    print(f"✅ Załadowano {len(commands)} komend")
    print()
    
    print("📋 Przykładowe komendy:")
    for i, (name, cmd) in enumerate(list(commands.items())[:5], 1):
        print(f"  {i}. {name}: {cmd.get('description', 'brak opisu')[:50]}...")
    
    print()
    print("🔍 Wyszukiwanie komendy 'ls':")
    ls_cmd = loader.get_command_by_name('ls')
    if ls_cmd:
        print(f"  Znaleziono: {ls_cmd.get('command', 'N/A')}")
    else:
        print("  Nie znaleziono")
    
    print()
    print("=" * 60)
    print("✅ Koniec demo 06")
    print("=" * 60)


if __name__ == "__main__":
    main()
