#!/usr/bin/env python3
"""
Example 02: OpenRouter API Key

Automatyczne pobranie klucza API z OpenRouter.ai i zapis do .env.
Wymaga: konto OpenRouter z zapisanym hasłem w Firefox lub .env.

Scenariusze:
1. Klucz już istnieje w .env → weryfikacja
2. Login w Firefox → auto-login → stwórz klucz → zapisz
3. Brak danych → instrukcje ręczne

Użycie:
    # Sprawdź czy masz dane do OpenRouter
    python run.py --check

    # Pobierz klucz (dry-run — pokazuje plan bez wykonania)
    python run.py --dry-run

    # Wykonaj pełny flow
    python run.py --execute

    # Z użyciem sesji Firefox (cookies injection)
    NLP2CMD_USE_FIREFOX_SESSIONS=1 python run.py --execute
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

SERVICE = "openrouter"
ENV_VAR = "OPENROUTER_API_KEY"
KEYS_URL = "https://openrouter.ai/settings/keys"


def check_credentials():
    """Sprawdź dostępność danych logowania."""
    from nlp2cmd.automation.password_store import get_password_store

    store = get_password_store()
    cred = store.get_credentials(SERVICE)

    print(f"=== OpenRouter Credential Check ===\n")

    # API key
    api_key = os.environ.get(ENV_VAR, "")
    if api_key:
        print(f"  ✓ API key: ${ENV_VAR} ({len(api_key)} znaków)")
    else:
        print(f"  ✗ API key: ${ENV_VAR} nie ustawiony")

    # Login credentials
    if cred and cred.username and cred.password:
        print(f"  ✓ Login: {cred.username} (via {cred.source})")
        print(f"  → Możliwy auto-login i tworzenie klucza")
    elif cred and cred.username:
        print(f"  ½ Username: {cred.username} (brak hasła)")
    else:
        print(f"  ✗ Brak danych logowania w Firefox ani .env")
        print(f"  → Zaloguj się na {KEYS_URL} w Firefox")

    # .env file
    env_path = Path(".env")
    if env_path.exists() and ENV_VAR in env_path.read_text():
        print(f"  ✓ .env: {ENV_VAR} znaleziony w {env_path.resolve()}")
    else:
        print(f"  ✗ .env: {ENV_VAR} nie znaleziony")

    return bool(api_key or (cred and cred.password))


def run_flow(dry_run: bool = False):
    """Uruchom pełny flow pobierania klucza."""
    from nlp2cmd.generation.pipeline import RuleBasedPipeline

    pipeline = RuleBasedPipeline()
    query = "wyciągnij klucz API z OpenRouter i zapisz do .env"

    print(f"\n=== OpenRouter Key Flow ===")
    print(f"Query: {query}")
    print(f"Dry-run: {dry_run}\n")

    result = pipeline.process(query)
    print(f"Domain: {result.domain}")
    print(f"Intent: {result.intent}")
    print(f"Confidence: {result.confidence:.0%}")

    if result.domain == "multi_step" and result.action_plan:
        plan = result.action_plan
        print(f"\nPlan ({len(plan.steps)} kroków):")
        for i, step in enumerate(plan.steps, 1):
            print(f"  {i}. [{step.action}] {step.description or ''}")

        if not dry_run:
            from nlp2cmd.pipeline_runner import PipelineRunner
            runner = PipelineRunner(headless=False)
            runner_result = runner.execute_action_plan(plan, dry_run=False, confirm=True)
            print(f"\nWynik: {'✓ Sukces' if runner_result.success else '✗ Błąd'}")
        else:
            print(f"\n[dry-run] Plan wygenerowany, ale nie wykonany.")
            print(f"Uruchom z --execute aby wykonać.")
    else:
        print(f"\nKomenda: {result.command}")


def main():
    parser = argparse.ArgumentParser(description="OpenRouter API key management")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="Sprawdź dostępność danych")
    group.add_argument("--dry-run", action="store_true", help="Pokaż plan bez wykonania")
    group.add_argument("--execute", action="store_true", help="Wykonaj pełny flow")
    args = parser.parse_args()

    if args.check:
        check_credentials()
    elif args.dry_run:
        run_flow(dry_run=True)
    elif args.execute:
        run_flow(dry_run=False)


if __name__ == "__main__":
    main()
