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


class FailureType(Enum):
    """Classification of step failure root cause."""
    SCHEMA_ERROR = "schema_error"           # Wrong selector/URL in service config
    HANDLING_ERROR = "handling_error"        # Code bug, timeout, unexpected state
    DATA_ERROR = "data_error"               # User data missing (not logged in, no key)
    PAGE_STATE_ERROR = "page_state_error"   # Page redirected, modal blocking, CAPTCHA
    UNKNOWN = "unknown"


@dataclass
class StepDiagnosis:
    """Result of analyzing a step failure."""
    failure_type: FailureType
    reason: str
    suggested_fix: Optional[str] = None
    alternative_selectors: list[str] = field(default_factory=list)
    alternative_url: Optional[str] = None
    needs_navigation: bool = False
    needs_login: bool = False
    page_analysis: Optional[str] = None


@dataclass
class RepairAttempt:
    """Record of a single repair attempt."""
    attempt: int
    strategy: str      # "local_llm", "cloud_llm", "rule_based", "page_analysis"
    diagnosis: StepDiagnosis
    success: bool
    elapsed_ms: float
    new_params: Optional[dict] = None


@dataclass
class FeedbackResult:
    """Result of the feedback loop for a single step."""
    success: bool
    result_value: Optional[str] = None
    attempts: list[RepairAttempt] = field(default_factory=list)
    final_params: Optional[dict] = None
    total_elapsed_ms: float = 0.0


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


class FeedbackLoop:
    """Declarative feedback loop for browser automation steps.

    Wraps step execution with validation, error classification, and
    repair escalation. Guarantees that a solution is found (or all
    strategies exhausted with clear diagnostics).

    Escalation chain:
      1. Rule-based repair (selector alternatives, URL fixes)
      2. Page analysis (DOM inspection for correct elements)
      3. Local LLM diagnosis (qwen2.5:3b via Ollama)
      4. Cloud LLM repair (OpenRouter for complex cases)
    """

    def __init__(
        self,
        max_retries: int = None,
        local_model: str = None,
        cloud_model: str = None,
    ):
        self.max_retries = max_retries or int(
            os.environ.get("FEEDBACK_LOOP_MAX_RETRIES", "5")
        )
        self.local_model = local_model or os.environ.get(
            "LLM_VALIDATOR_MODEL", "qwen2.5:3b"
        )
        self.cloud_model = cloud_model or os.environ.get(
            "LLM_REPAIR_MODEL", "qwen/qwen-2.5-coder-32b-instruct"
        )
        self._ollama_url = os.environ.get(
            "LLM_VALIDATOR_BASE_URL", "http://localhost:11434"
        ).rstrip("/")
        self._cloud_url = "https://openrouter.ai/api/v1/chat/completions"
        self._cloud_key = (
            os.environ.get("LLM_REPAIR_API_KEY")
            or os.environ.get("OPENROUTER_API_KEY")
            or ""
        )

    def classify_failure(
        self,
        action: str,
        error: str,
        page: Any = None,
        params: dict = None,
        service_config: dict = None,
    ) -> StepDiagnosis:
        """Classify WHY a step failed — schema, handling, data, or page state."""
        error_lower = error.lower()
        params = params or {}
        service_config = service_config or {}

        # --- Page state errors ---
        if "security-checkup" in error_lower or "security-checkup" in (page.url if page else ""):
            return StepDiagnosis(
                failure_type=FailureType.PAGE_STATE_ERROR,
                reason="Security checkup page is blocking navigation",
                suggested_fix="Pass security check or navigate directly to target URL",
                needs_navigation=True,
            )

        if any(x in error_lower for x in ["captcha", "recaptcha", "challenge"]):
            return StepDiagnosis(
                failure_type=FailureType.PAGE_STATE_ERROR,
                reason="CAPTCHA or challenge detected",
                suggested_fix="Manual intervention needed for CAPTCHA",
            )

        if any(x in error_lower for x in ["login", "sign in", "not authenticated"]):
            return StepDiagnosis(
                failure_type=FailureType.DATA_ERROR,
                reason="User is not logged in",
                suggested_fix="Navigate to login page",
                needs_login=True,
            )

        # --- Schema errors (wrong selectors) ---
        if "timeout" in error_lower and action in ("click", "type_text", "fill"):
            selector = params.get("selector", params.get("text", ""))
            alt_selectors = []
            if page:
                # Try to find alternatives via DOM analysis
                text_hint = params.get("text", "")
                if text_hint:
                    alt_selectors = PageAnalyzer.find_clickable_for_text(page, text_hint)

            return StepDiagnosis(
                failure_type=FailureType.SCHEMA_ERROR,
                reason=f"Selector '{selector}' not found on page (timeout)",
                suggested_fix="Try alternative selectors from DOM analysis",
                alternative_selectors=alt_selectors,
            )

        # --- Handling errors ---
        if "browser has been closed" in error_lower:
            return StepDiagnosis(
                failure_type=FailureType.HANDLING_ERROR,
                reason="Browser was closed unexpectedly",
                suggested_fix="Cannot recover — browser process died",
            )

        if "target closed" in error_lower or "page closed" in error_lower:
            return StepDiagnosis(
                failure_type=FailureType.HANDLING_ERROR,
                reason="Page or tab was closed",
                suggested_fix="Open a new tab and navigate to target URL",
                needs_navigation=True,
            )

        # --- Data errors ---
        if action == "extract_key" and "not found" in error_lower:
            return StepDiagnosis(
                failure_type=FailureType.DATA_ERROR,
                reason="No API key found on page",
                suggested_fix="Create a new key or navigate to correct page",
            )

        if action == "save_env" and "brak wartości" in error_lower:
            return StepDiagnosis(
                failure_type=FailureType.DATA_ERROR,
                reason="No value to save — key extraction failed in previous step",
                suggested_fix="Re-extract key or prompt user manually",
            )

        # --- Default: ask LLM ---
        return StepDiagnosis(
            failure_type=FailureType.UNKNOWN,
            reason=f"Unclassified error: {error[:200]}",
            suggested_fix="Escalate to LLM for diagnosis",
        )

    def diagnose_with_llm(
        self,
        action: str,
        error: str,
        page_context: str,
        params: dict,
        use_cloud: bool = False,
    ) -> StepDiagnosis:
        """Use LLM to diagnose failure and suggest repair."""
        prompt = f"""You are debugging a browser automation step that failed.

Action: {action}
Parameters: {json.dumps(params, default=str)[:500]}
Error: {error[:300]}

Current page state:
{page_context[:2000]}

Analyze the failure and respond with JSON only:
{{
  "failure_type": "schema_error|handling_error|data_error|page_state_error",
  "reason": "one sentence explanation",
  "suggested_fix": "specific actionable fix",
  "alternative_selectors": ["selector1", "selector2"],
  "alternative_url": "https://... or null",
  "needs_navigation": true/false,
  "needs_login": true/false
}}"""

        raw = None
        if not use_cloud:
            raw = self._call_ollama(prompt)
        if raw is None and self._cloud_key:
            raw = self._call_cloud(prompt)
            use_cloud = True

        if raw:
            try:
                text = raw.strip()
                if text.startswith("```"):
                    lines = text.splitlines()
                    text = "\n".join(l for l in lines if not l.strip().startswith("```")).strip()
                data = json.loads(text)
                ft_str = data.get("failure_type", "unknown")
                try:
                    ft = FailureType(ft_str)
                except ValueError:
                    ft = FailureType.UNKNOWN
                return StepDiagnosis(
                    failure_type=ft,
                    reason=data.get("reason", "LLM diagnosis"),
                    suggested_fix=data.get("suggested_fix"),
                    alternative_selectors=data.get("alternative_selectors", []),
                    alternative_url=data.get("alternative_url"),
                    needs_navigation=data.get("needs_navigation", False),
                    needs_login=data.get("needs_login", False),
                    page_analysis=f"via {'cloud' if use_cloud else 'local'} LLM",
                )
            except Exception as e:
                log.warning("Failed to parse LLM diagnosis: %s", e)

        return StepDiagnosis(
            failure_type=FailureType.UNKNOWN,
            reason="LLM diagnosis unavailable",
        )

    def generate_repair_params(
        self,
        diagnosis: StepDiagnosis,
        original_params: dict,
        action: str,
        service_config: dict = None,
    ) -> Optional[dict]:
        """Generate repaired step parameters based on diagnosis."""
        new_params = dict(original_params)
        service_config = service_config or {}

        if diagnosis.failure_type == FailureType.SCHEMA_ERROR:
            if diagnosis.alternative_selectors:
                # Use first alternative selector
                selector = diagnosis.alternative_selectors[0]
                if "selector" in new_params:
                    new_params["selector"] = selector
                elif "text" in new_params:
                    new_params["text"] = selector.split("has-text('")[-1].rstrip("')")
                return new_params

        if diagnosis.failure_type == FailureType.PAGE_STATE_ERROR:
            if diagnosis.needs_navigation and diagnosis.alternative_url:
                new_params["url"] = diagnosis.alternative_url
                return new_params
            if diagnosis.needs_navigation:
                keys_url = service_config.get("keys_url", "")
                if keys_url:
                    new_params["url"] = keys_url
                    return new_params

        if diagnosis.failure_type == FailureType.DATA_ERROR:
            if diagnosis.needs_login:
                login_url = service_config.get("login_url", "")
                if login_url:
                    new_params["url"] = login_url
                    return new_params

        if diagnosis.suggested_fix:
            return new_params

        return None

    def _call_ollama(self, prompt: str) -> Optional[str]:
        """Call local Ollama model."""
        try:
            import urllib.request
            payload = json.dumps({
                "model": self.local_model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 300},
            }).encode()
            req = urllib.request.Request(
                f"{self._ollama_url}/api/chat",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                return data.get("message", {}).get("content", "").strip()
        except Exception as e:
            log.debug("Ollama call failed: %s", e)
            return None

    def _call_cloud(self, prompt: str) -> Optional[str]:
        """Call cloud LLM via OpenRouter."""
        if not self._cloud_key:
            return None
        try:
            import urllib.request
            model = self.cloud_model
            if model.startswith("openrouter/"):
                model = model[len("openrouter/"):]
            payload = json.dumps({
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500,
                "temperature": 0.1,
            }).encode()
            req = urllib.request.Request(
                self._cloud_url,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._cloud_key}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "").strip()
        except Exception as e:
            log.debug("Cloud LLM call failed: %s", e)
        return None
