#!/usr/bin/env python3
"""
01_basics_docker_nlp2cmd — Basic Docker commands using nlp2cmd.

This script demonstrates using nlp2cmd for basic Docker command automation.

Usage:
    python3 01_basics_docker_nlp2cmd.py
    python3 01_basics_docker_nlp2cmd.py --command "list containers"
    python3 01_basics_docker_nlp2cmd.py --command "show images" --verbose
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add project root for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from nlp2cmd.cli.main import main as nlp2cmd_main


async def run_nlp2cmd_command(command: str, verbose: bool = False):
    """Run nlp2cmd with the given command."""
    # Build nlp2cmd arguments
    args = [
        "--run",
        command,
        "--verbose" if verbose else "",
    ]
    
    # Filter out empty arguments
    args = [arg for arg in args if arg]
    
    # Override sys.argv for nlp2cmd
    original_argv = sys.argv.copy()
    sys.argv = ["nlp2cmd"] + args
    
    try:
        await nlp2cmd_main()
    except SystemExit:
        pass  # nlp2cmd calls sys.exit
    finally:
        sys.argv = original_argv


def get_command_for_task(task: str) -> str:
    """Get natural language command for Docker tasks."""
    commands = {
        "list_containers": "Pokaż uruchomione kontenery Docker",
        "list_all_containers": "Pokaż wszystkie kontenery Docker",
        "show_images": "Pokaż obrazy Docker",
        "system_info": "Pokaż informacje o systemie Docker",
        "prune": "Wyczyść nieużywane obrazy i kontenery Docker",
        "logs": "Pokaż logi kontenerów",
    }
    return commands.get(task, task)


async def main():
    parser = argparse.ArgumentParser(description="Basic Docker commands using nlp2cmd")
    parser.add_argument("--command", default="list_containers",
                        help="Natural language command")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Show verbose output")
    args = parser.parse_args()

    command = get_command_for_task(args.command)
    
    print(f"=== NLP2CMD Docker Basics Example ===")
    print(f"Command: {command}")
    print(f"Task: {args.command}")
    print()
    
    await run_nlp2cmd_command(command, verbose=args.verbose)
    
    print()
    print("Done! Check the output for Docker command results.")


if __name__ == "__main__":
    asyncio.run(main())
