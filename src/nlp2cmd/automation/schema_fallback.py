"""
LLM-powered dynamic fallback for failed ActionPlan steps.

When a step fails during browser automation, this module:
1. Analyzes the failure context (DOM state, error, step history)
2. Generates alternative steps using LLM or rule-based heuristics
3. Returns a replacement sub-plan that can be injected into the execution loop

This replaces static "echo instructions" with dynamic re-planning.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Optional

log = logging.getLogger("nlp2cmd.schema_fallback")


@dataclass
class FallbackContext:
    """Context collected when a step fails, used to generate alternatives."""

    failed_action: str
    failed_params: dict[str, Any]
    error_message: str
    step_index: int
    total_steps: int
    variables: dict[str, str]
    dom_snapshot: dict[str, Any] = field(default_factory=dict)
    page_url: str = ""
    page_title: str = ""
    clipboard_content: str = ""
    previous_steps_ok: list[str] = field(default_factory=list)
    service_name: str = ""
    service_config: dict[str, Any] = field(default_factory=dict)


@dataclass
class FallbackResult:
    """Result of a fallback attempt."""

    success: bool
    strategy: str  # "rule_based", "llm", "clipboard", "dom_extraction"
    replacement_steps: list[dict[str, Any]] = field(default_factory=list)
    message: str = ""
    extracted_value: str = ""  # If we managed to extract the key directly


class SchemaFallback:
    """Generate alternative action schemas when steps fail.

    Uses a tiered approach:
    1. Rule-based heuristics (fast, no LLM needed)
    2. DOM-based extraction (inspect page for key elements)
    3. Clipboard-based extraction (check if user copied key)
    4. LLM-powered re-planning (generate new schema via Ollama)
    """

    def __init__(self, llm_model: str = "deepseek-r1:1.5b") -> None:
        self._llm_model = llm_model
        self._llm_available: Optional[bool] = None

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    def generate_fallback(
        self,
        ctx: FallbackContext,
        page: Any = None,
    ) -> FallbackResult:
        """Generate fallback steps for a failed action.

        Tries strategies in order: rule-based → DOM → clipboard → LLM.
        """
        log.info(
            "[SchemaFallback] Generating fallback for failed '%s' at step %d/%d",
            ctx.failed_action, ctx.step_index, ctx.total_steps,
        )

        # Strategy 1: Rule-based heuristics
        result = self._try_rule_based(ctx, page)
        if result and result.success:
            return result

        # Strategy 2: DOM extraction (if page available)
        if page is not None:
            result = self._try_dom_extraction(ctx, page)
            if result and result.success:
                return result

        # Strategy 3: Clipboard check
        result = self._try_clipboard(ctx)
        if result and result.success:
            return result

        # Strategy 4: LLM re-planning
        result = self._try_llm_replan(ctx)
        if result and result.success:
            return result

        return FallbackResult(
            success=False,
            strategy="none",
            message=f"All fallback strategies exhausted for '{ctx.failed_action}'",
        )

    # ------------------------------------------------------------------
    # Strategy 1: Rule-based heuristics
    # ------------------------------------------------------------------
    def _try_rule_based(self, ctx: FallbackContext, page: Any = None) -> Optional[FallbackResult]:
        """Rule-based fallback for known failure patterns."""

        # check_session failed → try navigating to login page
        if ctx.failed_action == "check_session":
            login_url = ctx.failed_params.get("login_url", "")
            keys_url = ctx.failed_params.get("keys_url", "")
            if login_url:
                return FallbackResult(
                    success=True,
                    strategy="rule_based",
                    message="Session check failed — redirecting to login page",
                    replacement_steps=[
                        {"action": "echo", "params": {"text": (
                            "⚠️ Sesja wygasła lub nie jesteś zalogowany.\n"
                            f"   Przekierowuję na stronę logowania: {login_url}\n"
                            "   Zaloguj się, a potem kontynuuj."
                        )}},
                        {"action": "navigate", "params": {"url": login_url}},
                        {"action": "wait", "params": {"ms": 5000}},
                        # After login, go back to keys page
                        {"action": "navigate", "params": {"url": keys_url}},
                        {"action": "wait", "params": {"ms": 2000}},
                        {"action": "check_session", "params": ctx.failed_params},
                    ],
                )

        # click failed (e.g. "Create" button not found) → try alternative selectors
        if ctx.failed_action == "click":
            selector = ctx.failed_params.get("selector", "")
            alternative_selectors = self._get_alternative_selectors(selector, ctx)
            if alternative_selectors:
                steps = []
                for alt in alternative_selectors[:3]:  # Try up to 3 alternatives
                    steps.append({
                        "action": "click",
                        "params": {"selector": alt},
                        "description": f"Alternatywny selektor: {alt}",
                    })
                return FallbackResult(
                    success=True,
                    strategy="rule_based",
                    message=f"Click failed for '{selector}' — trying alternatives",
                    replacement_steps=steps,
                )

        # extract_key failed → try creating a new key first
        if ctx.failed_action == "extract_key":
            svc = ctx.service_config
            create_cfg = svc.get("create_key", {})
            if create_cfg and create_cfg.get("button_selector"):
                btn_selector = create_cfg["button_selector"]
                # Extract text from selector for text-based click (more SPA-safe)
                # e.g. "button:has-text('Create')" → text="Create"
                btn_text = None
                if "has-text(" in btn_selector:
                    m = re.search(r"has-text\(['\"](.+?)['\"]\)", btn_selector)
                    if m:
                        btn_text = m.group(1)
                click_params: dict[str, Any] = {"timeout": 15000, "retries": 3}
                if btn_text:
                    click_params["text"] = btn_text
                else:
                    click_params["selector"] = btn_selector
                return FallbackResult(
                    success=True,
                    strategy="rule_based",
                    message="No existing key found — attempting to create new key",
                    replacement_steps=[
                        {"action": "echo", "params": {"text": (
                            "🔑 Nie znaleziono istniejącego klucza.\n"
                            "   Próbuję utworzyć nowy klucz API..."
                        )}},
                        {"action": "wait", "params": {"ms": 2000}},
                        {"action": "click", "params": click_params},
                        {"action": "wait", "params": {"ms": 3000}},
                        {"action": "extract_key", "params": ctx.failed_params},
                    ],
                )

        # prompt_secret failed (user didn't provide key) → try clipboard
        if ctx.failed_action == "prompt_secret":
            return FallbackResult(
                success=True,
                strategy="rule_based",
                message="Manual prompt failed — checking clipboard for key",
                replacement_steps=[
                    {"action": "check_clipboard", "params": {
                        "key_pattern": ctx.failed_params.get("key_pattern", ""),
                        "env_var": ctx.failed_params.get("env_var", ""),
                    }},
                ],
            )

        return None

    # ------------------------------------------------------------------
    # Strategy 2: DOM extraction
    # ------------------------------------------------------------------
    def _try_dom_extraction(self, ctx: FallbackContext, page: Any) -> Optional[FallbackResult]:
        """Try to extract key directly from page DOM."""
        if ctx.failed_action not in ("extract_key", "prompt_secret", "check_session"):
            return None

        svc = ctx.service_config
        key_pattern = svc.get("key_pattern", "")
        key_selectors = svc.get("key_selectors", [])
        generic_selectors = [
            "code", "pre", "input[readonly]", "input[type='text'][readonly]",
            ".api-key", "[data-testid*='key']", "[class*='key']",
            ".token", "[data-testid*='token']",
        ]

        all_selectors = list(key_selectors) + generic_selectors

        try:
            for selector in all_selectors:
                try:
                    elements = page.query_selector_all(selector)
                    for el in elements:
                        text = (el.text_content() or "").strip()
                        if not text or len(text) < 10:
                            continue
                        # Check if it matches key pattern
                        if key_pattern and re.match(key_pattern, text):
                            log.info("[SchemaFallback] Found key via DOM selector: %s", selector)
                            return FallbackResult(
                                success=True,
                                strategy="dom_extraction",
                                message=f"Key found in DOM via selector: {selector}",
                                extracted_value=text,
                            )
                        # No pattern but looks like a key (long alphanumeric)
                        if not key_pattern and re.match(r'^[a-zA-Z0-9_\-]{20,}$', text):
                            return FallbackResult(
                                success=True,
                                strategy="dom_extraction",
                                message=f"Potential key found in DOM: {selector} ({len(text)} chars)",
                                extracted_value=text,
                            )
                except Exception:
                    continue
        except Exception as e:
            log.warning("[SchemaFallback] DOM extraction failed: %s", e)

        return None

    # ------------------------------------------------------------------
    # Strategy 3: Clipboard check
    # ------------------------------------------------------------------
    def _try_clipboard(self, ctx: FallbackContext) -> Optional[FallbackResult]:
        """Check if the key is in the clipboard."""
        clipboard = ctx.clipboard_content
        if not clipboard:
            try:
                from nlp2cmd.automation.step_validator import StepValidator
                clipboard = StepValidator.get_clipboard()
            except Exception:
                return None

        if not clipboard or len(clipboard) < 10:
            return None

        key_pattern = ctx.service_config.get("key_pattern", "")
        if key_pattern and re.match(key_pattern, clipboard):
            return FallbackResult(
                success=True,
                strategy="clipboard",
                message=f"Key found in clipboard ({len(clipboard)} chars, matches pattern)",
                extracted_value=clipboard,
            )

        # No pattern but clipboard has something key-like
        if re.match(r'^[a-zA-Z0-9_\-]{20,}$', clipboard):
            return FallbackResult(
                success=True,
                strategy="clipboard",
                message=f"Potential key found in clipboard ({len(clipboard)} chars)",
                extracted_value=clipboard,
            )

        return None

    # ------------------------------------------------------------------
    # Strategy 4: LLM re-planning
    # ------------------------------------------------------------------
    def _try_llm_replan(self, ctx: FallbackContext) -> Optional[FallbackResult]:
        """Use LLM to generate alternative steps."""
        if not self._is_llm_available():
            return None

        prompt = self._build_replan_prompt(ctx)
        try:
            import subprocess
            result = subprocess.run(
                ["ollama", "run", self._llm_model],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return None

            response = result.stdout.strip()
            steps = self._parse_llm_steps(response)
            if steps:
                return FallbackResult(
                    success=True,
                    strategy="llm",
                    message=f"LLM generated {len(steps)} alternative steps",
                    replacement_steps=steps,
                )
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            log.warning("[SchemaFallback] LLM replan failed: %s", e)

        return None

    def _is_llm_available(self) -> bool:
        """Check if Ollama is available."""
        if self._llm_available is not None:
            return self._llm_available
        try:
            import subprocess
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True, text=True, timeout=5,
            )
            self._llm_available = result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self._llm_available = False
        return self._llm_available

    def _build_replan_prompt(self, ctx: FallbackContext) -> str:
        """Build prompt for LLM re-planning."""
        return (
            f"You are an automation planner. A step failed during browser automation.\n"
            f"Generate alternative steps in JSON format.\n\n"
            f"Failed action: {ctx.failed_action}\n"
            f"Error: {ctx.error_message}\n"
            f"Page URL: {ctx.page_url}\n"
            f"Service: {ctx.service_name}\n"
            f"Previous OK steps: {ctx.previous_steps_ok}\n"
            f"Available actions: navigate, click, type_text, wait, extract_text, "
            f"check_session, extract_key, prompt_secret, save_env, verify_env, echo\n\n"
            f"Respond with a JSON array of step objects, each with 'action' and 'params' keys.\n"
            f"Example: [{{'action': 'click', 'params': {{'selector': 'button.create'}}}}]\n"
        )

    @staticmethod
    def _parse_llm_steps(response: str) -> list[dict[str, Any]]:
        """Parse LLM response into step dictionaries."""
        # Try to find JSON array in response
        match = re.search(r'\[.*\]', response, re.DOTALL)
        if not match:
            return []
        try:
            steps = json.loads(match.group())
            if isinstance(steps, list):
                return [
                    s for s in steps
                    if isinstance(s, dict) and "action" in s
                ]
        except json.JSONDecodeError:
            pass
        return []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _get_alternative_selectors(failed_selector: str, ctx: FallbackContext) -> list[str]:
        """Generate alternative CSS selectors for a failed click."""
        alternatives = []

        # If it was a button with text
        text_match = re.search(r"has-text\('([^']+)'\)", failed_selector)
        if text_match:
            text = text_match.group(1)
            alternatives.extend([
                f"button:has-text('{text}')",
                f"a:has-text('{text}')",
                f"[role='button']:has-text('{text}')",
                f"text='{text}'",
                f"button >> text='{text}'",
            ])

        # Try common create-key selectors
        if any(w in failed_selector.lower() for w in ["create", "new", "generate"]):
            alternatives.extend([
                "button:has-text('Create')",
                "button:has-text('New')",
                "button:has-text('Generate')",
                "button:has-text('Create Key')",
                "button:has-text('New Key')",
                "[data-testid='create-key']",
                ".create-key-button",
            ])

        # Remove the original failed selector
        return [s for s in alternatives if s != failed_selector]
