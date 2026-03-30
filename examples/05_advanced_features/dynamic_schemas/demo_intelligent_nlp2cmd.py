#!/usr/bin/env python3
"""Enhanced NLP2CMD with intelligent version detection."""

import sys
from pathlib import Path
from typing import Dict, Optional, Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from nlp2cmd import NLP2CMD
from nlp2cmd.ir import ActionIR

from nlp2cmd.storage.versioned_store import VersionedSchemaStore
from nlp2cmd.intelligent.version_aware_generator import VersionAwareCommandGenerator


class IntelligentNLP2CMD:
    """NLP2CMD with automatic version detection and adaptation."""
    
    def __init__(
        self,
        schema_store: Optional[VersionedSchemaStore] = None,
        storage_dir: str = "./command_schemas",
        llm_config: Optional[Dict] = None
    ):
        """Initialize the intelligent NLP2CMD system."""
        # Initialize schema store if not provided
        if schema_store is None:
            schema_store = VersionedSchemaStore(storage_dir)
        
        self.schema_store = schema_store
        self.generator = VersionAwareCommandGenerator(schema_store)
        
        # Initialize base NLP2CMD (fallback)
        self.base_nlp = None
        
        # Version detection cache
        self.version_cache = {}
    
    def transform(self, query: str, detect_version: bool = True) -> ActionIR:
        """
        Transform natural language to command with version detection.
        
        Args:
            query: Natural language query
            detect_version: Whether to detect command version
            
        Returns:
            ActionIR with generated command and metadata
        """
        if detect_version:
            try:
                # Generate command with version awareness
                command, metadata = self.generator.generate_command(query)
                
                # Create ActionIR
                ir = ActionIR(
                    action_id=metadata['base_command'],
                    dsl=command,
                    dsl_kind="shell",
                    params=metadata['context'],
                    output_format="raw",
                    confidence=0.9,
                    explanation=f"Generated for {metadata['base_command']} v{metadata['detected_version'] or 'unknown'}",
                    metadata={
                        'version_aware': True,
                        'detected_version': metadata['detected_version'],
                        'adaptations': metadata['adaptations'],
                        'schema_version': metadata['schema_version']
                    }
                )
                
                return ir
                
            except Exception as e:
                print(f"Version-aware generation failed: {e}")
                # Fallback to base NLP2CMD
                pass
        
        # Fallback to standard generation
        if self.base_nlp:
            return self.base_nlp.transform_ir(query)
        
        # Simple fallback
        return ActionIR(
            action_id="echo",
            dsl=f'echo "{query}"',
            dsl_kind="shell",
            params={},
            output_format="raw",
            confidence=0.1,
            explanation="Fallback generation",
            metadata={'fallback': True}
        )
    
    def detect_and_adapt(self, command: str) -> Dict[str, Any]:
        """
        Detect command version and return adaptation info.
        
        Args:
            command: Command to check
            
        Returns:
            Dictionary with version and adaptation info
        """
        version = self.generator._detect_command_version(command)
        adaptations = self.generator._get_adaptations(command, version)
        
        # Load available versions from store
        available_versions = self.schema_store.list_versions(command)
        
        # Select best version
        best_version = self._select_best_version(command, version, available_versions)
        
        return {
            'command': command,
            'detected_version': version,
            'available_versions': available_versions,
            'selected_version': best_version,
            'adaptations': adaptations,
            'needs_update': self._needs_update(version, available_versions)
        }
    
    def _select_best_version(self, command: str, detected: Optional[str], available: list) -> Optional[str]:
        """Select the best schema version for the detected version."""
        if not available:
            return None
        
        if not detected:
            # Use latest available
            return available[-1] if available else None
        
        # Try to find exact match
        if detected in available:
            return detected
        
        # Find closest version
        detected_parts = [int(x) for x in detected.split('.')]
        
        best_match = None
        best_score = -1
        
        for version in available:
            version_parts = [int(x) for x in version.split('.')]
            
            # Calculate similarity score
            score = 0
            for i in range(min(len(detected_parts), len(version_parts))):
                if detected_parts[i] == version_parts[i]:
                    score += 1
                else:
                    break
            
            if score > best_score:
                best_score = score
                best_match = version
        
        return best_match
    
    def _needs_update(self, detected: Optional[str], available: list) -> bool:
        """Check if the detected version is older than available schemas."""
        if not detected or not available:
            return False
        
        # Get latest available version
        latest = available[-1]
        
        # Compare versions
        detected_parts = [int(x) for x in detected.split('.')]
        latest_parts = [int(x) for x in latest.split('.')]
        
        # Pad shorter version
        max_len = max(len(detected_parts), len(latest_parts))
        detected_parts.extend([0] * (max_len - len(detected_parts)))
        latest_parts.extend([0] * (max_len - len(latest_parts)))
        
        # Compare
        return detected_parts < latest_parts
    
    def update_command_schema(self, command: str, force: bool = False) -> bool:
        """
        Update command schema by extracting from current system.
        
        Args:
            command: Command to update
            force: Force update even if version matches
            
        Returns:
            True if updated
        """
        info = self.detect_and_adapt(command)
        
        if not force and not info['needs_update']:
            print(f"{command} schema is up to date")
            return False
        
        try:
            # Extract new schema from system
            from nlp2cmd.schema_extraction import DynamicSchemaRegistry
            registry = DynamicSchemaRegistry(
                use_per_command_storage=True,
                storage_dir=self.schema_store.base_dir
            )
            
            schema = registry.register_shell_help(command)
            if schema.commands:
                # Determine new version
                last_version = info['available_versions'][-1] if info['available_versions'] else "1.0.0"
                new_version = self._increment_version(last_version)
                
                # Store new version
                self.schema_store.store_schema_version(schema, new_version, make_active=True)
                print(f"Updated {command} schema to v{new_version}")
                return True
                
        except Exception as e:
            print(f"Failed to update {command} schema: {e}")
        
        return False
    
    def _increment_version(self, version: str) -> str:
        """Increment version number."""
        parts = version.split('.')
        parts[-1] = str(int(parts[-1]) + 1)
        return '.'.join(parts)
    
    def clear_cache(self):
        """Clear all caches."""
        self.generator.clear_version_cache()
        self.version_cache.clear()


def demo_intelligent_nlp2cmd():
    """Demonstrate the intelligent NLP2CMD system."""
    print("=" * 60)
    print("Intelligent NLP2CMD Demo")
    print("=" * 60)
    
    # Initialize system
    nlp = IntelligentNLP2CMD(
        storage_dir=str(PROJECT_ROOT / "generated" / "migrated_schemas")
    )
    
    # Test queries
    queries = [
        "list containers",
        "show all docker images", 
        "run nginx in background",
        "check disk usage",
        "find python files",
    ]
    
    print("\nGenerating commands with version detection:\n")
    
    for query in queries:
        print(f"Query: {query}")
        ir = nlp.transform(query, detect_version=True)
        
        print(f"  Command: {ir.dsl}")
        print(f"  Confidence: {ir.confidence:.2f}")
        print(f"  Explanation: {ir.explanation}")
        
        if ir.metadata.get('version_aware'):
            print(f"  Detected version: {ir.metadata.get('detected_version', 'Unknown')}")
            if ir.metadata.get('adaptations'):
                print(f"  Adaptations: {', '.join(ir.metadata['adaptations'])}")
        print()
    
    # Demonstrate version detection
    print("\nVersion Detection Analysis:")
    print("-" * 40)
    
    commands = ['docker', 'git', 'python3']
    for cmd in commands:
        info = nlp.detect_and_adapt(cmd)
        print(f"\n{cmd}:")
        print(f"  Detected: v{info['detected_version'] or 'Unknown'}")
        print(f"  Available: {', '.join(info['available_versions'])}")
        print(f"  Using: v{info['selected_version'] or 'None'}")
        print(f"  Needs update: {'Yes' if info['needs_update'] else 'No'}")
    
    # Demonstrate schema update
    print("\n\nSchema Update Demo:")
    print("-" * 40)
    
    # Simulate outdated docker schema
    print("Checking for schema updates...")
    nlp.update_command_schema('docker')
    
    print("\n✅ Demo completed!")


if __name__ == "__main__":
    demo_intelligent_nlp2cmd()
