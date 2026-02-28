#!/usr/bin/env python3
"""
Example prompts for API key generation workflows across multiple LLM providers.

Tests the enhanced ActionPlanner with:
- Multi-provider support (OpenRouter, Anthropic, OpenAI, Groq, Mistral, etc.)
- Session detection (logged in vs login page)
- Create-new-key form filling
- Email client fallback (Roundcube, Thunderbird)
- Verbose logging throughout

Usage:
    python -m examples.04_domain_specific.api_key_prompts
    python -m examples.04_domain_specific.api_key_prompts --provider openrouter
    python -m examples.04_domain_specific.api_key_prompts --test
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PromptExample:
    """Single prompt example with expected behavior."""
    query: str
    provider: str
    expected_actions: list[str] = field(default_factory=list)
    expects_create: bool = False
    expects_firefox: bool = False
    expects_save: bool = False
    description: str = ""
    language: str = "pl"  # pl or en


# ---------------------------------------------------------------------------
# OpenRouter prompts
# ---------------------------------------------------------------------------
OPENROUTER_PROMPTS = [
    PromptExample(
        query="otwórz tab w już otwartym oknie przeglądarki firefox wyciągnij klucz API z OpenRouter i zapisz do .env",
        provider="openrouter",
        expected_actions=["echo", "open_firefox_tab", "desktop_wait", "check_session", "echo", "echo", "prompt_secret", "save_env", "echo"],
        expects_firefox=True,
        expects_save=True,
        description="Pobierz klucz z OpenRouter przez istniejący Firefox",
    ),
    PromptExample(
        query="stwórz nowy klucz API na OpenRouter i zapisz do .env",
        provider="openrouter",
        expected_actions=["echo", "navigate", "echo", "check_session", "echo", "echo", "click", "wait", "type_text", "click", "wait", "screenshot", "echo", "prompt_secret", "save_env", "echo"],
        expects_create=True,
        expects_save=True,
        description="Utwórz nowy klucz API na OpenRouter",
    ),
    PromptExample(
        query="get OpenRouter API key",
        provider="openrouter",
        expected_actions=["echo", "navigate", "echo", "check_session", "echo", "echo", "prompt_secret"],
        description="Get OpenRouter key (English)",
        language="en",
    ),
]

# ---------------------------------------------------------------------------
# Anthropic prompts
# ---------------------------------------------------------------------------
ANTHROPIC_PROMPTS = [
    PromptExample(
        query="pobierz klucz API z Anthropic i zapisz do .env",
        provider="anthropic",
        expected_actions=["echo", "navigate", "echo", "check_session", "echo", "echo", "prompt_secret", "save_env", "echo"],
        expects_save=True,
        description="Pobierz klucz Anthropic",
    ),
    PromptExample(
        query="wygeneruj nowy klucz API Claude i zapisz",
        provider="anthropic",
        expected_actions=["echo", "navigate", "echo", "check_session", "echo", "echo", "click", "wait", "type_text", "click", "wait", "screenshot", "echo", "prompt_secret", "save_env", "echo"],
        expects_create=True,
        expects_save=True,
        description="Utwórz nowy klucz Claude/Anthropic",
    ),
]

# ---------------------------------------------------------------------------
# OpenAI prompts
# ---------------------------------------------------------------------------
OPENAI_PROMPTS = [
    PromptExample(
        query="otwórz OpenAI i pobierz klucz API, zapisz do .env",
        provider="openai",
        expects_save=True,
        description="Pobierz klucz OpenAI",
    ),
    PromptExample(
        query="create new OpenAI API key and save to .env",
        provider="openai",
        expects_create=True,
        expects_save=True,
        description="Create new OpenAI key (English)",
        language="en",
    ),
]

# ---------------------------------------------------------------------------
# Groq prompts
# ---------------------------------------------------------------------------
GROQ_PROMPTS = [
    PromptExample(
        query="pobierz klucz API z Groq i zapisz do .env",
        provider="groq",
        expects_save=True,
        description="Pobierz klucz Groq",
    ),
    PromptExample(
        query="stwórz nowy klucz API na Groq",
        provider="groq",
        expects_create=True,
        description="Utwórz nowy klucz Groq",
    ),
]

# ---------------------------------------------------------------------------
# Mistral prompts
# ---------------------------------------------------------------------------
MISTRAL_PROMPTS = [
    PromptExample(
        query="wyciągnij klucz API Mistral i zapisz do .env",
        provider="mistral",
        expects_save=True,
        description="Pobierz klucz Mistral",
    ),
]

# ---------------------------------------------------------------------------
# DeepSeek prompts
# ---------------------------------------------------------------------------
DEEPSEEK_PROMPTS = [
    PromptExample(
        query="pobierz klucz API z DeepSeek i zapisz do .env",
        provider="deepseek",
        expects_save=True,
        description="Pobierz klucz DeepSeek",
    ),
]

# ---------------------------------------------------------------------------
# Together.ai prompts
# ---------------------------------------------------------------------------
TOGETHER_PROMPTS = [
    PromptExample(
        query="pobierz klucz API z Together.ai i zapisz",
        provider="together",
        expects_save=True,
        description="Pobierz klucz Together.ai",
    ),
]

# ---------------------------------------------------------------------------
# GitHub prompts
# ---------------------------------------------------------------------------
GITHUB_PROMPTS = [
    PromptExample(
        query="wygeneruj nowy token GitHub i zapisz do .env",
        provider="github",
        expects_create=True,
        expects_save=True,
        description="Utwórz nowy token GitHub",
    ),
]

# ---------------------------------------------------------------------------
# HuggingFace prompts
# ---------------------------------------------------------------------------
HUGGINGFACE_PROMPTS = [
    PromptExample(
        query="pobierz token z HuggingFace i zapisz do .env",
        provider="huggingface",
        expects_save=True,
        description="Pobierz token HuggingFace",
    ),
]

# ---------------------------------------------------------------------------
# Multi-provider / complex prompts
# ---------------------------------------------------------------------------
COMPLEX_PROMPTS = [
    PromptExample(
        query="otwórz tab w już otwartym Firefox, przejdź na OpenRouter, stwórz nowy klucz API i zapisz do .env",
        provider="openrouter",
        expects_firefox=False,  # v1.0.91: forced to Playwright path (navigate, not open_firefox_tab)
        expects_create=True,
        expects_save=True,
        description="Firefox + create + save (full flow)",
    ),
    PromptExample(
        query="otwórz przeglądarkę i stronę openrouter.ai, wyciągnij klucz API i zapisz do pliku .env",
        provider="openrouter",
        expects_save=True,
        description="Browser + extract + save (classic)",
    ),
]

# ---------------------------------------------------------------------------
# All prompts
# ---------------------------------------------------------------------------
ALL_PROMPTS = (
    OPENROUTER_PROMPTS
    + ANTHROPIC_PROMPTS
    + OPENAI_PROMPTS
    + GROQ_PROMPTS
    + MISTRAL_PROMPTS
    + DEEPSEEK_PROMPTS
    + TOGETHER_PROMPTS
    + GITHUB_PROMPTS
    + HUGGINGFACE_PROMPTS
    + COMPLEX_PROMPTS
)

PROVIDER_PROMPTS = {
    "openrouter": OPENROUTER_PROMPTS,
    "anthropic": ANTHROPIC_PROMPTS,
    "openai": OPENAI_PROMPTS,
    "groq": GROQ_PROMPTS,
    "mistral": MISTRAL_PROMPTS,
    "deepseek": DEEPSEEK_PROMPTS,
    "together": TOGETHER_PROMPTS,
    "github": GITHUB_PROMPTS,
    "huggingface": HUGGINGFACE_PROMPTS,
}


def test_prompt(example: PromptExample, verbose: bool = True) -> dict:
    """Test a single prompt against ActionPlanner (dry-run, no browser)."""
    from nlp2cmd.automation.action_planner import ActionPlanner

    planner = ActionPlanner()
    plan = planner.decompose_sync(example.query)

    actions = [s.action for s in plan.steps]
    result = {
        "query": example.query,
        "provider": example.provider,
        "description": example.description,
        "plan_source": plan.source,
        "confidence": plan.confidence,
        "steps_count": len(plan.steps),
        "actions": actions,
    }

    # Validate expectations
    errors = []

    if example.expects_create:
        if "click" not in actions:
            errors.append("Expected 'click' action for create-key flow")
    if example.expects_save:
        if "save_env" not in actions:
            errors.append("Expected 'save_env' action")
    if example.expects_firefox:
        if "open_firefox_tab" not in actions:
            errors.append("Expected 'open_firefox_tab' action")

    # Check that service was resolved
    if plan.source == "heuristic":
        errors.append(f"Plan fell to heuristic (service '{example.provider}' not resolved)")

    result["errors"] = errors
    result["passed"] = len(errors) == 0

    if verbose:
        status = "✅" if result["passed"] else "❌"
        print(f"\n{status} [{example.provider}] {example.description}")
        print(f"   Query: {example.query[:80]}...")
        print(f"   Source: {plan.source} | Confidence: {plan.confidence:.0%} | Steps: {len(plan.steps)}")
        if verbose:
            for i, step in enumerate(plan.steps, 1):
                print(f"   {i:2d}. [{step.action}] {step.description}")
        if errors:
            for err in errors:
                print(f"   ⚠ {err}")

    return result


def run_all_tests(provider: Optional[str] = None, verbose: bool = True) -> dict:
    """Run all prompt tests and return summary."""
    prompts = PROVIDER_PROMPTS.get(provider, ALL_PROMPTS) if provider else ALL_PROMPTS

    print(f"{'='*80}")
    print(f"API Key Prompt Tests — {len(prompts)} prompts")
    if provider:
        print(f"Provider filter: {provider}")
    print(f"{'='*80}")

    results = []
    for example in prompts:
        result = test_prompt(example, verbose=verbose)
        results.append(result)

    passed = sum(1 for r in results if r["passed"])
    failed = sum(1 for r in results if not r["passed"])

    print(f"\n{'='*80}")
    print(f"WYNIKI: {passed}/{len(results)} passed, {failed} failed")

    if failed > 0:
        print(f"\nFailed prompts:")
        for r in results:
            if not r["passed"]:
                print(f"  ❌ [{r['provider']}] {r['description']}")
                for err in r["errors"]:
                    print(f"     ⚠ {err}")

    print(f"{'='*80}")

    return {
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "results": results,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="API Key Prompt Tests")
    parser.add_argument("--provider", "-p", help="Test specific provider")
    parser.add_argument("--test", "-t", action="store_true", help="Run all tests")
    parser.add_argument("--quiet", "-q", action="store_true", help="Minimal output")

    args = parser.parse_args()

    summary = run_all_tests(
        provider=args.provider,
        verbose=not args.quiet,
    )

    sys.exit(0 if summary["failed"] == 0 else 1)
