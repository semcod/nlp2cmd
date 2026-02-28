#!/usr/bin/env python3
"""
Example 06: Multi-Provider Setup

Batch setup kluczy API dla wielu providerów naraz.
Sprawdza które serwisy mają dane logowania, generuje plany dla każdego,
i wykonuje je sekwencyjnie.

Użycie:
    # Pokaż co jest dostępne
    python run.py --scan

    # Dry-run dla wszystkich dostępnych providerów
    python run.py --plan

    # Wykonaj setup dla konkretnych providerów
    python run.py --setup openrouter github

    # Wykonaj dla wszystkich z hasłami w Firefox
    python run.py --setup-all
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))


def scan():
    """Pokaż tabelę dostępności credentials."""
    from nlp2cmd.automation.password_store import get_password_store
    store = get_password_store()
    store.print_diagnosis(verbose=True)


def plan_all():
    """Wygeneruj plany dla providerów z hasłami ale bez kluczy API."""
    from nlp2cmd.automation.password_store import get_password_store
    from nlp2cmd.generation.pipeline import RuleBasedPipeline

    store = get_password_store()
    results = store.diagnose_providers()
    pipeline = RuleBasedPipeline()

    # Providerzy z loginami ale bez klucza API
    actionable = [r for r in results if r["has_login"] and not r["has_api_key"]]

    if not actionable:
        print("Wszystkie providerzy z hasłami mają już klucze API ✓")
        print("Lub brak haseł — uruchom --scan aby zobaczyć status.")
        return

    print(f"=== Plany dla {len(actionable)} providerów ===\n")
    for r in actionable:
        svc = r["service"]
        query = f"wyciągnij klucz API z {svc} i zapisz do .env"
        result = pipeline.process(query)

        print(f"--- {svc} ---")
        print(f"  Query: {query}")
        print(f"  Domain: {result.domain} | Confidence: {result.confidence:.0%}")

        if result.domain == "multi_step" and result.action_plan:
            for i, step in enumerate(result.action_plan.steps, 1):
                print(f"  {i}. [{step.action}] {step.description or step.action}")
        else:
            print(f"  Komenda: {result.command}")
        print()


def setup_providers(providers: list[str]):
    """Wykonaj setup dla wybranych providerów."""
    from nlp2cmd.automation.password_store import get_password_store
    from nlp2cmd.generation.pipeline import RuleBasedPipeline
    from nlp2cmd.pipeline_runner import PipelineRunner

    store = get_password_store()
    pipeline = RuleBasedPipeline()
    runner = PipelineRunner(headless=False)

    for svc in providers:
        cred = store.get_credentials(svc)
        env_var_map = {
            "openrouter": "OPENROUTER_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "github": "GITHUB_TOKEN",
            "huggingface": "HF_TOKEN",
            "groq": "GROQ_API_KEY",
            "mistral": "MISTRAL_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
            "together": "TOGETHER_API_KEY",
            "replicate": "REPLICATE_API_TOKEN",
        }
        env_var = env_var_map.get(svc, f"{svc.upper()}_API_KEY")

        # Skip if already have key
        if os.environ.get(env_var, ""):
            print(f"\n✓ {svc}: ${env_var} już ustawiony — pomijam")
            continue

        if not cred or not cred.password:
            print(f"\n✗ {svc}: brak danych logowania — pomijam")
            continue

        print(f"\n{'='*50}")
        print(f"▸ {svc}: Pobieram klucz API...")
        print(f"  Login: {cred.username} (via {cred.source})")
        print(f"{'='*50}")

        query = f"wyciągnij klucz API z {svc} i zapisz do .env"
        result = pipeline.process(query)

        if result.domain == "multi_step" and result.action_plan:
            runner_result = runner.execute_action_plan(
                result.action_plan, dry_run=False, confirm=True,
            )
            if runner_result.success:
                print(f"✓ {svc}: klucz zapisany do .env")
            else:
                print(f"✗ {svc}: błąd — {runner_result.error}")
        else:
            print(f"? {svc}: nie wygenerowano planu multi-step")


def setup_all():
    """Setup dla wszystkich providerów z hasłami ale bez kluczy."""
    from nlp2cmd.automation.password_store import get_password_store

    store = get_password_store()
    results = store.diagnose_providers()
    actionable = [r["service"] for r in results if r["has_login"] and not r["has_api_key"]]

    if not actionable:
        print("Brak providerów do skonfigurowania.")
        print("Wszystkie z hasłami mają już klucze, lub brak haseł.")
        return

    print(f"Providerzy do skonfigurowania: {', '.join(actionable)}")
    setup_providers(actionable)


def main():
    parser = argparse.ArgumentParser(description="Multi-provider API key setup")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--scan", action="store_true", help="Pokaż status credentials")
    group.add_argument("--plan", action="store_true", help="Pokaż plany (dry-run)")
    group.add_argument("--setup", nargs="+", metavar="PROVIDER", help="Setup konkretnych providerów")
    group.add_argument("--setup-all", action="store_true", help="Setup wszystkich z hasłami")
    args = parser.parse_args()

    if args.scan:
        scan()
    elif args.plan:
        plan_all()
    elif args.setup:
        setup_providers(args.setup)
    elif args.setup_all:
        setup_all()


if __name__ == "__main__":
    main()
