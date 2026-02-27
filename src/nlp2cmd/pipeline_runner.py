from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from nlp2cmd.adapters.base import SafetyPolicy
from nlp2cmd.ir import ActionIR
from nlp2cmd.utils.data_files import find_data_file
from rich.console import Console
from nlp2cmd.utils.yaml_compat import yaml

# Utility functions, classes, and dataclasses extracted to pipeline_runner_utils.py
from nlp2cmd.pipeline_runner_utils import (  # noqa: F401
    _debug,
    _DEBUG,
    _with_epipe_retry,
    _field_attrs,
    _is_junk_field,
    _is_contact_relevant_field,
    _looks_like_comment_form,
    _filter_form_fields,
    _MarkdownConsoleWrapper,
    ShellExecutionPolicy,
    RunnerResult,
    # Screenshot and video utilities
    get_timestamp,
    ensure_dir,
    ask_for_screenshot,
    take_screenshot,
    VideoRecorder,
    ask_for_video_recording,
)


class PipelineRunner:
    def __init__(
        self,
        *,
        shell_policy: Optional[ShellExecutionPolicy] = None,
        safety_policy: Optional[SafetyPolicy] = None,
        headless: bool = True,
        enable_history: bool = True,
        video_fmt: Optional[str] = None,
        video_dir: str = "./recordings",
    ):
        self.shell_policy = shell_policy or ShellExecutionPolicy()
        try:
            self.shell_policy.load_from_data()
        except Exception:
            pass
        self.safety_policy = safety_policy
        self.headless = headless
        # When video recording is requested, force headless=False so there's content to record
        self.video_fmt = video_fmt
        self.video_dir = video_dir
        if video_fmt:
            self.headless = False
        self.enable_history = enable_history
        self._history = None
        self._executor_registry = None

        # Etap 3: opt-in modular executor dispatch
        if os.getenv("NLP2CMD_USE_EXECUTOR_REGISTRY", "1") == "1":
            try:
                from nlp2cmd.execution.executor_registry import create_default_registry
                self._executor_registry = create_default_registry(
                    shell_policy=self.shell_policy,
                    safety_policy=self.safety_policy,
                )
            except Exception:
                self._executor_registry = None

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
        video_fmt: Optional[str] = None,
        video_dir: Optional[str] = None,
    ) -> RunnerResult:
        started = time.time()
        try:
            if ir.dsl_kind == "shell" and self._executor_registry and "shell" in self._executor_registry:
                from nlp2cmd.execution.base import ExecutorContext
                ctx = ExecutorContext(
                    dry_run=dry_run, confirm=confirm, headless=self.headless,
                    video_fmt=video_fmt or self.video_fmt,
                    video_dir=video_dir or self.video_dir,
                )
                executor_result = self._executor_registry.dispatch(
                    "shell",
                    {"command": ir.dsl, "cwd": cwd, "timeout_s": timeout_s},
                    ctx,
                )
                res = executor_result.to_runner_result()
            elif ir.dsl_kind == "shell":
                res = self._run_shell(ir.dsl, cwd=cwd, timeout_s=timeout_s, dry_run=dry_run, confirm=confirm)
            elif ir.dsl_kind == "dom":
                res = self._run_dom_dql(ir.dsl, dry_run=dry_run, confirm=confirm, web_url=web_url,
                                        video_fmt=video_fmt, video_dir=video_dir)
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
        use_resource_discovery: bool = True,
    ) -> RunnerResult:
        """
        Execute shell command with optional resource discovery on failure.
        
        When a command fails due to missing files/directories and
        use_resource_discovery is True, automatically attempts to discover
        and use alternative paths.
        """
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

        # Initialize resource discovery if enabled
        resource_discovery = None
        if use_resource_discovery:
            try:
                from nlp2cmd.exploration.resource_discovery import get_resource_discovery_manager
                resource_discovery = get_resource_discovery_manager()
            except Exception:
                pass

        # Try execution with potential recovery
        current_argv = argv
        discovery_attempts = 0
        max_discovery_attempts = 3

        while True:
            cp = subprocess.run(
                current_argv,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=timeout_s,
                check=False,
            )

            if cp.returncode == 0:
                return RunnerResult(
                    success=True,
                    kind="shell",
                    data={
                        "argv": current_argv,
                        "returncode": cp.returncode,
                        "stdout": cp.stdout,
                        "stderr": cp.stderr,
                    },
                )

            # Command failed - check if we can recover via resource discovery
            if resource_discovery and discovery_attempts < max_discovery_attempts:
                error_output = cp.stderr or ""
                command_str = " ".join(current_argv)
                
                recovered, new_command = resource_discovery.handle_execution_failure(
                    command_str,
                    error_output,
                    discovery_attempts,
                )
                
                if recovered and new_command:
                    # Parse new command and retry
                    try:
                        import shlex
                        current_argv = shlex.split(new_command)
                        discovery_attempts += 1
                        continue
                    except Exception:
                        pass

            # No recovery possible - return failure
            return RunnerResult(
                success=False,
                kind="shell",
                data={
                    "argv": current_argv,
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
        video_fmt: Optional[str] = None,
        video_dir: Optional[str] = None,
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
            return self._run_dom_multi_action(payload, dry_run=dry_run, confirm=confirm, web_url=web_url,
                                               video_fmt=video_fmt, video_dir=video_dir)

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
        video_fmt: Optional[str] = None,
        video_dir: Optional[str] = None,
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

            # Video recording: prefer CLI --video flag, fall back to interactive prompt
            should_record_video = False
            _effective_video_dir = video_dir or "./recordings"
            
            if video_fmt:
                # CLI --video flag was passed — record automatically
                should_record_video = True
                _effective_video_dir = video_dir or "./recordings"
                _debug(f"Video recording enabled via --video {video_fmt}")
            else:
                # Fallback: interactive prompt (TTY only)
                try:
                    is_tty = bool(getattr(sys.stdin, "isatty", lambda: False)())
                except Exception:
                    is_tty = False
                if confirm and is_tty:
                    should_record_video, _effective_video_dir = ask_for_video_recording(console)
            
            video_recorder = None
            
            if should_record_video:
                video_recorder = VideoRecorder(output_dir=_effective_video_dir)
                video_path = video_recorder.start_recording(name_prefix="browser_automation")
                if video_path:
                    console.print(f"[dim]🎥 Nagrywanie wideo: {video_path}[/dim]")
                    # Enable Playwright built-in video recording
                    ctx_opts["record_video_dir"] = _effective_video_dir
                    ctx_opts["record_video_size"] = {"width": 1280, "height": 720}

            context = browser.new_context(**ctx_opts)

            # Strategy 2: Block heavy resources for speed — but NOT when recording video
            # (blocking images/fonts breaks visual content like jspaint canvas)
            if not should_record_video:
                try:
                    _BLOCKED = (
                        "**/*.png", "**/*.jpg", "**/*.jpeg", "**/*.gif", "**/*.svg",
                        "**/*.webp", "**/*.ico", "**/*.bmp", "**/*.tiff",
                        "**/*.woff", "**/*.woff2", "**/*.ttf", "**/*.eot",
                        "**/*.mp4", "**/*.webm", "**/*.ogg", "**/*.mp3",
                    )
                    def _abort_heavy(route):
                        try:
                            route.abort()
                        except Exception:
                            pass
                    for pat in _BLOCKED:
                        context.route(pat, _abort_heavy)
                    _debug("Resource blocking enabled in pipeline_runner")
                except Exception:
                    pass

            page = context.new_page()

            detected_form_fields: list[object] | None = None
            filled_any_form_field: bool = False
            saw_fill_form_action: bool = False
            extracted_data: list[dict[str, str]] = []  # accumulated data for save_to_file
            
            try:
                for i, action_spec in enumerate(actions):
                    action = action_spec.get("action")
                    _action_t0 = time.perf_counter()
                    _debug(f"action[{i}]: executing '{action}' spec={action_spec}")
                    
                    if action in {"goto", "navigate"}:
                        action_url = action_spec.get("url", url)
                        page.goto(str(action_url), wait_until="domcontentloaded")
                        page.wait_for_timeout(500)
                        
                        # Try to dismiss common popups/cookie consents
                        self._dismiss_popups(page, schema_loader)

                    elif action == "explore_for_content":
                        # Explore site to find content
                        try:
                            from nlp2cmd.web_schema.site_explorer import SiteExplorer
                            
                            content_type = action_spec.get("content_type", "article")
                            console_wrapper.print(f"🔍 Exploring site for {content_type}...", language="text")
                            # Use smaller limits for docs to avoid timeouts
                            max_pages = 2 if content_type == "docs" else 8
                            max_depth = 1 if content_type == "docs" else 2
                            explorer = SiteExplorer(max_depth=max_depth, max_pages=max_pages, headless=self.headless, timeout_ms=5000, dynamic_wait_ms=1000)
                            
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
                            fill_target = page
                            fields = form_handler.detect_form_fields(fill_target)
                            detected_form_fields = fields

                            # If the page contains only junk fields (cookie/search/captcha/comments),
                            # treat it as no form found and attempt discovery/navigation.
                            fields = _filter_form_fields(fields, console_wrapper)
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
                                        fill_target = page
                                        fields = form_handler.detect_form_fields(fill_target)
                                        detected_form_fields = fields

                                        fields = _filter_form_fields(fields, console_wrapper)
                                        detected_form_fields = fields
                                except Exception as e:
                                    console_wrapper.print(f"Site exploration failed: {e}", language="text")
                                    # Fall through to simpler heuristic

                                # Fallback: simple heuristic - try to navigate to contact page
                                if not fields:
                                    try:
                                        # First try direct contact URLs (many sites hide menu items behind a hamburger).
                                        try:
                                            from urllib.parse import urljoin
                                            base = str(page.url or url)
                                        except Exception:
                                            base = str(url)

                                        direct_paths = [
                                            "/kontakt",
                                            "/kontakt/",
                                            "/kontakt.html",
                                            "/kontakt.php",
                                            "/kontakt-i-dane",
                                            "/kontakt-2",
                                            "/kontakt-2/",
                                            "/contact",
                                            "/contact/",
                                        ]

                                        direct_attempts: list[dict[str, object]] = []
                                        for pth in direct_paths:
                                            if fields:
                                                break
                                            try:
                                                cand_url = urljoin(base, pth)
                                                direct_attempt: dict[str, object] = {"candidate": cand_url}
                                                direct_attempts.append(direct_attempt)
                                                resp = page.goto(cand_url, wait_until="domcontentloaded", timeout=12000)
                                                page.wait_for_timeout(1200)
                                                self._dismiss_popups(page, schema_loader)

                                                # Some sites render the contact form only after JS hydration or scroll.
                                                try:
                                                    page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
                                                except Exception:
                                                    pass
                                                page.wait_for_timeout(900)

                                                try:
                                                    direct_attempt["forms"] = int(
                                                        page.evaluate("() => document.querySelectorAll('form').length")
                                                    )
                                                except Exception:
                                                    direct_attempt["forms"] = None

                                                try:
                                                    direct_attempt["status"] = int(resp.status) if resp is not None else None
                                                except Exception:
                                                    direct_attempt["status"] = None
                                                try:
                                                    direct_attempt["final_url"] = str(page.url or "")
                                                except Exception:
                                                    direct_attempt["final_url"] = ""
                                                try:
                                                    direct_attempt["title"] = page.title() or ""
                                                except Exception:
                                                    direct_attempt["title"] = ""

                                                fields = form_handler.detect_form_fields(page)
                                                detected_form_fields = fields
                                                fields = _filter_form_fields(fields, console_wrapper)
                                                detected_form_fields = fields
                                            except Exception:
                                                try:
                                                    if direct_attempts:
                                                        direct_attempts[-1]["error"] = "goto_failed"
                                                except Exception:
                                                    pass
                                                continue

                                        try:
                                            console_wrapper.print(
                                                yaml.safe_dump(
                                                    {
                                                        "status": "direct_contact_nav_attempts",
                                                        "base": base,
                                                        "attempts": direct_attempts,
                                                    },
                                                    sort_keys=False,
                                                    allow_unicode=True,
                                                ).rstrip(),
                                                language="yaml",
                                            )
                                        except Exception:
                                            pass

                                        if fields:
                                            clicked = True
                                        else:
                                            clicked = False

                                        candidates = [
                                            'a[href*="kontakt" i]',
                                            'a:has-text("Kontakt")',
                                            'a:has-text("Kontakt") >> visible=true',
                                            'a:has-text("Contact")',
                                            'a[href*="contact" i]',
                                        ]

                                        if not clicked:
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
                                            fill_target = page
                                            fields = form_handler.detect_form_fields(fill_target)
                                            detected_form_fields = fields

                                            fields = _filter_form_fields(fields, console_wrapper)
                                            detected_form_fields = fields
                                    except Exception:
                                        pass

                                # If still no fields, check if there is a contact form inside an iframe.
                                if not fields:
                                    try:
                                        frames = list(getattr(page, "frames", []) or [])
                                    except Exception:
                                        frames = []

                                    frame_attempts: list[dict[str, object]] = []
                                    for fr in frames[1:]:
                                        try:
                                            fr_url = ""
                                            try:
                                                fr_url = str(fr.url or "")
                                            except Exception:
                                                fr_url = ""

                                            frame_attempt: dict[str, object] = {"frame_url": fr_url}
                                            frame_attempts.append(frame_attempt)

                                            fr_fields = form_handler.detect_form_fields(fr)
                                            fr_fields = _filter_form_fields(fr_fields, console_wrapper)
                                            if fr_fields:
                                                fill_target = fr
                                                fields = fr_fields
                                                frame_attempt["found_fields"] = len(fr_fields)
                                                break
                                            frame_attempt["found_fields"] = 0
                                        except Exception as e:
                                            frame_attempts.append({"error": str(e)})
                                            continue

                                    try:
                                        console_wrapper.print(
                                            yaml.safe_dump(
                                                {
                                                    "status": "iframe_form_scan",
                                                    "frames": len(frames),
                                                    "attempts": frame_attempts,
                                                    "selected": "frame" if fill_target is not page else "page",
                                                },
                                                sort_keys=False,
                                                allow_unicode=True,
                                            ).rstrip(),
                                            language="yaml",
                                        )
                                    except Exception:
                                        pass

                                if not fields:
                                    # Graceful fallback: some sites have a "Kontakt" page but no contact form
                                    # (only a site-wide search form). In that case, extract contact info instead
                                    # of failing hard.
                                    contact_info: dict[str, object] = {"mailto": [], "tel": [], "emails": [], "phones": []}
                                    try:
                                        contact_info = page.evaluate(r"""() => {
                                            const mailto = Array.from(document.querySelectorAll('a[href^="mailto:"]'))
                                                .map(a => (a.getAttribute('href') || '').trim())
                                                .filter(Boolean);
                                            const tel = Array.from(document.querySelectorAll('a[href^="tel:"]'))
                                                .map(a => (a.getAttribute('href') || '').trim())
                                                .filter(Boolean);

                                            const text = (document.body && (document.body.innerText || document.body.textContent)) ? (document.body.innerText || document.body.textContent) : '';

                                            const emails = [];
                                            const emailRe = /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi;
                                            let m;
                                            while ((m = emailRe.exec(text)) !== null) {
                                                emails.push(m[0]);
                                                if (emails.length >= 20) break;
                                            }

                                            const phones = [];
                                            const phoneRe = /\b(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{2,4}[\s.-]?\d{2,4}[\s.-]?\d{2,4}\b/g;
                                            let p;
                                            while ((p = phoneRe.exec(text)) !== null) {
                                                const cand = (p[0] || '').trim();
                                                if (!cand) continue;
                                                // Keep only plausible lengths
                                                const digits = cand.replace(/\D/g, '');
                                                if (digits.length < 7 || digits.length > 15) continue;
                                                phones.push(cand);
                                                if (phones.length >= 20) break;
                                            }

                                            const uniq = (arr) => Array.from(new Set(arr));
                                            return {
                                                mailto: uniq(mailto),
                                                tel: uniq(tel),
                                                emails: uniq(emails),
                                                phones: uniq(phones),
                                            };
                                        }""")
                                    except Exception:
                                        contact_info = {"mailto": [], "tel": [], "emails": [], "phones": []}

                                    try:
                                        console_wrapper.print(
                                            yaml.safe_dump(
                                                {
                                                    "status": "no_contact_form_fallback_contact_info",
                                                    "url": str(page.url or url),
                                                    "contact_info": contact_info,
                                                },
                                                sort_keys=False,
                                                allow_unicode=True,
                                            ).rstrip(),
                                            language="yaml",
                                        )
                                    except Exception:
                                        pass

                                    return RunnerResult(
                                        success=True,
                                        kind="dom",
                                        data={
                                            "url": str(page.url or url),
                                            "contact_info": contact_info,
                                            "note": "No contact form detected; extracted contact info instead.",
                                        },
                                    )
                            
                            # Optional screenshot after form interaction (only if not in auto-confirm mode)
                            if not confirm:
                                try:
                                    default_screenshot_path = f"./screenshots/form_{get_timestamp()}.png"
                                    should_screenshot, screenshot_path = ask_for_screenshot(console, default_screenshot_path)
                                    if should_screenshot:
                                        take_screenshot(page, screenshot_path, console)
                                except Exception:
                                    pass  # Screenshot is optional, don't fail if it errors
                                
                        except Exception as e:
                            console_wrapper.print(f"fill_form failed: {e}", language="text")
                            return RunnerResult(
                                success=False,
                                kind="dom",
                                error=f"fill_form error: {e}",
                                data={"url": url},
                            )

                    elif action in ("extract_company_websites_deep", "extract_companies"):
                        # Navigate to each company profile and extract their external website
                        try:
                            _debug("extract_company_websites_deep: starting deep extraction")
                            # Oferteo renders results dynamically; wait more robustly than domcontentloaded.
                            try:
                                page.wait_for_load_state("networkidle", timeout=8000)
                            except Exception:
                                page.wait_for_load_state("domcontentloaded", timeout=10000)
                            page.wait_for_timeout(1200)

                            # Dismiss popups first
                            self._dismiss_popups(page, schema_loader)

                            max_companies = action_spec.get("max_companies", 20)
                            companies_data: list[dict[str, str]] = []
                            base_url = page.url
                            attempts: list[dict[str, object]] = []

                            try:
                                _start_url = str(page.url or "")
                            except Exception:
                                _start_url = ""
                            try:
                                _start_path = urlparse(_start_url).path
                            except Exception:
                                _start_path = ""

                            # If we start on Oferteo homepage, we are likely on category tiles, not company listings.
                            # Try a best-effort jump to a city listing (this command is specifically for Gdańsk).
                            cur = ""
                            try:
                                cur = str(page.url or "")
                            except Exception:
                                cur = ""

                            try:
                                cur_path = urlparse(cur).path or ""
                            except Exception:
                                cur_path = ""

                            _cond = ("oferteo.pl" in cur and cur_path in {"", "/"})
                            if _cond:
                                for cand in [
                                    "https://www.oferteo.pl/firmy/gdansk",
                                    "https://www.oferteo.pl/firmy/gda%C5%84sk",
                                    "https://www.oferteo.pl/firmy-gdansk",
                                    "https://www.oferteo.pl/firmy-budowlane/gdansk",
                                ]:
                                    attempt: dict[str, object] = {"candidate": cand}
                                    attempts.append(attempt)
                                    try:
                                        resp = page.goto(cand, wait_until="domcontentloaded", timeout=15000)
                                        page.wait_for_timeout(900)
                                        self._dismiss_popups(page, schema_loader)

                                        try:
                                            status = int(resp.status) if resp is not None else None
                                        except Exception:
                                            status = None

                                        try:
                                            cur_after = str(page.url or "")
                                        except Exception:
                                            cur_after = ""

                                        try:
                                            firma_cnt = page.evaluate(
                                                r"""() => Array.from(document.querySelectorAll('a[href]'))
  .map(a => (a.getAttribute('href') || '').toLowerCase())
  .filter(h => h.includes('/firma')).length"""
                                            )
                                        except Exception:
                                            firma_cnt = 0

                                        try:
                                            title = page.title() or ""
                                        except Exception:
                                            title = ""

                                        attempt["status"] = status
                                        attempt["final_url"] = cur_after
                                        attempt["title"] = title
                                        attempt["firma_links"] = firma_cnt
                                        attempt["error"] = None

                                        # accept the first candidate that navigates away from homepage successfully
                                        if status is None or (isinstance(status, int) and status < 400):
                                            if urlparse(cur_after).path.strip("/") != "":
                                                base_url = page.url
                                                break
                                    except Exception as e:
                                        attempt["error"] = str(e)
                                        continue

                            try:
                                console_wrapper.print(
                                    yaml.safe_dump(
                                        {
                                            "status": "oferteo_nav_attempts",
                                            "start_url": _start_url,
                                            "start_path": _start_path,
                                            "current_url": str(page.url or ""),
                                            "condition": bool(locals().get("_cond", False)),
                                            "attempts": attempts,
                                        },
                                        sort_keys=False,
                                        allow_unicode=True,
                                    ).rstrip(),
                                    language="yaml",
                                )
                            except Exception:
                                pass

                            # If we start on the global catalog page, it may not show company profile links directly.
                            # Jump to a city listing page to get real company profiles.
                            try:
                                cur = str(page.url or "")
                                if "oferteo.pl" in cur and "/katalog-firm" in urlparse(cur).path:
                                    page.goto("https://www.oferteo.pl/firmy/gdansk", wait_until="domcontentloaded", timeout=15000)
                                    page.wait_for_timeout(1200)
                                    self._dismiss_popups(page, schema_loader)
                                    base_url = page.url
                            except Exception:
                                pass

                            # Best-effort: if we still are on the homepage, force the most likely listing URL.
                            try:
                                if "oferteo.pl" in str(page.url or "") and urlparse(str(page.url or "")).path.strip("/") == "":
                                    page.goto("https://www.oferteo.pl/firmy/gdansk", wait_until="domcontentloaded", timeout=15000)
                                    page.wait_for_timeout(900)
                                    self._dismiss_popups(page, schema_loader)
                                    base_url = page.url
                            except Exception:
                                pass

                            # Wait for dynamically loaded company links to appear.
                            # This avoids false negatives when the page is hydrated by JS after initial load.
                            try:
                                start_t = time.time()
                                last_seen = 0
                                while (time.time() - start_t) < 15.0:
                                    try:
                                        cnt = page.evaluate(
                                            r"""() => Array.from(document.querySelectorAll('a[href]'))
  .map(a => (a.getAttribute('href') || '').toLowerCase())
  .filter(h => h.includes('/firma')).length"""
                                        )
                                    except Exception:
                                        cnt = 0

                                    if isinstance(cnt, int) and cnt > 0:
                                        _debug(f"extract_company_websites_deep: detected {cnt} '/firma/' links after wait")
                                        break

                                    # If the count is not growing, try a gentle scroll to trigger lazy loading.
                                    if isinstance(cnt, int) and cnt == last_seen:
                                        try:
                                            page.evaluate("() => window.scrollBy(0, Math.max(600, window.innerHeight))")
                                        except Exception:
                                            pass
                                    if isinstance(cnt, int):
                                        last_seen = cnt
                                    page.wait_for_timeout(900)
                            except Exception:
                                pass

                            # Find company profile links on the catalog page
                            _debug("extract_company_websites_deep: finding company links")
                            company_links: list[dict[str, str]] = []
                            try:
                                from urllib.parse import urljoin
                            except Exception:
                                urljoin = None

                            def _collect_company_links() -> list[dict[str, str]]:
                                res = page.evaluate(r"""() => {
                                    const links = [];
                                    const seen = new Set();

                                    // Prefer the main listings area if present
                                    const roots = document.querySelectorAll('main, [role="main"], .results, .listing, #content, .companies, .firmy');
                                    const root = roots.length > 0 ? roots[0] : document.body;

                                    const allLinks = Array.from(root.querySelectorAll('a[href]'));
                                    for (const el of allLinks) {
                                        const href = (el.getAttribute('href') || '').trim();
                                        const text = (el.textContent || '').trim().replace(/\s+/g, ' ');
                                        if (!href || !text) continue;
                                        if (text.length < 2 || text.length > 140) continue;
                                        if (/^(#|javascript:|mailto:|tel:)/i.test(href)) continue;

                                        const hrefLower = href.toLowerCase();
                                        // Exclude categories/listings and noise
                                        // Categories sometimes use /firma-... or /firmy-...
                                        if (hrefLower.includes('/firma-')) continue;
                                        if (hrefLower.includes('/firmy-')) continue;
                                        if (hrefLower.includes('/firmy/')) continue;
                                        if (hrefLower.includes('/katalog') || hrefLower.includes('/kategorie') || hrefLower.includes('/branze') || hrefLower.includes('/uslugi')) continue;
                                        if (hrefLower.includes('facebook.com') || hrefLower.includes('instagram.com') || hrefLower.includes('linkedin.com')) continue;

                                        // Company profiles: be flexible across portals
                                        const looksLikeCompany = (
                                            hrefLower.includes('/firma') ||
                                            hrefLower.includes('/company/') ||
                                            hrefLower.includes('/wykonawca') ||
                                            hrefLower.includes('/profil')
                                        );
                                        if (!looksLikeCompany) continue;

                                        if (seen.has(hrefLower)) continue;
                                        seen.add(hrefLower);
                                        links.push({name: text, href: href});
                                    }

                                    return links;
                                }""")
                                return res if isinstance(res, list) else []

                            # Try multiple passes with scrolling to load more results
                            try:
                                seen_hrefs: set[str] = set()
                                for pass_idx in range(4):
                                    batch = _collect_company_links()
                                    for item in batch:
                                        if not isinstance(item, dict):
                                            continue
                                        name = str(item.get("name", "")).strip()
                                        href = str(item.get("href", "")).strip()
                                        if not name or not href:
                                            continue

                                        # Make URL absolute
                                        if not href.startswith("http"):
                                            from urllib.parse import urljoin
                                            href = urljoin(base_url, href)

                                        key = href.lower()
                                        if key in seen_hrefs:
                                            continue
                                        seen_hrefs.add(key)
                                        company_links.append({"name": name, "href": href})

                                    if len(company_links) >= 120:
                                        break

                                    # Scroll to load more
                                    try:
                                        page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
                                        page.wait_for_timeout(900)
                                    except Exception:
                                        break
                            except Exception:
                                pass
                            
                            _debug(f"extract_company_websites_deep: raw company_links type={type(company_links)}, value={str(company_links)[:200]}")

                            if not isinstance(company_links, list) or not company_links:
                                # For Oferteo, generic fallback is too noisy (categories, navigation, etc.).
                                # Fail fast so we don't save incorrect category URLs.
                                if "oferteo.pl" in str(page.url or ""):
                                    try:
                                        cur_url = str(page.url or "")
                                    except Exception:
                                        cur_url = ""
                                    try:
                                        cur_title = page.title() or ""
                                    except Exception:
                                        cur_title = ""

                                    try:
                                        sample = page.evaluate(
                                            r"""() => {
                                                const hrefs = Array.from(document.querySelectorAll('a[href]'))
                                                    .map(a => (a.getAttribute('href') || '').trim())
                                                    .filter(h => h);
                                                const interesting = hrefs.filter(h => /firma|wykonawca|profil/i.test(h));
                                                const text = (document.body && document.body.innerText) ? document.body.innerText.toLowerCase() : '';
                                                const maybeBot = (text.includes('captcha') || text.includes('cloudflare') || text.includes('robot'));
                                                return {
                                                    links_total: hrefs.length,
                                                    interesting_sample: interesting.slice(0, 12),
                                                    maybe_bot: maybeBot,
                                                };
                                            }"""
                                        )
                                    except Exception:
                                        sample = None

                                    try:
                                        console_wrapper.print(
                                            yaml.safe_dump(
                                                {
                                                    "status": "oferteo_no_profile_links",
                                                    "url": cur_url,
                                                    "title": cur_title,
                                                    "attempts": attempts,
                                                    "sample": sample,
                                                },
                                                sort_keys=False,
                                                allow_unicode=True,
                                            ).rstrip(),
                                            language="yaml",
                                        )
                                    except Exception:
                                        pass

                                    console_wrapper.print("⚠️  No /firma/ links found on Oferteo listing page", language="text")
                                    return RunnerResult(
                                        success=False,
                                        kind="dom",
                                        error="No company profile links found on Oferteo",
                                        data={"url": cur_url, "title": cur_title, "attempts": attempts, "sample": sample},
                                    )

                                _debug("extract_company_websites_deep: no company links found, trying fallback")
                                # Fallback: try to find any links that look like company profiles
                                company_links = page.evaluate(r"""() => {
                                    const links = [];
                                    const seen = new Set();
                                    const allLinks = Array.from(document.querySelectorAll('a[href]'));
                                    for (const el of allLinks) {
                                        const href = el.getAttribute('href') || '';
                                        const text = el.textContent.trim();
                                        // Look for any non-empty link with reasonable text
                                        if (!href || href.startsWith('#') || href.startsWith('javascript:')) continue;
                                        if (!text || text.length < 3 || text.length > 80) continue;
                                        // Skip common non-company links
                                        if (href.includes('facebook') || href.includes('twitter') ||
                                            href.includes('linkedin') || href.includes('instagram')) continue;
                                        if (seen.has(href)) continue;
                                        seen.add(href);
                                        links.push({name: text, href: href});
                                    }
                                    return links.slice(0, 50);
                                }""")
                                _debug(f"extract_company_websites_deep: fallback found {len(company_links) if isinstance(company_links, list) else 0} links")

                            if not isinstance(company_links, list) or not company_links:
                                console_wrapper.print("⚠️  No company links found on catalog page", language="text")
                                return RunnerResult(success=False, kind="dom", error="No company links found")

                            _debug(f"extract_company_websites_deep: found {len(company_links)} potential companies")
                            console_wrapper.print(f"🔍 Found {len(company_links)} company profiles to check", language="text")

                            # Process profiles until we gather max_companies real websites
                            target_websites = int(max_companies) if isinstance(max_companies, int) else 20
                            # Keep this bounded so the whole run can finish under CLI timeouts.
                            # We collect rows even when website is empty, so there's no need to scan huge lists.
                            max_profiles_to_check = max(10, min(int(target_websites), 25))
                            if isinstance(company_links, list):
                                console_wrapper.print(f"🔍 Found {len(company_links)} company profiles to check", language="text")

                            # Always keep a fast fallback list of profile URLs.
                            # Oferteo often doesn't expose external websites publicly; in that case we still want
                            # to save >= max_companies profile URLs.
                            profile_fallback: list[dict[str, str]] = []
                            try:
                                _max_companies_int = int(max_companies)
                            except Exception:
                                _max_companies_int = 20
                            _max_companies_int = max(1, min(_max_companies_int, 200))

                            for company in company_links[:_max_companies_int]:
                                try:
                                    name = str(company.get("name", "")).strip()
                                    href = str(company.get("href", "")).strip()
                                    if not href:
                                        continue
                                    if not href.startswith("http"):
                                        from urllib.parse import urljoin
                                        href = urljoin(base_url, href)
                                    profile_fallback.append({"name": name, "oferteo_url": href, "website": ""})
                                except Exception:
                                    continue

                            # Visit a small probe set of profiles and try to extract external websites.
                            # (If this succeeds, save_to_file will write websites; otherwise it will write profile URLs.)
                            target_websites = _max_companies_int
                            action_deadline = time.time() + 85.0
                            checked = 0
                            probe_profiles = min(max_profiles_to_check, _max_companies_int)

                            for idx, company in enumerate(company_links[:probe_profiles], 1):
                                try:
                                    if time.time() >= action_deadline:
                                        _debug("extract_company_websites_deep: time budget exceeded; stopping early")
                                        break

                                    checked += 1
                                    name = str(company.get("name", "")).strip()
                                    href = str(company.get("href", "")).strip()
                                    if not name or not href:
                                        continue

                                    # Make URL absolute
                                    if not href.startswith("http"):
                                        from urllib.parse import urljoin
                                        href = urljoin(base_url, href)

                                    _debug(f"Processing {idx}/{min(len(company_links), max_profiles_to_check)}: {name}")
                                    console_wrapper.print(f"[{idx}/{min(len(company_links), max_profiles_to_check)}] Checking: {name}", language="text")

                                    # Navigate to company profile
                                    page.goto(href, wait_until="domcontentloaded", timeout=7000)
                                    page.wait_for_timeout(250)
                                    self._dismiss_popups(page, schema_loader)

                                    # Find external website link on the profile page
                                    external_site = page.evaluate(r"""() => {
                                        // Look for external website links (not social media)
                                        const externalPatterns = [
                                            'a[href^="http"]:not([href*="oferteo.pl"]):not([href*="facebook.com"]):not([href*="twitter.com"]):not([href*="instagram.com"]):not([href*="linkedin.com"]):not([href*="youtube.com"])',
                                            // Sometimes Oferteo uses redirect links to external sites
                                            'a[href*="oferteo.pl"][href*="redirect"]',
                                            'a[href*="oferteo.pl"][href*="url="]',
                                            '.website a', '.www a', '.company-website a',
                                            'a.external-link', 'a[rel="nofollow"]',
                                            '[data-website] a', '.biz-website a'
                                        ];
                                        for (const pattern of externalPatterns) {
                                            const links = document.querySelectorAll(pattern);
                                            for (const link of links) {
                                                const href = link.getAttribute('href');
                                                if (href && href.startsWith('http') && 
                                                    !href.includes('oferteo.pl') &&
                                                    !href.includes('facebook.com') &&
                                                    !href.includes('google.com')) {
                                                    return href;
                                                }

                                                // Allow oferteo redirects (decoded later in Python)
                                                if (href && href.includes('oferteo.pl') && (href.includes('redirect') || href.includes('url='))) {
                                                    return href;
                                                }
                                            }
                                        }
                                        // Try to find by text content
                                        const allLinks = document.querySelectorAll('a[href^="http"]');
                                        for (const link of allLinks) {
                                            const href = link.getAttribute('href');
                                            const text = link.textContent.toLowerCase();
                                            if (href && !href.includes('oferteo.pl') && 
                                                (text.includes('www.') || text.includes('strona') || 
                                                 text.includes('website') || text.includes('witryna'))) {
                                                return href;
                                            }
                                        }

                                        // Last resort: find anything that looks like a domain in visible text
                                        const bodyText = (document.body && document.body.innerText) ? document.body.innerText : '';
                                        const m = bodyText.match(/\b([a-z0-9][a-z0-9\-]{0,62}\.)+[a-z]{2,}\b/i);
                                        if (m && m[0]) {
                                            return m[0];
                                        }
                                        return null;
                                    }""")

                                    # Filter out non-company websites (app stores, social, tracking)
                                    if external_site and isinstance(external_site, str):
                                        raw_ext = external_site.strip()
                                        ext_low = raw_ext.lower()

                                        # If it's a bare domain found in text, normalize to https://
                                        if ext_low and (not ext_low.startswith("http")) and "." in ext_low and "/" not in ext_low:
                                            raw_ext = f"https://{raw_ext}"
                                            ext_low = raw_ext.lower()

                                        # Decode oferteo redirect links if present
                                        try:
                                            from urllib.parse import parse_qs, unquote, urlparse

                                            parsed = urlparse(raw_ext)
                                            if "oferteo.pl" in (parsed.netloc or ""):
                                                qs = parse_qs(parsed.query or "")
                                                for key in ("url", "u", "target", "redirect"):
                                                    if key in qs and qs[key]:
                                                        cand = unquote(str(qs[key][0]))
                                                        if cand.startswith("http"):
                                                            raw_ext = cand
                                                            ext_low = raw_ext.lower()
                                                            break
                                        except Exception:
                                            pass

                                        bad_domains = [
                                            "apps.apple.com",
                                            "play.google.com",
                                            "itunes.apple.com",
                                            "oferteo.pl",
                                            "facebook.com",
                                            "instagram.com",
                                            "linkedin.com",
                                            "twitter.com",
                                            "x.com",
                                            "youtube.com",
                                            "tiktok.com",
                                            "goo.gl",
                                            "bit.ly",
                                        ]
                                        if any(b in ext_low for b in bad_domains):
                                            external_site = None
                                        else:
                                            external_site = raw_ext

                                    if external_site and isinstance(external_site, str):
                                        companies_data.append({
                                            "name": name,
                                            "oferteo_url": href,
                                            "website": external_site
                                        })
                                        console_wrapper.print(f"   ✓ Found website: {external_site}", language="text")
                                        _debug(f"Found website for {name}: {external_site}")

                                        # Stop early when we have enough real websites
                                        real_websites = [c for c in companies_data if c.get("website")]
                                        if len(real_websites) >= target_websites:
                                            break
                                    else:
                                        console_wrapper.print(f"   ⚠ No external website found", language="text")
                                        companies_data.append({
                                            "name": name,
                                            "oferteo_url": href,
                                            "website": ""
                                        })

                                    # Go back to catalog (lighter than re-loading base_url each time)
                                    try:
                                        page.go_back(wait_until="domcontentloaded", timeout=9000)
                                        page.wait_for_timeout(200)
                                    except Exception:
                                        page.goto(base_url, wait_until="domcontentloaded", timeout=15000)
                                        page.wait_for_timeout(300)

                                except Exception as e:
                                    _debug(f"Error processing company: {e}")
                                    continue

                            # If we didn't find any real websites, fall back to the listing profile URLs.
                            # This guarantees that downstream save_to_file can write >= max_companies entries.
                            try:
                                real_websites_cnt = len([c for c in companies_data if str(c.get("website") or "").strip()])
                            except Exception:
                                real_websites_cnt = 0
                            if real_websites_cnt == 0 and profile_fallback:
                                companies_data = profile_fallback

                            _debug(f"extract_company_websites_deep: extracted {len(companies_data)} companies with websites")

                            if not companies_data:
                                console_wrapper.print("⚠️  No company website data extracted", language="text")
                                return RunnerResult(success=False, kind="dom", error="No company website data extracted")

                            # Store for save_to_csv action
                            extracted_data.extend(companies_data)

                            # Display results
                            console_wrapper.print(f"\n✅ Extracted {len(companies_data)} companies with websites:", language="text")
                            for c in companies_data[:10]:
                                website = c.get("website", "N/A")
                                console_wrapper.print(f"  • {c['name']}: {website}", language="text")
                            if len(companies_data) > 10:
                                console_wrapper.print(f"  ... and {len(companies_data) - 10} more", language="text")

                        except Exception as e:
                            return RunnerResult(success=False, kind="dom", error=f"Action {i}: Deep company extraction failed: {e}")

                    elif action == "save_to_file":
                        # Save extracted data to a file
                        try:
                            filename = action_spec.get("filename", "extracted_data.txt")
                            file_format = action_spec.get("format", "txt")
                            also_copy = bool(action_spec.get("also_copy") or action_spec.get("copy_to_clipboard"))
                            also_print = bool(action_spec.get("also_print") or action_spec.get("print_to_terminal"))
                            _debug(f"save_to_file: saving {len(extracted_data)} items to {filename}")

                            if not extracted_data:
                                console_wrapper.print("⚠️  No data to save (extraction produced no results)", language="text")
                                continue

                            filepath = Path(filename)
                            seen: set[str] = set()
                            lines: list[str] = []

                            def _is_bad_website(u: str) -> bool:
                                low = (u or "").strip().lower()
                                if not low:
                                    return True
                                if not (low.startswith("http://") or low.startswith("https://")):
                                    return True
                                bad = [
                                    "oferteo.pl",
                                    "apps.apple.com",
                                    "play.google.com",
                                    "itunes.apple.com",
                                    "facebook.com",
                                    "instagram.com",
                                    "linkedin.com",
                                    "twitter.com",
                                    "x.com",
                                    "youtube.com",
                                    "tiktok.com",
                                    "business.safety.google",
                                    "policies.google.com",
                                ]
                                return any(b in low for b in bad)

                            dicts = [it for it in extracted_data if isinstance(it, dict)]
                            has_website_field = any("website" in it for it in dicts)
                            has_real_websites = False
                            if has_website_field:
                                for it in dicts:
                                    try:
                                        w = str(it.get("website") or "").strip()
                                    except Exception:
                                        w = ""
                                    if w and not _is_bad_website(w):
                                        has_real_websites = True
                                        break

                            for item in extracted_data:
                                if isinstance(item, dict):
                                    candidate = ""
                                    if has_website_field:
                                        if has_real_websites:
                                            # In company-website extraction mode, only write real external websites.
                                            if item.get("website"):
                                                candidate = str(item.get("website") or "").strip()
                                            else:
                                                candidate = ""
                                        else:
                                            # Fallback: profiles do not expose external websites. Save profile URLs instead.
                                            if item.get("oferteo_url"):
                                                candidate = str(item.get("oferteo_url") or "").strip()
                                            elif item.get("url"):
                                                candidate = str(item.get("url") or "").strip()
                                            else:
                                                candidate = ""
                                    elif item.get("url"):
                                        candidate = str(item.get("url") or "").strip()
                                    elif item.get("oferteo_url"):
                                        candidate = str(item.get("oferteo_url") or "").strip()
                                    else:
                                        candidate = " ".join(str(v) for v in item.values()).strip()

                                    if has_website_field and has_real_websites and _is_bad_website(candidate):
                                        continue

                                    if not candidate:
                                        continue
                                    key = candidate.lower()
                                    if key in seen:
                                        continue
                                    seen.add(key)
                                    lines.append(candidate)
                                else:
                                    candidate = str(item).strip()
                                    if not candidate:
                                        continue
                                    key = candidate.lower()
                                    if key in seen:
                                        continue
                                    seen.add(key)
                                    lines.append(candidate)

                            filepath.write_text("\n".join(lines) + "\n", encoding="utf-8")

                            console_wrapper.print(f"💾 Saved {len(lines)} entries to {filepath.resolve()}", language="text")

                            if also_print:
                                try:
                                    console_wrapper.print("\n".join(lines), language="text")
                                except Exception as pe:
                                    _debug(f"save_to_file: print failed: {pe}")

                            if also_copy:
                                copied = False
                                copy_err = None
                                payload = ("\n".join(lines) + "\n").encode("utf-8")
                                try:
                                    # Prefer Wayland
                                    p = subprocess.Popen(
                                        ["wl-copy"],
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.DEVNULL,
                                        stderr=subprocess.PIPE,
                                    )
                                    _, err = p.communicate(payload, timeout=3)
                                    copied = p.returncode == 0
                                    if not copied:
                                        copy_err = (err or b"").decode("utf-8", errors="ignore")
                                except FileNotFoundError:
                                    pass
                                except Exception as ce:
                                    copy_err = str(ce)

                                if not copied:
                                    try:
                                        p = subprocess.Popen(
                                            ["xclip", "-selection", "clipboard"],
                                            stdin=subprocess.PIPE,
                                            stdout=subprocess.DEVNULL,
                                            stderr=subprocess.PIPE,
                                        )
                                        _, err = p.communicate(payload, timeout=3)
                                        copied = p.returncode == 0
                                        if not copied:
                                            copy_err = (err or b"").decode("utf-8", errors="ignore")
                                    except FileNotFoundError:
                                        pass
                                    except Exception as ce:
                                        copy_err = str(ce)

                                if not copied:
                                    try:
                                        p = subprocess.Popen(
                                            ["xsel", "--clipboard", "--input"],
                                            stdin=subprocess.PIPE,
                                            stdout=subprocess.DEVNULL,
                                            stderr=subprocess.PIPE,
                                        )
                                        _, err = p.communicate(payload, timeout=3)
                                        copied = p.returncode == 0
                                        if not copied:
                                            copy_err = (err or b"").decode("utf-8", errors="ignore")
                                    except FileNotFoundError:
                                        pass
                                    except Exception as ce:
                                        copy_err = str(ce)

                                if copied:
                                    console_wrapper.print(
                                        yaml.safe_dump(
                                            {
                                                "status": "copied_to_clipboard",
                                                "lines": len(lines),
                                            },
                                            sort_keys=False,
                                            allow_unicode=True,
                                        ).rstrip(),
                                        language="yaml",
                                    )
                                else:
                                    console_wrapper.print(
                                        yaml.safe_dump(
                                            {
                                                "status": "clipboard_copy_skipped",
                                                "reason": "no_clipboard_tool",
                                                "error": str(copy_err or ""),
                                            },
                                            sort_keys=False,
                                            allow_unicode=True,
                                        ).rstrip(),
                                        language="yaml",
                                    )

                            console_wrapper.print(
                                yaml.safe_dump(
                                    {
                                        "status": "saved_to_file",
                                        "filename": str(filepath.resolve()),
                                        "entries": len(lines),
                                    },
                                    sort_keys=False, allow_unicode=True,
                                ).rstrip(),
                                language="yaml",
                            )
                            _debug(f"save_to_file: wrote {len(lines)} lines to {filepath.resolve()}")

                        except Exception as e:
                            return RunnerResult(success=False, kind="dom", error=f"Action {i}: Save to file failed: {e}")

                    elif action == "save_to_csv":
                        # Save extracted data to a CSV file
                        try:
                            filename = action_spec.get("filename", "companies.csv")
                            _debug(f"save_to_csv: saving {len(extracted_data)} items to {filename}")

                            if not extracted_data:
                                console_wrapper.print("⚠️  No data to save (extraction produced no results)", language="text")
                                continue

                            import csv
                            from io import StringIO

                            filepath = Path(filename)

                            # Determine fieldnames from first item
                            fieldnames = list(extracted_data[0].keys()) if extracted_data else ["name", "website"]

                            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                                writer.writeheader()
                                for item in extracted_data:
                                    writer.writerow(item)

                            console_wrapper.print(f"💾 Saved {len(extracted_data)} entries to CSV: {filepath.resolve()}", language="text")
                            console_wrapper.print(
                                yaml.safe_dump(
                                    {
                                        "status": "saved_to_csv",
                                        "filename": str(filepath.resolve()),
                                        "entries": len(extracted_data),
                                        "columns": fieldnames,
                                    },
                                    sort_keys=False, allow_unicode=True,
                                ).rstrip(),
                                language="yaml",
                            )
                            _debug(f"save_to_csv: wrote {len(extracted_data)} rows to {filepath.resolve()}")

                        except Exception as e:
                            return RunnerResult(success=False, kind="dom", error=f"Action {i}: Save to CSV failed: {e}")

                    else:
                        return RunnerResult(success=False, kind="dom", error=f"Action {i}: Unsupported action: {action}")

                    # Strategy 9: Timing metric per action
                    _action_elapsed = (time.perf_counter() - _action_t0) * 1000
                    _debug(f"action[{i}] '{action}' completed in {_action_elapsed:.0f}ms")
                
                # Keep browser open for a moment to see the result
                page.wait_for_timeout(2000)
                
                # Stop video recording if active — save Playwright video to target path
                video_saved_path = None
                if video_recorder and video_recorder.is_recording:
                    try:
                        pw_video = page.video
                        if pw_video:
                            # Playwright auto-saves .webm; save_as copies to our target
                            target = video_recorder.video_path or str(Path(_effective_video_dir) / "browser_automation.webm")
                            pw_video.save_as(target)
                            video_saved_path = target
                            console.print(f"[green]🎥 Video saved: {target}[/green]")
                    except Exception as ve:
                        _debug(f"Video save_as failed: {ve}")
                    video_recorder.stop_recording(console)
                
                browser.close()
                
                result_data: dict[str, Any] = {"url": url, "actions_executed": len(actions), "extracted_count": len(extracted_data)}
                if video_saved_path:
                    result_data["video"] = video_saved_path
                return RunnerResult(
                    success=True, kind="dom",
                    data=result_data,
                )
            
            except Exception as e:
                # Stop video recording if active (even on error)
                if video_recorder and video_recorder.is_recording:
                    try:
                        pw_video = page.video
                        if pw_video and video_recorder.video_path:
                            pw_video.save_as(video_recorder.video_path)
                            console.print(f"[yellow]🎥 Partial video saved: {video_recorder.video_path}[/yellow]")
                    except Exception:
                        pass
                    video_recorder.stop_recording(console)
                
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

    # ═══ Multi-Step ActionPlan Execution ═════════════════════════════════

    def execute_action_plan(
        self,
        plan,
        *,
        dry_run: bool = False,
        confirm: bool = False,
    ) -> RunnerResult:
        """Execute an ActionPlan step by step using Playwright.

        Args:
            plan: ActionPlan instance with steps to execute
            dry_run: If True, only show the plan without executing
            confirm: If True, user has confirmed execution
        """
        from nlp2cmd.automation.action_planner import ActionPlan, ActionStep

        console = Console()

        console.print(f"\n[bold]🎯 Plan wykonania ({len(plan.steps)} kroków):[/bold]")
        for i, step in enumerate(plan.steps, 1):
            console.print(f"  {i}. {step.description or step.action}")

        if dry_run:
            return RunnerResult(
                success=True, kind="action_plan",
                data={"dry_run": True, "steps": [s.to_dict() for s in plan.steps]},
            )

        try:
            from playwright.sync_api import sync_playwright
        except ImportError as e:
            return RunnerResult(
                success=False, kind="action_plan",
                error=f"Playwright not available: {e}",
            )

        user_data_dir = Path.home() / ".nlp2cmd" / "browser_profile"
        user_data_dir.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as pw:
            try:
                context = pw.chromium.launch_persistent_context(
                    user_data_dir=str(user_data_dir),
                    headless=self.headless,
                    viewport={"width": 1280, "height": 720},
                )
            except Exception:
                if self.headless:
                    raise
                # Fallback for environments without a working headed display.
                context = pw.chromium.launch_persistent_context(
                    user_data_dir=str(user_data_dir),
                    headless=True,
                    viewport={"width": 1280, "height": 720},
                )
            page = context.pages[0] if context.pages else context.new_page()

            variables: dict[str, str] = {}  # stores results from prior steps
            results_log: list[dict] = []

            for i, step in enumerate(plan.steps):
                step_desc = step.description or step.action
                console.print(f"\n[cyan]▸ Krok {i+1}/{len(plan.steps)}:[/cyan] {step_desc}")

                if step.action == "new_tab":
                    page = context.new_page()
                    try:
                        page.bring_to_front()
                    except Exception:
                        pass
                    console.print("  [green]✓[/green] OK")
                    results_log.append({
                        "step": i + 1,
                        "action": step.action,
                        "status": "ok",
                        "stored": step.store_as,
                    })
                    continue

                try:
                    result = self._execute_plan_step(
                        page, context, step, variables
                    )
                    if step.store_as and result:
                        variables[step.store_as] = result
                        console.print(f"  [green]✓[/green] Zapisano jako ${step.store_as}")
                    else:
                        console.print(f"  [green]✓[/green] OK")

                    results_log.append({
                        "step": i + 1, "action": step.action,
                        "status": "ok", "stored": step.store_as,
                    })

                except Exception as e:
                    console.print(f"  [red]✗[/red] Błąd: {e}")
                    results_log.append({
                        "step": i + 1, "action": step.action,
                        "status": "error", "error": str(e),
                    })

                    if step.retry_on_fail:
                        console.print(f"  [yellow]↻[/yellow] Retry...")
                        page.wait_for_timeout(1000)
                        try:
                            result = self._execute_plan_step(
                                page, context, step, variables
                            )
                            if step.store_as and result:
                                variables[step.store_as] = result
                            console.print(f"  [green]✓[/green] Retry OK")
                            results_log[-1]["status"] = "ok_retry"
                        except Exception as e2:
                            console.print(f"  [red]✗[/red] Retry failed: {e2}")
                            results_log[-1]["status"] = "failed"

            context.close()

        return RunnerResult(
            success=all(r["status"] != "failed" for r in results_log),
            kind="action_plan",
            data={"steps": results_log, "variables": variables},
        )

    def _execute_plan_step(self, page, context, step, variables: dict) -> Optional[str]:
        """Execute a single ActionPlan step. Returns extracted value or None."""
        params = self._resolve_plan_variables(step.params, variables)
        action = step.action

        # Local console for interactive prompts in multi-step plans
        console = Console()

        if action == "browser_open":
            pass  # context already open

        elif action == "navigate":
            url = params.get("url", "")
            if not url.startswith("http"):
                url = f"https://{url}"
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(1000)

        elif action == "new_tab":
            page = context.new_page()

        elif action == "click":
            selector = params.get("selector")
            text = params.get("text")
            if text:
                page.get_by_text(text).first.click()
            elif selector:
                page.click(selector)

        elif action == "type_text":
            page.fill(params.get("selector", "input"), params.get("text", ""))

        elif action in ("extract_text", "extract_api_key"):
            # Do not scrape API keys or other secrets from pages.
            # API keys should be manually copied by the user and pasted via prompt_secret.
            if action == "extract_api_key":
                raise ValueError("extract_api_key is disabled for safety. Use prompt_secret to paste the key.")

            pattern = params.get("pattern")
            selectors = params.get("selectors", ["code", "pre", ".api-key"])

            for sel in selectors:
                try:
                    elements = page.query_selector_all(sel)
                    for el in elements:
                        text = (el.text_content() or "").strip()
                        if pattern and re.search(pattern, text):
                            return re.search(pattern, text).group(0)
                        elif not pattern and len(text) > 10:
                            return text
                except Exception:
                    continue

            # Fallback: regex on full body
            body = page.text_content("body") or ""
            if pattern:
                match = re.search(pattern, body)
                if match:
                    return match.group(0)
            return None

        elif action == "save_env":
            var_name = params.get("var_name", "UNKNOWN_KEY")
            value = params.get("value", "")
            file_path = params.get("file", ".env")

            # Resolve $variable references
            if isinstance(value, str) and value.startswith("$"):
                value = variables.get(value[1:], "")

            if not value:
                raise ValueError(f"Brak wartości do zapisania dla {var_name}")

            env_path = Path(file_path)
            existing = env_path.read_text() if env_path.exists() else ""

            if f"{var_name}=" in existing:
                updated = re.sub(
                    rf"{re.escape(var_name)}=.*",
                    f'{var_name}="{value}"',
                    existing,
                )
                env_path.write_text(updated)
            else:
                with open(env_path, "a") as f:
                    f.write(f'\n{var_name}="{value}"\n')

            return value

        elif action == "prompt_secret":
            prompt = str(params.get("prompt") or "Enter secret: ")
            env_var = str(params.get("env_var") or "").strip()

            # Non-interactive support: allow providing secret via environment.
            if env_var:
                try:
                    env_val = os.environ.get(env_var)
                except Exception:
                    env_val = None
                if isinstance(env_val, str) and env_val.strip():
                    return env_val.strip()

            # If stdin is not a TTY, prompting will fail (EOF). Provide a clear instruction.
            try:
                is_tty = bool(getattr(sys.stdin, "isatty", lambda: False)())
            except Exception:
                is_tty = False
            if not is_tty:
                if env_var:
                    raise ValueError(
                        f"prompt_secret requires interactive TTY or {env_var} in environment"
                    )
                raise ValueError("prompt_secret requires interactive TTY")

            try:
                import getpass
                val = getpass.getpass(prompt)
            except Exception:
                # Fallback (echoed) if getpass is unavailable
                val = console.input(prompt)

            val = str(val or "").strip()
            if not val:
                raise ValueError("No secret provided")
            return val

        elif action == "screenshot":
            path = params.get(
                "path", f"/tmp/nlp2cmd_screenshot_{int(time.time())}.png"
            )
            page.screenshot(path=path, full_page=True)
            return path

        elif action == "wait":
            ms = int(params.get("ms", 1000))
            page.wait_for_timeout(ms)

        elif action == "login":
            email = params.get("email", "")
            password = params.get("password", "")
            email_field = page.query_selector(
                'input[type="email"], input[name*="email"], input[name*="login"]'
            )
            if email_field:
                email_field.fill(email)
            pass_field = page.query_selector('input[type="password"]')
            if pass_field:
                pass_field.fill(password)
            submit = page.query_selector(
                'button[type="submit"], input[type="submit"]'
            )
            if submit:
                submit.click()

        elif action == "fill_form":
            fields = params.get("fields", {})
            for selector, value in fields.items():
                try:
                    page.fill(selector, str(value))
                except Exception:
                    pass

        elif action == "submit_form":
            submit = page.query_selector(
                'button[type="submit"], input[type="submit"], form button'
            )
            if submit:
                submit.click()

        elif action == "echo":
            _debug(params.get("message", ""))

        return None

    @staticmethod
    def _resolve_plan_variables(params: dict, variables: dict) -> dict:
        """Replace $variable references with values from prior steps."""
        resolved = {}
        for k, v in params.items():
            if isinstance(v, str) and v.startswith("$"):
                resolved[k] = variables.get(v[1:], v)
            else:
                resolved[k] = v
        return resolved

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
