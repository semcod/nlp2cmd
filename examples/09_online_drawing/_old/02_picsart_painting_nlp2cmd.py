#!/usr/bin/env python3
"""
02_picsart_painting_nlp2cmd — Paint patterns on Picsart using nlp2cmd.

This script demonstrates using nlp2cmd to automate painting patterns on Picsart
through natural language commands. Based on analysis findings, it includes
fallback mechanisms for when Picsart requires login.

Usage:
    python3 02_picsart_painting_nlp2cmd.py
    python3 02_picsart_painting_nlp2cmd.py --pattern spiral --color blue
    python3 02_picsart_painting_nlp2cmd.py --pattern grid --fallback --headless
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


def get_command_for_pattern_and_color(pattern: str, color: str, fallback: bool = False) -> str:
    """Get natural language command for painting patterns."""
    if fallback:
        # Based on analysis, kleki.com is the fallback for Picsart
        return f"Otwórz kleki.com i narysuj wzór {pattern} w kolorze {color}"
    else:
        return f"Otwórz picsart.com/draw i narysuj wzór {pattern} w kolorze {color}"


def get_pattern_analysis_info() -> str:
    """Get pattern painting information based on analysis."""
    return """
🎨 Pattern Painting (based on analysis):
• Picsart.com: Requires login for drawing, automatic fallback to kleki.com
• Kleki.com: Basic drawing tools, limited color support (gradient picker)
• Patterns: spiral, grid, waves, flower, geometric shapes

🌐 Site Handling:
• Primary: picsart.com/draw (redirects to design editor, fallback triggered)
• Fallback: kleki.com (no login required, basic tools)
• Color: Limited on kleki (gradient picker vs palette)

📋 Available Patterns:
• spiral - Mathematical spiral pattern
• grid - Grid or lattice pattern  
• waves - Wave or sine pattern
• flower - Flower or petal pattern
• geometric - Geometric shapes pattern
"""


async def main():
    parser = argparse.ArgumentParser(description="Paint patterns using nlp2cmd")
    parser.add_argument("--pattern", default="spiral",
                        choices=["spiral", "grid", "waves", "flower", "geometric"],
                        help="Pattern to paint")
    parser.add_argument("--color", default="blue",
                        help="Painting color (name or hex)")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--fallback", action="store_true", 
                        help="Use fallback site (kleki.com) based on analysis")
    parser.add_argument("--show-patterns", action="store_true",
                        help="Show pattern information")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Show verbose output")
    args = parser.parse_args()

    if args.show_patterns:
        print(get_pattern_analysis_info())
        return

    command = get_command_for_pattern_and_color(args.pattern, args.color, args.fallback)
    site_info = "kleki.com (fallback)" if args.fallback else "picsart.com (with automatic fallback)"
    
    print(f"=== NLP2CMD Pattern Painting Example ===")
    print(f"Command: {command}")
    print(f"Pattern: {args.pattern}")
    print(f"Color: {args.color}")
    print(f"Site: {site_info}")
    print()
    
    # Show analysis-based information
    print("📊 Based on analysis findings:")
    print("• Picsart.com requires login for drawing (detected and handled)")
    print("• Automatic fallback to kleki.com when login modal appears")
    print("• Limited color support on kleki.com (gradient picker)")
    print("• Pattern detection works for mathematical and artistic patterns")
    print()
    
    if not args.fallback:
        print("ℹ️  Note: Picsart.com redirects to design editor and requires login.")
        print("   The system will automatically fallback to kleki.com if needed.")
        print()
    
    exit_code = await run_nlp2cmd_command(command, headless=args.headless, verbose=args.verbose)
    
    print()
    if exit_code == 0:
        print("✅ Done! Check the browser for the pattern painting result.")
        print("   The system used intelligent site detection and fallback.")
    else:
        print(f"❌ Pattern painting failed with exit code {exit_code}")
        print("   Try with --fallback to use kleki.com directly.")


if __name__ == "__main__":
    asyncio.run(main())
