#!/usr/bin/env python3
"""
Demo 02: Command Generator
Prosty generator komend w oparciu o TOON.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))


def main():
    print("=" * 60)
    print("Demo 02: Command Generator")
    print("=" * 60)
    print()
    
    print("🎯 Prosty generator komend:")
    print("""
class SimpleCommandGenerator:
    def __init__(self, manager):
        self.manager = manager
    
    def get_command_info(self, command_name):
        # Pobierz komendę
        cmd = self.manager.get_command_by_name(command_name)
        if not cmd:
            return f"Komenda '{command_name}' nie znaleziona"
        
        # Zwróć informacje
        info = f"Komenda: {command_name}\\n"
        info += f"Opis: {cmd.get('description', 'Brak opisu')}\\n"
        info += f"Kategoria: {cmd.get('category', 'Nieznana')}\\n"
        
        examples = cmd.get('examples', [])
        if examples:
            info += f"Przykłady:\\n"
            for i, example in enumerate(examples[:3], 1):
                info += f"  {i}. {example}\\n"
        
        return info
    
    def list_by_category(self, category):
        # Lista komend z danej kategorii
        commands = self.manager.get_all_commands()
        return [c for c in commands 
                if c.get('category') == category]
""")
    
    print("💡 Przykłady użycia:")
    print("   generator = SimpleCommandGenerator(manager)")
    print("   info = generator.get_command_info('git')")
    print("   docker_cmds = generator.list_by_category('docker')")
    
    print()
    print("=" * 60)
    print("✅ Koniec demo 02")
    print("=" * 60)


if __name__ == "__main__":
    main()
