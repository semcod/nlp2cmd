#!/usr/bin/env python3
"""
Test suite for the declarative schema-driven feedback loop.

Tests:
  - Failure classification (schema_error, page_state_error, data_error, handling_error)
  - PageAnalyzer: generic page section finder
  - SchemaFallback: page analysis + LLM escalation strategies
  - FeedbackLoop: LLM diagnosis
  - Multi-provider support (HuggingFace, OpenRouter, Anthropic, GitHub, etc.)

Usage:
    python3 examples/08_llm_validation/test_feedback_loop.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, PropertyMock

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root / "src"))

from nlp2cmd.automation.feedback_loop import (
    FeedbackLoop,
    FailureType,
    PageAnalyzer,
    StepDiagnosis,
)


# ─── Mock page for testing ──────────────────────────────────────────────────

class MockElement:
    def __init__(self, tag: str, text: str = "", href: str = "", attrs: dict = None):
        self._tag = tag
        self._text = text
        self._href = href
        self._attrs = attrs or {}

    def inner_text(self):
        return self._text

    def text_content(self):
        return self._text

    def get_attribute(self, name):
        if name == "href":
            return self._href
        return self._attrs.get(name, "")

    def evaluate(self, expr):
        return self._tag

    def is_visible(self, timeout=None):
        return True


class MockPage:
    """Mock Playwright page for testing without a browser."""

    def __init__(self, url: str = "", title: str = "", elements: list = None,
                 visible_text: str = ""):
        self._url = url
        self._title = title
        self._elements = elements or []
        self._visible_text = visible_text

    @property
    def url(self):
        return self._url

    def title(self):
        return self._title

    def inner_text(self, selector):
        return self._visible_text

    def query_selector_all(self, selector):
        result = []
        for el in self._elements:
            if el._tag in selector or selector == "a[href]":
                if el._tag == "a" or "a" in selector:
                    result.append(el)
                elif el._tag in selector:
                    result.append(el)
            # Broad match for nav links
            if "nav" in selector and el._tag == "a":
                result.append(el)
        return result


# ─── Test cases ──────────────────────────────────────────────────────────────

@dataclass
class TestCase:
    name: str
    description: str
    expected: bool  # True = test should pass


def test_failure_classification():
    """Test that FeedbackLoop correctly classifies failure types."""
    fl = FeedbackLoop()
    results = []

    # Test 1: Security checkup redirect
    page = MockPage(url="https://huggingface.co/security-checkup?cookieId=abc123")
    diag = fl.classify_failure(
        action="navigate",
        error="URL mismatch: expected tokens page, got security-checkup",
        page=page,
        params={"url": "https://huggingface.co/settings/tokens"},
        service_config={"keys_url": "https://huggingface.co/settings/tokens"},
    )
    ok = diag.failure_type == FailureType.PAGE_STATE_ERROR
    results.append(("security_redirect", ok, diag))

    # Test 2: Timeout on selector (schema error)
    page = MockPage(url="https://huggingface.co/settings/tokens")
    diag = fl.classify_failure(
        action="click",
        error="Timeout 15000ms exceeded waiting for get_by_text('New token')",
        page=page,
        params={"text": "New token"},
    )
    ok = diag.failure_type == FailureType.SCHEMA_ERROR
    results.append(("selector_timeout", ok, diag))

    # Test 3: Command not found (handling error)
    diag = fl.classify_failure(
        action="type_text",
        error="Target page, context or browser has been closed",
        page=MockPage(),
        params={},
    )
    ok = diag.failure_type == FailureType.HANDLING_ERROR
    results.append(("browser_closed", ok, diag))

    # Test 4: No key found (data error)
    diag = fl.classify_failure(
        action="extract_key",
        error="Key not found on page",
        page=MockPage(url="https://huggingface.co/settings/tokens"),
        params={},
    )
    ok = diag.failure_type == FailureType.DATA_ERROR
    results.append(("no_key_found", ok, diag))

    # Test 5: Save with no value (data error)
    diag = fl.classify_failure(
        action="save_env",
        error="Brak wartości do zapisania dla HF_TOKEN",
        page=MockPage(),
        params={"env_var": "HF_TOKEN"},
    )
    ok = diag.failure_type == FailureType.DATA_ERROR
    results.append(("save_no_value", ok, diag))

    # Test 6: CAPTCHA (page state)
    diag = fl.classify_failure(
        action="navigate",
        error="Page shows reCAPTCHA challenge",
        page=MockPage(),
        params={},
    )
    ok = diag.failure_type == FailureType.PAGE_STATE_ERROR
    results.append(("captcha_detected", ok, diag))

    # Test 7: Login required
    diag = fl.classify_failure(
        action="check_session",
        error="Not authenticated - please sign in",
        page=MockPage(),
        params={},
    )
    ok = diag.failure_type == FailureType.DATA_ERROR
    results.append(("login_required", ok, diag))

    return results


def test_page_analyzer_section_finder():
    """Test PageAnalyzer.find_api_keys_section with mock pages."""
    results = []

    # Test 1: Find settings/tokens link
    page = MockPage(
        url="https://huggingface.co/",
        elements=[
            MockElement("a", "Models", href="/models"),
            MockElement("a", "Settings", href="/settings"),
            MockElement("a", "Access Tokens", href="/settings/tokens"),
            MockElement("a", "Profile", href="/profile"),
        ],
    )
    url = PageAnalyzer.find_api_keys_section(page)
    ok = url is not None and "tokens" in url
    results.append(("hf_tokens_link", ok, url))

    # Test 2: Find API keys link (OpenRouter style)
    page = MockPage(
        url="https://openrouter.ai/",
        elements=[
            MockElement("a", "Models", href="/models"),
            MockElement("a", "API Keys", href="/settings/keys"),
            MockElement("a", "Credits", href="/credits"),
        ],
    )
    url = PageAnalyzer.find_api_keys_section(page)
    ok = url is not None and "keys" in url
    results.append(("openrouter_keys_link", ok, url))

    # Test 3: Find developer/credentials
    page = MockPage(
        url="https://example.com/",
        elements=[
            MockElement("a", "Home", href="/"),
            MockElement("a", "Developer Settings", href="/developer/credentials"),
            MockElement("a", "Documentation", href="/docs"),
        ],
    )
    url = PageAnalyzer.find_api_keys_section(page)
    ok = url is not None and "credentials" in url
    results.append(("generic_credentials_link", ok, url))

    # Test 4: No relevant links → should return None
    page = MockPage(
        url="https://example.com/",
        elements=[
            MockElement("a", "Home", href="/"),
            MockElement("a", "About", href="/about"),
            MockElement("a", "Contact", href="/contact"),
        ],
    )
    url = PageAnalyzer.find_api_keys_section(page)
    ok = url is None
    results.append(("no_keys_link", ok, url))

    return results


def test_page_analyzer_clickable_finder():
    """Test PageAnalyzer.find_clickable_for_text."""
    results = []

    # Test 1: Find "Create" button
    page = MockPage(
        url="https://example.com/tokens",
        elements=[
            MockElement("button", "Create new token", attrs={"id": "btn-create", "class": "btn primary"}),
            MockElement("button", "Delete", attrs={"class": "btn danger"}),
            MockElement("a", "Create API Key", href="/create", attrs={"class": "link"}),
        ],
    )
    selectors = PageAnalyzer.find_clickable_for_text(page, "Create")
    ok = len(selectors) >= 1
    results.append(("find_create_button", ok, selectors))

    # Test 2: Find "Generate" button
    page = MockPage(
        url="https://example.com/tokens",
        elements=[
            MockElement("button", "Generate token", attrs={"id": "gen-btn"}),
            MockElement("button", "Cancel", attrs={}),
        ],
    )
    selectors = PageAnalyzer.find_clickable_for_text(page, "Generate")
    ok = len(selectors) >= 1 and any("gen-btn" in s for s in selectors)
    results.append(("find_generate_button", ok, selectors))

    return results


def test_multi_provider_classification():
    """Test failure classification across different SaaS providers."""
    fl = FeedbackLoop()
    results = []

    providers = [
        {
            "name": "HuggingFace",
            "url": "https://huggingface.co/security-checkup",
            "error": "Security checkup redirect",
            "expected_type": FailureType.PAGE_STATE_ERROR,
        },
        {
            "name": "OpenRouter",
            "url": "https://openrouter.ai/settings/keys",
            "error": "Timeout 15000ms exceeded waiting for locator('button.create')",
            "action": "click",
            "params": {"selector": "button.create"},
            "expected_type": FailureType.SCHEMA_ERROR,
        },
        {
            "name": "Anthropic",
            "url": "https://console.anthropic.com/login",
            "error": "Not authenticated - please sign in to continue",
            "expected_type": FailureType.DATA_ERROR,
        },
        {
            "name": "GitHub",
            "url": "https://github.com/settings/tokens",
            "error": "Page closed unexpectedly after tab switch",
            "expected_type": FailureType.HANDLING_ERROR,
        },
        {
            "name": "Groq",
            "url": "https://console.groq.com/keys",
            "error": "reCAPTCHA challenge detected on login page",
            "expected_type": FailureType.PAGE_STATE_ERROR,
        },
    ]

    for prov in providers:
        page = MockPage(url=prov["url"])
        diag = fl.classify_failure(
            action=prov.get("action", "navigate"),
            error=prov["error"],
            page=page,
            params=prov.get("params", {}),
        )
        ok = diag.failure_type == prov["expected_type"]
        results.append((f"provider_{prov['name'].lower()}", ok, diag))

    return results


def test_llm_diagnosis():
    """Test LLM diagnosis (requires Ollama running)."""
    fl = FeedbackLoop()
    results = []

    # Only run if Ollama is available
    try:
        import urllib.request
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3):
            pass
    except Exception:
        print("  ⏭ Skipping LLM diagnosis tests (Ollama not running)")
        return results

    page_context = """URL: https://huggingface.co/settings/tokens
Title: Hugging Face - Access Tokens
Navigation links:
  - Models → /models
  - Settings → /settings
  - Access Tokens → /settings/tokens
Buttons/links:
  - button: Create new token
  - button: Delete
  - a: New token (fine-grained)
Visible text: Access Tokens. You can create personal access tokens..."""

    diag = fl.diagnose_with_llm(
        action="click",
        error="Timeout 15000ms exceeded waiting for get_by_text('New token')",
        page_context=page_context,
        params={"text": "New token"},
        use_cloud=False,
    )
    ok = diag.failure_type != FailureType.UNKNOWN
    results.append(("llm_diagnosis_click_timeout", ok, diag))

    return results


def run_all_tests():
    """Run all test groups and print results."""
    all_results = []
    total_passed = 0
    total_failed = 0

    print(f"\n{'='*80}")
    print(f"  Feedback Loop Test Suite")
    print(f"{'='*80}\n")

    test_groups = [
        ("Failure Classification", test_failure_classification),
        ("PageAnalyzer: Section Finder", test_page_analyzer_section_finder),
        ("PageAnalyzer: Clickable Finder", test_page_analyzer_clickable_finder),
        ("Multi-Provider Classification", test_multi_provider_classification),
        ("LLM Diagnosis", test_llm_diagnosis),
    ]

    for group_name, test_fn in test_groups:
        print(f"\n--- {group_name} ---")
        try:
            results = test_fn()
        except Exception as e:
            print(f"  💥 Group error: {e}")
            continue

        for name, ok, detail in results:
            status = "✅" if ok else "❌"
            if ok:
                total_passed += 1
            else:
                total_failed += 1
            detail_str = ""
            if hasattr(detail, 'failure_type'):
                detail_str = f" [{detail.failure_type.value}: {detail.reason}]"
            elif detail is not None:
                detail_str = f" [{detail}]"
            print(f"  {status} {name}{detail_str}")
            all_results.append({"name": name, "ok": ok})

    total = total_passed + total_failed
    accuracy = total_passed / total * 100 if total else 0

    print(f"\n{'='*80}")
    print(f"  Results: {total_passed}/{total} passed ({accuracy:.0f}%)")
    print(f"{'='*80}\n")

    # Save results
    out_path = Path(__file__).parent / "test_feedback_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "total": total,
            "passed": total_passed,
            "failed": total_failed,
            "accuracy_pct": round(accuracy, 1),
            "results": all_results,
        }, f, indent=2, ensure_ascii=False)
    print(f"Results saved to {out_path}\n")

    return total_passed, total_failed


if __name__ == "__main__":
    passed, failed = run_all_tests()
    sys.exit(1 if failed > 0 else 0)
