#!/usr/bin/env python3
"""
Example 04: HuggingFace Token

Automatyczne pobranie HF Token i zapis do .env.
HuggingFace wymaga sesji Firefox (cookies injection) z powodu security-checkup.

Zadania:
- Sprawdź czy masz HF_TOKEN
- Zaloguj się na huggingface.co/settings/tokens
- Stwórz nowy token (Write access)
- Zapisz do .env jako HF_TOKEN

Użycie:
    python run.py --check
    python run.py --dry-run

    # Z cookies z Firefox (zalecane dla HuggingFace):
    NLP2CMD_USE_FIREFOX_SESSIONS=1 python run.py --execute

    # CLI equivalent:
    NLP2CMD_USE_FIREFOX_SESSIONS=1 nlp2cmd -r "wyciągnij token z HuggingFace i zapisz do .env"
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

SERVICE = "huggingface"
ENV_VAR = "HF_TOKEN"
KEYS_URL = "https://huggingface.co/settings/tokens"


def check():
    from nlp2cmd.automation.password_store import get_password_store
    store = get_password_store()
    cred = store.get_credentials(SERVICE)
    token = os.environ.get(ENV_VAR, "")

    print("=== HuggingFace Token Check ===\n")
    if token:
        prefix = token[:10] + "..." if len(token) > 10 else token
        print(f"  ✓ Token: ${ENV_VAR} = {prefix} ({len(token)} znaków)")
    else:
        print(f"  ✗ Token: ${ENV_VAR} nie ustawiony")

    if cred and cred.password:
        print(f"  ✓ Login: {cred.username} (via {cred.source})")
    else:
        print(f"  ✗ Brak hasła HuggingFace w Firefox")

    ff_sessions = os.environ.get("NLP2CMD_USE_FIREFOX_SESSIONS", "")
    if ff_sessions:
        print(f"  ✓ Firefox sessions: włączone ({ff_sessions})")
    else:
        print(f"  ⚠ Firefox sessions: wyłączone")
        print(f"    HuggingFace wymaga cookies — ustaw NLP2CMD_USE_FIREFOX_SESSIONS=1")

    if not token:
        print(f"\n  Sugerowana komenda:")
        print(f'    NLP2CMD_USE_FIREFOX_SESSIONS=1 nlp2cmd -r "wyciągnij token z HuggingFace i zapisz do .env"')


def run_flow(dry_run: bool):
    from nlp2cmd.generation.pipeline import RuleBasedPipeline

    pipeline = RuleBasedPipeline()
    query = "wyciągnij token z HuggingFace i zapisz do .env"

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
    parser = argparse.ArgumentParser(description="HuggingFace token management")
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
