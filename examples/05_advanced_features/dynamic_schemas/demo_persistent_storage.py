#!/usr/bin/env python3
"""Demonstrate per-command schema storage with persistence."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from nlp2cmd.schema_extraction import DynamicSchemaRegistry


def demonstrate_persistent_storage():
    """Demonstrate the persistent storage system."""
    
    print("=" * 60)
    print("Per-Command Schema Storage Demo")
    print("=" * 60)
    
    # Initialize registry with persistent storage
    storage_dir = "./my_command_schemas"
    registry = DynamicSchemaRegistry(
        use_per_command_storage=True,
        storage_dir=storage_dir,
        use_llm=True,
        llm_config={
            "model": "ollama/qwen2.5-coder:7b",
            "api_base": "http://localhost:11434",
            "temperature": 0.1,
            "max_tokens": 512,
            "timeout": 10,
        }
    )
    
    # Register some commands
    commands_to_register = [
        "find",
        "grep", 
        "tar",
        "git",
        "docker",
        "kubectl",
        "ps",
        "df",
        "curl",
        "wget"
    ]
    
    print(f"\nRegistering {len(commands_to_register)} commands...")
    for cmd in commands_to_register:
        try:
            schema = registry.register_shell_help(cmd)
            if schema.commands:
                print(f"  ✓ {cmd}: {schema.commands[0].category}")
        except Exception as e:
            print(f"  ✗ {cmd}: {e}")
    
    # Show storage stats
    if registry.per_command_store:
        print("\nStorage Statistics:")
        stats = registry.per_command_store.get_stats()
        print(f"  Total commands: {stats['total_commands']}")
        print(f"  Categories: {list(stats['categories'].keys())}")
        print(f"  Storage location: {stats['base_dir']}")
        
        # Show category breakdown
        print("\nCommands by category:")
        for category, info in stats['categories'].items():
            print(f"  {category}: {info['count']} commands")
    
    # Test persistence by creating new registry
    print("\n" + "=" * 60)
    print("Testing Persistence (creating new registry instance)")
    print("=" * 60)
    
    # Create new registry - should load from storage
    registry2 = DynamicSchemaRegistry(
        use_per_command_storage=True,
        storage_dir=storage_dir
    )
    
    print(f"\nLoaded {len(registry2.schemas)} schemas from storage")
    
    # Test accessing a stored schema
    if "find" in registry2.schemas:
        find_schema = registry2.schemas["find"]
        print(f"\nExample - Find command:")
        print(f"  Description: {find_schema.commands[0].description}")
        print(f"  Template: {find_schema.commands[0].template}")
        print(f"  Examples: {len(find_schema.commands[0].examples)} examples")
    
    # List all stored commands
    print("\nAll stored commands:")
    commands = registry2.per_command_store.list_commands()
    for cmd in sorted(commands):
        file_path = registry2.per_command_store._get_command_path(cmd)
        print(f"  - {cmd} ({file_path.name})")
    
    # Show file structure
    print("\nFile structure:")
    storage_path = Path(storage_dir)
    if storage_path.exists():
        for file in sorted(storage_path.rglob("*")):
            if file.is_file():
                rel_path = file.relative_to(storage_dir)
                print(f"  {rel_path}")
    
    print("\n✅ Persistence test successful!")
    print(f"\nSchemas are permanently stored in: {storage_path.absolute()}")
    print("They will survive system restarts and can be backed up.")


def show_storage_benefits():
    """Show the benefits of per-command storage."""
    
    print("\n" + "=" * 60)
    print("Benefits of Per-Command Storage")
    print("=" * 60)
    
    benefits = [
        "✅ Persistent storage - survives restarts",
        "✅ Individual files - easy to manage",
        "✅ Fast loading - loads only needed schemas",
        "✅ Easy backup - each command in separate file",
        "✅ Version control friendly - text files",
        "✅ Category organization - automatic categorization",
        "✅ Metadata tracking - creation/update times",
        "✅ Incremental updates - only save changes",
        "✅ Easy sharing - copy individual command files",
        "✅ Debugging - inspect specific command schemas"
    ]
    
    for benefit in benefits:
        print(f"  {benefit}")
    
    print("\nStorage structure:")
    print("""
    command_schemas/
    ├── commands/           # Individual command schemas
    │   ├── find.json
    │   ├── grep.json
    │   ├── tar.json
    │   └── ...
    ├── categories/         # Category indexes
    │   ├── file.json
    │   ├── network.json
    │   └── ...
    └── index.json         # Master index
    """)


if __name__ == "__main__":
    demonstrate_persistent_storage()
    show_storage_benefits()
