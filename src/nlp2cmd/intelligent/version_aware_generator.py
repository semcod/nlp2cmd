#!/usr/bin/env python3
"""Intelligent command generation with version detection."""

import subprocess
import re
from typing import Dict, Optional, Tuple, Any, List
from pathlib import Path

from nlp2cmd.storage.versioned_store import VersionedSchemaStore
from nlp2cmd.generation.schema.generator import SchemaBasedGenerator


class VersionAwareCommandGenerator:
    """Generates commands with automatic version detection."""
    
    def __init__(self, schema_store: VersionedSchemaStore):
        """Initialize with schema store."""
        self.schema_store = schema_store
        self.version_cache = {}  # Cache detected versions
        self.command_mappings = {
            # Map generic actions to specific commands
            'list containers': 'docker',
            'show images': 'docker',
            'run container': 'docker',
            'list pods': 'kubectl',
            'show services': 'kubectl',
            'deploy app': 'kubectl',
            'list processes': 'ps',
            'show memory': 'free',
            'check disk': 'df',
        }
    
    def generate_command(self, query: str) -> Tuple[str, Dict[str, Any]]:
        """
        Generate command with version awareness.
        
        Args:
            query: Natural language query
            
        Returns:
            Tuple of (generated_command, metadata)
        """
        # Detect the base command
        base_command = self._detect_base_command(query)
        
        # Detect version of the command
        version = self._detect_command_version(base_command)
        
        # Load appropriate schema
        schema = self.schema_store.load_schema_version(base_command, version)
        if not schema:
            # Fallback to any available version
            schema = self.schema_store.load_schema_version(base_command)
        
        # Generate command using schema
        generator = SchemaBasedGenerator()
        generator.learn_from_schema(schema)
        
        # Extract context from query
        context = self._extract_context(query, base_command)
        
        # Generate the command
        command = generator.generate_command(base_command, context)
        
        # Post-process based on version
        command = self._post_process_command(command, base_command, version)
        
        metadata = {
            'base_command': base_command,
            'detected_version': version,
            'schema_version': schema.metadata.get('version') if schema else None,
            'context': context,
            'adaptations': self._get_adaptations(base_command, version)
        }
        
        return command, metadata
    
    def _detect_base_command(self, query: str) -> str:
        """Detect the base command from query."""
        query_lower = query.lower()
        
        # Check direct mappings
        for action, command in self.command_mappings.items():
            if action in query_lower:
                return command
        
        # Check for explicit command names
        commands = self.schema_store.list_commands()
        for cmd in commands:
            if cmd in query_lower:
                return cmd
        
        # Fallback to first word
        words = query.split()
        return words[0] if words else 'echo'
    
    def _detect_command_version(self, command: str) -> Optional[str]:
        """Detect the installed version of a command."""
        # Check cache first
        if command in self.version_cache:
            return self.version_cache[command]
        
        try:
            # Run version command
            version_output = self._run_version_command(command)
            version = self._parse_version_output(command, version_output)
            
            # Cache the result
            self.version_cache[command] = version
            return version
            
        except Exception as e:
            print(f"Failed to detect version for {command}: {e}")
            return None
    
    def _run_version_command(self, command: str) -> str:
        """Run command to get version info."""
        version_commands = {
            'docker': ['docker', '--version'],
            'kubectl': ['kubectl', 'version', '--client', '--short'],
            'git': ['git', '--version'],
            'python': ['python', '--version'],
            'python3': ['python3', '--version'],
            'node': ['node', '--version'],
            'npm': ['npm', '--version'],
            'gcc': ['gcc', '--version'],
            'curl': ['curl', '--version'],
            'wget': ['wget', '--version'],
        }
        
        cmd = version_commands.get(command, [command, '--version'])
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            return result.stdout + result.stderr
        else:
            # Try alternative version flags
            for flag in ['-V', '-v', 'version']:
                try:
                    result = subprocess.run(
                        [command, flag],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        return result.stdout + result.stderr
                except:
                    continue
            
            raise RuntimeError(f"Could not get version for {command}")
    
    def _parse_version_output(self, command: str, output: str) -> Optional[str]:
        """Parse version output to extract version number."""
        output = output.strip()
        
        # Version patterns for different commands
        patterns = {
            'docker': r'Docker version (\d+\.\d+\.\d+)',
            'kubectl': r'Client Version: v?(\d+\.\d+\.\d+)',
            'git': r'git version (\d+\.\d+\.\d+)',
            'python': r'Python (\d+\.\d+\.\d+)',
            'python3': r'Python (\d+\.\d+\.\d+)',
            'node': r'v(\d+\.\d+\.\d+)',
            'npm': r'(\d+\.\d+\.\d+)',
            'gcc': r'gcc.*?(\d+\.\d+\.\d+)',
            'curl': r'curl (\d+\.\d+\.\d+)',
            'wget': r'GNU Wget (\d+\.\d+\.\d+)',
        }
        
        pattern = patterns.get(command, r'(\d+\.\d+\.\d+)')
        match = re.search(pattern, output)
        
        if match:
            return match.group(1)
        
        # Try to find any version-like number
        match = re.search(r'\d+\.\d+(?:\.\d+)?', output)
        if match:
            return match.group(0)
        
        return None
    
    def _extract_context(self, query: str, command: str) -> Dict[str, Any]:
        """Extract context from the query."""
        context = {}
        
        # Extract patterns in quotes
        quoted = re.findall(r'"([^"]*)"', query)
        if quoted:
            context['pattern'] = quoted[0]
        
        # Extract file extensions
        extensions = re.findall(r'\.\w+\b', query)
        if extensions:
            context['extension'] = extensions[0]
        
        # Extract sizes
        sizes = re.findall(r'\d+[KMGT]?B?', query, re.IGNORECASE)
        if sizes:
            context['size'] = sizes[0]
        
        # Extract numbers
        numbers = re.findall(r'\d+', query)
        if numbers:
            context['number'] = int(numbers[0])
        
        # Command-specific context
        if command == 'docker':
            if 'container' in query.lower():
                context['resource'] = 'container'
            elif 'image' in query.lower():
                context['resource'] = 'image'
            elif 'service' in query.lower():
                context['resource'] = 'service'
            elif 'swarm' in query.lower():
                context['orchestration'] = True
        
        elif command == 'kubectl':
            if 'pod' in query.lower():
                context['resource'] = 'pod'
            elif 'service' in query.lower():
                context['resource'] = 'service'
            elif 'deployment' in query.lower():
                context['resource'] = 'deployment'
            elif 'all' in query.lower():
                context['all_namespaces'] = True
        
        return context
    
    def _post_process_command(self, command: str, base_cmd: str, version: str) -> str:
        """Post-process command based on detected version."""
        if base_cmd == 'docker':
            # Docker version-specific adjustments
            if version:
                major = int(version.split('.')[0])
                if major < 1:
                    # Very old Docker versions
                    command = command.replace('docker ps', 'docker ps -a')
                elif major == 1:
                    # Docker 1.x
                    if 'swarm' in command:
                        command = command.replace('docker swarm', 'docker swarm manage')
                else:
                    # Docker 2.x+
                    if 'service' in command and version.startswith('2.0'):
                        # Early 2.x might not have all swarm features
                        command += ' --with-registry-auth'
        
        elif base_cmd == 'kubectl':
            # kubectl version adjustments
            if version:
                major, minor = map(int, version.split('.')[:2])
                if major < 1 or (major == 1 and minor < 16):
                    # Older kubectl versions
                    command = command.replace('--sort-by', '--sort')
        
        elif base_cmd == 'ps':
            # BSD vs GNU ps
            try:
                result = subprocess.run(['ps', '--version'], capture_output=True, text=True)
                if 'procps' in result.stdout:
                    # GNU ps
                    if 'all' in command:
                        command = command.replace('ps -a', 'ps aux')
                else:
                    # BSD ps (macOS)
                    command = command.replace('ps aux', 'ps -ef')
            except:
                pass
        
        return command
    
    def _get_adaptations(self, command: str, version: str) -> List[str]:
        """Get list of adaptations made for the version."""
        adaptations = []
        
        if command == 'docker' and version:
            major = int(version.split('.')[0])
            if major >= 2:
                adaptations.append("Using Docker 2.x+ syntax with swarm support")
            elif major == 1:
                adaptations.append("Using Docker 1.x syntax")
            else:
                adaptations.append("Using legacy Docker syntax")
        
        elif command == 'kubectl' and version:
            adaptations.append(f"Adapted for kubectl v{version}")
        
        return adaptations
    
    def clear_version_cache(self):
        """Clear the version detection cache."""
        self.version_cache.clear()


def test_version_aware_generation():
    """Test the version-aware command generation."""
    print("=" * 60)
    print("Version-Aware Command Generation Test")
    print("=" * 60)
    
    # Initialize with migrated schemas
    store = VersionedSchemaStore("./migrated_schemas")
    generator = VersionAwareCommandGenerator(store)
    
    test_queries = [
        "list containers",
        "show all images",
        "run nginx container",
        "list all pods",
        "show running processes",
        "check disk space",
    ]
    
    print("\nTesting command generation with version detection:\n")
    
    for query in test_queries:
        try:
            print(f"Query: {query}")
            command, metadata = generator.generate_command(query)
            
            print(f"  Generated: {command}")
            print(f"  Base command: {metadata['base_command']}")
            print(f"  Detected version: {metadata['detected_version'] or 'Unknown'}")
            print(f"  Adaptations: {', '.join(metadata['adaptations']) if metadata['adaptations'] else 'None'}")
            print()
            
        except Exception as e:
            print(f"  Error: {e}")
            print()
    
    # Test version detection specifically
    print("\nVersion Detection Results:")
    print("-" * 40)
    
    commands_to_check = ['docker', 'git', 'python3', 'curl']
    for cmd in commands_to_check:
        try:
            version = generator._detect_command_version(cmd)
            print(f"{cmd:10} -> {version or 'Not found'}")
        except:
            print(f"{cmd:10} -> Detection failed")


if __name__ == "__main__":
    test_version_aware_generation()
