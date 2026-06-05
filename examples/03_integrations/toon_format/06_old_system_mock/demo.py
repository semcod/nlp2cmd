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
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from old_system_loader import OldSystemLoader


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
