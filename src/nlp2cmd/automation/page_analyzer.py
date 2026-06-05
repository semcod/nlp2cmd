# PageAnalyzer - extracted from feedback_loop.py
"""
Declarative Schema-Driven Feedback Loop for browser automation.

Core algorithm:
  1. Execute step
  2. Validate result (page state, DOM, expected outcome)
  3. Classify failure: schema_error | handling_error | data_error | page_state_error
  4. Repair: local LLM → cloud LLM escalation
  5. Retry with repaired step (max N attempts)
  6. A solution is ALWAYS found — it's a matter of time, not algorithm limits

The feedback loop wraps each ActionPlan step execution with:
  - Pre-validation (are we on the right page? correct state?)
  - Post-validation (did the action achieve its goal?)
  - Error classification (WHY did it fail?)
  - Repair escalation (local → cloud LLM)
  - Page analysis (find correct selectors/sections via LLM)

Environment:
    LLM_VALIDATOR_MODEL     — local Ollama model for step validation
    LLM_REPAIR_MODEL        — cloud model for repair escalation
    FEEDBACK_LOOP_MAX_RETRIES — max repair attempts per step (default: 5)
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

log = logging.getLogger("nlp2cmd.feedback_loop")
class PageAnalyzer:
    """Analyzes page DOM to find correct sections, selectors, and navigation targets.

    Uses LLM to interpret page structure when hardcoded selectors fail.
    This enables provider-agnostic operation — works on any SaaS site.
    """

    # Common patterns for API key pages across SaaS providers
    KEY_PAGE_INDICATORS = [
        "api key", "api token", "access token", "secret key",
        "generate token", "create token", "new token", "create key",
        "personal access token", "bearer token",
    ]

    NAV_LINK_PATTERNS = [
        r"settings",
        r"api[- ]?keys?",
        r"tokens?",
        r"access[- ]?tokens?",
        r"developer",
        r"credentials",
        r"security",
        r"account",
    ]

    @staticmethod
    def extract_page_context(page: Any, max_chars: int = 3000) -> str:
        """Extract minimal but informative page context for LLM analysis."""
        try:
            url = page.url or ""
            title = page.title() or ""

            # Get visible text (truncated)
            visible_text = page.inner_text("body")[:1500] if page else ""

            # Get key interactive elements
            buttons = []
            try:
                for btn in page.query_selector_all("button, a[href], input[type='submit']"):
                    text = (btn.inner_text() or "").strip()[:50]
                    href = btn.get_attribute("href") or ""
                    tag = btn.evaluate("el => el.tagName.toLowerCase()")
                    if text:
                        buttons.append(f"{tag}: {text}" + (f" ({href})" if href else ""))
                buttons = buttons[:20]
            except Exception:
                pass

            # Get input fields
            inputs = []
            try:
                for inp in page.query_selector_all("input, textarea, select"):
                    name = inp.get_attribute("name") or ""
                    type_ = inp.get_attribute("type") or "text"
                    placeholder = inp.get_attribute("placeholder") or ""
                    inputs.append(f"input[name={name}, type={type_}]"
                                  + (f" placeholder='{placeholder}'" if placeholder else ""))
                inputs = inputs[:15]
            except Exception:
                pass

            # Get nav links
            nav_links = []
            try:
                for link in page.query_selector_all("nav a, aside a, [role='navigation'] a"):
                    text = (link.inner_text() or "").strip()[:40]
                    href = link.get_attribute("href") or ""
                    if text and href:
                        nav_links.append(f"{text} → {href}")
                nav_links = nav_links[:15]
            except Exception:
                pass

            context = f"URL: {url}\nTitle: {title}\n"
            if nav_links:
                context += f"\nNavigation links:\n" + "\n".join(f"  - {l}" for l in nav_links)
            if buttons:
                context += f"\nButtons/links:\n" + "\n".join(f"  - {b}" for b in buttons)
            if inputs:
                context += f"\nInput fields:\n" + "\n".join(f"  - {i}" for i in inputs)
            context += f"\nVisible text (excerpt):\n{visible_text[:800]}"

            return context[:max_chars]

        except Exception as e:
            return f"Error extracting page context: {e}"

    @staticmethod
    def find_api_keys_section(page: Any) -> Optional[str]:
        """Find the API keys/tokens section URL by analyzing navigation links."""
        try:
            links = page.query_selector_all("a[href]")
            candidates = []
            for link in links:
                href = link.get_attribute("href") or ""
                text = (link.inner_text() or "").strip().lower()
                score = 0
                for pattern in PageAnalyzer.NAV_LINK_PATTERNS:
                    if re.search(pattern, href.lower()) or re.search(pattern, text):
                        score += 1
                for indicator in PageAnalyzer.KEY_PAGE_INDICATORS:
                    if indicator in text:
                        score += 2
                if score > 0:
                    candidates.append((score, href, text))

            if candidates:
                candidates.sort(key=lambda x: -x[0])
                best_href = candidates[0][1]
                if not best_href.startswith("http"):
                    base = page.url.split("/")[0:3]
                    best_href = "/".join(base) + best_href
                return best_href
        except Exception:
            pass
        return None

    @staticmethod
    def find_clickable_for_text(page: Any, target_text: str) -> list[str]:
        """Find selectors for clickable elements containing target text."""
        selectors = []
        try:
            for tag in ["button", "a", "input[type='submit']", "[role='button']"]:
                elements = page.query_selector_all(tag)
                for el in elements:
                    text = (el.inner_text() or "").strip()
                    if target_text.lower() in text.lower():
                        # Build a robust selector
                        el_id = el.get_attribute("id")
                        if el_id:
                            selectors.append(f"#{el_id}")
                        el_class = el.get_attribute("class") or ""
                        if el_class:
                            classes = el_class.strip().split()[:2]
                            selectors.append(f"{tag}.{'.'.join(classes)}")
                        selectors.append(f"{tag}:has-text('{text[:30]}')")
        except Exception:
            pass
        return selectors[:5]
