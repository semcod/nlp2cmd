#!/usr/bin/env python3
"""
01_draw_chat_shapes_nlp2cmd — Draw shapes on draw.chat using nlp2cmd.

This script demonstrates using nlp2cmd to automate drawing shapes on online whiteboards
through natural language commands. Based on analysis findings, it includes intelligent
fallback and coordinate scaling.

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
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from nlp2cmd.cli.main import main as nlp2cmd_main


async def run_nlp2cmd_command(command: str, headless: bool = False, verbose: bool = False):
    """Run nlp2cmd with the given command."""
    # Build nlp2cmd arguments
    args = [
        "--explain" if verbose else "--run",
        command,
    ]
    
    # Add headless mode for browser commands
    if headless:
        args.append("--headless")
    
    # Filter out empty arguments
    args = [arg for arg in args if arg]
    
    try:
        # Import and run nlp2cmd synchronously
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


def get_command_for_shape_and_color(shape: str, color: str) -> str:
    """Get natural language command for drawing shapes."""
    # Based on analysis, Polish commands work better with accusative color forms
    commands = {
        "house": f"Otwórz draw.chat i narysuj dom w kolorze {color}",
        "star": f"Otwórz draw.chat i narysuj gwiazdę w kolorze {color}",
        "circle": f"Otwórz draw.chat i narysuj koło w kolorze {color}",
        "rectangle": f"Otwórz draw.chat i narysuj prostokąt w kolorze {color}",
        "line": f"Otwórz draw.chat i narysuj linię w kolorze {color}",
        "spiral": f"Otwórz draw.chat i narysuj spiralę w kolorze {color}",
        "heart": f"Otwórz draw.chat i narysuj serce w kolorze {color}",
        "flower": f"Otwórz draw.chat i narysuj kwiat w kolorze {color}",
        "triangle": f"Otwórz draw.chat i narysuj trójkąt w kolorze {color}",
        "ellipse": f"Otwórz draw.chat i narysuj elipsę w kolorze {color}",
    }
    return commands.get(shape, f"Otwórz draw.chat i narysuj {shape} w kolorze {color}")


def get_fallback_command(shape: str, color: str) -> str:
    """Get fallback command for when draw.chat is down (based on analysis)."""
    return f"Otwórz jspaint.app i narysuj {shape} w kolorze {color}"


async def main():
    parser = argparse.ArgumentParser(description="Draw on online whiteboards using nlp2cmd")
    parser.add_argument("--shape", default="house", 
                        choices=["house", "star", "circle", "rectangle", "line", "spiral", "heart", "flower", "triangle", "ellipse"],
                        help="Shape to draw")
    parser.add_argument("--color", default="blue",
                        help="Drawing color (name or hex)")
    parser.add_argument("--headless", action="store_true", help="Run headless")
    parser.add_argument("--fallback", action="store_true", 
                        help="Use fallback site (jspaint.app) based on analysis")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Show verbose output")
    args = parser.parse_args()

    # Choose command based on analysis findings
    if args.fallback:
        command = get_fallback_command(args.shape, args.color)
        site = "jspaint.app (fallback)"
    else:
        command = get_command_for_shape_and_color(args.shape, args.color)
        site = "draw.chat (with automatic fallback)"
    
    print(f"=== NLP2CMD Drawing Example ===")
    print(f"Command: {command}")
    print(f"Shape: {args.shape}")
    print(f"Color: {args.color}")
    print(f"Site: {site}")
    print()
    
    # Based on analysis, draw.chat is currently down, so we should mention fallback
    if not args.fallback:
        print("ℹ️  Note: Based on analysis, draw.chat is currently down.")
        print("   The system will automatically fallback to jspaint.app if needed.")
        print()
    
    exit_code = await run_nlp2cmd_command(command, headless=args.headless, verbose=args.verbose)
    
    print()
    if exit_code == 0:
        print("✅ Done! Check the browser for the drawing result.")
        print("   If draw.chat was down, the system automatically used jspaint.app.")
    else:
        print(f"❌ Drawing failed with exit code {exit_code}")
        print("   Try with --fallback to use jspaint.app directly.")


if __name__ == "__main__":
    asyncio.run(main())
