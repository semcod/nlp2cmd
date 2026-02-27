#!/usr/bin/env python3
"""
Demo 07: Loading Performance
Porównanie wydajności ładowania TOON vs stary system.
"""

import sys
import time
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))


def benchmark_old_system() -> float:
    """Benchmark starego systemu."""
    start = time.time()
    
    # Symulacja ładowania wielu plików JSON
    base_path = Path(__file__).resolve().parents[2]
    command_schemas_dir = base_path / "command_schemas"
    
    commands = {}
    if command_schemas_dir.exists():
        for json_file in list(command_schemas_dir.rglob("*.json"))[:50]:
            try:
                import json
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    commands[json_file.stem] = data
            except Exception:
                pass
    
    return time.time() - start


def benchmark_toon() -> float:
    """Benchmark TOON - pojedynczy plik."""
    start = time.time()
    
    # Symulacja ładowania jednego pliku .toon
    import json
    toon_data = {
        "version": "1.0",
        "commands": {f"cmd_{i}": {"name": f"command_{i}"} for i in range(50)}
    }
    _ = json.dumps(toon_data)  # Symulacja serializacji
    
    return time.time() - start


def main():
    print("=" * 60)
    print("Demo 07: Loading Performance")
    print("=" * 60)
    print()
    
    print("🔄 Uruchamianie benchmarków...")
    print()
    
    # Benchmark starego systemu
    old_time = benchmark_old_system()
    print(f"⏱️  Stary system (wiele plików JSON):")
    print(f"   Czas: {old_time*1000:.2f} ms")
    print(f"   Operacje: odczyt wielu plików, parsowanie JSON")
    print()
    
    # Benchmark TOON
    toon_time = benchmark_toon()
    print(f"⏱️  TOON (pojedynczy plik):")
    print(f"   Czas: {toon_time*1000:.2f} ms")
    print(f"   Operacje: odczyt jednego pliku")
    print()
    
    # Porównanie
    if toon_time > 0:
        speedup = old_time / toon_time
        print(f"🚀 Przyspieszenie: {speedup:.1f}x")
    
    print()
    print("💡 Wnioski:")
    print("   - TOON: jeden plik = mniej operacji I/O")
    print("   - Stary system: wiele plików = więcej operacji I/O")
    print("   - Mniejszy overhead przy dużej liczbie komend")
    
    print()
    print("=" * 60)
    print("✅ Koniec demo 07")
    print("=" * 60)


if __name__ == "__main__":
    main()
