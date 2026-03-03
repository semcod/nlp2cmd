#!/usr/bin/env python3
"""
03_adaptive_code_nlp2cmd — LLM-guided code generation with adaptive routing using nlp2cmd.

This script demonstrates using nlp2cmd with adaptive routing for intelligent
code generation and execution on online editors.

Usage:
    python3 03_adaptive_code_nlp2cmd.py
    python3 03_adaptive_code_nlp2cmd.py --prompt "Write a Python program that calculates prime numbers"
    python3 03_adaptive_code_nlp2cmd.py --prompt "Napisz kalkulator w JavaScript" --headless
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add project root for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from nlp2cmd.cli.main import main as nlp2cmd_main


async def run_nlp2cmd_command(command: str, headless: bool = False, verbose: bool = False):
    """Run nlp2cmd with the given command."""
    # Build nlp2cmd arguments
    args = [
        "--run",
        command,
        "--headless" if headless else "",
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


async def main():
    parser = argparse.ArgumentParser(description="Adaptive code generation using nlp2cmd")
    parser.add_argument("--prompt", default="Write a Python program that sorts a list of numbers",
                        help="Code generation prompt")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Show verbose output")
    args = parser.parse_args()

    command = f"Otwórz codepen.io i napisz program: {args.prompt}"
    
    print(f"=== NLP2CMD Adaptive Code Example ===")
    print(f"Command: {command}")
    print(f"Prompt: {args.prompt}")
    print()
    
    await run_nlp2cmd_command(command, headless=args.headless, verbose=args.verbose)
    
    print()
    print("Done! Check the browser for the adaptive code generation result.")


if __name__ == "__main__":
    asyncio.run(main())
