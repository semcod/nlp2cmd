from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from nlp2cmd.adapters.base import SafetyPolicy
from nlp2cmd.ir import ActionIR
from nlp2cmd.utils.data_files import find_data_file
from rich.console import Console
from nlp2cmd.utils.yaml_compat import yaml


class _MarkdownConsoleWrapper:
    """Context manager that captures console output into Markdown code blocks."""

    def __init__(self, console: Console, *, enable_markdown: bool, default_language: str = "text") -> None:
        self.console = console
        self.enable_markdown = enable_markdown
        self.default_language = default_language
        self._buffer: list[str] = []
        # Import inside class to avoid circular dependency
        from nlp2cmd.cli.markdown_output import print_markdown_block
        self.print_markdown_block = print_markdown_block

    def print(self, renderable, *, language: str | None = None) -> None:
        if self.enable_markdown:
            self.print_markdown_block(renderable, language=language or self.default_language, console=self.console)
        else:
            self.console.print(renderable)

    def capture(self):
        """Return context manager that captures printed text into a single block."""
        wrapper = self

        class _Capture:
            def __enter__(self):
                wrapper._buffer = []
                return wrapper._buffer

            def __exit__(self, exc_type, exc, tb):
                if wrapper.enable_markdown and wrapper._buffer:
                    wrapper.print_markdown_block("\n".join(wrapper._buffer), language=wrapper.default_language, console=wrapper.console)
                elif wrapper._buffer:
                    wrapper.console.print("\n".join(wrapper._buffer))

        return _Capture()


@dataclass
class ShellExecutionPolicy:
    allowlist: set[str] = field(default_factory=set)
    blocked_regex: list[str] = field(
        default_factory=lambda: [
            r"\brm\s+-rf\s+/\b",
            r"\brm\s+-rf\s+/\*\b",
            r"\bmkfs\b",
            r"\bdd\s+if=/dev/zero\b",
            r":\(\)\{:\|:&\};:",
        ]
    )
    require_confirm_regex: list[str] = field(
        default_factory=lambda: [
            r"\brm\b",
            r"\brmdir\b",
            r"\bkill\b",
            r"\bkillall\b",
            r"\bshutdown\b",
            r"\breboot\b",
            r"\bsystemctl\s+stop\b",
            r"\bdocker\s+rm\b",
            r"\bdocker\s+rmi\b",
        ]
    )
    allow_sudo: bool = False
    allow_pipes: bool = False

    def load_from_data(self, path: str = "./data/shell_execution_policy.json") -> None:
        """Optionally load policy configuration from JSON in data/."""

        p = find_data_file(explicit_path=path, default_filename="shell_execution_policy.json")
        if not p:
            return

        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return
        if not isinstance(raw, dict):
            return

        ar = raw.get("allowlist")
        if isinstance(ar, list):
            self.allowlist = {x.strip() for x in ar if isinstance(x, str) and x.strip()}

        br = raw.get("blocked_regex")
        if isinstance(br, list):
            self.blocked_regex = [x for x in br if isinstance(x, str) and x.strip()]

        rr = raw.get("require_confirm_regex")
        if isinstance(rr, list):
            self.require_confirm_regex = [x for x in rr if isinstance(x, str) and x.strip()]

        asu = raw.get("allow_sudo")
        if isinstance(asu, bool):
            self.allow_sudo = asu

        ap = raw.get("allow_pipes")
        if isinstance(ap, bool):
            self.allow_pipes = ap


@dataclass
class RunnerResult:
    success: bool
    kind: str
    data: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: float = 0.0


class PipelineRunner:
    def __init__(
        self,
        *,
        shell_policy: Optional[ShellExecutionPolicy] = None,
        safety_policy: Optional[SafetyPolicy] = None,
        headless: bool = True,
        enable_history: bool = True,
    ):
        self.shell_policy = shell_policy or ShellExecutionPolicy()
        try:
            self.shell_policy.load_from_data()
        except Exception:
            pass
        self.safety_policy = safety_policy
        self.headless = headless
        self.enable_history = enable_history
        self._history = None
        
        if enable_history:
            try:
                from nlp2cmd.web_schema.history import InteractionHistory
                self._history = InteractionHistory()
            except Exception:
                self._history = None

    def run(
        self,
        ir: ActionIR,
        *,
        cwd: Optional[str] = None,
        timeout_s: float = 15.0,
        dry_run: bool = True,
        confirm: bool = False,
        web_url: Optional[str] = None,
    ) -> RunnerResult:
        started = time.time()
        try:
            if ir.dsl_kind == "shell":
                res = self._run_shell(ir.dsl, cwd=cwd, timeout_s=timeout_s, dry_run=dry_run, confirm=confirm)
            elif ir.dsl_kind == "dom":
                res = self._run_dom_dql(ir.dsl, dry_run=dry_run, confirm=confirm, web_url=web_url)
            else:
                res = RunnerResult(
                    success=False,
                    kind=str(ir.dsl_kind),
                    error=f"Unsupported dsl_kind: {ir.dsl_kind}",
                )

            res.duration_ms = (time.time() - started) * 1000.0
            return res
        except Exception as e:
            return RunnerResult(
                success=False,
                kind=str(ir.dsl_kind),
                error=str(e),
                duration_ms=(time.time() - started) * 1000.0,
            )

    def _run_shell(
        self,
        command: str,
        *,
        cwd: Optional[str],
        timeout_s: float,
        dry_run: bool,
        confirm: bool,
    ) -> RunnerResult:
        cmd = str(command or "").strip()
        if not cmd:
            return RunnerResult(success=False, kind="shell", error="Empty command")

        if self.safety_policy is not None:
            chk = self._check_against_safety_policy(cmd, self.safety_policy)
            if not chk["allowed"]:
                return RunnerResult(success=False, kind="shell", error=str(chk.get("reason") or "Blocked"))
            if chk.get("requires_confirmation") and not confirm:
                return RunnerResult(
                    success=False,
                    kind="shell",
                    error="Command requires confirmation",
                    data={"requires_confirmation": True},
                )

        parsed = self._parse_shell_command(cmd)
        if not parsed["allowed"]:
            return RunnerResult(success=False, kind="shell", error=str(parsed.get("reason") or "Blocked"))

        if parsed.get("requires_confirmation") and not confirm:
            return RunnerResult(
                success=False,
                kind="shell",
                error="Command requires confirmation",
                data={"requires_confirmation": True},
            )

        argv = parsed.get("argv")
        if not isinstance(argv, list) or not argv:
            return RunnerResult(success=False, kind="shell", error="Failed to parse command")

        if dry_run:
            return RunnerResult(success=True, kind="shell", data={"argv": argv, "dry_run": True})

        cp = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout_s,
            check=False,
        )
        return RunnerResult(
            success=cp.returncode == 0,
            kind="shell",
            data={
                "argv": argv,
                "returncode": cp.returncode,
                "stdout": cp.stdout,
                "stderr": cp.stderr,
            },
            error=None if cp.returncode == 0 else (cp.stderr.strip() or f"returncode={cp.returncode}"),
        )

    def _parse_shell_command(self, command: str) -> dict[str, Any]:
        cmd = command.strip()
        cmd_lower = cmd.lower()

        if not self.shell_policy.allow_sudo and re.search(r"(^|\s)sudo(\s|$)", cmd_lower):
            return {"allowed": False, "reason": "sudo is not allowed"}

        if not self.shell_policy.allow_pipes and any(op in cmd for op in ["|", ";", "&&", "||", ">", "<"]):
            return {"allowed": False, "reason": "Pipes/redirects/chaining are not allowed"}

        if any(x in cmd for x in ["$(`", "`", "$(", "${"]):
            return {"allowed": False, "reason": "Shell expansions are not allowed"}

        for pat in self.shell_policy.blocked_regex:
            if re.search(pat, cmd_lower):
                return {"allowed": False, "reason": f"Command blocked by pattern: {pat}"}

        requires = any(re.search(p, cmd_lower) for p in self.shell_policy.require_confirm_regex)

        try:
            argv = shlex.split(cmd)
        except Exception:
            argv = cmd.split()

        if not argv:
            return {"allowed": False, "reason": "Empty command"}

        base = argv[0]
        if self.shell_policy.allowlist and base not in self.shell_policy.allowlist:
            return {"allowed": False, "reason": f"Command not in allowlist: {base}"}

        return {"allowed": True, "argv": argv, "requires_confirmation": requires}

    @staticmethod
    def _check_against_safety_policy(command: str, policy: SafetyPolicy) -> dict[str, Any]:
        cmd_lower = (command or "").lower()

        if not policy.enabled:
            return {"allowed": True, "requires_confirmation": False}

        for pattern in policy.blocked_patterns:
            if str(pattern).lower() in cmd_lower:
                return {"allowed": False, "reason": f"Blocked pattern: {pattern}", "requires_confirmation": False}

        requires = False
        for pattern in policy.require_confirmation_for:
            if str(pattern).lower() in cmd_lower:
                requires = True
                break

        return {"allowed": True, "requires_confirmation": requires}

    def _run_dom_dql(
        self,
        dql_json: str,
        *,
        dry_run: bool,
        confirm: bool,
        web_url: Optional[str],
    ) -> RunnerResult:
        try:
            payload = json.loads(dql_json)
        except Exception as e:
            return RunnerResult(success=False, kind="dom", error=f"Invalid dom_dql.v1 JSON: {e}")

        if not isinstance(payload, dict) or payload.get("dsl") != "dom_dql.v1":
            return RunnerResult(success=False, kind="dom", error="Unsupported dom DQL payload")

        # Check if this is a multi-action sequence
        actions = payload.get("actions")
        if actions and isinstance(actions, list):
            return self._run_dom_multi_action(payload, dry_run=dry_run, confirm=confirm, web_url=web_url)

        url = payload.get("url") or web_url
        action = str(payload.get("action") or "")
        target = payload.get("target") or {}
        selector = str((target or {}).get("value") or "")

        if not url:
            return RunnerResult(success=False, kind="dom", error="Missing url for dom action")
        if not action:
            return RunnerResult(success=False, kind="dom", error="Missing action")
        if action not in {"goto", "navigate"} and not selector:
            return RunnerResult(success=False, kind="dom", error="Missing target selector")

        params = payload.get("params") or {}
        if dry_run:
            return RunnerResult(
                success=True,
                kind="dom",
                data={"dry_run": True, "url": url, "action": action, "selector": selector, "params": params},
            )

        if action in {"click", "type", "select"} and not confirm:
            pass

        try:
            from playwright.sync_api import sync_playwright  # type: ignore
        except Exception as e:
            return RunnerResult(success=False, kind="dom", error=f"Playwright not available: {e}")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page()

            if action in {"goto", "navigate"}:
                page.goto(str(url))
                page.wait_for_timeout(250)
            else:
                page.goto(str(url))
                page.wait_for_timeout(250)

                locator = page.locator(selector).first

                if action == "click":
                    locator.click()
                elif action == "type":
                    value = (params or {}).get("value")
                    if value is None:
                        return RunnerResult(success=False, kind="dom", error="Missing params.value for type")
                    locator.fill(str(value))
                elif action == "select":
                    value = (params or {}).get("value")
                    if value is None:
                        return RunnerResult(success=False, kind="dom", error="Missing params.value for select")
                    locator.select_option(str(value))
                else:
                    return RunnerResult(success=False, kind="dom", error=f"Unsupported dom action: {action}")

            browser.close()

        return RunnerResult(success=True, kind="dom", data={"url": url, "action": action, "selector": selector})
    
    def _run_dom_multi_action(
        self,
        payload: dict[str, Any],
        *,
        dry_run: bool,
        confirm: bool,
        web_url: Optional[str],
    ) -> RunnerResult:
        """Execute multiple browser actions in sequence."""
        actions = payload.get("actions", [])
        url = payload.get("url") or web_url
        
        if not url:
            return RunnerResult(success=False, kind="dom", error="Missing url for multi-action")

        if not confirm:
            for a in actions:
                if isinstance(a, dict) and str(a.get("action") or "") == "press":
                    if str(a.get("key") or "") in {"Enter", "Return"}:
                        return RunnerResult(
                            success=False,
                            kind="dom",
                            error="Action requires confirmation",
                            data={
                                "requires_confirmation": True,
                                "confirmation_reason": "press_enter",
                                "url": url,
                            },
                        )
                if isinstance(a, dict) and str(a.get("action") or "") == "submit":
                    return RunnerResult(
                        success=False,
                        kind="dom",
                        error="Action requires confirmation",
                        data={
                            "requires_confirmation": True,
                            "confirmation_reason": "submit",
                            "url": url,
                        },
                    )
        
        if dry_run:
            return RunnerResult(
                success=True,
                kind="dom",
                data={"dry_run": True, "url": url, "actions": actions},
            )

        console = Console()
        console_wrapper = _MarkdownConsoleWrapper(console, enable_markdown=True)
        
        try:
            from playwright.sync_api import sync_playwright  # type: ignore
        except Exception as e:
            return RunnerResult(success=False, kind="dom", error=f"Playwright not available: {e}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            from nlp2cmd.web_schema.form_data_loader import FormDataLoader

            schema_loader = FormDataLoader(site=str(url))
            ctx_opts = schema_loader.get_browser_context_options()

            context = browser.new_context(**ctx_opts)
            page = context.new_page()

            detected_form_fields: list[object] | None = None
            filled_any_form_field: bool = False
            saw_fill_form_action: bool = False
            
            try:
                for i, action_spec in enumerate(actions):
                    action = action_spec.get("action")
                    
                    if action in {"goto", "navigate"}:
                        action_url = action_spec.get("url", url)
                        page.goto(str(action_url), wait_until="domcontentloaded")
                        page.wait_for_timeout(1000)
                        
                        # Try to dismiss common popups/cookie consents
                        self._dismiss_popups(page, schema_loader)

                    elif action == "explore_for_content":
                        # Explore site to find content
                        try:
                            from nlp2cmd.web_schema.site_explorer import SiteExplorer
                            
                            content_type = action_spec.get("content_type", "article")
                            console_wrapper.print(f"🔍 Exploring site for {content_type}...", language="text")
                            explorer = SiteExplorer(max_depth=2, max_pages=8, headless=self.headless)
                            
                            # Don't close browser - reuse current context
                            explore_result = explorer.find_content(
                                url=url,
                                content_type=content_type,
                                page=page,
                                context=context,
                                close_browser=False,
                            )
                            
                            if explore_result.success and explore_result.form_url:
                                content_url = explore_result.form_url
                                console_wrapper.print(f"✓ Found {content_type} at: {content_url}", language="text")
                                
                                # Navigate to the discovered content page
                                if content_url != page.url:
                                    page.goto(content_url, wait_until="domcontentloaded")
                                    page.wait_for_timeout(1500)
                                
                                # Update URL for subsequent actions
                                url = content_url
                            else:
                                console_wrapper.print(f"No {content_type} found during exploration", language="text")
                        except Exception as e:
                            console_wrapper.print(f"Content exploration failed: {e}", language="text")

                    elif action == "explore_for_form":
                        # Explore site to find forms before filling
                        try:
                            from nlp2cmd.web_schema.site_explorer import SiteExplorer
                            
                            intent = action_spec.get("intent", "contact")
                            console_wrapper.print(f"🔍 Exploring site for {intent} form...", language="text")
                            explorer = SiteExplorer(max_depth=2, max_pages=8, headless=self.headless)
                            
                            # Don't close browser - reuse current context
                            explore_result = explorer.find_form(
                                url=url,
                                intent=intent,
                                page=page,
                                context=context,
                                close_browser=False,
                            )
                            
                            if explore_result.success and explore_result.form_url:
                                form_url = explore_result.form_url
                                console_wrapper.print(f"✓ Found form at: {form_url}", language="text")
                                
                                # Navigate to the discovered form page
                                if form_url != page.url:
                                    page.goto(form_url, wait_until="domcontentloaded")
                                    page.wait_for_timeout(1500)
                                
                                # Update URL for subsequent actions
                                url = form_url
                            else:
                                console_wrapper.print("No form found during exploration", language="text")
                        except Exception as e:
                            console_wrapper.print(f"Site exploration failed: {e}", language="text")

                    elif action == "fill_form":
                        # Automatic form filling from .env and data/*.json
                        try:
                            from nlp2cmd.web_schema.form_handler import FormHandler
                            from nlp2cmd.web_schema.site_explorer import SiteExplorer
                            
                            form_handler = FormHandler(console=console, use_markdown=True)
                            data_loader = schema_loader

                            saw_fill_form_action = True
                            
                            # Wait for page to be fully loaded.
                            # Try networkidle first (best for static sites), but fall back
                            # to domcontentloaded for sites with persistent network activity
                            # (analytics, chat widgets, websockets) that prevent networkidle.
                            console_wrapper.print("⏳ Waiting for page to load...", language="text")
                            try:
                                page.wait_for_load_state("networkidle", timeout=5000)
                            except Exception:
                                # networkidle timed out — page has persistent connections
                                try:
                                    page.wait_for_load_state("domcontentloaded", timeout=10000)
                                except Exception:
                                    pass  # proceed anyway, DOM is likely ready
                            page.wait_for_timeout(1500)
                            
                            # Detect form fields
                            console_wrapper.print("🔍 Detecting form fields...", language="text")
                            fields = form_handler.detect_form_fields(page)
                            detected_form_fields = fields
                            
                            if not fields:
                                console_wrapper.print("No form fields detected on this page", language="text")

                                try:
                                    console_wrapper.print(
                                        yaml.safe_dump(
                                            {
                                                "status": "form_discovery_started",
                                                "strategy": "site_explorer",
                                                "max_depth": 2,
                                                "max_pages": 8,
                                                "url": url,
                                            },
                                            sort_keys=False,
                                            allow_unicode=True,
                                        ).rstrip(),
                                        language="yaml",
                                    )
                                except Exception:
                                    pass

                                try:
                                    explorer = SiteExplorer(max_depth=2, max_pages=8, headless=self.headless)
                                    explore_result = explorer.find_form(
                                        url=url,
                                        intent="contact",
                                        page=page,
                                        context=context,
                                        close_browser=False,
                                    )
                                    
                                    if explore_result.success and explore_result.form_url:
                                        form_url = explore_result.form_url
                                        console_wrapper.print(f"✓ Found form at: {form_url}", language="text")
                                        
                                        # Navigate to the discovered form page
                                        if form_url != page.url:
                                            page.goto(form_url, wait_until="domcontentloaded")
                                            page.wait_for_timeout(1500)
                                        
                                        # Retry form detection
                                        console_wrapper.print("🔁 Retrying form field detection after exploration...", language="text")
                                        fields = form_handler.detect_form_fields(page)
                                        detected_form_fields = fields
                                except Exception as e:
                                    console_wrapper.print(f"Site exploration failed: {e}", language="text")
                                    # Fall through to simpler heuristic

                                # Fallback: simple heuristic - try to navigate to contact page
                                if not fields:
                                    try:
                                        candidates = [
                                            'a[href*="kontakt" i]',
                                            'a:has-text("Kontakt")',
                                            'a:has-text("Kontakt") >> visible=true',
                                            'a:has-text("Contact")',
                                            'a[href*="contact" i]',
                                        ]
                                        clicked = False
                                        for sel in candidates:
                                            try:
                                                loc = page.locator(sel).first
                                                if loc.count() > 0:
                                                    loc.click(timeout=1500)
                                                    page.wait_for_load_state("domcontentloaded", timeout=8000)
                                                    page.wait_for_timeout(1200)
                                                    clicked = True
                                                    break
                                            except Exception:
                                                continue

                                        if clicked:
                                            console_wrapper.print("🔁 Retrying form field detection after navigating...", language="text")
                                            fields = form_handler.detect_form_fields(page)
                                            detected_form_fields = fields
                                    except Exception:
                                        pass

                                if not fields:
                                    return RunnerResult(
                                        success=False,
                                        kind="dom",
                                        error="No form fields detected on the current page (contact form not found).",
                                        data={"url": url},
                                    )
                            else:
                                console_wrapper.print("🔍 Detected form fields:", language="text")
                                console_wrapper.print(
                                    yaml.safe_dump(
                                        {
                                            "status": "form_fields_detected",
                                            "count": len(fields),
                                            "fields": [
                                                {
                                                    "field": f.get_display_name(),
                                                    "type": f.field_type,
                                                    "selector": f.selector,
                                                    "name": f.name,
                                                    "id": f.id,
                                                }
                                                for f in fields
                                            ],
                                        },
                                        sort_keys=False,
                                        allow_unicode=True,
                                    ).rstrip(),
                                    language="yaml",
                                )
                                
                                # Automatic fill from .env and data/ files
                                if data_loader.has_data():
                                    console_wrapper.print("📂 Loading form data from .env and data/...", language="text")
                                    form_data = form_handler.automatic_fill(fields, data_loader)
                                else:
                                    console_wrapper.print("No form data in .env or data/ - using interactive mode", language="text")
                                    form_data = form_handler.interactive_fill(fields)
                                if form_data is not None:
                                    form_data.submit_selector = form_handler.detect_submit_button(page, data_loader)
                                
                                # Fill the form if we have data
                                if form_data and form_data.fields:
                                    console_wrapper.print("📝 Filling form...", language="text")
                                    ok = form_handler.fill_form(page, form_data)
                                    if ok:
                                        filled_any_form_field = True
                                
                            page.wait_for_timeout(500)
                            
                        except Exception as e:
                            return RunnerResult(success=False, kind="dom", error=f"Action {i}: Form filling failed: {e}")
                    
                    elif action == "type":
                        selector = action_spec.get("selector", "__auto__")
                        text = action_spec.get("text", "")
                        
                        if not text:
                            return RunnerResult(success=False, kind="dom", error=f"Action {i}: Missing text for type")
                        
                        selectors_to_try: list[str] = []

                        if isinstance(selector, str) and selector.strip() and selector.strip() != "__auto__":
                            selectors_to_try.append(selector.strip())

                        search_selectors = schema_loader.get_type_selectors("search")
                        generic_selectors = schema_loader.get_type_selectors("generic")
                        search_selector_set = set(search_selectors)
                        generic_selector_set = set(generic_selectors)

                        selectors_to_try.extend(search_selectors)
                        selectors_to_try.extend(generic_selectors)
                        selectors_to_try = FormDataLoader.dedupe_selectors(selectors_to_try)
                        
                        typed = False
                        last_error = None
                        
                        for sel in selectors_to_try:
                            try:
                                # Wait for selector to be visible
                                page.wait_for_selector(sel, state="visible", timeout=2000)
                                locator = page.locator(sel).first
                                
                                # Click to focus
                                locator.click()
                                page.wait_for_timeout(200)
                                
                                # Clear and type
                                locator.fill("")
                                locator.type(str(text), delay=50)
                                page.wait_for_timeout(500)

                                selector_group = "search" if sel in search_selector_set else "generic"
                                schema_loader.add_type_selector(sel, selector_type=selector_group)
                                
                                # Record successful interaction
                                if self._history:
                                    parsed = urlparse(url)
                                    self._history.learn_from_success(
                                        domain=parsed.netloc,
                                        action_type="type",
                                        selector=sel,
                                    )
                                
                                typed = True
                                break
                            except Exception as e:
                                last_error = str(e)
                                
                                # Record failed attempt
                                if self._history:
                                    parsed = urlparse(url)
                                    self._history.learn_from_failure(
                                        domain=parsed.netloc,
                                        action_type="type",
                                        selector=sel,
                                        error=str(e),
                                    )
                                continue
                        
                        if not typed:
                            return RunnerResult(
                                success=False,
                                kind="dom",
                                error=f"Action {i}: Could not find typeable input field. Last error: {last_error}"
                            )
                    
                    elif action == "click":
                        selector = action_spec.get("selector", "")
                        if not selector:
                            return RunnerResult(success=False, kind="dom", error=f"Action {i}: Missing selector for click")
                        
                        try:
                            page.wait_for_selector(selector, state="visible", timeout=3000)
                            locator = page.locator(selector).first
                            locator.click()
                            page.wait_for_timeout(500)
                        except Exception as e:
                            return RunnerResult(success=False, kind="dom", error=f"Action {i}: Could not click {selector}: {e}")
                    
                    elif action == "press":
                        key = action_spec.get("key", "")
                        if not key:
                            return RunnerResult(success=False, kind="dom", error=f"Action {i}: Missing key for press")
                        
                        page.keyboard.press(str(key))
                        page.wait_for_timeout(500)
                    
                    elif action == "submit":
                        # Submit form by clicking submit button
                        # Load submit selectors from schema
                        if saw_fill_form_action and not filled_any_form_field:
                            return RunnerResult(
                                success=False,
                                kind="dom",
                                error="Submit requested but no form fields were filled (skipping Enter fallback).",
                                data={"url": url, "form_fields_detected": int(len(detected_form_fields or []))},
                            )

                        submit_selectors = schema_loader.get_submit_selectors()
                        
                        submitted = False
                        for sel in submit_selectors:
                            try:
                                page.wait_for_selector(sel, state="visible", timeout=2000)
                                page.click(sel)
                                submitted = True
                                console_wrapper.print(f"Form submitted via: {sel}", language="text")
                                schema_loader.add_submit_selector(sel)
                                break
                            except Exception:
                                continue
                        
                        if not submitted:
                            return RunnerResult(
                                success=False,
                                kind="dom",
                                error="Could not find a visible submit button on this page (not submitting via Enter).",
                                data={"url": url, "form_fields_detected": int(len(detected_form_fields or []))},
                            )
                        
                        page.wait_for_timeout(2000)
                    
                    elif action == "extract_article":
                        # Extract article content from the page
                        try:
                            # Get mode and topic from action spec
                            mode = action_spec.get("mode", "single")  # "single" or "list"
                            topic = action_spec.get("topic")  # Optional topic filter
                            
                            # Wait for page to be fully loaded
                            page.wait_for_load_state("domcontentloaded", timeout=5000)
                            page.wait_for_timeout(1000)

                            # Collect all article links
                            article_links: list[dict[str, str]] = []
                            attempted_llm = False

                            for attempt in range(2):
                                article_selectors = schema_loader.get_article_link_selectors()
                                for selector in article_selectors:
                                    try:
                                        links = page.locator(selector).all()
                                        for link in links[:20]:  # Limit to first 20
                                            try:
                                                href = link.get_attribute("href")
                                                text = link.inner_text().strip()
                                                if href and text:
                                                    article_links.append({"href": href, "text": text})
                                            except Exception:
                                                continue
                                    except Exception:
                                        continue
                                
                                if article_links:
                                    break

                                if attempted_llm:
                                    break
                                attempted_llm = True

                                llm_suggestion = self._llm_suggest_article_selectors(page)
                                if not llm_suggestion:
                                    break

                                for sel in llm_suggestion.get("article_link_selectors") or []:
                                    try:
                                        schema_loader.add_article_link_selector(sel)
                                    except Exception:
                                        pass
                                for sel in llm_suggestion.get("article_content_selectors") or []:
                                    try:
                                        schema_loader.add_article_content_selector(sel)
                                    except Exception:
                                        pass

                            if not article_links:
                                console_wrapper.print("⚠️  No article links found on page", language="text")
                                return RunnerResult(success=False, kind="dom", error="No article links found")
                            
                            # Filter by topic if specified
                            if topic:
                                filtered_links = []
                                topic_lower = topic.lower()
                                for link in article_links:
                                    text_lower = link["text"].lower()
                                    # Simple keyword matching (can be enhanced with similarity)
                                    if topic_lower in text_lower or any(word in text_lower for word in topic_lower.split()):
                                        filtered_links.append(link)
                                
                                if filtered_links:
                                    article_links = filtered_links
                                    if console_wrapper.enable_markdown:
                                        console.print(f"\n## Browser automation: filtered by topic '{topic}'", markup=False)
                                    console_wrapper.print(f"Found {len(article_links)} articles matching topic", language="text")
                                else:
                                    console_wrapper.print(f"⚠️  No articles found matching topic '{topic}'", language="text")
                            
                            # Handle list mode (plural)
                            if mode == "list":
                                if console_wrapper.enable_markdown:
                                    console.print("\n## Browser automation: article list", markup=False)
                                if console_wrapper.enable_markdown:
                                    console.print(f"Found {len(article_links)} articles:", markup=False)
                                    console.print("", markup=False)

                                    from urllib.parse import urljoin

                                    for link in article_links[:10]:  # Show max 10
                                        title = str(link.get("text") or "").strip()
                                        href = str(link.get("href") or "").strip()
                                        if not href:
                                            continue
                                        abs_url = href
                                        if not abs_url.startswith("http"):
                                            abs_url = urljoin(url, abs_url)
                                        if title:
                                            console.print(f"- [{title}]({abs_url})", markup=False)
                                        else:
                                            console.print(f"- {abs_url}", markup=False)

                                    if len(article_links) > 10:
                                        console.print(f"\n... and {len(article_links) - 10} more", markup=False)
                                else:
                                    console_wrapper.print(f"Found {len(article_links)} articles:", language="text")
                                    console_wrapper.print("", language="text")

                                    for idx, link in enumerate(article_links[:10], 1):  # Show max 10
                                        from urllib.parse import urljoin
                                        abs_url = link["href"]
                                        if not abs_url.startswith("http"):
                                            abs_url = urljoin(url, abs_url)
                                        console_wrapper.print(f"{idx}. {link['text']}", language="text")
                                        console_wrapper.print(f"   {abs_url}", language="text")
                                        console_wrapper.print("", language="text")

                                    if len(article_links) > 10:
                                        console_wrapper.print(f"... and {len(article_links) - 10} more", language="text")
                            
                            # Handle single mode (extract first article)
                            else:
                                selected_link = article_links[0]
                                article_url = selected_link["href"]
                                article_title = selected_link["text"]
                                
                                # Make URL absolute if needed
                                if article_url and not article_url.startswith("http"):
                                    from urllib.parse import urljoin
                                    article_url = urljoin(url, article_url)

                                if console_wrapper.enable_markdown:
                                    console.print("\n## Browser automation: found article", markup=False)
                                console_wrapper.print(f"Title: {article_title}", language="text")
                                console_wrapper.print(f"URL: {article_url}", language="text")
                                
                                # Navigate to article
                                page.goto(article_url, wait_until="domcontentloaded")
                                page.wait_for_timeout(1500)
                                
                                # Dismiss popups on article page
                                self._dismiss_popups(page, schema_loader)
                                
                                attempted_llm_content = False

                                for attempt in range(2):
                                    # Extract article content
                                    content_selectors = schema_loader.get_article_content_selectors()

                                    article_content = None
                                    for selector in content_selectors:
                                        try:
                                            article_element = page.locator(selector).first
                                            if article_element is not None and article_element.count() > 0:
                                                article_content = article_element.inner_text()
                                                if article_content and len(article_content.strip()) > 100:
                                                    break
                                        except Exception:
                                            continue

                                    if article_content and len(article_content.strip()) > 100:
                                        break

                                    if attempted_llm_content:
                                        break
                                    attempted_llm_content = True

                                    llm_suggestion = self._llm_suggest_article_selectors(page)
                                    if not llm_suggestion:
                                        break

                                    for sel in llm_suggestion.get("article_content_selectors") or []:
                                        try:
                                            schema_loader.add_article_content_selector(sel)
                                        except Exception:
                                            pass
                                
                                if not article_content:
                                    # Fallback: try to get main content
                                    try:
                                        article_content = page.locator("main").first.inner_text()
                                    except Exception:
                                        article_content = None
                                
                                if article_content:
                                    # Clean up the content
                                    lines = [line.strip() for line in article_content.split("\n") if line.strip()]
                                    cleaned_content = "\n".join(lines)

                                    if console_wrapper.enable_markdown:
                                        console.print("\n## Browser automation: article content", markup=False)
                                    console_wrapper.print(cleaned_content[:2000], language="text")  # Limit to 2000 chars
                                    if len(cleaned_content) > 2000:
                                        console_wrapper.print(
                                            f"... (truncated, {len(cleaned_content)} total characters)",
                                            language="text",
                                        )
                                else:
                                    console_wrapper.print("⚠️  Could not extract article content", language="text")
                                    return RunnerResult(success=False, kind="dom", error="Could not extract article content")
                            
                        except Exception as e:
                            return RunnerResult(success=False, kind="dom", error=f"Action {i}: Article extraction failed: {e}")
                    
                    else:
                        return RunnerResult(success=False, kind="dom", error=f"Action {i}: Unsupported action: {action}")
                
                # Keep browser open for a moment to see the result
                page.wait_for_timeout(2000)
                browser.close()
                
                return RunnerResult(success=True, kind="dom", data={"url": url, "actions_executed": len(actions)})
            
            except Exception as e:
                browser.close()
                return RunnerResult(success=False, kind="dom", error=f"Multi-action execution failed: {e}")

    @staticmethod
    def _dismiss_popups(page, schema_loader=None) -> None:
        """Try to dismiss common popups and cookie consents."""
        from nlp2cmd.web_schema.form_data_loader import FormDataLoader
        
        # Load dismiss selectors from schema
        loader = schema_loader if schema_loader is not None else FormDataLoader()
        dismiss_selectors = loader.get_dismiss_selectors()
        
        for selector in dismiss_selectors:
            try:
                page.wait_for_selector(selector, state="visible", timeout=1000)
                page.click(selector, timeout=1000)
                page.wait_for_timeout(500)

                try:
                    loader.add_dismiss_selector(selector)
                except Exception:
                    pass
                break
            except:
                continue

    @staticmethod
    def _extract_json_from_llm_response(text: str) -> Optional[dict[str, Any]]:
        if not isinstance(text, str) or not text.strip():
            return None

        raw = text.strip()
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, flags=re.DOTALL | re.IGNORECASE)
        if m:
            raw = m.group(1).strip()
        else:
            m2 = re.search(r"(\{.*\})", raw, flags=re.DOTALL)
            if m2:
                raw = m2.group(1).strip()

        try:
            payload = json.loads(raw)
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        return payload

    @staticmethod
    def _normalize_llm_article_selector_payload(payload: dict[str, Any]) -> dict[str, list[str]]:
        def _clean_list(value: Any) -> list[str]:
            if not isinstance(value, list):
                return []
            out: list[str] = []
            for s in value:
                if isinstance(s, str) and s.strip():
                    out.append(s.strip())
            return out

        link_selectors = _clean_list(payload.get("article_link_selectors"))
        content_selectors = _clean_list(payload.get("article_content_selectors"))
        return {
            "article_link_selectors": link_selectors,
            "article_content_selectors": content_selectors,
        }

    @staticmethod
    def _collect_page_links_for_llm(page, *, limit: int = 40) -> list[dict[str, str]]:
        try:
            items = page.evaluate(
                r"""(limit) => {
  const out = [];
  const nodes = Array.from(document.querySelectorAll('a[href]'));
  for (const a of nodes) {
    if (out.length >= limit) break;
    const href = a.getAttribute('href') || '';
    const text = (a.textContent || '').trim().replace(/\s+/g, ' ');
    if (!href) continue;
    out.push({href, text});
  }
  return out;
}""",
                limit,
            )
        except Exception:
            return []

        if not isinstance(items, list):
            return []
        out: list[dict[str, str]] = []
        for it in items:
            if not isinstance(it, dict):
                continue
            href = it.get("href")
            text = it.get("text")
            if isinstance(href, str) and isinstance(text, str):
                out.append({"href": href, "text": text})
        return out

    def _llm_suggest_article_selectors(self, page) -> Optional[dict[str, list[str]]]:
        try:
            import litellm
            from litellm import completion
        except Exception:
            return None

        model = (
            os.environ.get("LITELLM_MODEL")
            or os.environ.get("NLP2CMD_LLM_MODEL")
            or "ollama/qwen2.5-coder:7b"
        )
        api_base = (
            os.environ.get("LITELLM_API_BASE")
            or os.environ.get("NLP2CMD_LLM_API_BASE")
            or "http://localhost:11434"
        )
        api_key = os.environ.get("LITELLM_API_KEY") or os.environ.get("NLP2CMD_LLM_API_KEY") or ""
        temperature = float(os.environ.get("LITELLM_TEMPERATURE") or os.environ.get("NLP2CMD_LLM_TEMPERATURE") or "0.1")
        max_tokens = int(os.environ.get("LITELLM_MAX_TOKENS") or os.environ.get("NLP2CMD_LLM_MAX_TOKENS") or "512")
        timeout = float(os.environ.get("LITELLM_TIMEOUT") or os.environ.get("NLP2CMD_LLM_TIMEOUT") or "30")

        litellm.api_base = api_base
        if api_key:
            litellm.api_key = api_key
        litellm.timeout = timeout

        try:
            html = page.content()
        except Exception:
            html = ""
        links = self._collect_page_links_for_llm(page, limit=40)

        html_short = html[:24000] if isinstance(html, str) else ""
        links_json = json.dumps(links[:40], ensure_ascii=False)

        system = (
            "Jesteś ekspertem od selektorów CSS i ekstrakcji artykułów. "
            "Dostajesz HTML strony oraz listę linków. "
            "Masz zwrócić TYLKO JSON z propozycją selektorów."
        )
        user = (
            "Zaproponuj selektory CSS do: (1) znalezienia linku do artykułu na stronie głównej oraz "
            "(2) wyciągnięcia treści artykułu na stronie artykułu.\n\n"
            "Wymagany format JSON:\n"
            "{\n"
            "  \"article_link_selectors\": [\"...\"],\n"
            "  \"article_content_selectors\": [\"...\"]\n"
            "}\n\n"
            "Zasady:\n"
            "- Tylko JSON, bez markdown i bez komentarzy\n"
            "- Selektory mają być możliwie specyficzne, ale stabilne\n"
            "- Jeśli nie masz pewności, zwróć 2-5 propozycji na listę\n\n"
            f"LINKS_JSON:\n{links_json}\n\n"
            f"HTML_SNIPPET:\n{html_short}"
        )

        try:
            resp = completion(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = str(resp.choices[0].message["content"])
        except Exception:
            return None

        parsed = self._extract_json_from_llm_response(content)
        if not parsed:
            return None
        normalized = self._normalize_llm_article_selector_payload(parsed)
        if not normalized.get("article_link_selectors") and not normalized.get("article_content_selectors"):
            return None
        return normalized
