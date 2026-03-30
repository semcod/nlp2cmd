#!/usr/bin/env python3
"""
Simple demonstration: How schemas work in NLP2CMD
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from nlp2cmd.schema_extraction import DynamicSchemaRegistry
from nlp2cmd.schema_based.adapter import SchemaDrivenAppSpecAdapter
from nlp2cmd import NLP2CMD


def main():
    print("=" * 60)
    print("HOW SCHEMAS WORK IN NLP2CMD")
    print("=" * 60)
    
    # 1. Load schemas from storage
    print("\n1. Loading schemas from storage...")
    command_schemas_dir = PROJECT_ROOT / "command_schemas"
    registry = DynamicSchemaRegistry(
        use_per_command_storage=True,
        storage_dir=str(command_schemas_dir)
    )
    print(f"   Loaded {len(registry.schemas)} schemas")
    
    # 2. Show available commands
    print("\n2. Available commands with schemas:")
    commands = sorted(registry.schemas.keys())[:10]
    for cmd in commands:
        print(f"   - {cmd}")
    print(f"   ... and {len(registry.schemas) - 10} more")
    
    # 3. Show a specific schema
    print("\n3. Example: Docker schema structure")
    docker_schema = registry.get_command_by_name("docker")
    if docker_schema:
        print(f"   Command: {docker_schema.name}")
        print(f"   Category: {docker_schema.category}")
        print(f"   Template: {docker_schema.template}")
        print(f"   Parameters: {len(docker_schema.parameters)}")
        print(f"   Examples: {docker_schema.examples}")
    
    # 4. Use schemas for command generation
    print("\n4. Using schemas to generate commands:")
    
    # Initialize NLP2CMD with schema-driven adapter
    # Note: SchemaDrivenAppSpecAdapter loads schemas from validated_schemas.json
    # Let's copy our schemas there first
    import shutil
    validated_schemas_path = command_schemas_dir / 'exports' / 'validated_schemas.json'
    if (command_schemas_dir / 'index.json').exists():
        shutil.copy(command_schemas_dir / 'index.json', validated_schemas_path)
    
    adapter = SchemaDrivenAppSpecAdapter()
    nlp = NLP2CMD(adapter=adapter)
    
    # Test queries
    test_queries = [
        ("list docker containers", "docker"),
        ("show git status", "git"),
        ("find python files", "find"),
        ("check disk space", "df"),
        ("compress directory", "tar"),
    ]
    
    print("\n   Query -> Generated Command")
    print("   " + "-" * 40)
    
    for query, expected_cmd in test_queries:
        try:
            result = nlp.transform(query)
            print(f"   '{query}' -> {result.command}")
        except Exception as e:
            print(f"   '{query}' -> Error: {e}")
    
    # 5. Show where schemas are stored
    print("\n5. Schema storage location:")
    print(f"   Directory: ./command_schemas/")
    print(f"   Individual schemas: ./command_schemas/commands/*.json")
    print(f"   Index: ./command_schemas/index.json")
    
    # 6. How to update schemas
    print("\n6. How to update/add schemas:")
    print("   # Generate schemas for all commands")
    print("   python3 update_schemas.py --force")
    print()
    print("   # Generate schema for specific command")
    print("   registry.register_shell_help('new_command')")
    
    print("\n" + "=" * 60)
    print("KEY POINTS")
    print("=" * 60)
    print("""
1. Schema Extraction:
   - Command help text -> Parsed schema -> JSON file
   
2. Storage:
   - Each command in separate JSON file
   - Persistent across restarts
   
3. Usage:
   - Load schemas from storage
   - Use SchemaDrivenAppSpecAdapter
   - Transform user prompts to commands
   
4. Files:
   - ./command_schemas/commands/docker.json
   - ./src/nlp2cmd/schema_extraction/
   - ./src/nlp2cmd/schema_based/
    """)


if __name__ == "__main__":
    main()
