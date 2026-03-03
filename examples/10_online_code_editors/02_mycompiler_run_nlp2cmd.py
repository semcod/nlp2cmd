#!/usr/bin/env python3
"""
02_mycompiler_run_nlp2cmd — Run code on myCompiler.io using nlp2cmd.

This script demonstrates using nlp2cmd to automate code execution on myCompiler.io
through natural language commands.

Usage:
    python3 02_mycompiler_run_nlp2cmd.py
    python3 02_mycompiler_run_nlp2cmd.py --code fibonacci
    python3 02_mycompiler_run_nlp2cmd.py --code factorial --lang python --headless
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


def get_command_for_code(code: str, lang: str = "python") -> str:
    """Get natural language command for code execution."""
    commands = {
        "fibonacci": f"Otwórz mycompiler.io i uruchom program {lang} obliczający ciąg Fibonacciego",
        "factorial": f"Otwórz mycompiler.io i uruchom program {lang} obliczający silnię",
        "sorting": f"Otwórz mycompiler.io i uruchom program {lang} sortujący listę liczb",
        "hello": f"Otwórz mycompiler.io i uruchom prosty program {lang} wyświetlający 'Hello World'",
    }
    return commands.get(code, f"Otwórz mycompiler.io i uruchom program {lang} z kodem: {code}")


async def main():
    parser = argparse.ArgumentParser(description="Run code on myCompiler.io using nlp2cmd")
    parser.add_argument("--code", default="fibonacci",
                        choices=["fibonacci", "factorial", "sorting", "hello"],
                        help="Code preset to run")
    parser.add_argument("--lang", default="python",
                        choices=["python", "javascript", "cpp"],
                        help="Programming language")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Show verbose output")
    args = parser.parse_args()

    command = get_command_for_code(args.code, args.lang)
    
    print(f"=== NLP2CMD myCompiler Example ===")
    print(f"Command: {command}")
    print(f"Code: {args.code}")
    print(f"Language: {args.lang}")
    print()
    
    await run_nlp2cmd_command(command, headless=args.headless, verbose=args.verbose)
    
    print()
    print("Done! Check the browser for the execution result.")


if __name__ == "__main__":
    asyncio.run(main())
