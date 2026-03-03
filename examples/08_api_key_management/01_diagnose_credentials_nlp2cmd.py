#!/usr/bin/env python3
"""
01_diagnose_credentials_nlp2cmd — Diagnose API credentials using nlp2cmd.

This script demonstrates using nlp2cmd to diagnose and extract API credentials
from various services.

Usage:
    python3 01_diagnose_credentials_nlp2cmd.py
    python3 01_diagnose_credentials_nlp2cmd.py --service openrouter
    python3 01_diagnose_credentials_nlp2cmd.py --service all --verbose
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


def get_command_for_service(service: str) -> str:
    """Get natural language command for credential diagnosis."""
    commands = {
        "openrouter": "Sprawdź klucze API OpenRouter w środowisku i przeglądarce",
        "anthropic": "Sprawdź klucze API Anthropic w środowisku i przeglądarce",
        "openai": "Sprawdź klucze API OpenAI w środowisku i przeglądarce",
        "github": "Sprawdź tokeny GitHub w środowisku i przeglądarce",
        "all": "Sprawdź wszystkie dostępne klucze API i tokeny w środowisku i przeglądarce",
    }
    return commands.get(service, f"Sprawdź klucze API dla serwisu {service}")


async def main():
    parser = argparse.ArgumentParser(description="Diagnose API credentials using nlp2cmd")
    parser.add_argument("--service", default="all",
                        choices=["openrouter", "anthropic", "openai", "github", "all"],
                        help="Service to check")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Show verbose output")
    args = parser.parse_args()

    command = get_command_for_service(args.service)
    
    print(f"=== NLP2CMD Credential Diagnosis Example ===")
    print(f"Command: {command}")
    print(f"Service: {args.service}")
    print()
    
    await run_nlp2cmd_command(command, verbose=args.verbose)
    
    print()
    print("Done! Check the output for credential information.")


if __name__ == "__main__":
    asyncio.run(main())
