#!/usr/bin/env python3
"""
Example 05: OpenAI API Key

Automatyczne pobranie klucza API z OpenAI i zapis do .env.
Wymaga: konto OpenAI z zapisanym hasłem w Firefox.

Użycie:
    python run.py --check
    python run.py --dry-run
    python run.py --execute

    # CLI equivalent:
    nlp2cmd -r "wyciągnij klucz API z OpenAI i zapisz do .env"
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

SERVICE = "openai"
ENV_VAR = "OPENAI_API_KEY"
KEYS_URL = "https://platform.openai.com/api-keys"


def check():
    from nlp2cmd.automation.password_store import get_password_store
    store = get_password_store()
    cred = store.get_credentials(SERVICE)
    api_key = os.environ.get(ENV_VAR, "")

    print("=== OpenAI API Key Check ===\n")
    if api_key:
        prefix = api_key[:10] + "..." if len(api_key) > 10 else api_key
        print(f"  ✓ API key: ${ENV_VAR} = {prefix} ({len(api_key)} znaków)")
    else:
        print(f"  ✗ API key: ${ENV_VAR} nie ustawiony")

    if cred and cred.password:
        print(f"  ✓ Login: {cred.username} (via {cred.source})")
        print(f"    → Możliwy auto-login na {KEYS_URL}")
    else:
        print(f"  ✗ Brak hasła OpenAI w Firefox")

    if not api_key and cred and cred.password:
        print(f"\n  Sugerowana komenda:")
        print(f'    nlp2cmd -r "wyciągnij klucz API z OpenAI i zapisz do .env"')


def run_flow(dry_run: bool):
    from nlp2cmd.generation.pipeline import RuleBasedPipeline
    pipeline = RuleBasedPipeline()
    query = "wyciągnij klucz API z OpenAI i zapisz do .env"

    result = pipeline.process(query)
    print(f"Domain: {result.domain} | Intent: {result.intent} | Confidence: {result.confidence:.0%}")

    if result.domain == "multi_step" and result.action_plan:
        plan = result.action_plan
        print(f"\nPlan ({len(plan.steps)} kroków):")
        for i, step in enumerate(plan.steps, 1):
            print(f"  {i}. [{step.action}] {step.description or step.action}")

        if not dry_run:
            from nlp2cmd.pipeline_runner import PipelineRunner
            runner = PipelineRunner(headless=False)
            res = runner.execute_action_plan(plan, dry_run=False, confirm=True)
            print(f"\nWynik: {'✓' if res.success else '✗'}")
        else:
            print("\n[dry-run] Użyj --execute aby uruchomić.")
    else:
        print(f"Komenda: {result.command}")


def main():
    parser = argparse.ArgumentParser(description="OpenAI API key management")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    if args.check:
        check()
    else:
        run_flow(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
