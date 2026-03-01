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
        mode = os.environ.get("NLP2CMD_LLM_SCHEMA_MODE", "llm_first").strip().lower()
        self._prefer_llm = mode in {"llm_first", "always", "1", "true"}
        try:
            self._llm_repair_rounds = max(
                1,
                int(os.environ.get("NLP2CMD_LLM_REPLAN_ROUNDS", "2")),
            )
        except ValueError:
            self._llm_repair_rounds = 2

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    def generate_fallback(
        self,
        ctx: FallbackContext,
        page: Any = None,
    ) -> FallbackResult:
        """Generate fallback steps for a failed action.

        Tries strategies in order:
          1. Rule-based heuristics (fast, no LLM)
          2. DOM extraction (inspect page for keys)
          3. Page analysis (find correct section/selectors via DOM scan)
          4. Clipboard check
          5. Local LLM re-planning (Ollama)
          6. Cloud LLM re-planning (OpenRouter escalation)
        """
        print(f"[DEBUG] SchemaFallback: generate_fallback called for action={ctx.failed_action}")
        log.info(
            "[SchemaFallback] Generating fallback for failed '%s' at step %d/%d",
            ctx.failed_action, ctx.step_index, ctx.total_steps,
        )

        # For extract_key failures, ALWAYS prefer rule-based first — it has the
        # complete create-key flow (dismiss overlays → discover section → pre-clicks
        # → click Create → fill form → submit → extract key → save_env).
        # LLM tends to generate weak 1-step responses that short-circuit this.
        _rules_first_actions = {"extract_key", "check_session", "navigate"}

        if self._prefer_llm and ctx.failed_action not in _rules_first_actions:
            result = self._run_llm_repair_rounds(ctx, page)
            if result and result.success:
                return result

        # Strategy 1: Rule-based heuristics
        result = self._try_rule_based(ctx, page)
        if result and result.success:
            return result

        # Strategy 2: DOM extraction (if page available)
        if page is not None:
            result = self._try_dom_extraction(ctx, page)
            if result and result.success:
                return result

        # Strategy 2b: Dynamic page schema — scan DOM for buttons/forms/tokens
        # and generate an action plan based on what's actually visible
        if page is not None:
            result = self._try_dynamic_page_schema(ctx, page)
            if result and result.success:
                return result

        # Strategy 2c: Page analysis — find correct section/selectors
        if page is not None:
            result = self._try_page_analysis(ctx, page)
            if result and result.success:
                return result

        # Strategy 3: Clipboard check
        result = self._try_clipboard(ctx)
        if result and result.success:
            return result

        # Strategy 4+5: LLM re-planning (if not already attempted, or for
        # extract_key where we now try it after rules)
        llm_already_tried = (
            self._prefer_llm and ctx.failed_action not in _rules_first_actions
        )
        if not llm_already_tried:
            result = self._run_llm_repair_rounds(ctx, page)
            if result and result.success:
                return result

        return FallbackResult(
            success=False,
            strategy="none",
            message=f"All fallback strategies exhausted for '{ctx.failed_action}'",
        )

    def _run_llm_repair_rounds(
        self,
        ctx: FallbackContext,
        page: Any = None,
    ) -> Optional[FallbackResult]:
        """Run iterative LLM repair rounds (local first, cloud escalation)."""
        # Local rounds
        for idx in range(self._llm_repair_rounds):
            result = self._try_llm_replan(ctx, page=page, use_cloud=False)
            if result and result.success:
                if idx > 0:
                    result.message = f"{result.message} (round {idx + 1})"
                return result

        # Single cloud escalation pass (if key available)
        result = self._try_llm_replan(ctx, page=page, use_cloud=True)
        if result and result.success:
            return result

        return None

    # ------------------------------------------------------------------
    # Strategy 1: Rule-based heuristics
    # ------------------------------------------------------------------
    def _try_rule_based(self, ctx: FallbackContext, page: Any = None) -> Optional[FallbackResult]:
        """Rule-based fallback for known failure patterns."""
        print(f"[DEBUG] SchemaFallback: _try_rule_based called for action={ctx.failed_action}")

        # navigate failed/mismatched URL -> discover the keys/tokens section dynamically
        if ctx.failed_action == "navigate":
            svc = ctx.service_config
            if svc:
                return FallbackResult(
                    success=True,
                    strategy="rule_based",
                    message="Navigation mismatch — trying dynamic section discovery",
                    replacement_steps=[
                        {"action": "echo", "params": {"text": (
                            "🔎 Strona docelowa nie została osiągnięta po nawigacji.\n"
                            "   Próbuję dynamicznie znaleźć sekcję kluczy/tokenów..."
                        )}},
                        {
                            "action": "discover_service_section",
                            "params": {
                                "service": ctx.service_name or "service",
                                "section": "keys",
                                "base_url": svc.get("base_url", ""),
                                "keys_url": svc.get("keys_url", ""),
                                "hints": svc.get("section_hints", svc.get("session_indicators", [])),
                            },
                            "store_as": "resolved_keys_url",
                        },
                        {"action": "wait", "params": {"ms": 1200}},
                    ],
                )

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
                steps: list[dict[str, Any]] = []

                steps.append({"action": "echo", "params": {"text": (
                    "🔑 Nie znaleziono istniejącego klucza.\n"
                    "   Próbuję utworzyć nowy klucz API..."
                )}})

                # 0. Dismiss cookie consent banners that block interaction
                steps.append({
                    "action": "dismiss_overlay",
                    "params": {},
                    "description": "Zamknij banery cookie/consent",
                })

                # 0b. Provider-agnostic section discovery (works even when redirected)
                steps.append({
                    "action": "discover_service_section",
                    "params": {
                        "service": ctx.service_name or "service",
                        "section": "keys",
                        "base_url": svc.get("base_url", ""),
                        "keys_url": svc.get("keys_url", ""),
                        "hints": svc.get("section_hints", svc.get("session_indicators", [])),
                    },
                    "store_as": "resolved_keys_url",
                    "description": "Znajdź sekcję kluczy API (fallback)",
                })
                steps.append({"action": "wait", "params": {"ms": 1200}})

                # 1a. Pre-clicks (e.g. open dropdown before selecting option)
                pre_clicks = create_cfg.get("pre_clicks", [])
                for pc in pre_clicks:
                    pc_params: dict[str, Any] = {"timeout": 5000}
                    if pc.get("text"):
                        pc_params["text"] = pc["text"]
                    elif pc.get("selector"):
                        pc_params["selector"] = pc["selector"]
                    steps.append({
                        "action": "click",
                        "params": pc_params,
                        "description": pc.get("description", "Pre-click"),
                    })
                    steps.append({"action": "wait", "params": {"ms": 800}})

                # 1b. Click page-level "Create" button (or dropdown option)
                btn_selector = create_cfg["button_selector"]
                btn_text = None
                if "has-text(" in btn_selector:
                    m = re.search(r"has-text\(['\"](.+?)['\"]\)", btn_selector)
                    if m:
                        btn_text = m.group(1)
                open_params: dict[str, Any] = {"timeout": 15000, "retries": 3}
                if btn_text:
                    open_params["text"] = btn_text
                else:
                    open_params["selector"] = btn_selector
                steps.append({"action": "click", "params": open_params})
                steps.append({"action": "wait", "params": {"ms": 1500}})

                # 2. Fill form fields (e.g. Name = "nlp2cmd", select radio button)
                # Wait for form to fully load (radio buttons may appear after animation)
                form_fields = create_cfg.get("form_fields", {})
                print(f"[DEBUG] SchemaFallback: Processing form fields: {list(form_fields.keys())}")
                log.info("[SchemaFallback] Processing form fields: %s", list(form_fields.keys()))
                for _fname, field_cfg in form_fields.items():
                    log.info("[SchemaFallback] Field %s: action=%s, selector=%s", 
                            _fname, field_cfg.get("action"), field_cfg.get("selector"))
                    if field_cfg.get("default"):
                        # Special handling for radio buttons (e.g., token type selection)
                        if field_cfg.get("action") == "click_radio":
                            log.info("[SchemaFallback] Adding radio button click for %s", _fname)
                            steps.append({
                                "action": "click_radio",
                                "params": {
                                    "selector": field_cfg["selector"],
                                    "timeout": 5000,
                                },
                                "description": f"Wybierz opcję: {_fname} = {field_cfg['default']}",
                            })
                            steps.append({"action": "wait", "params": {"ms": 300}})
                        else:
                            # Regular text input
                            log.info("[SchemaFallback] Adding type_text for %s", _fname)
                            _type_params: dict[str, Any] = {
                                "selector": field_cfg["selector"],
                                "text": field_cfg["default"],
                            }
                            if field_cfg.get("alt_selectors"):
                                _type_params["alt_selectors"] = field_cfg["alt_selectors"]
                            steps.append({
                                "action": "type_text",
                                "params": _type_params,
                                "description": f"Wypełnij pole: {_fname}",
                            })
                steps.append({"action": "wait", "params": {"ms": 500}})

                # 3. Submit form + capture key (non-blocking click + polling)
                #    Key reveal dialog may auto-close — polling captures it in time
                submit_sel = create_cfg.get("submit_selector", btn_selector)
                steps.append({
                    "action": "submit_and_extract_key",
                    "params": {
                        "selector": submit_sel,
                        "key_pattern": svc.get("key_pattern", ""),
                        "timeout": 60000,
                        "selectors": create_cfg.get(
                            "key_reveal_selector", "code, pre"
                        ).split(", "),
                    },
                    "store_as": "extracted_key",
                    "description": "Kliknij Create i przechwytuj klucz",
                })

                # 4. Save captured key to .env
                steps.append({"action": "save_env", "params": {
                    "var_name": svc.get("env_var", "API_KEY"),
                    "value": "$extracted_key",
                    "file": ".env",
                }})

                return FallbackResult(
                    success=True,
                    strategy="rule_based",
                    message="No existing key found — filling form and creating new key",
                    replacement_steps=steps,
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
    # Strategy 2b: Dynamic page schema — scan DOM to understand page
    # ------------------------------------------------------------------
    def _try_dynamic_page_schema(
        self, ctx: FallbackContext, page: Any,
    ) -> Optional[FallbackResult]:
        """Scan the page DOM to discover actionable elements and build a plan.

        This is the "schema generation" step — instead of relying on hardcoded
        selectors, we look at what's actually on the page (buttons, forms,
        tokens, copy buttons) and construct an action plan dynamically.
        """
        if ctx.failed_action not in ("extract_key", "click", "type_text"):
            return None

        svc = ctx.service_config or {}
        key_pattern = svc.get("key_pattern", "")
        env_var = svc.get("env_var", "API_KEY")

        try:
            # ---- Phase 1: Scan page for key-like elements ----
            page_schema = self._extract_page_schema(page)
            log.info(
                "[DynamicSchema] buttons=%d, forms=%d, radio_btns=%d, tokens=%d, copy_btns=%d",
                len(page_schema.get("buttons", [])),
                len(page_schema.get("forms", [])),
                len(page_schema.get("radio_buttons", [])),
                len(page_schema.get("tokens", [])),
                len(page_schema.get("copy_buttons", [])),
            )

            steps: list[dict[str, Any]] = []

            # ---- Phase 2: If tokens already visible → extract directly ----
            if page_schema["tokens"]:
                tok = page_schema["tokens"][0]
                steps.append({
                    "action": "echo",
                    "params": {"text": (
                        f"🔍 Dynamiczny schemat: znaleziono token na stronie "
                        f"(selektor: {tok['selector']})"
                    )},
                })
                # If there's a copy button nearby, click it first
                if page_schema["copy_buttons"]:
                    cb = page_schema["copy_buttons"][0]
                    steps.append({
                        "action": "click",
                        "params": {"selector": cb["selector"], "timeout": 3000},
                        "description": f"Kliknij przycisk kopiowania: {cb.get('text', '')}",
                    })
                    steps.append({"action": "wait", "params": {"ms": 500}})
                    steps.append({
                        "action": "check_clipboard",
                        "params": {"key_pattern": key_pattern, "env_var": env_var},
                        "store_as": "extracted_key",
                        "description": "Pobierz klucz ze schowka",
                    })
                else:
                    steps.append({
                        "action": "extract_key",
                        "params": {
                            "service": ctx.service_name,
                            "key_pattern": key_pattern,
                            "selectors": [tok["selector"]],
                        },
                        "store_as": "extracted_key",
                        "description": f"Pobierz token z {tok['selector']}",
                    })
                steps.append({
                    "action": "save_env",
                    "params": {"var_name": env_var, "value": "$extracted_key", "file": ".env"},
                })
                return FallbackResult(
                    success=True,
                    strategy="dynamic_schema",
                    message=f"Found existing token on page (selector: {tok['selector']})",
                    replacement_steps=steps,
                )

            # ---- Phase 3: No tokens visible → find "Create" button and form ----
            create_buttons = [
                b for b in page_schema["buttons"]
                if any(kw in b.get("text", "").lower() for kw in (
                    "create", "new", "generate", "add", "utwórz", "nowy",
                ))
            ]

            if create_buttons:
                btn = create_buttons[0]
                steps.append({
                    "action": "echo",
                    "params": {"text": (
                        f"🔍 Dynamiczny schemat: brak tokenu, znaleziono przycisk "
                        f"'{btn['text']}' — tworzę nowy klucz"
                    )},
                })
                steps.append({
                    "action": "click",
                    "params": {
                        "selector": btn["selector"],
                        "timeout": 10000,
                    },
                    "description": f"Kliknij: {btn['text']}",
                })
                steps.append({"action": "wait", "params": {"ms": 2000}})

                # After clicking Create, handle radio buttons first (token type selection)
                if page_schema["radio_buttons"]:
                    # Prefer "read" token type for general access
                    read_radio = next((rb for rb in page_schema["radio_buttons"] if rb.get("value") == "read"), None)
                    if read_radio:
                        steps.append({
                            "action": "click",
                            "params": {"selector": read_radio["selector"], "timeout": 5000},
                            "description": f"Wybierz typ tokenu: {read_radio.get('label', 'Read')}",
                        })
                        steps.append({"action": "wait", "params": {"ms": 300}})

                # Fill any visible text form fields
                if page_schema["forms"]:
                    for field in page_schema["forms"][:3]:
                        default = "nlp2cmd" if "name" in field.get("name", "").lower() else ""
                        if not default and "name" in field.get("placeholder", "").lower():
                            default = "nlp2cmd"
                        if not default and "token" in field.get("placeholder", "").lower():
                            default = "nlp2cmd"
                        if default:
                            steps.append({
                                "action": "type_text",
                                "params": {
                                    "selector": field["selector"],
                                    "text": default,
                                },
                                "description": f"Wypełnij pole: {field.get('name') or field.get('placeholder', '')}",
                            })

                # Submit form + extract key
                submit_buttons = [
                    b for b in page_schema["buttons"]
                    if any(kw in b.get("text", "").lower() for kw in (
                        "create", "generate", "submit", "confirm", "ok",
                        "utwórz", "generuj", "zatwierdź",
                    ))
                ]
                submit_sel = submit_buttons[0]["selector"] if submit_buttons else btn["selector"]

                steps.append({
                    "action": "submit_and_extract_key",
                    "params": {
                        "selector": submit_sel,
                        "key_pattern": key_pattern,
                        "timeout": 60000,
                        "selectors": svc.get("key_selectors", ["code", "pre", "input[readonly]"]),
                    },
                    "store_as": "extracted_key",
                    "description": "Zatwierdź i przechwytuj nowy klucz",
                })
                steps.append({
                    "action": "save_env",
                    "params": {"var_name": env_var, "value": "$extracted_key", "file": ".env"},
                })

                return FallbackResult(
                    success=True,
                    strategy="dynamic_schema",
                    message=f"Built dynamic create-key plan via button '{btn['text']}'",
                    replacement_steps=steps,
                )

        except Exception as e:
            log.warning("[DynamicSchema] Failed: %s", e)

        return None

    @staticmethod
    def _extract_page_schema(page: Any) -> dict[str, list[dict[str, str]]]:
        """Extract actionable elements from the current page DOM.

        Returns a schema dict with:
        - buttons: visible clickable elements (button, a[role=button], etc.)
        - forms: visible text input fields
        - radio_buttons: radio button groups (for token type selection)
        - tokens: elements that look like API tokens/keys
        - copy_buttons: buttons likely used to copy tokens
        """
        schema: dict[str, list[dict[str, str]]] = {
            "buttons": [],
            "forms": [],
            "radio_buttons": [],
            "tokens": [],
            "copy_buttons": [],
        }

        try:
            # --- Buttons ---
            btn_locators = page.locator(
                "button:visible, a[role='button']:visible, "
                "[role='button']:visible"
            )
            for i in range(min(btn_locators.count(), 30)):
                try:
                    el = btn_locators.nth(i)
                    text = (el.text_content() or "").strip()[:80]
                    if not text or len(text) < 2:
                        continue
                    # Build a unique selector
                    test_id = el.get_attribute("data-testid") or ""
                    aria = el.get_attribute("aria-label") or ""
                    if test_id:
                        sel = f"[data-testid='{test_id}']"
                    elif aria:
                        sel = f"[aria-label='{aria}']"
                    else:
                        sel = f"text='{text}'"
                    schema["buttons"].append({
                        "text": text, "selector": sel,
                        "tag": el.evaluate("el => el.tagName.toLowerCase()"),
                    })
                except Exception:
                    continue

            # --- Text inputs (forms) ---
            input_locators = page.locator(
                "input[type='text']:visible, input:not([type]):visible, "
                "textarea:visible"
            )
            for i in range(min(input_locators.count(), 15)):
                try:
                    el = input_locators.nth(i)
                    name = el.get_attribute("name") or ""
                    placeholder = el.get_attribute("placeholder") or ""
                    inp_type = el.get_attribute("type") or "text"
                    test_id = el.get_attribute("data-testid") or ""
                    if test_id:
                        sel = f"[data-testid='{test_id}']"
                    elif name:
                        sel = f"input[name='{name}']"
                    elif placeholder:
                        sel = f"input[placeholder='{placeholder}']"
                    else:
                        sel = f"input[type='{inp_type}']:visible >> nth={i}"
                    schema["forms"].append({
                        "name": name, "placeholder": placeholder,
                        "selector": sel, "type": inp_type,
                    })
                except Exception:
                    continue

            # --- Radio buttons (for token type selection) ---
            radio_locators = page.locator("input[type='radio']:visible")
            for i in range(min(radio_locators.count(), 10)):
                try:
                    el = radio_locators.nth(i)
                    value = el.get_attribute("value") or ""
                    name = el.get_attribute("name") or ""
                    test_id = el.get_attribute("data-testid") or ""
                    # Find associated label text
                    label_sel = f"label[for='{el.get_attribute('id') or ''}']"
                    label_text = ""
                    try:
                        label_el = page.query_selector(label_sel)
                        if label_el:
                            label_text = (label_el.text_content() or "").strip()[:30]
                    except Exception:
                        pass
                    if test_id:
                        sel = f"[data-testid='{test_id}']"
                    elif name and value:
                        sel = f"input[name='{name}'][value='{value}']"
                    elif value:
                        sel = f"input[type='radio'][value='{value}']"
                    else:
                        sel = f"input[type='radio']:visible >> nth={i}"
                    schema["radio_buttons"].append({
                        "value": value, "name": name, "label": label_text,
                        "selector": sel,
                    })
                except Exception:
                    continue

            # --- Token-like elements ---
            token_selectors = [
                "input[readonly]", "input[type='text'][readonly]",
                "code", "pre", ".token-value", "[data-testid*='token']",
                ".api-key", "[class*='secret']", "[class*='token']",
            ]
            for ts in token_selectors:
                try:
                    els = page.query_selector_all(ts)
                    for el in els[:5]:
                        text = (el.text_content() or el.get_attribute("value") or "").strip()
                        if text and len(text) >= 10:
                            schema["tokens"].append({
                                "selector": ts, "text_preview": text[:20] + "...",
                                "length": str(len(text)),
                            })
                except Exception:
                    continue

            # --- Copy buttons ---
            copy_locators = page.locator(
                "button:has-text('Copy'):visible, "
                "button:has-text('Kopiuj'):visible, "
                "button[aria-label*='copy' i]:visible, "
                "button[aria-label*='clipboard' i]:visible, "
                "[data-testid*='copy']:visible"
            )
            for i in range(min(copy_locators.count(), 5)):
                try:
                    el = copy_locators.nth(i)
                    text = (el.text_content() or "").strip()[:40]
                    test_id = el.get_attribute("data-testid") or ""
                    aria = el.get_attribute("aria-label") or ""
                    if test_id:
                        sel = f"[data-testid='{test_id}']"
                    elif aria:
                        sel = f"button[aria-label='{aria}']"
                    else:
                        sel = f"text='{text}'" if text else "button >> nth=0"
                    schema["copy_buttons"].append({"text": text, "selector": sel})
                except Exception:
                    continue

        except Exception as e:
            log.warning("[DynamicSchema] Schema extraction error: %s", e)

        return schema

    # ------------------------------------------------------------------
    # Strategy 2c: Page analysis
    # ------------------------------------------------------------------
    def _try_page_analysis(self, ctx: FallbackContext, page: Any) -> Optional[FallbackResult]:
        """Analyze page DOM to find correct navigation target or selectors."""
        try:
            from nlp2cmd.automation.feedback_loop import PageAnalyzer
        except ImportError:
            return None

        # If navigation/extract failed, try finding the right section
        if ctx.failed_action in ("navigate", "extract_key", "check_session"):
            keys_url = PageAnalyzer.find_api_keys_section(page)
            if keys_url and keys_url != ctx.page_url:
                return FallbackResult(
                    success=True,
                    strategy="page_analysis",
                    message=f"Found API keys section: {keys_url}",
                    replacement_steps=[
                        {"action": "navigate", "params": {"url": keys_url}},
                        {"action": "wait", "params": {"ms": 2000}},
                    ],
                )

        # If click failed, try finding the right button
        if ctx.failed_action == "click":
            text_hint = ctx.failed_params.get("text", "")
            if not text_hint:
                sel = ctx.failed_params.get("selector", "")
                m = re.search(r"has-text\(['\"](.+?)['\"]\)", sel)
                if m:
                    text_hint = m.group(1)
            if text_hint:
                alts = PageAnalyzer.find_clickable_for_text(page, text_hint)
                if alts:
                    steps = [{"action": "click", "params": {"selector": s},
                              "description": f"Page analysis: {s}"}
                             for s in alts[:3]]
                    return FallbackResult(
                        success=True,
                        strategy="page_analysis",
                        message=f"Found {len(alts)} clickable elements for '{text_hint}'",
                        replacement_steps=steps,
                    )

        # If type_text failed, try finding input fields
        if ctx.failed_action == "type_text":
            try:
                inputs = page.query_selector_all(
                    "input:not([type='hidden']):not([type='submit']), textarea"
                )
                visible_inputs = []
                for inp in inputs:
                    try:
                        if inp.is_visible(timeout=500):
                            name = inp.get_attribute("name") or ""
                            placeholder = inp.get_attribute("placeholder") or ""
                            type_ = inp.get_attribute("type") or "text"
                            sel = f"input[name='{name}']" if name else f"input[type='{type_}']"
                            visible_inputs.append((sel, name or placeholder))
                    except Exception:
                        continue
                if visible_inputs:
                    sel, desc = visible_inputs[0]
                    text = ctx.failed_params.get("text", "nlp2cmd")
                    return FallbackResult(
                        success=True,
                        strategy="page_analysis",
                        message=f"Found visible input: {desc or sel}",
                        replacement_steps=[{
                            "action": "type_text",
                            "params": {"selector": sel, "text": text},
                            "description": f"Wypełnij: {desc or sel}",
                        }],
                    )
            except Exception:
                pass

        return None

    # ------------------------------------------------------------------
    # Strategy 4+5: LLM re-planning (local → cloud escalation)
    # ------------------------------------------------------------------
    def _try_llm_replan(
        self,
        ctx: FallbackContext,
        page: Any = None,
        use_cloud: bool = False,
    ) -> Optional[FallbackResult]:
        """Use LLM to generate alternative steps.

        When use_cloud=False, tries local Ollama first.
        When use_cloud=True, escalates to OpenRouter cloud LLM.
        """
        prompt = self._build_replan_prompt(ctx, page)

        response = None
        strategy = "llm"

        if not use_cloud:
            if not self._is_llm_available():
                return None
            response = self._call_local_llm(prompt)
            strategy = "llm"
        else:
            response = self._call_cloud_llm(prompt)
            strategy = "cloud_llm"

        if not response:
            return None

        steps = self._parse_llm_steps(response)
        if steps:
            return FallbackResult(
                success=True,
                strategy=strategy,
                message=f"LLM generated {len(steps)} alternative steps",
                replacement_steps=steps,
            )

        return None

    def _call_local_llm(self, prompt: str) -> Optional[str]:
        """Call local Ollama model via API (not subprocess)."""
        try:
            import urllib.request
            ollama_url = os.environ.get(
                "LLM_VALIDATOR_BASE_URL", "http://localhost:11434"
            ).rstrip("/")
            payload = json.dumps({
                "model": self._llm_model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 500},
            }).encode()
            req = urllib.request.Request(
                f"{ollama_url}/api/chat",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read())
                return data.get("message", {}).get("content", "").strip()
        except Exception as e:
            log.debug("[SchemaFallback] Local LLM call failed: %s", e)
            return None

    def _call_cloud_llm(self, prompt: str) -> Optional[str]:
        """Call cloud LLM via OpenRouter for complex repair."""
        api_key = (
            os.environ.get("LLM_REPAIR_API_KEY")
            or os.environ.get("OPENROUTER_API_KEY")
            or ""
        )
        if not api_key:
            return None

        model = os.environ.get(
            "LLM_REPAIR_MODEL", "qwen/qwen-2.5-coder-32b-instruct"
        )
        if model.startswith("openrouter/"):
            model = model[len("openrouter/"):]

        try:
            import urllib.request
            payload = json.dumps({
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 800,
                "temperature": 0.1,
            }).encode()
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "").strip()
        except Exception as e:
            log.debug("[SchemaFallback] Cloud LLM call failed: %s", e)
        return None

    def _is_llm_available(self) -> bool:
        """Check if Ollama is available."""
        if self._llm_available is not None:
            return self._llm_available
        try:
            import urllib.request
            ollama_url = os.environ.get(
                "LLM_VALIDATOR_BASE_URL", "http://localhost:11434"
            ).rstrip("/")
            with urllib.request.urlopen(f"{ollama_url}/api/tags", timeout=3) as r:
                self._llm_available = r.status == 200
        except Exception:
            self._llm_available = False
        return self._llm_available

    def _build_replan_prompt(self, ctx: FallbackContext, page: Any = None) -> str:
        """Build prompt for LLM re-planning with page context."""
        page_context = ""
        if page is not None:
            try:
                from nlp2cmd.automation.feedback_loop import PageAnalyzer
                page_context = PageAnalyzer.extract_page_context(page, max_chars=1500)
            except Exception:
                page_context = f"URL: {ctx.page_url}\nTitle: {ctx.page_title}"

        return (
            f"You are a browser automation planner and schema repair engine.\n"
            f"A step failed and you must auto-generate a robust replacement schema.\n\n"
            f"Failed action: {ctx.failed_action}\n"
            f"Parameters: {json.dumps(ctx.failed_params, default=str)[:300]}\n"
            f"Error: {ctx.error_message[:300]}\n"
            f"Service: {ctx.service_name}\n"
            f"Previous OK steps: {ctx.previous_steps_ok}\n\n"
            f"Current page state:\n{page_context}\n\n"
            f"Available actions: navigate, click, type_text, wait, extract_text, "
            f"check_session, extract_key, prompt_secret, save_env, verify_env, "
            f"echo, dismiss_overlay, open_tab, select, discover_service_section, submit_and_extract_key\n\n"
            f"Rules:\n"
            f"- Respond with ONLY JSON (no markdown).\n"
            f"- Preferred format:\n"
            f"  {{\"diagnosis\": {{\"root_cause\": \"schema_definition_error|schema_execution_error|schema_data_error\","
            f" \"reason\": \"...\"}}, \"steps\": [ ... ]}}\n"
            f"- Allowed fallback format: JSON array of steps.\n"
            f"- Each step: {{\"action\": \"...\", \"params\": {{...}}, \"description\": \"...\", \"store_as\": \"optional\"}}\n"
            f"- Use actual selectors visible on the page, not guesses.\n"
            f"- If the page is on a different URL than expected, add a navigate step first.\n"
            f"- For SaaS key flows, prefer discover_service_section before create/extract if section is unclear.\n"
            f"- Maximum 5 steps.\n"
        )

    @staticmethod
    def _parse_llm_steps(response: str) -> list[dict[str, Any]]:
        """Parse LLM response into step dictionaries."""
        # 1) Try full response as JSON
        payload: Any = None
        try:
            payload = json.loads(response)
        except Exception:
            payload = None

        # 2) Fallback: extract JSON object or array from noisy output
        if payload is None:
            for pattern in (r'\{.*\}', r'\[.*\]'):
                match = re.search(pattern, response, re.DOTALL)
                if not match:
                    continue
                try:
                    payload = json.loads(match.group())
                    break
                except Exception:
                    continue

        if payload is None:
            return []

        # Support both:
        # - [{"action": ...}, ...]
        # - {"diagnosis": {...}, "steps": [{"action": ...}, ...]}
        if isinstance(payload, dict):
            maybe_steps = payload.get("steps") or payload.get("replacement_steps") or []
        else:
            maybe_steps = payload

        if not isinstance(maybe_steps, list):
            return []

        parsed: list[dict[str, Any]] = []
        for s in maybe_steps:
            if not isinstance(s, dict) or "action" not in s:
                continue
            step = {
                "action": str(s.get("action", "")).strip(),
                "params": s.get("params", {}) if isinstance(s.get("params", {}), dict) else {},
            }
            if s.get("description"):
                step["description"] = str(s.get("description"))
            if s.get("store_as"):
                step["store_as"] = str(s.get("store_as"))
            if step["action"]:
                parsed.append(step)
        return parsed

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
