#!/usr/bin/env python3
"""
Demonstration: From Command Schema to Generated Command

This script shows the complete flow:
1. Extract schema from command help
2. Store schema persistently
3. Load schema from storage
4. Generate command from user prompt
"""

from pathlib import Path
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from nlp2cmd.schema_extraction import DynamicSchemaRegistry
from nlp2cmd.schema_based.generator import SchemaBasedGenerator
from nlp2cmd.intelligent.command_detector import CommandDetector


def demonstrate_schema_flow():
    """Demonstrate complete schema flow."""
    
    print("=" * 60)
    print("SCHEMA TO COMMAND FLOW DEMONSTRATION")
    print("=" * 60)
    
    # Step 1: Initialize registry
    print("\n1. Initializing Schema Registry...")
    command_schemas_dir = PROJECT_ROOT / "command_schemas"
    registry = DynamicSchemaRegistry(
        use_per_command_storage=True,
        storage_dir=str(command_schemas_dir)
    )
    print(f"   Storage location: {command_schemas_dir}")
    print(f"   Loaded schemas: {len(registry.schemas)}")
    
    # Step 2: Extract schema from command
    command = "docker"
    print(f"\n2. Extracting schema from '{command}' command...")
    
    # Get help text (simulated)
    schema = registry.register_shell_help(command)
    if schema and schema.commands:
        cmd_schema = schema.commands[0]
        print(f"   ✓ Command: {cmd_schema.name}")
        print(f"   ✓ Category: {cmd_schema.category}")
        print(f"   ✓ Description: {cmd_schema.description[:100]}...")
        print(f"   ✓ Template: {cmd_schema.template}")
        print(f"   ✓ Parameters: {len(cmd_schema.parameters)}")
        print(f"   ✓ Examples: {len(cmd_schema.examples)}")
    
    # Step 3: Show stored schema file
    print(f"\n3. Schema stored in file system...")
    schema_file = command_schemas_dir / "commands" / f"{command}.json"
    if schema_file.exists():
        print(f"   File: {schema_file}")
        print(f"   Size: {schema_file.stat().st_size} bytes")
        
        # Show structure
        with open(schema_file) as f:
            data = json.load(f)
        print(f"   Keys: {list(data.keys())}")
    
    # Step 4: Load schema from storage
    print(f"\n4. Loading schema from storage...")
    loaded_schema = registry.get_command_by_name(command)
    if loaded_schema:
        print(f"   ✓ Loaded schema for {loaded_schema.name}")
        print(f"   ✓ Template: {loaded_schema.template}")
    
    # Step 5: Process user prompt
    print(f"\n5. Processing user prompt...")
    user_prompt = "show all running containers"
    print(f"   User prompt: '{user_prompt}'")
    
    # Detect command from prompt
    detector = CommandDetector()
    detected_matches = detector.detect_command(user_prompt)
    print(f"   Detected matches: {len(detected_matches)}")
    
    # Use the best match (first one with highest confidence)
    detected_command = detected_matches[0].command if detected_matches else "docker"
    print(f"   Selected command: {detected_command}")
    
    # Step 6: Generate command using schema
    print(f"\n6. Generating command using schema...")
    
    # Method 1: SchemaBasedGenerator
    generator = SchemaBasedGenerator()
    
    # Create ExtractedSchema wrapper
    from nlp2cmd.schema_extraction import ExtractedSchema
    wrapped_schema = ExtractedSchema(
        source=loaded_schema.name,
        source_type="stored",
        commands=[loaded_schema],
        metadata={}
    )
    
    generator.learn_from_schema(wrapped_schema)
    
    # Extract context from prompt
    context = {
        "action": "show",
        "state": "running",
        "resource": "containers"
    }
    
    generated_command = generator.generate_command(detected_command, context)
    print(f"   Generated command: {generated_command}")
    
    # Step 7: Show complete flow
    print(f"\n7. Complete Flow Summary:")
    print(f"   User Prompt: '{user_prompt}'")
    print(f"   ↓ Command Detection")
    print(f"   Detected: {detected_command}")
    print(f"   ↓ Schema Lookup")
    print(f"   Schema: {loaded_schema.commands[0].template}")
    print(f"   ↓ Context Extraction")
    print(f"   Context: {context}")
    print(f"   ↓ Command Generation")
    print(f"   Result: {generated_command}")
    
    return generated_command


def demonstrate_multiple_commands():
    """Demonstrate with multiple commands."""
    
    print("\n" + "=" * 60)
    print("MULTIPLE COMMAND EXAMPLES")
    print("=" * 60)
    
    # Initialize
    registry = DynamicSchemaRegistry(
        use_per_command_storage=True,
        storage_dir="./command_schemas"
    )
    
    generator = SchemaBasedGenerator()
    detector = CommandDetector()
    
    # Test cases
    test_cases = [
        ("list all running docker containers", "docker"),
        ("show git repository status", "git"),
        ("find all python files", "find"),
        ("compress logs directory", "tar"),
        ("check disk space", "df"),
    ]
    
    for prompt, expected_cmd in test_cases:
        print(f"\nPrompt: '{prompt}'")
        
        # Detect command
        detected_matches = detector.detect_command(prompt)
        detected = detected_matches[0].command if detected_matches else expected_cmd
        print(f"Detected: {detected}")
        
        # Load schema
        schema = registry.get_command_by_name(detected)
        if schema:
            # Generate command
            from nlp2cmd.schema_extraction import ExtractedSchema
            wrapped_schema = ExtractedSchema(
                source=detected,
                source_type="stored",
                commands=[schema],
                metadata={}
            )
            generator.learn_from_schema(wrapped_schema)
            command = generator.generate_command(detected, {})
            print(f"Generated: {command}")
        else:
            print("No schema found!")


def show_schema_details():
    """Show detailed schema information."""
    
    print("\n" + "=" * 60)
    print("DETAILED SCHEMA INFORMATION")
    print("=" * 60)
    
    registry = DynamicSchemaRegistry(
        use_per_command_storage=True,
        storage_dir="./command_schemas"
    )
    
    # Show Docker schema details
    cmd_schema = registry.get_command_by_name("docker")
    if cmd_schema:
        
        print("\nDocker Schema Details:")
        print("-" * 40)
        print(f"Name: {cmd_schema.name}")
        print(f"Category: {cmd_schema.category}")
        print(f"Description: {cmd_schema.description}")
        print(f"Source Type: {cmd_schema.source_type}")
        print(f"Template: {cmd_schema.template}")
        
        print("\nParameters:")
        for param in cmd_schema.parameters[:5]:
            print(f"  - {param.name}: {param.type} ({'required' if param.required else 'optional'})")
        
        print("\nExamples:")
        for example in cmd_schema.examples[:3]:
            print(f"  - {example}")
        
        print("\nPatterns:")
        for pattern in cmd_schema.patterns[:3]:
            print(f"  - {pattern}")


def main():
    """Main demonstration."""
    
    try:
        # Run demonstrations
        demonstrate_schema_flow()
        demonstrate_multiple_commands()
        show_schema_details()
        
        print("\n" + "=" * 60)
        print("KEY TAKEAWAYS")
        print("=" * 60)
        print("""
1. Schema Extraction:
   - Command help → Schema object → JSON file
   
2. Storage:
   - Each command in separate JSON file
   - Persistent across restarts
   
3. Generation:
   - User prompt → Command detection → Schema lookup → Command generation
   
4. Components:
   - DynamicSchemaRegistry: Manages schemas
   - SchemaBasedGenerator: Generates commands
   - CommandDetector: Detects command from prompt
   
5. Files:
   - ./command_schemas/commands/docker.json
   - ./src/nlp2cmd/schema_extraction/
   - ./src/nlp2cmd/schema_based/
        """)
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
