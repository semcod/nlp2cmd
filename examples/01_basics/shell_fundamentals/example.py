#!/usr/bin/env python3
"""
NLP2CMD Shell Example

Demonstrates natural language to shell command transformation
with environment context and safety policies.

📚 Related Documentation:
- https://github.com/wronai/nlp2cmd/blob/main/docs/guides/user-guide.md
- https://github.com/wronai/nlp2cmd/blob/main/docs/api/README.md
- https://github.com/wronai/nlp2cmd/blob/main/THERMODYNAMIC_INTEGRATION.md

🚀 More Examples:
- https://github.com/wronai/nlp2cmd/tree/main/examples/use_cases
"""

from pathlib import Path
import sys
import json
import tempfile

sys.path.append(str(Path(__file__).resolve().parents[2]))

from _example_helpers import print_rule, print_separator

from app2schema import extract_appspec_to_file
from nlp2cmd import NLP2CMD
from nlp2cmd.schema_based import SchemaDrivenAppSpecAdapter
from nlp2cmd.adapters.shell import ShellSafetyPolicy
from nlp2cmd.environment import EnvironmentAnalyzer


def main():
    # Analyze current environment
    env_analyzer = EnvironmentAnalyzer()
    env_info = env_analyzer.analyze()
    tools = env_analyzer.detect_tools(["docker", "git", "kubectl", "aws", "curl"])

    print_separator("Environment Analysis", width=60)
    print(f"OS: {env_info['os']['system']} {env_info['os']['release']}")
    print(f"Shell: {env_info['shell']['name']}")
    print(f"Available tools: {[t for t, i in tools.items() if i.available]}")

    # Configure safety policy
    safety_policy = ShellSafetyPolicy(
        blocked_commands=[
            "rm -rf /",
            "rm -rf /*",
            "mkfs",
            "dd if=/dev/zero",
        ],
        require_confirmation_for=[
            "rm",
            "kill",
            "shutdown",
        ],
        allow_sudo=False,
        max_pipe_depth=5,
        sandbox_mode=True,
    )

    # Build combined appspec with all tools
    export_path = Path("./generated_shell_appspec.json")

    first = True
    for tool_name, info in tools.items():
        if not info.available:
            continue
        try:
            extract_appspec_to_file(
                tool_name,
                export_path,
                source_type="shell",
                merge=not first,
            )
            first = False
            print(f"[BasicShell] Extracted AppSpec for {tool_name}", file=sys.stderr)
        except Exception as e:
            print(f"[BasicShell] Failed to extract {tool_name}: {e}", file=sys.stderr)
            continue

    adapter = SchemaDrivenAppSpecAdapter(
        appspec_path=export_path if export_path.exists() else None,
        safety_policy=safety_policy,
        llm_config={
            "model": "ollama/qwen2.5-coder:7b",
            "api_base": "http://localhost:11434",
            "temperature": 0.1,
            "max_tokens": 512,
            "timeout": 10,
        }
    )

    nlp = NLP2CMD(adapter=adapter)

# Example commands
commands = [
    "Find files larger than 100MB modified in the last week",
    "Show top 10 processes by memory usage",
    "List all running Docker containers",
    "Count lines of Python code in current directory",
    "Show disk usage sorted by size",
    "Find all TODO comments in source files",
    "Compress the logs directory",
    "Show git commits from last week by author",
]

print_separator("NLP2CMD Shell Examples", leading_newline=True, width=60)

for cmd in commands:
    print(f"\n📝 Request: {cmd}")
    print_rule(width=40)

    ir = nlp.transform_ir(cmd)

    print(f"Action: {ir.action_id}")
    print(f"\nGenerated command:")
    print(f"   $ {ir.dsl}")
    
    # Ask for feedback (optional)
    if input("\nIs this correct? (Y/n): ").lower() == 'n':
        correction = input("What should it be? ")
        adapter.learn_from_feedback(cmd, ir.dsl, correction)
        print("Thanks! I've learned from that.")

# Safety policy demo
print_separator("Safety Policy Demo", leading_newline=True, width=60)

dangerous_commands = [
    "Delete everything in root directory",
    "Run command with sudo",
]

for cmd in dangerous_commands:
    print(f"\n📝 Request: {cmd}")
    try:
        ir = nlp.transform_ir(cmd)
        print(f"Generated: {ir.dsl}")
    except Exception as e:
        print(f"❌ Blocked: {e}")
    
    # Save learned improvements
    adapter.save_improvements("./learned_schemas.json")
    print("\n✅ Saved learned improvements to learned_schemas.json")

# Example commands
commands = [
    "Find files larger than 100MB modified in the last week",
    "Show top 10 processes by memory usage",
    "List all running Docker containers",
    "Count lines of Python code in current directory",
    "Show disk usage sorted by size",
    "Find all TODO comments in source files",
    "Compress the logs directory",
    "Show git commits from last week by author",
]

print_separator("NLP2CMD Shell Examples", leading_newline=True, width=60)

for cmd in commands:
    print(f"\n📝 Request: {cmd}")
    print_rule(width=40)

    ir = nlp.transform_ir(cmd)

    print(f"Action: {ir.action_id}")
    print(f"\nGenerated command:")
    print(f"   $ {ir.dsl}")
    
    # Ask for feedback (optional)
    if input("\nIs this correct? (Y/n): ").lower() == 'n':
        correction = input("What should it be? ")
        adapter.learn_from_feedback(cmd, ir.dsl, correction)
        print("Thanks! I've learned from that.")

# Safety policy demo
print_separator("Safety Policy Demo", leading_newline=True, width=60)

dangerous_commands = [
    "Delete everything in root directory",
    "Run command with sudo",
]

for cmd in dangerous_commands:
    print(f"\n📝 Request: {cmd}")
    try:
        ir = nlp.transform_ir(cmd)
        print(f"Generated: {ir.dsl}")
    except Exception as e:
        print(f"❌ Blocked: {e}")
    
    # Save learned improvements
    adapter.save_improvements("./learned_schemas.json")
    print("\n✅ Saved learned improvements to learned_schemas.json")

# Safety policy demo
print_separator("Safety Policy Demo", leading_newline=True, width=60)

dangerous_commands = [
    "Delete everything in root directory",
    "Run command with sudo",
]

for cmd in dangerous_commands:
    print(f"\n📝 Request: {cmd}")
    try:
        ir = nlp.transform_ir(cmd)
        print(f"Generated: {ir.dsl}")
    except Exception as e:
        print(f"❌ Blocked: {e}")
    
    # Save learned improvements
    adapter.save_improvements("./learned_schemas.json")
    print("\n✅ Saved learned improvements to learned_schemas.json")


if __name__ == "__main__":
    main()
