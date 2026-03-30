#!/usr/bin/env python3
"""Practical demonstration of version-aware command generation."""

import subprocess
import json
from pathlib import Path

def demonstrate_version_detection():
    """Demonstrate practical version detection and command adaptation."""
    
    print("=" * 60)
    print("Practical Version-Aware Command Generation")
    print("=" * 60)
    
    # Example 1: Docker version detection
    print("\n1. Docker Version Detection:")
    print("-" * 40)
    
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        docker_version = result.stdout.strip()
        print(f"Detected: {docker_version}")
        
        # Extract version number
        import re
        match = re.search(r'Docker version (\d+\.\d+\.\d+)', docker_version)
        if match:
            version = match.group(1)
            major = int(version.split('.')[0])
            
            print(f"Version: {version}")
            print(f"Major version: {major}")
            
            # Generate appropriate command
            if major >= 2:
                print("\nGenerated command for 'list containers':")
                print("  docker ps")
                print("  docker ps -a  # (show all containers)")
                print("  docker service ls  # (if swarm mode)")
            else:
                print("\nGenerated command for 'list containers':")
                print("  docker ps")
                print("  docker ps -a  # (show all containers)")
                print("  # Note: Swarm not available in v1.x")
    
    except FileNotFoundError:
        print("Docker not installed")
    
    # Example 2: kubectl version detection
    print("\n\n2. kubectl Version Detection:")
    print("-" * 40)
    
    try:
        result = subprocess.run(['kubectl', 'version', '--client', '--short'], 
                              capture_output=True, text=True)
        kubectl_version = result.stdout.strip()
        print(f"Detected: {kubectl_version}")
        
        match = re.search(r'Client Version: v?(\d+\.\d+\.\d+)', kubectl_version)
        if match:
            version = match.group(1)
            major, minor = map(int, version.split('.')[:2])
            
            print(f"Version: {version}")
            
            # Generate appropriate command
            print("\nGenerated command for 'list pods':")
            if major > 1 or (major == 1 and minor >= 16):
                print("  kubectl get pods -A  # (all namespaces)")
                print("  kubectl get pods --sort-by=.metadata.creationTimestamp")
            else:
                print("  kubectl get pods")
                print("  kubectl get pods --all-namespaces")
    
    except FileNotFoundError:
        print("kubectl not installed")
    
    # Example 3: System command detection (ps)
    print("\n\n3. System Command Detection (ps):")
    print("-" * 40)
    
    try:
        # Try to detect ps variant
        result = subprocess.run(['ps', '--version'], capture_output=True, text=True)
        if 'procps' in result.stdout:
            print("Detected: GNU ps (Linux)")
            print("\nGenerated command for 'show all processes':")
            print("  ps aux")
            print("  ps -ef  # (alternative format)")
        else:
            print("Detected: BSD ps (macOS/BSD)")
            print("\nGenerated command for 'show all processes':")
            print("  ps -ef")
            print("  ps aux  # (may not work)")
    
    except:
        print("Could not detect ps variant")
    
    # Example 4: Python version detection
    print("\n\n4. Python Version Detection:")
    print("-" * 40)
    
    try:
        result = subprocess.run(['python3', '--version'], capture_output=True, text=True)
        python_version = result.stderr.strip()  # Python outputs to stderr
        print(f"Detected: {python_version}")
        
        match = re.search(r'Python (\d+\.\d+\.\d+)', python_version)
        if match:
            version = match.group(1)
            major, minor = map(int, version.split('.')[:2])
            
            print(f"Version: {version}")
            
            # Generate appropriate command
            print("\nGenerated command for 'run Python script':")
            if major >= 3:
                print("  python3 script.py")
                if minor >= 7:
                    print("  python3 -m pip install package  # (recommended)")
            else:
                print("  python3 script.py")
                print("  pip3 install package")
    
    except FileNotFoundError:
        print("Python3 not installed")


def show_integration_example():
    """Show how to integrate version detection into NLP2CMD."""
    
    print("\n" + "=" * 60)
    print("Integration Example")
    print("=" * 60)
    
    code = '''
# Integration in NLP2CMD
class VersionAwareNLP2CMD:
    def transform(self, query):
        # 1. Detect base command
        command = self.detect_command(query)
        
        # 2. Check version BEFORE generating
        version = self.detect_version(command)
        
        # 3. Load appropriate schema
        schema = self.load_schema(command, version)
        
        # 4. Generate command
        result = self.generate_command(query, schema)
        
        # 5. Adapt to version if needed
        adapted = self.adapt_to_version(result, command, version)
        
        return adapted

# Example flow for "list containers":
# 1. Detect: docker
# 2. Check: docker --version → "Docker version 29.1.5"
# 3. Load: docker schema v2.0.0 (closest to 29.x)
# 4. Generate: "docker ps"
# 5. Adapt: Add swarm options if available
'''
    
    print(code)


def show_version_mapping():
    """Show version mapping for different commands."""
    
    print("\n" + "=" * 60)
    print("Version Mapping Examples")
    print("=" * 60)
    
    mappings = {
        "docker": {
            "detected": "29.1.5",
            "schema_versions": ["1.0.0", "2.0.0"],
            "selected": "2.0.0",
            "reason": "Latest available schema",
            "adaptations": ["swarm support", "new CLI syntax"]
        },
        "kubectl": {
            "detected": "1.28.2",
            "schema_versions": ["1.0.0"],
            "selected": "1.0.0",
            "reason": "Only schema available",
            "adaptations": ["Add -A flag for all namespaces"]
        },
        "git": {
            "detected": "2.51.0",
            "schema_versions": ["1.0.0"],
            "selected": "1.0.0",
            "reason": "Base schema compatible",
            "adaptations": ["Use modern git flags"]
        }
    }
    
    for cmd, info in mappings.items():
        print(f"\n{cmd.upper()}:")
        print(f"  System version: {info['detected']}")
        print(f"  Available schemas: {', '.join(info['schema_versions'])}")
        print(f"  Selected schema: v{info['selected']}")
        print(f"  Reason: {info['reason']}")
        print(f"  Adaptations: {', '.join(info['adaptations'])}")


def main():
    """Main demonstration."""
    demonstrate_version_detection()
    show_integration_example()
    show_version_mapping()
    
    print("\n" + "=" * 60)
    print("Key Benefits")
    print("=" * 60)
    print("""
✅ Automatic version detection before command generation
✅ Schema selection based on detected version
✅ Command adaptation for version compatibility
✅ Fallback to generic schemas if needed
✅ Cache results for performance
✅ Support for multiple command variants
    """)


if __name__ == "__main__":
    main()
