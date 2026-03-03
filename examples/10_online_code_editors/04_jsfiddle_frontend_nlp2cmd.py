#!/usr/bin/env python3
"""
04_jsfiddle_frontend_nlp2cmd — Write frontend code on JSFiddle using nlp2cmd.

This script demonstrates using nlp2cmd to automate frontend code writing on JSFiddle
through natural language commands.

Usage:
    python3 04_jsfiddle_frontend_nlp2cmd.py
    python3 04_jsfiddle_frontend_nlp2cmd.py --preset hello
    python3 04_jsfiddle_frontend_nlp2cmd.py --preset particles --headless
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


def get_command_for_preset(preset: str) -> str:
    """Get natural language command for a preset."""
    commands = {
        "hello": "Otwórz jsfiddle.net i stwórz stronę z przyciskiem, który zmienia tekst po kliknięciu",
        "particles": "Otwórz jsfiddle.net i stwórz animację cząsteczek w Canvas",
        "calculator": "Otwórz jsfiddle.net i stwórz kalkulator z podstawowymi operacjami",
    }
    return commands.get(preset, f"Otwórz jsfiddle.net i stwórz stronę z presetem {preset}")


async def main():
    parser = argparse.ArgumentParser(description="Write frontend code on JSFiddle using nlp2cmd")
    parser.add_argument("--preset", default="hello",
                        choices=["hello", "particles", "calculator"],
                        help="Preset code snippet")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Show verbose output")
    args = parser.parse_args()

    command = get_command_for_preset(args.preset)
    
    print(f"=== NLP2CMD JSFiddle Example ===")
    print(f"Command: {command}")
    print(f"Preset: {args.preset}")
    print()
    
    await run_nlp2cmd_command(command, headless=args.headless, verbose=args.verbose)
    
    print()
    print("Done! Check the browser for the JSFiddle result.")


if __name__ == "__main__":
    asyncio.run(main())
