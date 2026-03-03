#!/usr/bin/env python3
"""
03_adaptive_drawing_nlp2cmd — LLM-guided drawing with adaptive routing using nlp2cmd.

This script demonstrates using nlp2cmd with adaptive routing for intelligent
drawing automation on online whiteboards.

Usage:
    python3 03_adaptive_drawing_nlp2cmd.py
    python3 03_adaptive_drawing_nlp2cmd.py --prompt "Draw a colorful mandala"
    python3 03_adaptive_drawing_nlp2cmd.py --prompt "Narysuj dom z drzewem" --headless
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
    parser = argparse.ArgumentParser(description="Adaptive drawing using nlp2cmd")
    parser.add_argument("--prompt", default="Draw a simple house with a tree",
                        help="Drawing description")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Show verbose output")
    args = parser.parse_args()

    command = f"Otwórz draw.chat i narysuj: {args.prompt}"
    
    print(f"=== NLP2CMD Adaptive Drawing Example ===")
    print(f"Command: {command}")
    print(f"Prompt: {args.prompt}")
    print()
    
    await run_nlp2cmd_command(command, headless=args.headless, verbose=args.verbose)
    
    print()
    print("Done! Check the browser for the adaptive drawing result.")


if __name__ == "__main__":
    asyncio.run(main())
