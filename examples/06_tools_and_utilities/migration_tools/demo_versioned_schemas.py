#!/usr/bin/env python3
"""Migrate existing schemas to versioned storage and demonstrate updates."""

import json
import shutil
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from nlp2cmd.storage.versioned_store import VersionedSchemaStore
from nlp2cmd.schema_extraction import ExtractedSchema, CommandSchema, CommandParameter


def migrate_existing_schemas(source_file: str = str(PROJECT_ROOT / "command_schemas" / "exports" / "validated_schemas.json")):
    """Migrate existing schemas to versioned storage."""
    
    print("=" * 60)
    print("Migrating Existing Schemas to Versioned Storage")
    print("=" * 60)
    
    # Initialize versioned store
    store = VersionedSchemaStore(str(PROJECT_ROOT / "generated" / "migrated_schemas"))
    
    # Load existing schemas
    print(f"\nLoading schemas from {source_file}...")
    with open(source_file) as f:
        data = json.load(f)
    
    schemas = data.get("schemas", {})
    print(f"Found {len(schemas)} schemas to migrate")
    
    # Migrate each schema
    migrated = 0
    for source, schema_data in schemas.items():
        try:
            # Reconstruct ExtractedSchema
            commands = []
            for cmd_data in schema_data.get("commands", []):
                # Reconstruct parameters
                parameters = []
                for p in cmd_data.get("parameters", []):
                    parameters.append(
                        CommandParameter(
                            name=p["name"],
                            type=p["type"],
                            description=p.get("description", ""),
                            required=p.get("required", False),
                            default=p.get("default"),
                            choices=p.get("choices", []),
                            pattern=p.get("pattern"),
                            location=p.get("location", "unknown"),
                        )
                    )
                
                command = CommandSchema(
                    name=cmd_data["name"],
                    description=cmd_data.get("description", ""),
                    category=cmd_data.get("category", "general"),
                    parameters=parameters,
                    examples=cmd_data.get("examples", []),
                    patterns=cmd_data.get("patterns", []),
                    source_type=cmd_data.get("source_type", "migrated"),
                    metadata=cmd_data.get("metadata", {}),
                    template=cmd_data.get("template"),
                )
                commands.append(command)
            
            if commands:
                schema = ExtractedSchema(
                    source=source,
                    source_type="migrated",
                    commands=commands,
                    metadata=schema_data.get("metadata", {}),
                )
                
                # Store as version 1.0.0
                if store.store_schema_version(schema, "1.0.0", make_active=True):
                    migrated += 1
                    print(f"  ✓ Migrated: {source}")
        
        except Exception as e:
            print(f"  ✗ Failed to migrate {source}: {e}")
    
    print(f"\nMigration complete: {migrated}/{len(schemas)} schemas migrated")
    
    # Show stats
    stats = store.get_version_stats()
    print(f"\nStorage stats:")
    print(f"  Total commands: {stats['total_commands']}")
    print(f"  Versioned commands: {stats['versioned_commands']}")
    print(f"  Total versions: {stats['total_versions']}")
    
    return store


def demonstrate_schema_updates(store: VersionedSchemaStore):
    """Demonstrate updating schemas with new versions."""
    
    print("\n" + "=" * 60)
    print("Demonstrating Schema Updates")
    print("=" * 60)
    
    # Simulate an update to the 'find' command
    # Version 1.0.0 (already migrated)
    print("\nCurrent 'find' command (v1.0.0):")
    v1 = store.load_schema_version("find", "1.0.0")
    if v1:
        cmd = v1.commands[0]
        print(f"  Description: {cmd.description}")
        print(f"  Template: {cmd.template}")
        print(f"  Examples: {cmd.examples[:2]}")
    
    # Create version 1.1.0 with improvements
    print("\nUpdating to v1.1.0 with enhanced features...")
    find_v1_1 = ExtractedSchema(
        source="find",
        source_type="updated",
        commands=[
            CommandSchema(
                name="find",
                description="Search for files with size and time constraints",
                category="file",
                parameters=[
                    CommandParameter(
                        name="size",
                        type="string",
                        description="File size filter (e.g., '+100M', '-1K')",
                        required=False,
                        example="+100M"
                    ),
                    CommandParameter(
                        name="mtime",
                        type="string", 
                        description="Modification time filter (e.g., '-7', '+30')",
                        required=False,
                        example="-7"
                    )
                ],
                examples=[
                    "find . -name '*.py'",
                    "find /home -size +100M -mtime -7",
                    "find . -mtime -30 -name '*.log'"
                ],
                patterns=["find"],
                source_type="updated",
                metadata={"version": "1.1.0", "features": ["size_filter", "time_filter"]},
                template="find {path} -name '{pattern}' -size {size} -mtime {mtime}"
            )
        ],
        metadata={"updated_at": datetime.now().isoformat()}
    )
    
    # Store new version
    store.store_schema_version(find_v1_1, "1.1.0", make_active=True)
    
    # Show the update
    print("\nUpdated 'find' command (v1.1.0):")
    v1_1 = store.load_schema_version("find", "1.1.0")
    if v1_1:
        cmd = v1_1.commands[0]
        print(f"  Description: {cmd.description}")
        print(f"  Template: {cmd.template}")
        print(f"  New parameters: {[p.name for p in cmd.parameters]}")
    
    # Compare versions
    print("\nComparison between v1.0.0 and v1.1.0:")
    comparison = store.compare_versions("find", "1.0.0", "1.1.0")
    for change, happened in comparison["changes"].items():
        status = "✓" if happened else "✗"
        print(f"  {status} {change}: {'Changed' if happened else 'Same'}")
    
    if "parameter_changes" in comparison:
        print("\n  Parameter changes:")
        for change in comparison["parameter_changes"]:
            print(f"    - {change}")
    
    # Simulate a major version update (2.0.0)
    print("\n\nCreating major version update v2.0.0...")
    find_v2 = ExtractedSchema(
        source="find",
        source_type="major_update",
        commands=[
            CommandSchema(
                name="find",
                description="Advanced file search with regex and exec capabilities",
                category="file",
                parameters=[
                    CommandParameter(
                        name="regex",
                        type="boolean",
                        description="Use regex for pattern matching",
                        required=False,
                        default=False
                    ),
                    CommandParameter(
                        name="exec",
                        type="string",
                        description="Execute command on found files",
                        required=False,
                        example="rm -f"
                    )
                ],
                examples=[
                    "find . -regex '.*\\.py$'",
                    "find /tmp -type f -exec rm -f {} \\;",
                    "find . -name '*.log' -mtime +30 -exec gzip {} \\;"
                ],
                patterns=["find"],
                source_type="major_update",
                metadata={"version": "2.0.0", "breaking_changes": True},
                template="find {path} -{options} -{regex} -name '{pattern}' -exec {exec}"
            )
        ],
        metadata={"major_version": True, "updated_at": datetime.now().isoformat()}
    )
    
    store.store_schema_version(find_v2, "2.0.0", make_active=False)
    
    # List all versions
    print("\nAll versions of 'find':")
    versions = store.list_versions("find")
    for v in versions:
        active = "(ACTIVE)" if v == store.get_active_version("find") else ""
        metadata = store.load_schema_version("find", v).metadata
        print(f"  v{v} {active} - {metadata.get('features', ['Basic'])[0]}")
    
    return store


def demonstrate_dual_versions(store: VersionedSchemaStore):
    """Demonstrate handling two versions of the same command."""
    
    print("\n" + "=" * 60)
    print("Handling Multiple Command Versions")
    print("=" * 60)
    
    # Simulate having two versions of 'docker' command
    # Docker 1.x (older version)
    docker_v1 = ExtractedSchema(
        source="docker",
        source_type="docker_v1",
        commands=[
            CommandSchema(
                name="docker",
                description="Docker container management (v1.x)",
                category="development",
                parameters=[
                    CommandParameter(
                        name="action",
                        type="string",
                        description="Action to perform",
                        required=True,
                        choices=["run", "ps", "stop", "rm", "images"]
                    )
                ],
                examples=[
                    "docker run ubuntu",
                    "docker ps",
                    "docker stop container_id"
                ],
                patterns=["docker"],
                source_type="docker_v1",
                metadata={"docker_version": "1.x", "api_version": "v1.23"},
                template="docker {action} {options}"
            )
        ],
        metadata={}
    )
    
    # Docker 2.x (newer version with swarm mode)
    docker_v2 = ExtractedSchema(
        source="docker",
        source_type="docker_v2",
        commands=[
            CommandSchema(
                name="docker",
                description="Docker container management with swarm (v2.x)",
                category="development",
                parameters=[
                    CommandParameter(
                        name="action",
                        type="string",
                        description="Action to perform",
                        required=True,
                        choices=["run", "ps", "stop", "rm", "images", "service", "stack", "swarm"]
                    ),
                    CommandParameter(
                        name="orchestration",
                        type="boolean",
                        description="Use swarm orchestration",
                        required=False,
                        default=False
                    )
                ],
                examples=[
                    "docker run ubuntu",
                    "docker service create nginx",
                    "docker stack deploy mystack",
                    "docker swarm init"
                ],
                patterns=["docker"],
                source_type="docker_v2",
                metadata={"docker_version": "2.x", "api_version": "v1.41", "features": ["swarm"]},
                template="docker {action} {orchestration_options} {options}"
            )
        ],
        metadata={}
    )
    
    # Store both versions
    print("\nStoring Docker v1.x and v2.x...")
    store.store_schema_version(docker_v1, "1.0.0", make_active=True)
    store.store_schema_version(docker_v2, "2.0.0", make_active=False)
    
    # Show differences
    print("\nDocker v1.x:")
    v1 = store.load_schema_version("docker", "1.0.0")
    if v1:
        cmd = v1.commands[0]
        print(f"  Description: {cmd.description}")
        print(f"  Actions: {cmd.parameters[0].choices}")
    
    print("\nDocker v2.x:")
    v2 = store.load_schema_version("docker", "2.0.0")
    if v2:
        cmd = v2.commands[0]
        print(f"  Description: {cmd.description}")
        print(f"  Actions: {cmd.parameters[0].choices}")
        print(f"  Features: {cmd.metadata.get('features', [])}")
    
    # Switch between versions based on context
    print("\nVersion switching based on environment:")
    
    # Check which docker version is installed
    def get_docker_version():
        """Simulate checking docker version."""
        # In real implementation, this would run: docker --version
        return "2.0.0"  # Simulate Docker 2.x
    
    installed_version = get_docker_version()
    print(f"  Detected Docker version: {installed_version}")
    
    # Switch to appropriate version
    if installed_version.startswith("2"):
        store.set_active_version("docker", "2.0.0")
        print("  Switched to Docker v2.x schema")
    else:
        store.set_active_version("docker", "1.0.0")
        print("  Switched to Docker v1.x schema")
    
    # Load active version
    active = store.load_schema_version("docker")
    print(f"  Active schema: {active.metadata.get('docker_version')}")


def main():
    """Main demonstration."""
    
    # Step 1: Migrate existing schemas
    store = migrate_existing_schemas()
    
    # Step 2: Demonstrate updates
    store = demonstrate_schema_updates(store)
    
    # Step 3: Show dual version handling
    demonstrate_dual_versions(store)
    
    # Final stats
    print("\n" + "=" * 60)
    print("Final Statistics")
    print("=" * 60)
    
    stats = store.get_version_stats()
    print(f"Total commands with versions: {stats['versioned_commands']}")
    print(f"Total versions stored: {stats['total_versions']}")
    
    # Show storage structure
    print("\nStorage structure:")
    storage_path = PROJECT_ROOT / "generated" / "migrated_schemas"
    if storage_path.exists():
        for item in sorted(storage_path.rglob("*")):
            if item.is_file():
                rel = item.relative_to(storage_path)
                print(f"  {rel}")
    
    print(f"\n✅ All schemas are now versioned and persistent!")
    print(f"Storage location: {storage_path.absolute()}")
    
    # Clean up option
    if input("\nDelete demo files? (y/N): ").lower() == 'y':
        shutil.rmtree(storage_path)
        print("Demo files cleaned up.")


if __name__ == "__main__":
    main()
