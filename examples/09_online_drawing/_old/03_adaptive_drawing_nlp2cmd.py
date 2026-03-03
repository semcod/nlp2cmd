#!/usr/bin/env python3
"""
03_adaptive_drawing_nlp2cmd — LLM-guided drawing with adaptive routing using nlp2cmd.

This script demonstrates using nlp2cmd with adaptive routing for intelligent
drawing automation on online whiteboards. Based on analysis findings, it includes
coordinate scaling, color handling, and intelligent fallback.

Usage:
    python3 03_adaptive_drawing_nlp2cmd.py
    python3 03_adaptive_drawing_nlp2cmd.py --prompt "Draw a colorful mandala"
    python3 03_adaptive_drawing_nlp2cmd.py --prompt "Narysuj czerwona gwiazda" --headless
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


def get_adaptive_command(prompt: str, fallback: bool = False) -> str:
    """Get adaptive drawing command based on analysis findings."""
    # Based on analysis, Polish commands work better with proper color declensions
    if fallback:
        return f"Otwórz jspaint.app i narysuj: {prompt}"
    else:
        return f"Otwórz draw.chat i narysuj: {prompt}"


def get_color_analysis_info() -> str:
    """Get color handling information based on analysis."""
    return """
🎨 Color Handling (based on analysis):
• jspaint.app: Full color support via palette click (28 colors)
• kleki.com: Limited color support (gradient picker)
• draw.chat: Currently down, automatic fallback active

🌐 Supported sites:
• Primary: draw.chat (with automatic fallback to jspaint.app)
• Fallback: jspaint.app (reliable, full color support)
• Alternative: kleki.com (basic shapes, limited colors)
"""


async def main():
    parser = argparse.ArgumentParser(description="Adaptive drawing using nlp2cmd")
    parser.add_argument("--prompt", default="Draw a simple house with a tree",
                        help="Drawing description")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--fallback", action="store_true", 
                        help="Use fallback site (jspaint.app) based on analysis")
    parser.add_argument("--show-colors", action="store_true",
                        help="Show color handling information")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Show verbose output")
    args = parser.parse_args()

    if args.show_colors:
        print(get_color_analysis_info())
        return

    command = get_adaptive_command(args.prompt, args.fallback)
    site_info = "jspaint.app (fallback)" if args.fallback else "draw.chat (with automatic fallback)"
    
    print(f"=== NLP2CMD Adaptive Drawing Example ===")
    print(f"Command: {command}")
    print(f"Prompt: {args.prompt}")
    print(f"Site: {site_info}")
    print()
    
    # Show analysis-based information
    print("📊 Based on analysis findings:")
    print("• Coordinate scaling automatically applied for different canvas sizes")
    print("• Polish color declensions supported (czerwoną, niebieską, etc.)")
    print("• Automatic popup dismissal and canvas polling")
    print("• Vision verification available (when models are accessible)")
    print()
    
    if not args.fallback:
        print("ℹ️  Note: draw.chat is currently down according to analysis.")
        print("   The system will automatically fallback to jspaint.app if needed.")
        print()
    
    exit_code = await run_nlp2cmd_command(command, headless=args.headless, verbose=args.verbose)
    
    print()
    if exit_code == 0:
        print("✅ Done! Check the browser for the adaptive drawing result.")
        print("   The system used intelligent routing and fallback mechanisms.")
    else:
        print(f"❌ Adaptive drawing failed with exit code {exit_code}")
        print("   Try with --fallback to use jspaint.app directly.")


if __name__ == "__main__":
    asyncio.run(main())
