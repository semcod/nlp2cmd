#!/usr/bin/env python3
"""
Demo 05: Advanced Patterns
Zaawansowane wzorce użycia TOON.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))


def main():
    print("=" * 60)
    print("Demo 05: Advanced Patterns")
    print("=" * 60)
    print()
    
    print("🚀 Zaawansowane wzorce:")
    print()
    
    print("1️⃣ Pipeline processing:")
    print("""
# Łączenie komend w pipeline
pipeline = [
    manager.get_command_by_name('docker-ps'),
    manager.get_command_by_name('grep'),
    manager.get_command_by_name('wc')
]
""")
    
    print("2️⃣ Conditional execution:")
    print("""
# Warunkowe wykonanie na podstawie typu
if command['type'] == 'shell':
    result = execute_shell(command)
elif command['type'] == 'sql':
    result = execute_sql(command)
elif command['type'] == 'kubernetes':
    result = execute_kubectl(command)
""")
    
    print("3️⃣ Template generation:")
    print("""
# Generowanie komend z szablonów
template = "docker run -d -p {port}:{port} {image}"
command = template.format(port=8080, image="nginx")
""")
    
    print("4️⃣ Validation:")
    print("""
# Walidacja komend przed wykonaniem
if manager.validate_command(command):
    execute(command)
else:
    raise ValueError("Invalid command")
""")
    
    print()
    print("=" * 60)
    print("✅ Koniec demo 05")
    print("=" * 60)


if __name__ == "__main__":
    main()
