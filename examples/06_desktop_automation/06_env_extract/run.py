#!/usr/bin/env python3
"""
06_env_extract — Extract API keys from browser sessions and save to .env.

Usage:
    python3 run.py --service openrouter --env-path .env
    python3 run.py --service github --env-path ~/project/.env
    python3 run.py --list-services
"""

import argparse
import asyncio
import sys

# Add project root to path
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))


async def main():
    parser = argparse.ArgumentParser(description="Extract API keys from browser → .env")
    parser.add_argument("--service", default="openrouter", help="Service name (e.g. openrouter, anthropic, openai)")
    parser.add_argument("--env-path", default=".env", help="Path to .env file")
    parser.add_argument("--headless", action="store_true", help="Run browser headless (not recommended for first login)")
    parser.add_argument("--list-services", action="store_true", help="List supported services")
    args = parser.parse_args()

    from nlp2cmd.automation.env_extractor import EnvExtractor, KNOWN_SERVICES

    if args.list_services:
        print("Supported services:")
        for name, config in KNOWN_SERVICES.items():
            print(f"  {name:15s} → {config.env_var:25s} ({config.url})")
        return

    extractor = EnvExtractor()
    print(f"Extracting API key from: {args.service}")
    print(f"Target .env file: {args.env_path}")
    print()

    result = await extractor.extract_and_save(
        service=args.service,
        env_path=args.env_path,
        headless=args.headless,
    )

    if result.get("needs_login"):
        print(f"⚠️  Login required: {result.get('instructions', '')}")

    if result["success"]:
        print(f"✅ Success!")
        print(f"   Key: {result.get('key_masked', '***')}")
        print(f"   Var: {result.get('env_var', '?')}")
        print(f"   File: {result.get('env_path', '?')}")
    else:
        print(f"❌ Failed: {result.get('error', 'unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
