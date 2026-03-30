from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import shutil
import sys
import threading
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse, urljoin

from rich.console import Console

from nlp2cmd.pipeline_runner_utils import (
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
    get_timestamp,
    ensure_dir,
    ask_for_screenshot,
    take_screenshot,
    VideoRecorder,
    ask_for_video_recording,
)
from nlp2cmd.utils.yaml_compat import yaml

from nlp2cmd.adapters.base import SafetyPolicy

# Import new step handlers for modular dispatch
from nlp2cmd.step_handlers import StepDispatcher

# Import new plan execution components
from nlp2cmd.plan_execution import PlanExecutor


# Maximum total steps allowed in a plan (including fallback-injected steps)
_MAX_PLAN_STEPS = int(os.environ.get("NLP2CMD_MAX_PLAN_STEPS", "30"))
# Maximum number of fallback injections per plan execution
_MAX_FALLBACK_INJECTIONS = int(os.environ.get("NLP2CMD_MAX_FALLBACK_INJECTIONS", "3"))
# Default prompt timeout in seconds (0 = no timeout)
_PROMPT_TIMEOUT = int(os.environ.get("NLP2CMD_PROMPT_TIMEOUT", "60"))


class PlanExecutionMixin:
    """Multi-step ActionPlan execution methods for PipelineRunner."""

    @staticmethod
    def _sanitize_replacement_steps(
        steps: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Drop invalid injected steps (mostly from LLM) to keep execution safe.

        This is not a security boundary; it is a robustness filter.
        """
        sanitized: list[dict[str, Any]] = []
        for s in steps or []:
            if not isinstance(s, dict):
                continue
            action = str(s.get("action") or "").strip()
            params = s.get("params", {})
            if not action:
                continue
            if not isinstance(params, dict):
                params = {}

            if action in {"save_env", "verify_env"}:
                var_name = str(params.get("var_name") or "").strip()
                if not var_name or var_name.upper() in {"UNKNOWN", "UNKNOWN_KEY"}:
                    _debug(f"sanitize: dropping invalid {action} step (var_name={var_name!r})")
                    continue

            sanitized.append(
                {
                    "action": action,
                    "params": params,
                    **({"description": s.get("description", "")} if s.get("description") else {}),
                    **({"store_as": s.get("store_as")} if s.get("store_as") else {}),
                }
            )
        return sanitized

    @staticmethod
    def _detect_desktop_steps(plan: Any) -> bool:
        """Detect whether a plan contains steps that must use desktop execution."""
        desktop_actions = frozenset({"open_firefox_tab", "desktop_wait"})
        try:
            steps_iter = getattr(plan, "steps", None) or []
            return any(
                str(getattr(step, "action", "")).startswith("desktop_")
                or str(getattr(step, "action", "")) in desktop_actions
                for step in steps_iter
            )
        except Exception:
            return False

    @staticmethod
    def _initialize_plan_variables(plan: Any) -> dict[str, str]:
        """Initialize execution variables, including known service metadata."""
        variables: dict[str, str] = {}
        try:
            from nlp2cmd.automation.action_planner import KNOWN_SERVICES

            query = (getattr(plan, "query", "") or "").lower()
            for service_name, service in KNOWN_SERVICES.items():
                if service_name in query:
                    variables["_key_pattern"] = service.get("key_pattern", "")
                    break
        except Exception:
            pass
        return variables

    @staticmethod
    def _build_service_context(plan: Any) -> tuple[dict[str, Any], str]:
        """Resolve service config used by validator/fallback infrastructure."""
        service_config: dict[str, Any] = {}
        service_name = ""
        try:
            from nlp2cmd.automation.action_planner import KNOWN_SERVICES

            query = (getattr(plan, "query", "") or "").lower()
            for known_name, known_config in KNOWN_SERVICES.items():
                if known_name in query:
                    service_config = known_config
                    service_name = known_name
                    break
        except Exception:
            pass
        return service_config, service_name

    def _inject_replacement_steps(
        self,
        step_queue: list[Any],
        step_idx: int,
        replacement_steps: list[dict[str, Any]],
        console: Console,
        *,
        injection_count: int,
        noun: str,
    ) -> tuple[bool, int]:
        """Inject sanitized fallback steps after the current step when limits allow."""
        if (
            injection_count >= _MAX_FALLBACK_INJECTIONS
            or len(step_queue) + len(replacement_steps) > _MAX_PLAN_STEPS
        ):
            console.print(
                f"  [yellow]⚠ Limit fallbacków osiągnięty "
                f"({injection_count}/{_MAX_FALLBACK_INJECTIONS} "
                f"injekcji, {len(step_queue)} kroków) — pomijam[/yellow]"
            )
            return False, injection_count

        from nlp2cmd.automation.action_planner import ActionStep

        new_steps = []
        for replacement_step in self._sanitize_replacement_steps(replacement_steps):
            new_steps.append(
                ActionStep(
                    action=replacement_step["action"],
                    params=replacement_step.get("params", {}),
                    description=replacement_step.get("description", ""),
                    store_as=replacement_step.get("store_as"),
                )
            )

        step_queue[step_idx + 1 : step_idx + 1] = new_steps
        injection_count += 1
        console.print(
            f"  [dim]   📝 Wstawiono {len(new_steps)} {noun} kroków[/dim]"
        )
        return True, injection_count

    @staticmethod
    def _summarize_results(results_log: list[dict[str, Any]]) -> tuple[int, int, int, int]:
        """Return ok, error, failed, and total elapsed milliseconds."""
        ok_count = sum(
            1
            for result in results_log
            if result["status"] in ("ok", "ok_retry", "ok_fallback", "fallback_injected")
        )
        fail_count = sum(1 for result in results_log if result["status"] == "failed")
        err_count = sum(
            1 for result in results_log if result["status"] in ("error", "failed_validation")
        )
        total_ms = sum(result.get("elapsed_ms", 0) for result in results_log)
        return ok_count, err_count, fail_count, total_ms

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

        has_desktop_steps = self._detect_desktop_steps(plan)

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
            variables = self._initialize_plan_variables(plan)
            results_log: list[dict] = []

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
                ok_count, err_count, fail_count, total_ms = self._summarize_results(results_log)

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

            try:
                from nlp2cmd.automation.feedback_loop import FeedbackLoop, PageAnalyzer
                feedback_loop = FeedbackLoop()
            except ImportError:
                feedback_loop = None

            # Resolve service config for fallback context
            _svc_config, _svc_name = self._build_service_context(plan)

            # Build mutable step queue (allows injecting fallback steps)
            step_queue = list(plan.steps)
            step_idx = 0
            _fallback_injection_count = 0

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
                    # Skip prompt when key is already available
                    if step.action == "prompt_secret":
                        details = pre_result.details or {}
                        already_extracted = bool(details.get("already_extracted"))
                        already_set = bool(details.get("already_set"))
                        already_set_invalid = bool(details.get("already_set_invalid"))
                        if already_extracted or already_set:
                            existing_val = ""
                            source = ""

                            if already_extracted:
                                var_name = details.get("var", "api_key")
                                existing_val = variables.get(var_name, "")
                                source = f"${var_name}"
                            else:
                                env_var = str(params_resolved.get("env_var") or "").strip()
                                if env_var:
                                    existing_val = os.environ.get(env_var, "")
                                    source = f"os.environ[{env_var}]"

                            if existing_val and not already_set_invalid:
                                console.print(
                                    f"  [green]✓[/green] Klucz już dostępny "
                                    f"({source}, {len(existing_val)} znaków) — pomijam prompt"
                                )
                                if step.store_as:
                                    variables[step.store_as] = existing_val
                                results_log.append({
                                    "step": step_idx + 1, "action": step.action,
                                    "status": "ok", "stored": step.store_as,
                                    "note": "skipped_already_available",
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
                                step.action in ("navigate", "check_session", "extract_key")
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
                                        injected, _fallback_injection_count = self._inject_replacement_steps(
                                            step_queue,
                                            step_idx,
                                            fb_result.replacement_steps,
                                            console,
                                            injection_count=_fallback_injection_count,
                                            noun="dodatkowych",
                                        )
                                        if injected:
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

                    # --- Feedback loop: classify failure ---
                    _diagnosis_str = ""
                    if feedback_loop:
                        try:
                            params_resolved_diag = self._resolve_plan_variables(
                                step.params or {}, variables,
                            )
                            diagnosis = feedback_loop.classify_failure(
                                action=step.action,
                                error=str(e),
                                page=page,
                                params=params_resolved_diag,
                                service_config=_svc_config,
                            )
                            _diagnosis_str = (
                                f"{diagnosis.failure_type.value}: {diagnosis.reason}"
                            )
                            console.print(
                                f"  [dim]   🔍 Diagnoza: {_diagnosis_str}[/dim]"
                            )
                            if diagnosis.suggested_fix:
                                console.print(
                                    f"  [dim]   💡 Sugestia: {diagnosis.suggested_fix}[/dim]"
                                )
                        except Exception:
                            pass

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
                            error_message=str(e) + (f" [{_diagnosis_str}]" if _diagnosis_str else ""),
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
                                injected, _fallback_injection_count = self._inject_replacement_steps(
                                    step_queue,
                                    step_idx,
                                    fb_result.replacement_steps,
                                    console,
                                    injection_count=_fallback_injection_count,
                                    noun="alternatywnych",
                                )
                                if injected:
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
            ok_count, err_count, fail_count, total_ms = self._summarize_results(results_log)

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

    def execute_action_plan_dispatch(
        self,
        plan,
        *,
        dry_run: bool = False,
        video_fmt: Optional[str] = None,
        video_dir: Optional[str] = None,
        confirm: bool = False,
    ) -> RunnerResult:
        """Execute an ActionPlan using the modular PlanExecutor (v2).
        
        This method uses the PlanExecutor to handle browser setup, step execution,
        validation, fallback, and retry logic in a modular way.
        
        Falls back to legacy execute_action_plan for unhandled cases.
        
        Args:
            plan: ActionPlan instance with steps to execute
            dry_run: If True, only show the plan without executing
            video_fmt: Video format for recording
            video_dir: Directory for video recordings
            confirm: If True, user has confirmed execution
            
        Returns:
            RunnerResult with execution status and data
        """
        # Create executor with same headless setting
        executor = PlanExecutor(headless=self.headless)
        
        # Execute the plan
        return executor.execute(
            plan=plan,
            dry_run=dry_run,
            video_fmt=video_fmt or self.video_fmt,
            video_dir=video_dir or self.video_dir,
            confirm=confirm,
        )

    def _execute_plan_step(self, page, context, step, variables: dict) -> Optional[str]:
        """Execute a single ActionPlan step. Returns extracted value or None."""
        params = self._resolve_plan_variables(step.params or {}, variables)
        action = step.action

        console = Console()
        print(f"DEBUG: _execute_plan_step called with action={action}", file=sys.stderr, flush=True)

        if StepDispatcher.has_handler(action):
            try:
                return StepDispatcher.dispatch(
                    action=action,
                    page=page,
                    context=context,
                    params=params,
                    variables=variables,
                    console=console,
                )
            except Exception as e:
                _debug(f"Dispatcher failed for {action}: {e}")
                raise

        return None

    def _execute_plan_step_dispatch(
        self,
        page,
        context,
        step,
        variables: dict,
    ) -> Optional[str]:
        """Execute a step using the new modular dispatcher (v2).
        
        This method uses the StepDispatcher to route actions to modular handlers.
        Falls back to legacy _execute_plan_step if no handler is registered.
        
        Args:
            page: Playwright page
            context: Playwright browser context
            step: ActionStep with action and params
            variables: Variables dict from previous steps
            
        Returns:
            Result value or None
        """
        from rich.console import Console
        console = Console()
        
        action = step.action
        params = self._resolve_plan_variables(step.params or {}, variables)
        
        # Try new dispatcher first
        if StepDispatcher.has_handler(action):
            try:
                result = StepDispatcher.dispatch(
                    action=action,
                    page=page,
                    context=context,
                    params=params,
                    variables=variables,
                    console=console,
                )
                return result
            except Exception as e:
                _debug(f"Dispatcher error for {action}: {e}")
                raise
        
        # Fallback to legacy method
        return self._execute_plan_step(page, context, step, variables)

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
