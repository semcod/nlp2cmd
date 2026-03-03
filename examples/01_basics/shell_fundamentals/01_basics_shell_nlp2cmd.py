#!/usr/bin/env python3
"""
01_basics_shell_nlp2cmd — Basic shell commands using nlp2cmd.

This script demonstrates using nlp2cmd for basic shell command automation.

Usage:
    python3 01_basics_shell_nlp2cmd.py
    python3 01_basics_shell_nlp2cmd.py --command "list files"
    python3 01_basics_shell_nlp2cmd.py --command "show system info" --verbose
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add project root for imports
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from nlp2cmd.cli.main import main as nlp2cmd_main


async def run_nlp2cmd_command(command: str, verbose: bool = False):
    """Run nlp2cmd with the given command."""
    # Build nlp2cmd arguments
    args = [
        "--explain" if verbose else "--run",
        command,
    ]
    
    # Filter out empty arguments
    args = [arg for arg in args if arg]
    
    try:
        # Import and run nlp2cmd synchronously for shell commands
        import subprocess
        env = os.environ.copy()
        env['PYTHONPATH'] = f"{project_root}/src:{env.get('PYTHONPATH', '')}"
        
        cmd = [sys.executable, "-m", "nlp2cmd"] + args
        # Pipe "Y" to auto-confirm execution
        process = subprocess.Popen(cmd, 
                                  stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT,
                                  text=True, 
                                  cwd=project_root, env=env)
        
        # Auto-confirm with "Y" and wait for completion
        stdout, _ = process.communicate(input="Y\n")
        print(stdout, end='')  # Print the output
        
        return process.returncode
    except SystemExit:
        pass  # nlp2cmd calls sys.exit
    except Exception as e:
        print(f"Error running nlp2cmd: {e}")
        return 1


def get_command_for_task(task: str) -> str:
    """Get natural language command for shell tasks."""
    commands = {
        "list_files": "Pokaż pliki w bieżącym katalogu",
        "system_info": "Pokaż informacje o systemie",
        "processes": "Pokaż uruchomione procesy",
        "disk_usage": "Pokaż użycie dysku",
        "memory": "Pokaż użycie pamięci",
        "network": "Pokaż połączenia sieciowe",
    }
    return commands.get(task, task)


async def main():
    parser = argparse.ArgumentParser(description="Basic shell commands using nlp2cmd")
    parser.add_argument("--command", default="list_files",
                        help="Natural language command")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Show verbose output")
    args = parser.parse_args()

    command = get_command_for_task(args.command)
    
    print(f"=== NLP2CMD Shell Basics Example ===")
    print(f"Command: {command}")
    print(f"Task: {args.command}")
    print()
    
    exit_code = await run_nlp2cmd_command(command, verbose=args.verbose)
    
    print()
    if exit_code == 0:
        print("Done! Check the output for command results.")
    else:
        print(f"Command failed with exit code {exit_code}")


if __name__ == "__main__":
    asyncio.run(main())
