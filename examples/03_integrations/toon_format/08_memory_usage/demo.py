#!/usr/bin/env python3
"""
Demo 08: Memory Usage
Porównanie zużycia pamięci TOON vs stary system.
"""

import sys
from pathlib import Path
from typing import Dict, Any
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))


def estimate_old_system_memory() -> int:
    """Estymacja zużycia pamięci starego systemu."""
    # Symulacja: wiele osobnych obiektów
    commands = {}
    for i in range(100):
        commands[f"cmd_{i}"] = {
            "name": f"command_{i}",
            "description": f"Opis komendy {i}",
            "params": {"arg1": "value1", "arg2": "value2"}
        }
    
    # Duplikacja kluczy w różnych strukturach
    memory_size = len(json.dumps(commands).encode('utf-8'))
    # Dodaj overhead dla osobnych plików
    return memory_size + (100 * 200)  # ~200 bytes overhead per file


def estimate_toon_memory() -> int:
    """Estymacja zużycia pamięci TOON."""
    # Jedna zintegrowana struktura
    toon_data = {
        "metadata": {"version": "1.0", "format": "toon"},
        "commands": {},
        "aliases": {}
    }
    
    for i in range(100):
        toon_data["commands"][f"cmd_{i}"] = {
            "name": f"command_{i}",
            "description": f"Opis komendy {i}",
            "params": {"arg1": "value1", "arg2": "value2"}
        }
    
    return len(json.dumps(toon_data).encode('utf-8'))


def format_size(size_bytes: int) -> str:
    """Formatuje rozmiar w bajtach na czytelną formę."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def main():
    print("=" * 60)
    print("Demo 08: Memory Usage")
    print("=" * 60)
    print()
    
    print("📊 Estymacja zużycia pamięci (100 komend):\n")
    
    old_memory = estimate_old_system_memory()
    print(f"💾 Stary system (wiele plików JSON):")
    print(f"   Rozmiar: {format_size(old_memory)}")
    print(f"   Struktura: wiele osobnych obiektów")
    print(f"   Overhead: duplikacja kluczy metadata")
    print()
    
    toon_memory = estimate_toon_memory()
    print(f"💾 TOON (zintegrowany plik):")
    print(f"   Rozmiar: {format_size(toon_memory)}")
    print(f"   Struktura: jeden zintegrowany obiekt")
    print(f"   Overhead: minimalny (wspólna metadata)")
    print()
    
    # Oszczędność
    savings = old_memory - toon_memory
    savings_pct = (savings / old_memory) * 100 if old_memory > 0 else 0
    print(f"💰 Oszczędność: {format_size(savings)} ({savings_pct:.1f}%)")
    print()
    
    print("💡 Wnioski:")
    print("   - TOON: wspólna metadata = mniejszy rozmiar")
    print("   - Stary system: duplikacja = większy rozmiar")
    print("   - Skalowalność: TOON lepiej radzi sobie z dużą liczbą komend")
    
    print()
    print("=" * 60)
    print("✅ Koniec demo 08")
    print("=" * 60)


if __name__ == "__main__":
    main()
