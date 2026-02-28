#!/usr/bin/env python3
"""
Example 03: GitHub Personal Access Token

Automatyczne tworzenie GitHub PAT (Personal Access Token) i zapis do .env.
Wymaga: konto GitHub z zapisanym hasłem w Firefox.

Zadania:
- Sprawdź czy masz klucz GITHUB_TOKEN
- Zaloguj się na github.com/settings/tokens
- Stwórz nowy token z nazwą "nlp2cmd"
- Zapisz do .env jako GITHUB_TOKEN

Użycie:
    python run.py --check
    python run.py --dry-run
    python run.py --execute

    # CLI equivalent:
    nlp2cmd -r "wyciągnij token z GitHub i zapisz do .env"
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

SERVICE = "github"
ENV_VAR = "GITHUB_TOKEN"
KEYS_URL = "https://github.com/settings/tokens"


def check():
    from nlp2cmd.automation.password_store import get_password_store
    store = get_password_store()
    cred = store.get_credentials(SERVICE)
    api_key = os.environ.get(ENV_VAR, "")

    print("=== GitHub Token Check ===\n")
    if api_key:
        prefix = api_key[:10] + "..." if len(api_key) > 10 else api_key
        print(f"  ✓ Token: ${ENV_VAR} = {prefix} ({len(api_key)} znaków)")
    else:
        print(f"  ✗ Token: ${ENV_VAR} nie ustawiony")

    if cred and cred.password:
        print(f"  ✓ Login: {cred.username} (via {cred.source})")
        print(f"    → Możliwy auto-login na {KEYS_URL}")
    else:
        print(f"  ✗ Brak hasła GitHub w Firefox")
        print(f"    → Zaloguj się na github.com w Firefox")

    if not api_key and cred and cred.password:
        print(f"\n  Sugerowana komenda:")
        print(f'    nlp2cmd -r "otwórz github.com/settings/tokens, stwórz token i zapisz do .env"')


def run_flow(dry_run: bool):
    from nlp2cmd.generation.pipeline import RuleBasedPipeline

    pipeline = RuleBasedPipeline()
    query = "otwórz github.com, przejdź do settings/tokens, stwórz nowy Personal Access Token i zapisz do .env"

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
            print(f"\n[dry-run] Użyj --execute aby uruchomić.")
    else:
        print(f"Komenda: {result.command}")


def main():
    parser = argparse.ArgumentParser(description="GitHub token management")
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
