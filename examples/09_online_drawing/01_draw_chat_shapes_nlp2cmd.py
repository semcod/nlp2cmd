#!/usr/bin/env python3
"""
01_draw_chat_shapes_nlp2cmd — Draw shapes on draw.chat using nlp2cmd.

This script demonstrates using nlp2cmd to automate drawing shapes on draw.chat
whiteboard through natural language commands.

Usage:
    python3 01_draw_chat_shapes_nlp2cmd.py
    python3 01_draw_chat_shapes_nlp2cmd.py --shape star --color blue
    python3 01_draw_chat_shapes_nlp2cmd.py --shape house --color red --headless
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
    parser = argparse.ArgumentParser(description="Draw on draw.chat using nlp2cmd")
    parser.add_argument("--shape", default="house", 
                        choices=["house", "star", "circle", "rectangle", "line", "spiral"],
                        help="Shape to draw")
    parser.add_argument("--color", default="blue",
                        help="Drawing color (name or hex)")
    parser.add_argument("--headless", action="store_true", help="Run headless")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Show verbose output")
    args = parser.parse_args()

    # Natural language command for nlp2cmd
    command = f"Otwórz draw.chat i narysuj {args.shape} w kolorze {args.color}"
    
    print(f"=== NLP2CMD Drawing Example ===")
    print(f"Command: {command}")
    print(f"Shape: {args.shape}")
    print(f"Color: {args.color}")
    print()
    
    await run_nlp2cmd_command(command, headless=args.headless, verbose=args.verbose)
    
    print()
    print("Done! Check the browser for the drawing result.")


if __name__ == "__main__":
    asyncio.run(main())
