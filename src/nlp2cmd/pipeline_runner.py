from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import shutil
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
                            try:
                                pw_video.save_as(target)
                                video_saved_path = target
                            except Exception:
                                try:
                                    video_saved_path = pw_video.path()
                                except Exception:
                                    video_saved_path = None
                            if video_saved_path:
                                console.print(f"[green]🎥 Video saved: {video_saved_path}[/green]")
                    except Exception as ve:
                        _debug(f"Video save_as failed: {ve}")
                    video_recorder.stop_recording(console, saved_path=video_saved_path)
                
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
            try:
                return json.loads(m.group(1))
            except Exception:
                pass

        # Fallback: try parsing the whole text as JSON
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

        # Fallback: find first { ... } block
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(raw[start:end + 1])
            except Exception:
                pass

        return None

    @staticmethod
    def _detect_desktop_backend() -> str:
        """Detect best desktop automation backend: 'ydotool', 'xdotool', or 'none'."""
        session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
        is_wayland = session_type == "wayland" or bool(os.environ.get("WAYLAND_DISPLAY"))
        if is_wayland and shutil.which("ydotool"):
            return "ydotool"
        if shutil.which("xdotool"):
            return "xdotool"
        if shutil.which("wmctrl"):
            return "wmctrl"  # wmctrl only for focus, not type/key
        return "none"

    def _execute_desktop_plan_step(self, step, variables: dict) -> Optional[str]:
        """Execute an ActionPlan step via local desktop automation.

        Supports three backends:
        - ydotool: works on Wayland (requires ydotoold daemon)
        - xdotool: works on X11
        - wmctrl: X11 window management only
        """
        params = self._resolve_plan_variables(getattr(step, "params", {}) or {}, variables)
        action = str(getattr(step, "action", "") or "")
        backend = self._detect_desktop_backend()

        if backend == "none":
            raise ValueError(
                "No desktop automation tool available. "
                "On Wayland: sudo apt install ydotool && sudo systemctl enable --now ydotool. "
                "On X11: sudo apt install xdotool wmctrl."
            )

        if action == "desktop_focus_app":
            title = str(params.get("title") or "Firefox")
            if backend == "ydotool":
                # ydotool can't focus windows; try gdbus on GNOME
                _debug(f"desktop_focus_app: ydotool can't focus windows, trying Alt+Tab")
                subprocess.run(["ydotool", "key", "56:1", "15:1", "15:0", "56:0"], check=False)
                time.sleep(0.3)
                return None
            if shutil.which("wmctrl") is not None:
                subprocess.run(["wmctrl", "-a", title], check=True)
                return None
            # xdotool fallback
            candidates = [
                ("--name", title),
                ("--name", "Mozilla Firefox"),
                ("--class", title),
                ("--class", "firefox"),
                ("--class", "Navigator"),
            ]
            win_id = ""
            for flag, value in candidates:
                try:
                    out = subprocess.check_output(
                        ["xdotool", "search", "--onlyvisible", flag, value],
                        stderr=subprocess.DEVNULL,
                        text=True,
                    )
                    win_id = (out.strip().splitlines() or [""])[0].strip()
                    if win_id:
                        break
                except Exception:
                    continue
            if win_id:
                subprocess.run(["xdotool", "windowactivate", "--sync", win_id], check=True)
            else:
                _debug(f"desktop_focus_app: could not find visible window for '{title}', continuing")
            return None

        if action == "desktop_shortcut":
            keys = str(params.get("keys") or "").strip() or "ctrl+t"
            if backend == "ydotool":
                ydotool_keys = self._xdotool_keys_to_ydotool(keys)
                subprocess.run(["ydotool", "key"] + ydotool_keys, check=True)
            else:
                subprocess.run(["xdotool", "key", keys], check=True)
            return None

        if action == "desktop_key":
            key = str(params.get("key") or "Return").strip() or "Return"
            if backend == "ydotool":
                ydotool_keys = self._xdotool_keys_to_ydotool(key)
                subprocess.run(["ydotool", "key"] + ydotool_keys, check=True)
            else:
                subprocess.run(["xdotool", "key", key], check=True)
            return None

        if action == "desktop_type":
            txt = str(params.get("text") or "")
            if not txt.strip():
                return None
            if backend == "ydotool":
                subprocess.run(["ydotool", "type", "--key-delay", "20", txt], check=True)
            else:
                subprocess.run(["xdotool", "type", "--delay", "20", txt], check=True)
            return None

        if action == "wait":
            ms = int(params.get("ms", 500))
            time.sleep(max(ms, 0) / 1000.0)
            return None

        if action == "desktop_wait":
            ms = int(params.get("ms", 500))
            time.sleep(max(ms, 0) / 1000.0)
            return None

        if action == "open_firefox_tab":
            url = str(params.get("url") or "").strip()
            if not url:
                return None
            if shutil.which("firefox") is None:
                raise ValueError("Firefox executable not found in PATH")

            # Open a new tab in existing Firefox instance (remote command).
            # This is more reliable than synthetic key events.
            try:
                subprocess.run(["firefox", "--new-tab", url], check=True)
            except Exception:
                subprocess.run(["firefox", "--new-window", url], check=True)
            return None

        if action == "check_session":
            # In desktop mode we opened the URL in the user's real Firefox.
            # We don't have a Playwright page to inspect, so just inform the user.
            service = params.get("service", "unknown")
            console = Console()
            console.print(f"  [dim]🔍 Strona {service} została otwarta w Twojej przeglądarce.[/dim]")
            console.print(f"  [dim]   Sprawdź, czy jesteś zalogowany. Jeśli nie — zaloguj się teraz.[/dim]")
            # Give user time to check
            time.sleep(2)
            return "desktop_skipped"

        # Reuse safe non-desktop steps
        if action == "echo":
            msg = str(params.get("message", "") or params.get("text", ""))
            if msg:
                _debug(msg)
                console = Console()
                for line in msg.split("\n"):
                    console.print(f"  [dim]{line}[/dim]")
            return None

        if action == "prompt_secret":
            from nlp2cmd.automation.action_planner import ActionStep as _ActionStep
            _step = _ActionStep(
                action="prompt_secret",
                params=params,
                store_as=getattr(step, "store_as", None),
                retry_on_fail=getattr(step, "retry_on_fail", False),
            )
            console = Console()
            console.print(f"  [dim]🔐 prompt_secret: env_var={params.get('env_var', '?')}[/dim]")
            result = self._execute_plan_step(page=None, context=None, step=_step, variables=variables)
            if result:
                console.print(f"  [dim]   ✓ Otrzymano klucz ({len(result)} znaków)[/dim]")
                # Validate key pattern if available in variables
                key_pattern = variables.get("_key_pattern", "")
                if key_pattern:
                    import re as _re
                    if _re.match(key_pattern, result):
                        console.print(f"  [green]   ✓ Klucz pasuje do wzorca: {key_pattern}[/green]")
                    else:
                        console.print(f"  [yellow]   ⚠ Klucz NIE pasuje do wzorca: {key_pattern}[/yellow]")
                        console.print(f"  [yellow]     Kontynuuję mimo to — sprawdź poprawność klucza.[/yellow]")
            else:
                console.print(f"  [red]   ✗ Nie otrzymano klucza![/red]")
            return result

        if action == "save_env":
            from nlp2cmd.automation.action_planner import ActionStep as _ActionStep
            _step = _ActionStep(
                action="save_env",
                params=params,
                store_as=getattr(step, "store_as", None),
                retry_on_fail=getattr(step, "retry_on_fail", False),
            )
            console = Console()
            var_name = params.get("var_name", "?")
            file_path = params.get("file", ".env")
            console.print(f"  [dim]💾 save_env: {var_name} → {file_path}[/dim]")
            result = self._execute_plan_step(page=None, context=None, step=_step, variables=variables)
            if result:
                console.print(f"  [green]   ✓ Zapisano {var_name} ({len(result)} znaków) do {file_path}[/green]")
            else:
                console.print(f"  [red]   ✗ Nie zapisano wartości![/red]")
            return result

        if action == "verify_env":
            console = Console()
            var_name = params.get("var_name", "UNKNOWN")
            file_path = params.get("file", ".env")
            return self._do_verify_env(console, var_name, file_path, variables)

        raise ValueError(f"Unsupported desktop plan action: {action}")

    @staticmethod
    def _xdotool_keys_to_ydotool(keys: str) -> list[str]:
        """Convert xdotool key names to ydotool keycode sequences.

        ydotool uses Linux input event keycodes (evdev), not X11 keysyms.
        Format: keycode:1 (press), keycode:0 (release).
        """
        _KEYMAP = {
            "ctrl": "29", "control": "29",
            "alt": "56", "shift": "42", "super": "125",
            "return": "28", "enter": "28",
            "tab": "15", "escape": "1", "esc": "1",
            "space": "57", "backspace": "14", "delete": "111",
            "up": "103", "down": "108", "left": "105", "right": "106",
            "home": "102", "end": "107",
            "pageup": "104", "page_up": "104",
            "pagedown": "109", "page_down": "109",
            "f1": "59", "f2": "60", "f3": "61", "f4": "62",
            "f5": "63", "f6": "64", "f7": "65", "f8": "66",
            "f9": "67", "f10": "68", "f11": "87", "f12": "88",
        }
        # Letters a-z
        for i, c in enumerate("abcdefghijklmnopqrstuvwxyz"):
            _KEYMAP[c] = str(30 + i if i < 12 else 44 + i - 12 if i < 24 else 50 + i - 24)
        # More accurate letter keycodes
        _LETTER_CODES = {
            "a": "30", "b": "48", "c": "46", "d": "32", "e": "18", "f": "33",
            "g": "34", "h": "35", "i": "23", "j": "36", "k": "37", "l": "38",
            "m": "50", "n": "49", "o": "24", "p": "25", "q": "16", "r": "19",
            "s": "31", "t": "20", "u": "22", "v": "47", "w": "17", "x": "45",
            "y": "21", "z": "44",
        }
        _KEYMAP.update(_LETTER_CODES)

        parts = keys.lower().replace("+", " ").split()
        codes = [_KEYMAP.get(p, p) for p in parts]

        # Build press-all then release-all sequence
        result = []
        for code in codes:
            result.append(f"{code}:1")
        for code in reversed(codes):
            result.append(f"{code}:0")
        return result

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
        video_fmt: Optional[str] = None,
        video_dir: Optional[str] = None,
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

        # Detect steps that need the desktop executor (not Playwright)
        _DESKTOP_ACTIONS = frozenset({"open_firefox_tab", "desktop_wait"})
        try:
            steps_iter = getattr(plan, "steps", None) or []
            has_desktop_steps = any(
                str(getattr(s, "action", "")).startswith("desktop_")
                or str(getattr(s, "action", "")) in _DESKTOP_ACTIONS
                for s in steps_iter
            )
        except Exception:
            has_desktop_steps = False

        console.print(f"\n[bold]🎯 Plan wykonania ({len(plan.steps)} kroków):[/bold]")
        console.print(f"  [dim]Źródło: {getattr(plan, 'source', '?')} | "
                       f"Pewność: {getattr(plan, 'confidence', 0):.0%} | "
                       f"Est. czas: {getattr(plan, 'estimated_time_ms', 0)/1000:.1f}s[/dim]")
        for i, step in enumerate(plan.steps, 1):
            action_tag = f"[cyan]{step.action}[/cyan]" if hasattr(step, 'action') else ""
            console.print(f"  {i}. {step.description or step.action} {action_tag}")

        if dry_run:
            return RunnerResult(
                success=True, kind="action_plan",
                data={"dry_run": True, "steps": [s.to_dict() for s in plan.steps]},
            )

        # Video recording setup
        should_record_video = False
        _effective_video_dir = video_dir or self.video_dir or "./recordings"
        _fmt = video_fmt or self.video_fmt
        
        if _fmt:
            should_record_video = True
            _debug(f"Video recording enabled for ActionPlan via --video {_fmt}")
        else:
            try:
                is_tty = bool(getattr(sys.stdin, "isatty", lambda: False)())
            except Exception:
                is_tty = False
            if confirm and is_tty:
                should_record_video, _effective_video_dir = ask_for_video_recording(console)

        video_recorder = None
        video_saved_path = None
        
        if should_record_video:
            video_recorder = VideoRecorder(output_dir=_effective_video_dir)
            video_path = video_recorder.start_recording(name_prefix="action_plan_automation")
            if video_path:
                console.print(f"[dim]🎥 Nagrywanie wideo: {video_path}[/dim]")

        if has_desktop_steps:
            variables: dict[str, str] = {}
            results_log: list[dict] = []
            # Store key pattern in variables so validation steps can access it
            try:
                from nlp2cmd.automation.action_planner import KNOWN_SERVICES
                for _svc_name, _svc in KNOWN_SERVICES.items():
                    if _svc_name in (getattr(plan, "query", "") or "").lower():
                        variables["_key_pattern"] = _svc.get("key_pattern", "")
                        break
            except Exception:
                pass

            # Critical actions — if these fail, abort the plan
            _CRITICAL_ACTIONS = frozenset({"prompt_secret", "save_env"})
            plan_aborted = False

            try:
                for i, step in enumerate(plan.steps):
                    step_desc = step.description or step.action
                    step_start = time.time()
                    console.print(
                        f"\n[cyan]▸ Krok {i+1}/{len(plan.steps)}:[/cyan] {step_desc}"
                        f"  [dim]({step.action})[/dim]"
                    )
                    if step.params:
                        # Log params (mask secrets)
                        safe_params = {
                            k: ("***" if "secret" in k or "password" in k or "key" in k.lower() else v)
                            for k, v in step.params.items()
                        }
                        _debug(f"  params: {safe_params}")

                    try:
                        result = self._execute_desktop_plan_step(step, variables)
                        elapsed_ms = (time.time() - step_start) * 1000

                        if step.store_as and result:
                            variables[step.store_as] = result
                            console.print(f"  [green]✓[/green] Zapisano jako ${step.store_as}")
                        else:
                            console.print(f"  [green]✓[/green] OK")

                        console.print(f"  [dim]   ⏱ {elapsed_ms:.0f}ms[/dim]")

                        results_log.append({
                            "step": i + 1,
                            "action": step.action,
                            "status": "ok",
                            "stored": step.store_as,
                            "elapsed_ms": round(elapsed_ms),
                        })

                    except Exception as e:
                        elapsed_ms = (time.time() - step_start) * 1000
                        console.print(f"  [red]✗[/red] Błąd: {e}")
                        console.print(f"  [dim]   ⏱ {elapsed_ms:.0f}ms[/dim]")

                        results_log.append({
                            "step": i + 1,
                            "action": step.action,
                            "status": "error",
                            "error": str(e),
                            "elapsed_ms": round(elapsed_ms),
                        })

                        if step.retry_on_fail:
                            console.print("  [yellow]↻[/yellow] Retry...")
                            time.sleep(1)
                            try:
                                result = self._execute_desktop_plan_step(step, variables)
                                if step.store_as and result:
                                    variables[step.store_as] = result
                                console.print("  [green]✓[/green] Retry OK")
                                results_log[-1]["status"] = "ok_retry"
                            except Exception as e2:
                                console.print(f"  [red]✗[/red] Retry failed: {e2}")
                                results_log[-1]["status"] = "failed"

                        # Abort on critical failures
                        if step.action in _CRITICAL_ACTIONS and results_log[-1]["status"] == "failed":
                            console.print(
                                f"\n  [bold red]⛔ PRZERWANIE PLANU[/bold red]: "
                                f"Krytyczny krok '{step.action}' nie powiódł się.\n"
                                f"  [dim]Nie ma sensu kontynuować — napraw problem i uruchom ponownie.[/dim]"
                            )
                            plan_aborted = True
                            break

                    # Status assessment after each step
                    if step.action == "prompt_secret" and step.store_as:
                        val = variables.get(step.store_as, "")
                        if not val:
                            console.print(
                                f"  [bold yellow]⚠ STATUS[/bold yellow]: "
                                f"Brak klucza po kroku prompt_secret. "
                                f"Następny krok (save_env) nie będzie miał co zapisać."
                            )
                    if step.action == "check_session":
                        session_val = variables.get("session_status", "")
                        if session_val == "needs_login":
                            console.print(
                                f"  [bold yellow]⚠ STATUS[/bold yellow]: "
                                f"Niezalogowany. Zaloguj się w przeglądarce, potem kontynuuj."
                            )

                if video_recorder and video_recorder.is_recording:
                    video_recorder.stop_recording(None)
                    console.print("[dim]⚠️ Uwaga: Nagrywanie wideo jest niedostępne w trybie 'desktop' (wymaga pełnego silnika Playwright).[/dim]")

                # Final summary
                ok_count = sum(1 for r in results_log if r["status"] in ("ok", "ok_retry"))
                fail_count = sum(1 for r in results_log if r["status"] == "failed")
                err_count = sum(1 for r in results_log if r["status"] == "error")
                total_ms = sum(r.get("elapsed_ms", 0) for r in results_log)

                console.print(f"\n[bold]📊 Podsumowanie planu:[/bold]")
                console.print(
                    f"  Kroki: {ok_count}✓ {err_count}⚠ {fail_count}✗ "
                    f"z {len(plan.steps)} | Czas: {total_ms/1000:.1f}s"
                    f"{' | PRZERWANY' if plan_aborted else ''}"
                )

                result_data = {"steps": results_log, "variables": variables, "mode": "desktop"}

                return RunnerResult(
                    success=(not plan_aborted and all(r["status"] not in ("failed", "error") for r in results_log)),
                    kind="action_plan",
                    data=result_data,
                )
            except Exception as e:
                return RunnerResult(success=False, kind="action_plan", error=str(e))

        try:
            from playwright.sync_api import sync_playwright
        except ImportError as e:
            return RunnerResult(
                success=False, kind="action_plan",
                error=f"Playwright not available: {e}",
            )

        # --- Firefox session injection ---
        # NLP2CMD_USE_FIREFOX_SESSIONS=1       → Chromium + Firefox cookie injection (safest, SPA-compatible)
        # NLP2CMD_USE_FIREFOX_SESSIONS=cookies → same as =1
        # NLP2CMD_USE_FIREFOX_SESSIONS=firefox → full Firefox profile copy (may crash on SPAs!)
        # NLP2CMD_FIREFOX_PROFILE=/path        → explicit Firefox profile path
        use_ff_sessions = os.environ.get("NLP2CMD_USE_FIREFOX_SESSIONS", "").strip()
        ff_profile_override = os.environ.get("NLP2CMD_FIREFOX_PROFILE", "").strip() or None
        ff_session_importer = None
        ff_chromium_cookies: list[dict] = []

        if use_ff_sessions:
            try:
                from nlp2cmd.automation.firefox_sessions import FirefoxSessionImporter
                importer_kwargs: dict[str, Any] = {}
                if ff_profile_override:
                    importer_kwargs["firefox_profile"] = ff_profile_override

                if use_ff_sessions == "firefox":
                    # Full Firefox profile mode (WARNING: may crash SPAs!)
                    importer_kwargs["browser"] = "firefox"
                    ff_session_importer = FirefoxSessionImporter(**importer_kwargs)
                    ff_profile_dir = ff_session_importer.prepare_playwright_profile()
                    if ff_profile_dir:
                        console.print(
                            f"[dim]🦊 Skopiowano sesje Firefox → {ff_profile_dir}[/dim]"
                        )
                    else:
                        console.print("[yellow]⚠ Nie znaleziono profilu Firefox[/yellow]")
                        ff_session_importer = None
                else:
                    # Cookie injection mode (=1, =cookies, or any truthy value)
                    # Safe for SPAs — uses Chromium + Firefox cookies only
                    importer_kwargs["browser"] = "chromium"
                    ff_session_importer = FirefoxSessionImporter(**importer_kwargs)
                    ff_chromium_cookies = ff_session_importer.get_chromium_cookies()
                    if ff_chromium_cookies:
                        console.print(
                            f"[dim]🦊 Załadowano {len(ff_chromium_cookies)} ciasteczek "
                            f"z Firefox do Chromium[/dim]"
                        )
                    else:
                        console.print("[yellow]⚠ Nie znaleziono ciasteczek Firefox[/yellow]")
            except Exception as e:
                _debug(f"Firefox session import failed: {e}")
                console.print(f"[yellow]⚠ Import sesji Firefox: {e}[/yellow]")

        # --- Determine browser & profile ---
        if ff_session_importer and use_ff_sessions == "firefox":
            # Full Firefox profile mode
            user_data_dir = ff_session_importer.target_dir
            _pw_browser = "firefox"
        else:
            user_data_dir = Path.home() / ".nlp2cmd" / "browser_profile"
            user_data_dir.mkdir(parents=True, exist_ok=True)
            _pw_browser = "chromium"

        with sync_playwright() as pw:
            ctx_opts: dict[str, Any] = {
                "user_data_dir": str(user_data_dir),
                "headless": self.headless,
                "viewport": {"width": 1280, "height": 720},
            }
            if should_record_video:
                ctx_opts["record_video_dir"] = _effective_video_dir
                ctx_opts["record_video_size"] = {"width": 1280, "height": 720}

            context = None

            # --- Try Firefox first (if session mode) ---
            if _pw_browser == "firefox":
                console.print("[dim]🦊 Uruchamiam Playwright Firefox z sesjami...[/dim]")
                for headless_try in ([self.headless] if self.headless else [False, True]):
                    try:
                        ctx_opts["headless"] = headless_try
                        context = pw.firefox.launch_persistent_context(**ctx_opts)
                        break
                    except Exception as ff_err:
                        ff_err_str = str(ff_err)
                        if "Executable doesn't exist" in ff_err_str:
                            # Firefox binary not installed → fallback to Chromium + cookies
                            console.print(
                                "[yellow]⚠ Playwright Firefox nie zainstalowany "
                                "(uruchom: playwright install firefox)[/yellow]"
                            )
                            console.print(
                                "[dim]   ↳ Fallback: Chromium + wstrzykiwanie ciasteczek Firefox[/dim]"
                            )
                            _pw_browser = "chromium"
                            # Load cookies for injection if we haven't yet
                            if not ff_chromium_cookies and ff_session_importer:
                                ff_chromium_cookies = ff_session_importer.get_chromium_cookies()
                            # Switch user_data_dir to Chromium profile
                            user_data_dir = Path.home() / ".nlp2cmd" / "browser_profile"
                            user_data_dir.mkdir(parents=True, exist_ok=True)
                            ctx_opts["user_data_dir"] = str(user_data_dir)
                            break
                        if headless_try:
                            raise
                        _debug(f"Firefox headed launch failed: {ff_err}, trying headless")

            # --- Chromium path (default or fallback from Firefox) ---
            if context is None:
                for headless_try in ([self.headless] if self.headless else [False, True]):
                    try:
                        ctx_opts["headless"] = headless_try
                        context = pw.chromium.launch_persistent_context(**ctx_opts)
                        break
                    except Exception:
                        if headless_try:
                            raise

            page = context.pages[0] if context.pages else context.new_page()

            # Inject Firefox cookies into Chromium context
            if ff_chromium_cookies and _pw_browser == "chromium":
                try:
                    context.add_cookies(ff_chromium_cookies)
                    console.print(
                        f"[dim]🦊 Wstrzyknięto {len(ff_chromium_cookies)} "
                        f"ciasteczek Firefox do Chromium[/dim]"
                    )
                except Exception as e:
                    _debug(f"Cookie injection failed: {e}")

            variables: dict[str, str] = {}  # stores results from prior steps
            results_log: list[dict] = []
            _fallback_tried: set[str] = set()  # track fallback attempts to prevent loops

            # --- Validation & fallback infrastructure ---
            try:
                from nlp2cmd.automation.step_validator import StepValidator
                validator = StepValidator()
            except ImportError:
                validator = None

            try:
                from nlp2cmd.automation.schema_fallback import SchemaFallback, FallbackContext
                fallback_engine = SchemaFallback()
            except ImportError:
                fallback_engine = None

            # Resolve service config for fallback context
            _svc_config: dict = {}
            _svc_name: str = ""
            try:
                from nlp2cmd.automation.action_planner import KNOWN_SERVICES
                for _sn, _sc in KNOWN_SERVICES.items():
                    if _sn in (getattr(plan, "query", "") or "").lower():
                        _svc_config = _sc
                        _svc_name = _sn
                        break
            except Exception:
                pass

            # Build mutable step queue (allows injecting fallback steps)
            step_queue = list(plan.steps)
            step_idx = 0

            while step_idx < len(step_queue):
                step = step_queue[step_idx]
                step_desc = step.description or step.action
                total_display = len(step_queue)
                console.print(
                    f"\n[cyan]▸ Krok {step_idx+1}/{total_display}:[/cyan] {step_desc}"
                    f"  [dim]({step.action})[/dim]"
                )

                if step.action == "new_tab":
                    page = context.new_page()
                    try:
                        page.bring_to_front()
                    except Exception:
                        pass
                    console.print("  [green]✓[/green] OK")
                    results_log.append({
                        "step": step_idx + 1, "action": step.action,
                        "status": "ok", "stored": step.store_as,
                    })
                    step_idx += 1
                    continue

                # --- Pre-validation ---
                pre_ok = True
                pre_message = ""
                if validator:
                    params_resolved = self._resolve_plan_variables(
                        step.params or {}, variables,
                    )
                    pre_result = validator.validate_pre(
                        step.action, page, params_resolved, variables,
                    )
                    if not pre_result.passed:
                        console.print(f"  [yellow]⚠ Pre-check:[/yellow] {pre_result.message}")
                        if pre_result.suggestion:
                            console.print(f"  [dim]   💡 {pre_result.suggestion}[/dim]")
                        pre_ok = False
                        pre_message = str(pre_result.message or "")
                    # Check if key already extracted (skip prompt_secret)
                    if (step.action == "prompt_secret"
                            and pre_result.details.get("already_extracted")):
                        var_name = pre_result.details.get("var", "api_key")
                        existing_val = variables.get(var_name, "")
                        if existing_val:
                            console.print(
                                f"  [green]✓[/green] Klucz już wyekstrahowany "
                                f"(${var_name}, {len(existing_val)} znaków) — pomijam prompt"
                            )
                            if step.store_as:
                                variables[step.store_as] = existing_val
                            results_log.append({
                                "step": step_idx + 1, "action": step.action,
                                "status": "ok", "stored": step.store_as,
                                "note": "skipped_already_extracted",
                            })
                            step_idx += 1
                            continue

                    # Snapshot clipboard before key-related steps
                    if step.action in ("extract_key", "prompt_secret", "check_clipboard"):
                        validator.snapshot_clipboard()

                step_start = time.time()
                try:
                    result = self._execute_plan_step(
                        page, context, step, variables
                    )
                    elapsed_ms = (time.time() - step_start) * 1000

                    step_status = "ok"
                    step_error = ""
                    if not pre_ok:
                        step_status = "warning_pre"
                        step_error = pre_message

                    if step.store_as and result:
                        variables[step.store_as] = result

                    fb_applied = False

                    # --- Post-validation ---
                    if validator:
                        params_resolved = self._resolve_plan_variables(
                            step.params or {}, variables,
                        )
                        post_result = validator.validate_post(
                            step.action, page, params_resolved, result,
                        )
                        if not post_result.passed:
                            console.print(
                                f"  [yellow]⚠ Post-check:[/yellow] {post_result.message}"
                            )
                            if post_result.suggestion:
                                console.print(f"  [dim]   💡 {post_result.suggestion}[/dim]")
                            step_status = "failed_validation"
                            step_error = str(post_result.message or "")

                            # Post-validation failure on critical steps → trigger fallback
                            _fb_key = f"post:{step.action}"
                            if (
                                step.action in ("check_session", "extract_key")
                                and fallback_engine
                                and _fb_key not in _fallback_tried
                            ):
                                _fallback_tried.add(_fb_key)
                                console.print(
                                    f"  [cyan]🔄 Uruchamiam dynamiczny fallback...[/cyan]"
                                )
                                try:
                                    _fb_url = page.url if page else ""
                                    _fb_title = page.title() if page else ""
                                except Exception:
                                    _fb_url = _fb_title = ""
                                fb_ctx = FallbackContext(
                                    failed_action=step.action,
                                    failed_params=params_resolved,
                                    error_message=post_result.message,
                                    step_index=step_idx,
                                    total_steps=len(step_queue),
                                    variables=dict(variables),
                                    page_url=_fb_url,
                                    page_title=_fb_title,
                                    service_name=_svc_name,
                                    service_config=_svc_config,
                                    previous_steps_ok=[
                                        r["action"] for r in results_log
                                        if r.get("status") in ("ok", "ok_retry", "ok_fallback")
                                    ],
                                )
                                fb_result = fallback_engine.generate_fallback(fb_ctx, page)
                                if fb_result.success:
                                    console.print(
                                        f"  [green]✓ Fallback:[/green] {fb_result.strategy}"
                                        f" — {fb_result.message}"
                                    )
                                    if fb_result.extracted_value:
                                        if step.store_as:
                                            variables[step.store_as] = fb_result.extracted_value
                                        variables["extracted_key"] = fb_result.extracted_value
                                        console.print(
                                            f"  [green]✓[/green] Wyekstrahowano klucz "
                                            f"({len(fb_result.extracted_value)} znaków)"
                                        )
                                        step_status = "ok_fallback"
                                        step_error = ""
                                        fb_applied = True
                                    elif fb_result.replacement_steps:
                                        from nlp2cmd.automation.action_planner import ActionStep
                                        new_steps = []
                                        for rs in fb_result.replacement_steps:
                                            new_steps.append(ActionStep(
                                                action=rs["action"],
                                                params=rs.get("params", {}),
                                                description=rs.get("description", ""),
                                            ))
                                        step_queue[step_idx+1:step_idx+1] = new_steps
                                        console.print(
                                            f"  [dim]   📝 Wstawiono {len(new_steps)} "
                                            f"dodatkowych kroków[/dim]"
                                        )
                                        step_status = "fallback_injected"
                                        step_error = ""
                                        fb_applied = True

                    if step.store_as and result:
                        console.print(f"  [green]✓[/green] Zapisano jako ${step.store_as}")
                    elif step_status in ("ok", "ok_retry", "ok_fallback", "fallback_injected"):
                        console.print(f"  [green]✓[/green] OK")
                    else:
                        console.print(f"  [red]✗[/red] Krok nie przeszedł walidacji")

                    console.print(f"  [dim]   ⏱ {elapsed_ms:.0f}ms[/dim]")

                    results_log.append({
                        "step": step_idx + 1, "action": step.action,
                        "status": step_status, "stored": step.store_as,
                        "elapsed_ms": round(elapsed_ms),
                        **({"error": step_error} if step_error else {}),
                    })

                except Exception as e:
                    elapsed_ms = (time.time() - step_start) * 1000
                    console.print(f"  [red]✗[/red] Błąd: {e}")
                    console.print(f"  [dim]   ⏱ {elapsed_ms:.0f}ms[/dim]")

                    # Screenshot on failure for debugging
                    if step.action in ("click", "extract_key", "check_session"):
                        try:
                            dbg_dir = Path.home() / ".nlp2cmd" / "debug"
                            dbg_dir.mkdir(parents=True, exist_ok=True)
                            ss_path = dbg_dir / f"fail_{step.action}_{step_idx}.png"
                            page.screenshot(path=str(ss_path))
                            console.print(f"  [dim]   📸 Screenshot: {ss_path}[/dim]")
                        except Exception:
                            pass
                    results_log.append({
                        "step": step_idx + 1, "action": step.action,
                        "status": "error", "error": str(e),
                        "elapsed_ms": round(elapsed_ms),
                    })

                    # --- Dynamic fallback on error ---
                    fallback_handled = False
                    _fb_err_key = f"err:{step.action}"
                    if fallback_engine and _fb_err_key not in _fallback_tried:
                        _fallback_tried.add(_fb_err_key)
                        console.print(f"  [cyan]🔄 Uruchamiam dynamiczny fallback...[/cyan]")
                        params_resolved = self._resolve_plan_variables(
                            step.params or {}, variables,
                        )
                        try:
                            _fb_url = page.url if page else ""
                            _fb_title = page.title() if page else ""
                        except Exception:
                            _fb_url = _fb_title = ""
                        fb_ctx = FallbackContext(
                            failed_action=step.action,
                            failed_params=params_resolved,
                            error_message=str(e),
                            step_index=step_idx,
                            total_steps=len(step_queue),
                            variables=dict(variables),
                            page_url=_fb_url,
                            page_title=_fb_title,
                            service_name=_svc_name,
                            service_config=_svc_config,
                            previous_steps_ok=[
                                r["action"] for r in results_log
                                if r.get("status") in ("ok", "ok_retry")
                            ],
                        )
                        fb_result = fallback_engine.generate_fallback(fb_ctx, page)
                        if fb_result.success:
                            console.print(
                                f"  [green]✓ Fallback:[/green] {fb_result.strategy}"
                                f" — {fb_result.message}"
                            )
                            if fb_result.extracted_value:
                                if step.store_as:
                                    variables[step.store_as] = fb_result.extracted_value
                                variables["extracted_key"] = fb_result.extracted_value
                                results_log[-1]["status"] = "ok_fallback"
                                fallback_handled = True
                            elif fb_result.replacement_steps:
                                from nlp2cmd.automation.action_planner import ActionStep
                                new_steps = []
                                for rs in fb_result.replacement_steps:
                                    new_steps.append(ActionStep(
                                        action=rs["action"],
                                        params=rs.get("params", {}),
                                        description=rs.get("description", ""),
                                    ))
                                step_queue[step_idx+1:step_idx+1] = new_steps
                                console.print(
                                    f"  [dim]   📝 Wstawiono {len(new_steps)} "
                                    f"alternatywnych kroków[/dim]"
                                )
                                results_log[-1]["status"] = "fallback_injected"
                                fallback_handled = True
                        else:
                            console.print(
                                f"  [dim]   Fallback wyczerpany: {fb_result.message}[/dim]"
                            )

                    # Detect browser-closed — no point retrying
                    _browser_dead = "browser has been closed" in str(e).lower()

                    if not fallback_handled and step.retry_on_fail and not _browser_dead:
                        console.print(f"  [yellow]↻[/yellow] Retry...")
                        try:
                            page.wait_for_timeout(1000)
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

                    if _browser_dead:
                        console.print(
                            "  [red]⛔ Przeglądarka zamknięta — przerywam wykonanie[/red]"
                        )
                        break

                step_idx += 1

            # --- Validation summary ---
            if validator:
                summary = validator.summary()
                if summary.get("failed", 0) > 0:
                    console.print(
                        f"\n[bold yellow]⚠ Walidacja:[/bold yellow] "
                        f"{summary['failed']} kroków nie przeszło walidacji"
                    )


            # Final summary
            ok_count = sum(1 for r in results_log if r["status"] in ("ok", "ok_retry", "ok_fallback", "fallback_injected"))
            fail_count = sum(1 for r in results_log if r["status"] == "failed")
            err_count = sum(1 for r in results_log if r["status"] in ("error", "failed_validation"))
            total_ms = sum(r.get("elapsed_ms", 0) for r in results_log)

            console.print(f"\n[bold]📊 Podsumowanie planu:[/bold]")
            console.print(
                f"  Kroki: {ok_count}✓ {err_count}⚠ {fail_count}✗ "
                f"z {len(plan.steps)} | Czas: {total_ms/1000:.1f}s"
            )

            if video_recorder and video_recorder.is_recording:
                try:
                    # To ensure the video file is completely written, Playwright requires the page/context to be closed
                    # But we want a screenshot first. We do it below.
                    pass
                except Exception as ve:
                    pass

            # Capture final screenshot on success/failure
            screenshot_path = None
            try:
                if not should_record_video or page:
                    timestamp = get_timestamp()
                    screenshot_path = str(Path(_effective_video_dir) / f"action_plan_final_{timestamp}.png")
                    # need to ensure page isn't closed if we didn't save video yet
                    if not page.is_closed():
                        page.screenshot(path=screenshot_path)
                        console.print(f"[dim]📸 Zrzut ekranu zapisany: {screenshot_path}[/dim]")
            except Exception as e:
                _debug(f"Failed to capture final screenshot: {e}")

            try:
                context.close()
            except Exception:
                pass
                
            if video_recorder and video_recorder.is_recording:
                try:
                    pw_video = page.video
                    if pw_video:
                        target = video_recorder.video_path or str(Path(_effective_video_dir) / "action_plan_automation.webm")
                        # save_as works after context is closed
                        try:
                            pw_video.save_as(target)
                            video_saved_path = target
                        except Exception:
                            try:
                                video_saved_path = pw_video.path()
                            except Exception:
                                video_saved_path = None
                        if video_saved_path:
                            console.print(f"[green]🎥 Video saved: {video_saved_path}[/green]")
                except Exception as ve:
                    _debug(f"Video save_as failed: {ve}")
                video_recorder.stop_recording(console, saved_path=video_saved_path)

        result_data = {"steps": results_log, "variables": variables, "mode": "playwright"}
        if video_saved_path:
            result_data["video"] = video_saved_path
        if screenshot_path:
            result_data["screenshot"] = screenshot_path

        return RunnerResult(
            success=all(r["status"] not in ("failed", "error", "failed_validation") for r in results_log),
            kind="action_plan",
            data=result_data,
        )

    def _execute_plan_step(self, page, context, step, variables: dict) -> Optional[str]:
        """Execute a single ActionPlan step. Returns extracted value or None."""
        params = self._resolve_plan_variables(step.params, variables)
        action = step.action

        # Local console for interactive prompts in multi-step plans
        console = Console()
        
        # DEBUG: Confirm method is being called
        import sys
        print(f"DEBUG: _execute_plan_step called with action={action}", file=sys.stderr, flush=True)

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
            timeout = int(params.get("timeout", 10000))
            max_retries = int(params.get("retries", 3))

            # Wait for page to stabilize (SPA re-renders)
            try:
                page.wait_for_load_state("domcontentloaded", timeout=5000)
            except Exception:
                pass
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass

            last_err = None
            for attempt in range(1, max_retries + 1):
                try:
                    if text:
                        locator = page.get_by_text(text).first
                        locator.wait_for(state="visible", timeout=timeout)
                        locator.click(timeout=timeout)
                    elif selector:
                        page.wait_for_selector(selector, state="visible", timeout=timeout)
                        page.click(selector, timeout=timeout)
                    last_err = None
                    break
                except Exception as click_err:
                    last_err = click_err
                    err_str = str(click_err)
                    if "detached from the DOM" in err_str and attempt < max_retries:
                        _debug(f"click: element detached, retry {attempt}/{max_retries}")
                        page.wait_for_timeout(1000)
                        continue
                    if "Target page, context or browser has been closed" in err_str:
                        raise
                    if attempt < max_retries:
                        _debug(f"click: attempt {attempt} failed: {click_err}")
                        page.wait_for_timeout(500)
                        continue
                    # Last attempt: try force click
                    try:
                        if text:
                            page.get_by_text(text).first.click(force=True, timeout=timeout)
                        elif selector:
                            page.click(selector, force=True, timeout=timeout)
                        last_err = None
                    except Exception as force_err:
                        last_err = force_err
            if last_err:
                raise last_err

        elif action == "dismiss_overlay":
            # Try to dismiss cookie consent banners and overlay dialogs
            _debug("dismiss_overlay: scanning for overlay buttons")
            dismissed = False
            # Common cookie/consent button texts
            dismiss_texts = ["Accept", "Decline", "OK", "Got it", "Close",
                             "Akceptuję", "Zamknij", "Zgadzam się"]
            for txt in dismiss_texts:
                try:
                    btn = page.get_by_text(txt, exact=True).first
                    if btn.is_visible(timeout=500):
                        btn.click(timeout=2000)
                        _debug(f"dismiss_overlay: clicked '{txt}'")
                        dismissed = True
                        page.wait_for_timeout(300)
                        break
                except Exception:
                    continue
            # Fallback: try common CSS selectors for close buttons
            if not dismissed:
                for sel in ["[aria-label='Close']", "[aria-label='Dismiss']",
                            "button.close", ".cookie-banner button", "[id*='cookie'] button"]:
                    try:
                        el = page.query_selector(sel)
                        if el and el.is_visible():
                            el.click()
                            _debug(f"dismiss_overlay: clicked selector '{sel}'")
                            dismissed = True
                            break
                    except Exception:
                        continue
            if not dismissed:
                _debug("dismiss_overlay: no overlay found to dismiss")

        elif action == "type_text":
            page.fill(params.get("selector", "input"), params.get("text", ""))

        elif action == "wait_for_canvas":
            page.wait_for_selector("canvas", state="visible", timeout=15000)
            
        elif action == "get_canvas_center":
            canvas = page.query_selector("canvas")
            if canvas:
                box = canvas.bounding_box()
                if box:
                    _debug(f"Canvas: {box}")
                    variables["canvas_cx"] = str(box["x"] + box["width"] / 2)
                    variables["canvas_cy"] = str(box["y"] + box["height"] / 2)

        elif action == "select_tool":
            tool = params.get("tool", "")
            tool_map = {
                "ellipse": "ellipse",
                "rectangle": "rectangle",
                "line": "line",
                "brush": "brush",
                "pencil": "pencil",
                "fill": "fill",
                "text": "text",
            }
            mapped = tool_map.get(tool, tool)
            try:
                page.evaluate(f'''() => {{
                    const tools = document.querySelectorAll('.tool');
                    for (const t of tools) {{
                        if (t.title && t.title.toLowerCase().includes('{mapped}')) {{
                            t.click();
                            return;
                        }}
                    }}
                }}''')
                page.wait_for_timeout(500)
            except Exception as e:
                raise RuntimeError(f"Tool selection error: {e}")

        elif action == "set_color":
            color = params.get("color", "#000000")
            try:
                page.evaluate(f'''() => {{
                    // Store a stable color value even if JSPaint internals differ.
                    window.__nlp2cmd_foreground = '{color}';
                    window.__nlp2cmd_background = '{color}';
                    if (window.colors) {{
                        window.colors.foreground = '{color}';
                        window.colors.background = '{color}';
                    }}
                }}''')
                page.wait_for_timeout(200)
            except Exception as e:
                raise RuntimeError(f"Color set error: {e}")

        elif action == "draw_circle":
            radius = float(params.get("radius", 10))
            offset = params.get("offset", [0, 0])
            try:
                page.evaluate(f'''() => {{
                    const pickCanvas = () => {{
                        const all = Array.from(document.querySelectorAll('canvas'));
                        if (!all.length) return null;
                        // Prefer explicit main canvas if present.
                        const main = document.querySelector('.main-canvas');
                        if (main && main instanceof HTMLCanvasElement) return main;
                        // Otherwise pick the largest visible canvas.
                        let best = null;
                        let bestArea = -1;
                        for (const c of all) {{
                            if (!(c instanceof HTMLCanvasElement)) continue;
                            const r = c.getBoundingClientRect();
                            if (!r || r.width <= 64 || r.height <= 64) continue;
                            const style = window.getComputedStyle(c);
                            if (style && (style.visibility === 'hidden' || style.display === 'none')) continue;
                            const area = r.width * r.height;
                            if (area > bestArea) {{
                                bestArea = area;
                                best = c;
                            }}
                        }}
                        return best;
                    }};

                    const canvas = pickCanvas();
                    if (!canvas) throw new Error('No suitable canvas found');
                    const ctx = canvas.getContext('2d');
                    if (!ctx) throw new Error('Canvas 2D context unavailable');
                    const rect = canvas.getBoundingClientRect();
                    const sx = (canvas.width && rect.width) ? (canvas.width / rect.width) : 1;
                    const sy = (canvas.height && rect.height) ? (canvas.height / rect.height) : 1;
                    const cx = (rect.width / 2 + {offset[0]}) * sx;
                    const cy = (rect.height / 2 + {offset[1]}) * sy;
                    const r = {radius} * Math.max(sx, sy);
                    ctx.beginPath();
                    ctx.arc(cx, cy, r, 0, 2 * Math.PI);
                    ctx.fillStyle = (window.__nlp2cmd_foreground || (window.__nlp2cmd_foreground || (window.colors && window.colors.foreground)) || '#000');
                    ctx.fill();
                }}''')
                page.wait_for_timeout(200)
            except Exception as e:
                raise RuntimeError(f"Draw circle error: {e}")
                
        elif action == "draw_filled_ellipse":
            rx = float(params.get("rx", 10))
            ry = float(params.get("ry", 10))
            offset = params.get("offset", [0, 0])
            rotation = float(params.get("rotation", 0))
            try:
                page.evaluate(f'''() => {{
                    const pickCanvas = () => {{
                        const all = Array.from(document.querySelectorAll('canvas'));
                        if (!all.length) return null;
                        const main = document.querySelector('.main-canvas');
                        if (main && main instanceof HTMLCanvasElement) return main;
                        let best = null;
                        let bestArea = -1;
                        for (const c of all) {{
                            if (!(c instanceof HTMLCanvasElement)) continue;
                            const r = c.getBoundingClientRect();
                            if (!r || r.width <= 64 || r.height <= 64) continue;
                            const style = window.getComputedStyle(c);
                            if (style && (style.visibility === 'hidden' || style.display === 'none')) continue;
                            const area = r.width * r.height;
                            if (area > bestArea) {{
                                bestArea = area;
                                best = c;
                            }}
                        }}
                        return best;
                    }};

                    const canvas = pickCanvas();
                    if (!canvas) throw new Error('No suitable canvas found');
                    const ctx = canvas.getContext('2d');
                    if (!ctx) throw new Error('Canvas 2D context unavailable');
                    const rect = canvas.getBoundingClientRect();
                    const sx = (canvas.width && rect.width) ? (canvas.width / rect.width) : 1;
                    const sy = (canvas.height && rect.height) ? (canvas.height / rect.height) : 1;
                    const cx = (rect.width / 2 + {offset[0]}) * sx;
                    const cy = (rect.height / 2 + {offset[1]}) * sy;
                    const _rx = {rx} * sx;
                    const _ry = {ry} * sy;
                    ctx.beginPath();
                    ctx.ellipse(cx, cy, _rx, _ry, {rotation}, 0, 2 * Math.PI);
                    ctx.fillStyle = (window.__nlp2cmd_foreground || (window.__nlp2cmd_foreground || (window.colors && window.colors.foreground)) || '#000');
                    ctx.fill();
                }}''')
                page.wait_for_timeout(200)
            except Exception as e:
                raise RuntimeError(f"Draw filled ellipse error: {e}")

        elif action == "draw_filled_circle":
            radius = float(params.get("radius", 10))
            offset = params.get("offset", [0, 0])
            try:
                # Check canvas before drawing - use same logic as drawing code
                before_check = page.evaluate('''() => {
                    const pickCanvas = () => {
                        const all = Array.from(document.querySelectorAll('canvas'));
                        if (!all.length) return null;
                        const main = document.querySelector('.main-canvas');
                        if (main && main instanceof HTMLCanvasElement) return main;
                        let best = null;
                        let bestArea = -1;
                        for (const c of all) {
                            if (!(c instanceof HTMLCanvasElement)) continue;
                            const r = c.getBoundingClientRect();
                            if (!r || r.width <= 64 || r.height <= 64) continue;
                            const style = window.getComputedStyle(c);
                            if (style && (style.visibility === 'hidden' || style.display === 'none')) continue;
                            const area = r.width * r.height;
                            if (area > bestArea) {
                                bestArea = area;
                                best = c;
                            }
                        }
                        return best;
                    };
                    const canvas = pickCanvas();
                    if (!canvas) return {error: 'No canvas found'};
                    const ctx = canvas.getContext('2d');
                    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                    let nonWhite = 0;
                    for (let i = 0; i < imageData.data.length; i += 400) {
                        if (imageData.data[i] !== 255 || imageData.data[i+1] !== 255 || imageData.data[i+2] !== 255) {
                            nonWhite++;
                        }
                    }
                    return {nonWhitePixels: nonWhite, isBlank: nonWhite <= 10, width: canvas.width, height: canvas.height};
                }''')
                console.print(f"  [dim]Canvas before: {before_check}[/dim]")
                
                page.evaluate(f'''() => {{
                    const pickCanvas = () => {{
                        const all = Array.from(document.querySelectorAll('canvas'));
                        if (!all.length) return null;
                        const main = document.querySelector('.main-canvas');
                        if (main && main instanceof HTMLCanvasElement) return main;
                        let best = null;
                        let bestArea = -1;
                        for (const c of all) {{
                            if (!(c instanceof HTMLCanvasElement)) continue;
                            const r = c.getBoundingClientRect();
                            if (!r || r.width <= 64 || r.height <= 64) continue;
                            const style = window.getComputedStyle(c);
                            if (style && (style.visibility === 'hidden' || style.display === 'none')) continue;
                            const area = r.width * r.height;
                            if (area > bestArea) {{
                                bestArea = area;
                                best = c;
                            }}
                        }}
                        return best;
                    }};

                    const canvas = pickCanvas();
                    if (!canvas) throw new Error('No suitable canvas found');
                    const ctx = canvas.getContext('2d');
                    if (!ctx) throw new Error('Canvas 2D context unavailable');
                    const rect = canvas.getBoundingClientRect();
                    const sx = (canvas.width && rect.width) ? (canvas.width / rect.width) : 1;
                    const sy = (canvas.height && rect.height) ? (canvas.height / rect.height) : 1;
                    const cx = (rect.width / 2 + {offset[0]}) * sx;
                    const cy = (rect.height / 2 + {offset[1]}) * sy;
                    const r = {radius} * Math.max(sx, sy);
                    ctx.beginPath();
                    ctx.arc(cx, cy, r, 0, 2 * Math.PI);
                    ctx.fillStyle = (window.__nlp2cmd_foreground || (window.__nlp2cmd_foreground || (window.colors && window.colors.foreground)) || '#ff0000');
                    ctx.fill();
                    console.log('Drew circle at', cx, cy, 'radius', r, 'color', ctx.fillStyle);
                }}''')
                page.wait_for_timeout(200)
                
                # Verify drawing actually happened - use same canvas selection
                after_check = page.evaluate('''() => {
                    const pickCanvas = () => {
                        const all = Array.from(document.querySelectorAll('canvas'));
                        if (!all.length) return null;
                        const main = document.querySelector('.main-canvas');
                        if (main && main instanceof HTMLCanvasElement) return main;
                        let best = null;
                        let bestArea = -1;
                        for (const c of all) {
                            if (!(c instanceof HTMLCanvasElement)) continue;
                            const r = c.getBoundingClientRect();
                            if (!r || r.width <= 64 || r.height <= 64) continue;
                            const style = window.getComputedStyle(c);
                            if (style && (style.visibility === 'hidden' || style.display === 'none')) continue;
                            const area = r.width * r.height;
                            if (area > bestArea) {
                                bestArea = area;
                                best = c;
                            }
                        }
                        return best;
                    };
                    const canvas = pickCanvas();
                    if (!canvas) return {error: 'No canvas found'};
                    const ctx = canvas.getContext('2d');
                    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                    let nonWhite = 0;
                    for (let i = 0; i < imageData.data.length; i += 400) {
                        if (imageData.data[i] !== 255 || imageData.data[i+1] !== 255 || imageData.data[i+2] !== 255) {
                            nonWhite++;
                        }
                    }
                    return {nonWhitePixels: nonWhite, isBlank: nonWhite <= 10, width: canvas.width, height: canvas.height};
                }''')
                console.print(f"  [dim]Canvas after: {after_check}[/dim]")
                
                if after_check.get('isBlank') and not before_check.get('isBlank'):
                    console.print(f"  [yellow]⚠ Canvas still blank after drawing![/yellow]")
                elif after_check.get('nonWhitePixels', 0) > before_check.get('nonWhitePixels', 0):
                    console.print(f"  [green]✓ Drawing visible: {after_check.get('nonWhitePixels')} non-white pixels[/green]")
                else:
                    console.print(f"  [yellow]⚠ No visible change in canvas pixels[/yellow]")
                    
            except Exception as e:
                raise RuntimeError(f"Draw filled circle error: {e}")

        elif action == "draw_filled_rectangle":
            w = float(params.get("width", 50))
            h = float(params.get("height", 50))
            offset = params.get("offset", [0, 0])
            try:
                page.evaluate(f'''() => {{
                    const pickCanvas = () => {{
                        const all = Array.from(document.querySelectorAll('canvas'));
                        if (!all.length) return null;
                        const main = document.querySelector('.main-canvas');
                        if (main && main instanceof HTMLCanvasElement) return main;
                        let best = null;
                        let bestArea = -1;
                        for (const c of all) {{
                            if (!(c instanceof HTMLCanvasElement)) continue;
                            const r = c.getBoundingClientRect();
                            if (!r || r.width <= 64 || r.height <= 64) continue;
                            const style = window.getComputedStyle(c);
                            if (style && (style.visibility === 'hidden' || style.display === 'none')) continue;
                            const area = r.width * r.height;
                            if (area > bestArea) {{ bestArea = area; best = c; }}
                        }}
                        return best;
                    }};
                    const canvas = pickCanvas();
                    if (!canvas) throw new Error('No suitable canvas found');
                    const ctx = canvas.getContext('2d');
                    if (!ctx) throw new Error('Canvas 2D context unavailable');
                    const rect = canvas.getBoundingClientRect();
                    const sx = (canvas.width && rect.width) ? (canvas.width / rect.width) : 1;
                    const sy = (canvas.height && rect.height) ? (canvas.height / rect.height) : 1;
                    const cx = (rect.width / 2 + {offset[0]}) * sx;
                    const cy = (rect.height / 2 + {offset[1]}) * sy;
                    const _w = {w} * sx;
                    const _h = {h} * sy;
                    ctx.fillStyle = (window.__nlp2cmd_foreground || (window.__nlp2cmd_foreground || (window.colors && window.colors.foreground)) || '#000');
                    ctx.fillRect(cx - _w/2, cy - _h/2, _w, _h);
                }}''')
                page.wait_for_timeout(200)
            except Exception as e:
                raise RuntimeError(f"Draw filled rectangle error: {e}")

        elif action == "draw_arc":
            radius = float(params.get("radius", 50))
            start_angle = float(params.get("start_angle", 0))
            end_angle = float(params.get("end_angle", 3.14159))
            offset = params.get("offset", [0, 0])
            fill = params.get("fill", False)
            line_width = float(params.get("line_width", 2))
            try:
                fill_js = "true" if fill else "false"
                page.evaluate(f'''() => {{
                    const pickCanvas = () => {{
                        const all = Array.from(document.querySelectorAll('canvas'));
                        if (!all.length) return null;
                        const main = document.querySelector('.main-canvas');
                        if (main && main instanceof HTMLCanvasElement) return main;
                        let best = null;
                        let bestArea = -1;
                        for (const c of all) {{
                            if (!(c instanceof HTMLCanvasElement)) continue;
                            const r = c.getBoundingClientRect();
                            if (!r || r.width <= 64 || r.height <= 64) continue;
                            const style = window.getComputedStyle(c);
                            if (style && (style.visibility === 'hidden' || style.display === 'none')) continue;
                            const area = r.width * r.height;
                            if (area > bestArea) {{ bestArea = area; best = c; }}
                        }}
                        return best;
                    }};
                    const canvas = pickCanvas();
                    if (!canvas) throw new Error('No suitable canvas found');
                    const ctx = canvas.getContext('2d');
                    if (!ctx) throw new Error('Canvas 2D context unavailable');
                    const rect = canvas.getBoundingClientRect();
                    const sx = (canvas.width && rect.width) ? (canvas.width / rect.width) : 1;
                    const sy = (canvas.height && rect.height) ? (canvas.height / rect.height) : 1;
                    const cx = (rect.width / 2 + {offset[0]}) * sx;
                    const cy = (rect.height / 2 + {offset[1]}) * sy;
                    const rr = {radius} * Math.max(sx, sy);
                    ctx.beginPath();
                    ctx.arc(cx, cy, rr, {start_angle}, {end_angle});
                    ctx.lineWidth = {line_width} * Math.max(sx, sy);
                    const col = (window.__nlp2cmd_foreground || (window.__nlp2cmd_foreground || (window.colors && window.colors.foreground)) || '#000');
                    ctx.strokeStyle = col;
                    ctx.fillStyle = col;
                    if ({fill_js}) {{
                        ctx.lineTo(cx, cy);
                        ctx.closePath();
                        ctx.fill();
                    }} else {{
                        ctx.stroke();
                    }}
                }}''')
                page.wait_for_timeout(200)
            except Exception as e:
                raise RuntimeError(f"Draw arc error: {e}")

        elif action == "draw_polygon":
            points = params.get("points", [])
            offset = params.get("offset", [0, 0])
            fill = params.get("fill", True)
            line_width = float(params.get("line_width", 2))
            if len(points) >= 3:
                try:
                    fill_js = "true" if fill else "false"
                    pts_js = ",".join(f"[{p[0]},{p[1]}]" for p in points)
                    page.evaluate(f'''() => {{
                        const pickCanvas = () => {{
                            const all = Array.from(document.querySelectorAll('canvas'));
                            if (!all.length) return null;
                            const main = document.querySelector('.main-canvas');
                            if (main && main instanceof HTMLCanvasElement) return main;
                            let best = null;
                            let bestArea = -1;
                            for (const c of all) {{
                                if (!(c instanceof HTMLCanvasElement)) continue;
                                const r = c.getBoundingClientRect();
                                if (!r || r.width <= 64 || r.height <= 64) continue;
                                const style = window.getComputedStyle(c);
                                if (style && (style.visibility === 'hidden' || style.display === 'none')) continue;
                                const area = r.width * r.height;
                                if (area > bestArea) {{ bestArea = area; best = c; }}
                            }}
                            return best;
                        }};
                        const canvas = pickCanvas();
                        if (!canvas) throw new Error('No suitable canvas found');
                        const ctx = canvas.getContext('2d');
                        if (!ctx) throw new Error('Canvas 2D context unavailable');
                        const rect = canvas.getBoundingClientRect();
                        const sx = (canvas.width && rect.width) ? (canvas.width / rect.width) : 1;
                        const sy = (canvas.height && rect.height) ? (canvas.height / rect.height) : 1;
                        const cx = (rect.width / 2 + {offset[0]}) * sx;
                        const cy = (rect.height / 2 + {offset[1]}) * sy;
                        const pts = [{pts_js}].map(p => [p[0] * sx, p[1] * sy]);
                        ctx.beginPath();
                        ctx.moveTo(cx + pts[0][0], cy + pts[0][1]);
                        for (let i = 1; i < pts.length; i++) {{
                            ctx.lineTo(cx + pts[i][0], cy + pts[i][1]);
                        }}
                        ctx.closePath();
                        ctx.lineWidth = {line_width} * Math.max(sx, sy);
                        const col = (window.__nlp2cmd_foreground || (window.__nlp2cmd_foreground || (window.colors && window.colors.foreground)) || '#000');
                        ctx.strokeStyle = col;
                        ctx.fillStyle = col;
                        if ({fill_js}) {{
                            ctx.fill();
                        }} else {{
                            ctx.stroke();
                        }}
                    }}''')
                    page.wait_for_timeout(200)
                except Exception as e:
                    raise RuntimeError(f"Draw polygon error: {e}")

        elif action == "draw_bezier":
            curves = params.get("curves", [])
            offset = params.get("offset", [0, 0])
            fill = params.get("fill", False)
            close = params.get("close", False)
            line_width = float(params.get("line_width", 2))
            if curves:
                try:
                    fill_js = "true" if fill else "false"
                    close_js = "true" if close else "false"
                    curves_js = json.dumps(curves)
                    page.evaluate(f'''() => {{
                        const pickCanvas = () => {{
                            const all = Array.from(document.querySelectorAll('canvas'));
                            if (!all.length) return null;
                            const main = document.querySelector('.main-canvas');
                            if (main && main instanceof HTMLCanvasElement) return main;
                            let best = null;
                            let bestArea = -1;
                            for (const c of all) {{
                                if (!(c instanceof HTMLCanvasElement)) continue;
                                const r = c.getBoundingClientRect();
                                if (!r || r.width <= 64 || r.height <= 64) continue;
                                const style = window.getComputedStyle(c);
                                if (style && (style.visibility === 'hidden' || style.display === 'none')) continue;
                                const area = r.width * r.height;
                                if (area > bestArea) {{ bestArea = area; best = c; }}
                            }}
                            return best;
                        }};
                        const canvas = pickCanvas();
                        if (!canvas) throw new Error('No suitable canvas found');
                        const ctx = canvas.getContext('2d');
                        if (!ctx) throw new Error('Canvas 2D context unavailable');
                        const rect = canvas.getBoundingClientRect();
                        const sx = (canvas.width && rect.width) ? (canvas.width / rect.width) : 1;
                        const sy = (canvas.height && rect.height) ? (canvas.height / rect.height) : 1;
                        const cx = (rect.width / 2 + {offset[0]}) * sx;
                        const cy = (rect.height / 2 + {offset[1]}) * sy;
                        const curves = {curves_js};
                        ctx.beginPath();
                        for (let i = 0; i < curves.length; i++) {{
                            const c = curves[i];
                            if (c.type === 'M' || (i === 0 && !c.type)) {{
                                ctx.moveTo(cx + c.x * sx, cy + c.y * sy);
                            }} else if (c.type === 'L') {{
                                ctx.lineTo(cx + c.x * sx, cy + c.y * sy);
                            }} else if (c.type === 'Q') {{
                                ctx.quadraticCurveTo(cx + c.cpx * sx, cy + c.cpy * sy, cx + c.x * sx, cy + c.y * sy);
                            }} else if (c.type === 'C') {{
                                ctx.bezierCurveTo(cx + c.cp1x * sx, cy + c.cp1y * sy, cx + c.cp2x * sx, cy + c.cp2y * sy, cx + c.x * sx, cy + c.y * sy);
                            }}
                        }}
                        if ({close_js}) ctx.closePath();
                        ctx.lineWidth = {line_width} * Math.max(sx, sy);
                        const col = (window.__nlp2cmd_foreground || (window.__nlp2cmd_foreground || (window.colors && window.colors.foreground)) || '#000');
                        ctx.strokeStyle = col;
                        ctx.fillStyle = col;
                        if ({fill_js}) {{
                            ctx.fill();
                        }} else {{
                            ctx.stroke();
                        }}
                    }}''')
                    page.wait_for_timeout(200)
                except Exception as e:
                    raise RuntimeError(f"Draw bezier error: {e}")

        elif action == "draw_svg_path":
            path_d = params.get("d", "")
            offset = params.get("offset", [0, 0])
            fill = params.get("fill", True)
            scale = float(params.get("scale", 1.0))
            line_width = float(params.get("line_width", 2))
            if path_d:
                try:
                    fill_js = "true" if fill else "false"
                    page.evaluate(f'''() => {{
                        const pickCanvas = () => {{
                            const all = Array.from(document.querySelectorAll('canvas'));
                            if (!all.length) return null;
                            const main = document.querySelector('.main-canvas');
                            if (main && main instanceof HTMLCanvasElement) return main;
                            let best = null;
                            let bestArea = -1;
                            for (const c of all) {{
                                if (!(c instanceof HTMLCanvasElement)) continue;
                                const r = c.getBoundingClientRect();
                                if (!r || r.width <= 64 || r.height <= 64) continue;
                                const style = window.getComputedStyle(c);
                                if (style && (style.visibility === 'hidden' || style.display === 'none')) continue;
                                const area = r.width * r.height;
                                if (area > bestArea) {{ bestArea = area; best = c; }}
                            }}
                            return best;
                        }};
                        const canvas = pickCanvas();
                        if (!canvas) throw new Error('No suitable canvas found');
                        const ctx = canvas.getContext('2d');
                        if (!ctx) throw new Error('Canvas 2D context unavailable');
                        const rect = canvas.getBoundingClientRect();
                        const sx = (canvas.width && rect.width) ? (canvas.width / rect.width) : 1;
                        const sy = (canvas.height && rect.height) ? (canvas.height / rect.height) : 1;
                        const cx = (rect.width / 2 + {offset[0]}) * sx;
                        const cy = (rect.height / 2 + {offset[1]}) * sy;
                        ctx.save();
                        ctx.translate(cx, cy);
                        ctx.scale({scale} * sx, {scale} * sy);
                        const p = new Path2D('{path_d}');
                        ctx.lineWidth = ({line_width} / {scale}) * Math.max(sx, sy);
                        const col = (window.__nlp2cmd_foreground || (window.__nlp2cmd_foreground || (window.colors && window.colors.foreground)) || '#000');
                        ctx.strokeStyle = col;
                        ctx.fillStyle = col;
                        if ({fill_js}) {{
                            ctx.fill(p);
                        }} else {{
                            ctx.stroke(p);
                        }}
                        ctx.restore();
                    }}''')
                    page.wait_for_timeout(200)
                except Exception as e:
                    raise RuntimeError(f"Draw SVG path error: {e}")

        elif action == "set_line_width":
            width = float(params.get("width", 2))
            try:
                page.evaluate(f'''() => {{
                    const pickCanvas = () => {{
                        const all = Array.from(document.querySelectorAll('canvas'));
                        if (!all.length) return null;
                        const main = document.querySelector('.main-canvas');
                        if (main && main instanceof HTMLCanvasElement) return main;
                        let best = null;
                        let bestArea = -1;
                        for (const c of all) {{
                            if (!(c instanceof HTMLCanvasElement)) continue;
                            const r = c.getBoundingClientRect();
                            if (!r || r.width <= 64 || r.height <= 64) continue;
                            const style = window.getComputedStyle(c);
                            if (style && (style.visibility === 'hidden' || style.display === 'none')) continue;
                            const area = r.width * r.height;
                            if (area > bestArea) {{ bestArea = area; best = c; }}
                        }}
                        return best;
                    }};
                    const canvas = pickCanvas();
                    if (!canvas) throw new Error('No suitable canvas found');
                    const ctx = canvas.getContext('2d');
                    if (!ctx) throw new Error('Canvas 2D context unavailable');
                    const rect = canvas.getBoundingClientRect();
                    const sx = (canvas.width && rect.width) ? (canvas.width / rect.width) : 1;
                    const sy = (canvas.height && rect.height) ? (canvas.height / rect.height) : 1;
                    ctx.lineWidth = {width} * Math.max(sx, sy);
                }}''')
            except Exception as e:
                raise RuntimeError(f"Set line width error: {e}")

        elif action == "draw_rectangle":
            w = float(params.get("width", 50))
            h = float(params.get("height", 50))
            offset = params.get("offset", [0, 0])
            try:
                page.evaluate(f'''() => {{
                    const pickCanvas = () => {{
                        const all = Array.from(document.querySelectorAll('canvas'));
                        if (!all.length) return null;
                        const main = document.querySelector('.main-canvas');
                        if (main && main instanceof HTMLCanvasElement) return main;
                        let best = null;
                        let bestArea = -1;
                        for (const c of all) {{
                            if (!(c instanceof HTMLCanvasElement)) continue;
                            const r = c.getBoundingClientRect();
                            if (!r || r.width <= 64 || r.height <= 64) continue;
                            const style = window.getComputedStyle(c);
                            if (style && (style.visibility === 'hidden' || style.display === 'none')) continue;
                            const area = r.width * r.height;
                            if (area > bestArea) {{ bestArea = area; best = c; }}
                        }}
                        return best;
                    }};
                    const canvas = pickCanvas();
                    if (!canvas) throw new Error('No suitable canvas found');
                    const ctx = canvas.getContext('2d');
                    if (!ctx) throw new Error('Canvas 2D context unavailable');
                    const rect = canvas.getBoundingClientRect();
                    const sx = (canvas.width && rect.width) ? (canvas.width / rect.width) : 1;
                    const sy = (canvas.height && rect.height) ? (canvas.height / rect.height) : 1;
                    const cx = (rect.width / 2 + {offset[0]}) * sx;
                    const cy = (rect.height / 2 + {offset[1]}) * sy;
                    const _w = {w} * sx;
                    const _h = {h} * sy;
                    const col = (window.__nlp2cmd_foreground || (window.__nlp2cmd_foreground || (window.colors && window.colors.foreground)) || '#000');
                    ctx.fillStyle = col;
                    ctx.strokeStyle = col;
                    ctx.fillRect(cx - _w/2, cy - _h/2, _w, _h);
                }}''')
                page.wait_for_timeout(200)
            except Exception as e:
                raise RuntimeError(f"Draw rectangle error: {e}")

        elif action == "draw_line":
            fo = params.get("from_offset", [0, 0])
            to = params.get("to_offset", [0, 0])
            try:
                # Check canvas before drawing
                before_check = page.evaluate('''() => {
                    const canvas = document.querySelector('.main-canvas') || document.querySelector('canvas');
                    if (!canvas) return {error: 'No canvas'};
                    const ctx = canvas.getContext('2d');
                    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                    let nonWhite = 0;
                    for (let i = 0; i < imageData.data.length; i += 400) {
                        if (imageData.data[i] !== 255 || imageData.data[i+1] !== 255 || imageData.data[i+2] !== 255) {
                            nonWhite++;
                        }
                    }
                    return {nonWhitePixels: nonWhite, isBlank: nonWhite <= 10};
                }''')
                
                page.evaluate(f'''() => {{
                    const pickCanvas = () => {{
                        const all = Array.from(document.querySelectorAll('canvas'));
                        if (!all.length) return null;
                        const main = document.querySelector('.main-canvas');
                        if (main && main instanceof HTMLCanvasElement) return main;
                        let best = null;
                        let bestArea = -1;
                        for (const c of all) {{
                            if (!(c instanceof HTMLCanvasElement)) continue;
                            const r = c.getBoundingClientRect();
                            if (!r || r.width <= 64 || r.height <= 64) continue;
                            const style = window.getComputedStyle(c);
                            if (style && (style.visibility === 'hidden' || style.display === 'none')) continue;
                            const area = r.width * r.height;
                            if (area > bestArea) {{ bestArea = area; best = c; }}
                        }}
                        return best;
                    }};
                    const canvas = pickCanvas();
                    if (!canvas) throw new Error('No suitable canvas found');
                    const ctx = canvas.getContext('2d');
                    if (!ctx) throw new Error('Canvas 2D context unavailable');
                    const rect = canvas.getBoundingClientRect();
                    const sx = (canvas.width && rect.width) ? (canvas.width / rect.width) : 1;
                    const sy = (canvas.height && rect.height) ? (canvas.height / rect.height) : 1;
                    const cx = (rect.width / 2) * sx;
                    const cy = (rect.height / 2) * sy;
                    ctx.beginPath();
                    ctx.moveTo(cx + {fo[0]} * sx, cy + {fo[1]} * sy);
                    ctx.lineTo(cx + {to[0]} * sx, cy + {to[1]} * sy);
                    ctx.strokeStyle = (window.__nlp2cmd_foreground || (window.__nlp2cmd_foreground || (window.colors && window.colors.foreground)) || '#ff0000');
                    ctx.lineWidth = 3;
                    ctx.stroke();
                    console.log('Drew line from', cx + {fo[0]} * sx, cy + {fo[1]} * sy, 'to', cx + {to[0]} * sx, cy + {to[1]} * sy);
                }}''')
                page.wait_for_timeout(200)
                
                # Verify drawing
                after_check = page.evaluate('''() => {
                    const canvas = document.querySelector('.main-canvas') || document.querySelector('canvas');
                    if (!canvas) return {error: 'No canvas'};
                    const ctx = canvas.getContext('2d');
                    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                    let nonWhite = 0;
                    for (let i = 0; i < imageData.data.length; i += 400) {
                        if (imageData.data[i] !== 255 || imageData.data[i+1] !== 255 || imageData.data[i+2] !== 255) {
                            nonWhite++;
                        }
                    }
                    return {nonWhitePixels: nonWhite, isBlank: nonWhite <= 10};
                }''')
                
                if after_check.get('nonWhitePixels', 0) > before_check.get('nonWhitePixels', 0):
                    console.print(f"  [green]✓ Line drawn: {after_check.get('nonWhitePixels')} non-white pixels[/green]")
                elif after_check.get('isBlank'):
                    console.print(f"  [yellow]⚠ Canvas still blank after line![/yellow]")
                else:
                    console.print(f"  [dim]Canvas pixels: {before_check.get('nonWhitePixels')} → {after_check.get('nonWhitePixels')}[/dim]")
                    
            except Exception as e:
                raise RuntimeError(f"Draw line error: {e}")

        elif action == "draw_ellipse":
            rx = float(params.get("rx", 10))
            ry = float(params.get("ry", 10))
            offset = params.get("offset", [0, 0])
            try:
                page.evaluate(f'''() => {{
                    const pickCanvas = () => {{
                        const all = Array.from(document.querySelectorAll('canvas'));
                        if (!all.length) return null;
                        const main = document.querySelector('.main-canvas');
                        if (main && main instanceof HTMLCanvasElement) return main;
                        let best = null;
                        let bestArea = -1;
                        for (const c of all) {{
                            if (!(c instanceof HTMLCanvasElement)) continue;
                            const r = c.getBoundingClientRect();
                            if (!r || r.width <= 64 || r.height <= 64) continue;
                            const style = window.getComputedStyle(c);
                            if (style && (style.visibility === 'hidden' || style.display === 'none')) continue;
                            const area = r.width * r.height;
                            if (area > bestArea) {{ bestArea = area; best = c; }}
                        }}
                        return best;
                    }};
                    const canvas = pickCanvas();
                    if (!canvas) throw new Error('No suitable canvas found');
                    const ctx = canvas.getContext('2d');
                    if (!ctx) throw new Error('Canvas 2D context unavailable');
                    const rect = canvas.getBoundingClientRect();
                    const sx = (canvas.width && rect.width) ? (canvas.width / rect.width) : 1;
                    const sy = (canvas.height && rect.height) ? (canvas.height / rect.height) : 1;
                    const cx = (rect.width / 2 + {offset[0]}) * sx;
                    const cy = (rect.height / 2 + {offset[1]}) * sy;
                    const _rx = {rx} * sx;
                    const _ry = {ry} * sy;
                    ctx.beginPath();
                    ctx.ellipse(cx, cy, _rx, _ry, 0, 0, 2 * Math.PI);
                    ctx.strokeStyle = (window.__nlp2cmd_foreground || (window.__nlp2cmd_foreground || (window.colors && window.colors.foreground)) || '#000');
                    ctx.stroke();
                }}''')
                page.wait_for_timeout(200)
            except Exception as e:
                raise RuntimeError(f"Draw ellipse error: {e}")
                
        elif action == "fill_at":
            offset = params.get("offset", [0, 0])
            try:
                page.evaluate(f'''() => {{
                    const pickCanvas = () => {{
                        const all = Array.from(document.querySelectorAll('canvas'));
                        if (!all.length) return null;
                        const main = document.querySelector('.main-canvas');
                        if (main && main instanceof HTMLCanvasElement) return main;
                        let best = null;
                        let bestArea = -1;
                        for (const c of all) {{
                            if (!(c instanceof HTMLCanvasElement)) continue;
                            const r = c.getBoundingClientRect();
                            if (!r || r.width <= 64 || r.height <= 64) continue;
                            const style = window.getComputedStyle(c);
                            if (style && (style.visibility === 'hidden' || style.display === 'none')) continue;
                            const area = r.width * r.height;
                            if (area > bestArea) {{
                                bestArea = area;
                                best = c;
                            }}
                        }}
                        return best;
                    }};
                    const canvas = pickCanvas();
                    const rect = canvas.getBoundingClientRect();
                    const cx = rect.width / 2 + {offset[0]};
                    const cy = rect.height / 2 + {offset[1]};
                    const ev = new MouseEvent('pointerdown', {{
                        clientX: rect.left + cx,
                        clientY: rect.top + cy,
                        bubbles: true
                    }});
                    canvas.dispatchEvent(ev);
                    setTimeout(() => {{
                        const up = new MouseEvent('pointerup', {{
                            clientX: rect.left + cx,
                            clientY: rect.top + cy,
                            bubbles: true
                        }});
                        canvas.dispatchEvent(up);
                    }}, 50);
                }}''')
                page.wait_for_timeout(200)
            except Exception as e:
                raise RuntimeError(f"Fill at error: {e}")

        elif action == "click_canvas":
            offset = params.get("offset", [0, 0])
            try:
                page.evaluate(f'''() => {{
                    const pickCanvas = () => {{
                        const all = Array.from(document.querySelectorAll('canvas'));
                        if (!all.length) return null;
                        const main = document.querySelector('.main-canvas');
                        if (main && main instanceof HTMLCanvasElement) return main;
                        let best = null;
                        let bestArea = -1;
                        for (const c of all) {{
                            if (!(c instanceof HTMLCanvasElement)) continue;
                            const r = c.getBoundingClientRect();
                            if (!r || r.width <= 64 || r.height <= 64) continue;
                            const style = window.getComputedStyle(c);
                            if (style && (style.visibility === 'hidden' || style.display === 'none')) continue;
                            const area = r.width * r.height;
                            if (area > bestArea) {{
                                bestArea = area;
                                best = c;
                            }}
                        }}
                        return best;
                    }};
                    const canvas = pickCanvas();
                    const rect = canvas.getBoundingClientRect();
                    const cx = rect.width / 2 + {offset[0]};
                    const cy = rect.height / 2 + {offset[1]};
                    const ev = new MouseEvent('pointerdown', {{
                        clientX: rect.left + cx,
                        clientY: rect.top + cy,
                        bubbles: true
                    }});
                    canvas.dispatchEvent(ev);
                    setTimeout(() => {{
                        const up = new MouseEvent('pointerup', {{
                            clientX: rect.left + cx,
                            clientY: rect.top + cy,
                            bubbles: true
                        }});
                        canvas.dispatchEvent(up);
                    }}, 50);
                }}''')
                page.wait_for_timeout(200)
            except Exception as e:
                raise RuntimeError(f"Click canvas error: {e}")


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

            _debug(f"save_env: var_name={var_name}, file={file_path}, value_src={'$ref' if isinstance(value, str) and value.startswith('$') else 'direct'}")

            # Resolve $variable references
            if isinstance(value, str) and value.startswith("$"):
                ref_name = value[1:]
                value = variables.get(ref_name, "")
                _debug(f"save_env: resolved ${ref_name} → {'<empty>' if not value else f'{len(value)} chars'}")

            if not value:
                raise ValueError(f"Brak wartości do zapisania dla {var_name} (zmienna nie zawiera klucza)")

            env_path = Path(file_path).resolve()
            existing = env_path.read_text() if env_path.exists() else ""

            if f"{var_name}=" in existing:
                updated = re.sub(
                    rf"{re.escape(var_name)}=.*",
                    f'{var_name}="{value}"',
                    existing,
                )
                env_path.write_text(updated)
                _debug(f"save_env: updated existing {var_name} in {env_path}")
            else:
                with open(env_path, "a") as f:
                    f.write(f'\n{var_name}="{value}"\n')
                _debug(f"save_env: appended {var_name} to {env_path}")

            # Also set in current process environment so subsequent steps can use it
            os.environ[var_name] = value
            _debug(f"save_env: os.environ[{var_name}] set ({len(value)} chars)")

            # Verify the file was actually written
            try:
                verify_content = env_path.read_text()
                if f'{var_name}="{value}"' not in verify_content and f"{var_name}={value}" not in verify_content:
                    console.print(f"  [red]⚠ Weryfikacja: {var_name} NIE znaleziony w {env_path}![/red]")
                else:
                    _debug(f"save_env: verified {var_name} present in {env_path}")
            except Exception as ve:
                _debug(f"save_env: verification read failed: {ve}")

            return value

        elif action == "prompt_secret":
            prompt = str(params.get("prompt") or "Enter secret: ")
            env_var = str(params.get("env_var") or "").strip()
            key_pattern = str(params.get("key_pattern") or "").strip()

            # Check if stdin is a TTY
            try:
                is_tty = bool(getattr(sys.stdin, "isatty", lambda: False)())
            except Exception:
                is_tty = False

            # Non-interactive fallback: use env var ONLY when no TTY available
            if not is_tty:
                if env_var:
                    try:
                        env_val = os.environ.get(env_var)
                    except Exception:
                        env_val = None
                    if isinstance(env_val, str) and env_val.strip():
                        _debug(f"prompt_secret: non-TTY, using {env_var} from environment")
                        console.print(f"  [dim]ℹ Użyto istniejącej wartości {env_var} z os.environ (brak TTY)[/dim]")
                        return env_val.strip()
                    raise ValueError(
                        f"prompt_secret requires interactive TTY or {env_var} in environment"
                    )
                raise ValueError("prompt_secret requires interactive TTY")

            # Interactive mode — always prompt the user
            _debug(f"prompt_secret: TTY available, prompting user (env_var={env_var})")

            max_attempts = 3
            for attempt in range(1, max_attempts + 1):
                try:
                    import getpass
                    val = getpass.getpass(prompt)
                except Exception:
                    val = console.input(prompt)

                val = str(val or "").strip()
                if not val:
                    if attempt < max_attempts:
                        console.print(f"  [yellow]⚠ Pusty klucz. Próba {attempt}/{max_attempts}. Spróbuj ponownie.[/yellow]")
                        continue
                    raise ValueError("Nie podano klucza API (3 próby)")

                # Validate against key pattern if provided
                if key_pattern:
                    if re.match(key_pattern, val):
                        _debug(f"prompt_secret: key matches pattern {key_pattern}")
                        console.print(f"  [green]✓ Klucz pasuje do wzorca {key_pattern}[/green]")
                    else:
                        console.print(f"  [yellow]⚠ Klucz nie pasuje do oczekiwanego wzorca: {key_pattern}[/yellow]")
                        if attempt < max_attempts:
                            console.print(f"  [yellow]  Próba {attempt}/{max_attempts}. Wklej poprawny klucz lub Enter aby użyć tego.[/yellow]")
                            try:
                                retry = getpass.getpass("  Wklej ponownie (lub Enter aby zachować): ")
                            except Exception:
                                retry = ""
                            if retry.strip():
                                val = retry.strip()
                                if re.match(key_pattern, val):
                                    console.print(f"  [green]✓ Klucz pasuje do wzorca[/green]")
                                    break
                            else:
                                console.print(f"  [dim]  Używam podanego klucza mimo niezgodności wzorca.[/dim]")
                                break
                        else:
                            console.print(f"  [dim]  Używam podanego klucza mimo niezgodności wzorca.[/dim]")

                _debug(f"prompt_secret: got {len(val)} chars")
                return val

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

        elif action == "check_session":
            # Check if the user is logged into a service by examining page content
            service = params.get("service", "unknown")
            session_indicators = params.get("session_indicators", [])
            login_indicators = params.get("login_indicators", [])
            login_url = params.get("login_url", "")
            keys_url = params.get("keys_url", "")

            _debug(f"check_session: checking {service} session state")
            console.print(f"  [dim]🔍 Sprawdzam sesję {service}...[/dim]")

            try:
                body_text = page.text_content("body") or ""
                current_url = page.url

                # Check login indicators first (are we on a login page?)
                is_login_page = any(ind.lower() in body_text.lower() for ind in login_indicators)
                if login_url and login_url in current_url:
                    is_login_page = True

                # Check session indicators (are we logged in?)
                has_session = any(ind.lower() in body_text.lower() for ind in session_indicators)

                if has_session and not is_login_page:
                    console.print(f"  [green]✓[/green] Zalogowany na {service}")
                    _debug(f"check_session: {service} — session active")
                    return "logged_in"
                elif is_login_page:
                    console.print(f"  [yellow]![/yellow] Niezalogowany na {service}")
                    console.print(f"  [dim]   Strona logowania: {current_url}[/dim]")
                    console.print(f"  [dim]   Zaloguj się w przeglądarce, potem kontynuuj[/dim]")
                    _debug(f"check_session: {service} — login page detected")

                    # Ask user if they want to open email to get verification link
                    try:
                        is_tty = bool(getattr(sys.stdin, "isatty", lambda: False)())
                    except Exception:
                        is_tty = False

                    if is_tty:
                        console.print(
                            f"\n  [bold]Czy potrzebujesz otworzyć email "
                            f"(np. do weryfikacji logowania)?[/bold]"
                        )
                        console.print(
                            f"  Wpisz nazwę klienta email "
                            f"(roundcube/thunderbird/gmail/outlook) lub Enter aby pominąć:"
                        )
                        email_choice = input("  > ").strip().lower()
                        if email_choice:
                            _debug(f"check_session: user chose email client: {email_choice}")
                            variables["_email_client"] = email_choice
                            return "needs_login_with_email"

                    return "needs_login"
                else:
                    console.print(f"  [dim]?[/dim] Nie udało się określić stanu sesji {service}")
                    _debug(f"check_session: {service} — session state unknown")
                    return "unknown"
            except Exception as e:
                _debug(f"check_session error: {e}")
                return "error"

        elif action == "extract_key":
            # Try to extract API key from page DOM + clipboard
            key_pattern = params.get("key_pattern", "")
            key_selectors = params.get("selectors", [
                "code", "pre", "input[readonly]", "input[type='text'][readonly]",
                ".api-key", "[data-testid*='key']", "[class*='key']",
                ".token", "[data-testid*='token']",
            ])
            service = params.get("service", "")
            console.print(f"  [dim]🔍 Szukam klucza API na stronie {service}...[/dim]")

            def _copy_key_to_clipboard(found_key: str) -> None:
                """Copy extracted key to clipboard via JS."""
                try:
                    page.evaluate(f"navigator.clipboard.writeText({json.dumps(found_key)})")
                    _debug(f"extract_key: copied key to clipboard ({len(found_key)} chars)")
                except Exception as ce:
                    _debug(f"extract_key: clipboard copy failed: {ce}")

            # Strategy 1: Search DOM elements
            for sel in key_selectors:
                try:
                    elements = page.query_selector_all(sel)
                    for el in elements:
                        text = (el.text_content() or "").strip()
                        if not text or len(text) < 10:
                            continue
                        if key_pattern and re.match(key_pattern, text):
                            console.print(f"  [green]✓[/green] Znaleziono klucz w DOM ({sel}, {len(text)} znaków)")
                            _debug(f"extract_key: found via DOM selector {sel}")
                            _copy_key_to_clipboard(text)
                            return text
                        if not key_pattern and re.match(r'^[a-zA-Z0-9_\-]{20,}$', text):
                            console.print(f"  [green]✓[/green] Potencjalny klucz w DOM ({sel}, {len(text)} znaków)")
                            _copy_key_to_clipboard(text)
                            return text
                except Exception:
                    continue

            # Strategy 2: Check clipboard
            try:
                from nlp2cmd.automation.step_validator import StepValidator
                clipboard = StepValidator.get_clipboard()
                if clipboard and len(clipboard) >= 10:
                    if key_pattern and re.match(key_pattern, clipboard):
                        console.print(f"  [green]✓[/green] Klucz znaleziony w schowku ({len(clipboard)} znaków, pasuje do wzorca)")
                        return clipboard
                    elif not key_pattern and re.match(r'^[a-zA-Z0-9_\-]{20,}$', clipboard):
                        console.print(f"  [green]✓[/green] Potencjalny klucz w schowku ({len(clipboard)} znaków)")
                        return clipboard
            except Exception as e:
                _debug(f"extract_key: clipboard check failed: {e}")

            # Strategy 3: Full body regex scan
            try:
                body = page.text_content("body") or ""
                if key_pattern:
                    match = re.search(key_pattern, body)
                    if match:
                        found = match.group(0)
                        console.print(f"  [green]✓[/green] Klucz znaleziony w treści strony ({len(found)} znaków)")
                        _copy_key_to_clipboard(found)
                        return found
            except Exception as e:
                _debug(f"extract_key: body scan failed: {e}")

            console.print(f"  [yellow]⚠[/yellow] Nie znaleziono klucza na stronie")
            return None

        elif action == "check_clipboard":
            # Validate clipboard content against expected key pattern
            key_pattern = params.get("key_pattern", "")
            env_var = params.get("env_var", "")
            console.print(f"  [dim]📋 Sprawdzam schowek...[/dim]")
            try:
                from nlp2cmd.automation.step_validator import StepValidator
                clipboard = StepValidator.get_clipboard()
                if clipboard and len(clipboard) >= 10:
                    if key_pattern and re.match(key_pattern, clipboard):
                        console.print(f"  [green]✓[/green] Klucz w schowku pasuje do wzorca ({len(clipboard)} znaków)")
                        return clipboard
                    elif clipboard and len(clipboard) >= 20:
                        console.print(f"  [dim]   Schowek zawiera {len(clipboard)} znaków (brak wzorca do walidacji)[/dim]")
                        return clipboard
                    else:
                        console.print(f"  [yellow]⚠[/yellow] Schowek nie zawiera klucza API")
                else:
                    console.print(f"  [yellow]⚠[/yellow] Schowek pusty lub za krótki")
            except Exception as e:
                console.print(f"  [yellow]⚠[/yellow] Nie można odczytać schowka: {e}")
            return None

        elif action == "verify_env":
            var_name = params.get("var_name", "UNKNOWN")
            file_path = params.get("file", ".env")
            return self._do_verify_env(console, var_name, file_path, variables)

        elif action == "echo":
            msg = params.get("message", "") or params.get("text", "")
            if msg:
                _debug(msg)
                # Also print to user console for visibility
                for line in str(msg).split("\n"):
                    console.print(f"  [dim]{line}[/dim]")

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

    def _do_verify_env(self, console, var_name: str, file_path: str, variables: dict) -> str:
        """Verify that an env var was saved to .env and is accessible.

        Returns a status string: 'verified', 'file_missing', 'var_missing', 'error'.
        """
        env_path = Path(file_path).resolve()
        _debug(f"verify_env: checking {var_name} in {env_path}")

        results = []

        # 1. Check .env file exists and contains the variable
        if env_path.exists():
            try:
                content = env_path.read_text()
                if f"{var_name}=" in content:
                    # Extract value (handle quoted and unquoted)
                    match = re.search(rf'{re.escape(var_name)}="?([^"\n]*)"?', content)
                    val_preview = ""
                    if match:
                        val = match.group(1)
                        val_preview = f"{val[:8]}...{val[-4:]}" if len(val) > 16 else f"{len(val)} chars"
                    console.print(f"  [green]✓[/green] Plik {env_path}: {var_name} znaleziony ({val_preview})")
                    results.append("file_ok")
                else:
                    console.print(f"  [red]✗[/red] Plik {env_path}: {var_name} NIE znaleziony!")
                    results.append("var_missing")
            except Exception as e:
                console.print(f"  [red]✗[/red] Błąd odczytu {env_path}: {e}")
                results.append("error")
        else:
            console.print(f"  [red]✗[/red] Plik {env_path} nie istnieje!")
            results.append("file_missing")

        # 2. Check os.environ
        env_val = os.environ.get(var_name)
        if env_val:
            console.print(f"  [green]✓[/green] os.environ[{var_name}]: ustawiony ({len(env_val)} znaków)")
            results.append("env_ok")
        else:
            console.print(f"  [yellow]![/yellow] os.environ[{var_name}]: nie ustawiony (wymaga: source {file_path})")
            results.append("env_missing")

        # 3. Check variables dict (pipeline internal)
        api_key_val = variables.get("api_key", "")
        if api_key_val:
            _debug(f"verify_env: pipeline variable 'api_key' has {len(api_key_val)} chars")
        else:
            _debug("verify_env: pipeline variable 'api_key' is empty")

        # 4. Final summary
        if "file_ok" in results:
            console.print(f"\n  [bold green]✅ WERYFIKACJA POZYTYWNA[/bold green]: {var_name} zapisany w {file_path}")
            console.print(f"  [dim]   Aby załadować w bieżącej sesji: source {file_path}[/dim]")
            console.print(f"  [dim]   Aby sprawdzić: echo ${var_name}[/dim]")
            return "verified"
        else:
            console.print(f"\n  [bold red]❌ WERYFIKACJA NEGATYWNA[/bold red]: {var_name} nie został zapisany!")
            console.print(f"  [dim]   Status: {', '.join(results)}[/dim]")
            return "failed"

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
