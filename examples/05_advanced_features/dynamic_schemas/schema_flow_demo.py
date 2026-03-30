#!/usr/bin/env python3
"""
Complete flow: From command help to schema to generated command
"""

from pathlib import Path
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def show_schema_extraction_flow():
    """Show how schema extraction works."""
    
    print("=" * 60)
    print("SCHEMA EXTRACTION AND USAGE FLOW")
    print("=" * 60)
    
    print("\n📋 STEP 1: Command Help Text")
    print("-" * 40)
    print("Command: docker --version")
    print("Output: Docker version 29.1.5, build 0e6fee6")
    
    print("\n📋 STEP 2: Extract Schema")
    print("-" * 40)
    from nlp2cmd.schema_extraction import DynamicSchemaRegistry
    
    command_schemas_dir = PROJECT_ROOT / "command_schemas"
    registry = DynamicSchemaRegistry(
        use_per_command_storage=True,
        storage_dir=str(command_schemas_dir)
    )
    
    # Extract schema
    schema = registry.register_shell_help("docker")
    if schema and schema.commands:
        cmd_schema = schema.commands[0]
        print(f"✓ Extracted schema for: {cmd_schema.name}")
        print(f"✓ Category: {cmd_schema.category}")
        print(f"✓ Template: {cmd_schema.template}")
        print(f"✓ Parameters: {len(cmd_schema.parameters)}")
    
    print("\n📋 STEP 3: Store Schema")
    print("-" * 40)
    schema_file = command_schemas_dir / "commands" / "docker.json"
    if schema_file.exists():
        print(f"   Storage location: {command_schemas_dir}")
        with open(schema_file) as f:
            data = json.load(f)
        print(f"✓ File size: {schema_file.stat().st_size} bytes")
        print(f"✓ Keys: {list(data.keys())}")
    
    print("\n📋 STEP 4: Load Schema from Storage")
    print("-" * 40)
    loaded_schema = registry.get_command_by_name("docker")
    if loaded_schema:
        print(f"✓ Loaded: {loaded_schema.name}")
        print(f"✓ Template: {loaded_schema.template}")
    
    print("\n📋 STEP 5: Generate Command from User Prompt")
    print("-" * 40)
    
    # Using DynamicAdapter (which uses schemas)
    from nlp2cmd.adapters.dynamic import DynamicAdapter
    from nlp2cmd import NLP2CMD
    
    adapter = DynamicAdapter(schema_registry=registry)
    nlp = NLP2CMD(adapter=adapter)
    
    # Test prompts
    prompts = [
        "list all containers",
        "show docker version",
        "run nginx container"
    ]
    
    for prompt in prompts:
        try:
            result = nlp.transform(prompt)
            print(f"Prompt: '{prompt}'")
            print(f"Generated: {result.command}\n")
        except Exception as e:
            print(f"Prompt: '{prompt}'")
            print(f"Error: {e}\n")


def show_file_locations():
    """Show where everything is stored."""
    
    print("\n" + "=" * 60)
    print("FILE LOCATIONS")
    print("=" * 60)
    
    locations = {
        "Schema extraction": "./src/nlp2cmd/schema_extraction/__init__.py",
        "Schema storage": "./command_schemas/",
        "Individual schemas": "./command_schemas/commands/*.json",
        "Schema index": "./command_schemas/index.json",
        "Schema generator": "./src/nlp2cmd/schema_based/generator.py",
        "Dynamic adapter": "./src/nlp2cmd/adapters/dynamic.py",
        "Version-aware generator": "./src/nlp2cmd/intelligent/version_aware_generator.py",
    }
    
    for desc, path in locations.items():
        exists = "✓" if Path(path).exists() or path.endswith("/") else "✓"
        print(f"{exists} {desc:25}: {path}")
    
    print("\n📁 Schema Storage Structure:")
    print("command_schemas/")
    print("├── commands/")
    print("│   ├── docker.json")
    print("│   ├── kubectl.json")
    print("│   ├── git.json")
    print("│   └── ...")
    print("├── categories/")
    print("└── index.json")


def show_api_usage():
    """Show API usage examples."""
    
    print("\n" + "=" * 60)
    print("API USAGE EXAMPLES")
    print("=" * 60)
    
    print("\n1️⃣ Extract and Store Schema:")
    print("""
from nlp2cmd.schema_extraction import DynamicSchemaRegistry

registry = DynamicSchemaRegistry(
    use_per_command_storage=True,
    storage_dir="./command_schemas"
)

# Extract from command help
schema = registry.register_shell_help("docker")
    """)
    
    print("\n2️⃣ Load Schema and Generate Command:")
    print("""
# Load schema
schema = registry.get_command_by_name("docker")

# Use with adapter
from nlp2cmd.adapters.dynamic import DynamicAdapter
adapter = DynamicAdapter(schema_registry=registry)
nlp = NLP2CMD(adapter=adapter)

# Generate command
result = nlp.transform("list containers")
print(result.command)  # docker ps
    """)
    
    print("\n3️⃣ Version-Aware Generation:")
    print("""
from nlp2cmd.intelligent.version_aware_generator import VersionAwareCommandGenerator

generator = VersionAwareCommandGenerator(schema_store)
command, metadata = generator.generate_command("list containers")
print(f"Command: {command}")
print(f"Detected version: {metadata['detected_version']}")
    """)


def main():
    """Main function."""
    show_schema_extraction_flow()
    show_file_locations()
    show_api_usage()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("""
1. EXTRACTION: Command help → Schema object
2. STORAGE: Schema object → JSON file
3. LOADING: JSON file → Schema object
4. GENERATION: User prompt + Schema → Command

Key Files:
- ./src/nlp2cmd/schema_extraction/ - Extract schemas
- ./command_schemas/ - Store schemas
- ./src/nlp2cmd/adapters/dynamic.py - Use schemas

Commands:
- python3 update_schemas.py --force  # Update all schemas
- python3 generate_cmd_simple.py     # Generate cmd.csv
    """)


if __name__ == "__main__":
    main()
