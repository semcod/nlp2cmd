#!/usr/bin/env python3
"""Practical demonstration of version-aware command generation."""

import re
import subprocess


def _demo_tool_version(title: str, command: list[str], parser, on_detected) -> None:
    print(f"\n{title}")
    print("-" * 40)
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        output = result.stdout.strip() or result.stderr.strip()
        print(f"Detected: {output}")
        match = parser(output)
        if match:
            on_detected(match, output)
    except FileNotFoundError:
        print(f"{command[0]} not installed")


def _demo_docker() -> None:
    def on_detected(match, _output):
        version = match.group(1)
        major = int(version.split(".")[0])
        print(f"Version: {version}")
        print(f"Major version: {major}")
        print("\nGenerated command for 'list containers':")
        print("  docker ps")
        print("  docker ps -a  # (show all containers)")
        if major >= 2:
            print("  docker service ls  # (if swarm mode)")
        else:
            print("  # Note: Swarm not available in v1.x")

    _demo_tool_version(
        "1. Docker Version Detection:",
        ["docker", "--version"],
        lambda text: re.search(r"Docker version (\d+\.\d+\.\d+)", text),
        on_detected,
    )


def _demo_kubectl() -> None:
    def on_detected(match, _output):
        version = match.group(1)
        major, minor = map(int, version.split(".")[:2])
        print(f"Version: {version}")
        print("\nGenerated command for 'list pods':")
        if major > 1 or (major == 1 and minor >= 16):
            print("  kubectl get pods -A  # (all namespaces)")
            print("  kubectl get pods --sort-by=.metadata.creationTimestamp")
        else:
            print("  kubectl get pods")
            print("  kubectl get pods --all-namespaces")

    _demo_tool_version(
        "\n\n2. kubectl Version Detection:",
        ["kubectl", "version", "--client", "--short"],
        lambda text: re.search(r"Client Version: v?(\d+\.\d+\.\d+)", text),
        on_detected,
    )


def _demo_ps() -> None:
    def on_detected(_match, output):
        if "procps" in output:
            print("Detected: GNU ps (Linux)")
            print("\nGenerated command for 'show all processes':")
            print("  ps aux")
            print("  ps -ef  # (alternative format)")
        else:
            print("Detected: BSD ps (macOS/BSD)")
            print("\nGenerated command for 'show all processes':")
            print("  ps -ef")
            print("  ps aux  # (may not work)")

    _demo_tool_version(
        "\n\n3. System Command Detection (ps):",
        ["ps", "--version"],
        lambda text: re.search(r".+", text),
        on_detected,
    )


def _demo_python() -> None:
    def on_detected(match, _output):
        version = match.group(1)
        major, minor = map(int, version.split(".")[:2])
        print(f"Version: {version}")
        print("\nGenerated command for 'run Python script':")
        print("  python3 script.py")
        if major >= 3 and minor >= 7:
            print("  python3 -m pip install package  # (recommended)")
        elif major >= 3:
            print("  pip3 install package")

    _demo_tool_version(
        "\n\n4. Python Version Detection:",
        ["python3", "--version"],
        lambda text: re.search(r"Python (\d+\.\d+\.\d+)", text),
        on_detected,
    )


def demonstrate_version_detection():
    """Demonstrate practical version detection and command adaptation."""
    print("=" * 60)
    print("Practical Version-Aware Command Generation")
    print("=" * 60)
    _demo_docker()
    _demo_kubectl()
    _demo_ps()
    _demo_python()


def show_integration_example():
    """Show how to integrate version detection into NLP2CMD."""
    print("\n" + "=" * 60)
    print("Integration Example")
    print("=" * 60)
    print("""
# Integration in NLP2CMD
class VersionAwareNLP2CMD:
    def transform(self, query):
        command = self.detect_command(query)
        version = self.detect_version(command)
        schema = self.load_schema(command, version)
        result = self.generate_command(query, schema)
        return self.adapt_to_version(result, command, version)
""")


def show_version_mapping():
    """Show version mapping for different commands."""
    print("\n" + "=" * 60)
    print("Version Mapping Examples")
    print("=" * 60)

    mappings = {
        "docker": ("29.1.5", ["1.0.0", "2.0.0"], "2.0.0", "Latest available schema",
                   ["swarm support", "new CLI syntax"]),
        "kubectl": ("1.28.2", ["1.0.0"], "1.0.0", "Only schema available",
                    ["Add -A flag for all namespaces"]),
        "git": ("2.51.0", ["1.0.0"], "1.0.0", "Base schema compatible",
                ["Use modern git flags"]),
    }

    for cmd, (detected, schemas, selected, reason, adaptations) in mappings.items():
        print(f"\n{cmd.upper()}:")
        print(f"  System version: {detected}")
        print(f"  Available schemas: {', '.join(schemas)}")
        print(f"  Selected schema: v{selected}")
        print(f"  Reason: {reason}")
        print(f"  Adaptations: {', '.join(adaptations)}")


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
