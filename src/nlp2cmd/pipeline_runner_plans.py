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

            try:
                from nlp2cmd.automation.feedback_loop import FeedbackLoop, PageAnalyzer
                feedback_loop = FeedbackLoop()
            except ImportError:
                feedback_loop = None

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
                                        if (
                                            _fallback_injection_count >= _MAX_FALLBACK_INJECTIONS
                                            or len(step_queue) + len(fb_result.replacement_steps) > _MAX_PLAN_STEPS
                                        ):
                                            console.print(
                                                f"  [yellow]⚠ Limit fallbacków osiągnięty "
                                                f"({_fallback_injection_count}/{_MAX_FALLBACK_INJECTIONS} "
                                                f"injekcji, {len(step_queue)} kroków) — pomijam[/yellow]"
                                            )
                                        else:
                                            from nlp2cmd.automation.action_planner import ActionStep
                                            new_steps = []
                                            for rs in self._sanitize_replacement_steps(fb_result.replacement_steps):
                                                new_steps.append(ActionStep(
                                                    action=rs["action"],
                                                    params=rs.get("params", {}),
                                                    description=rs.get("description", ""),
                                                    store_as=rs.get("store_as"),
                                                ))
                                            step_queue[step_idx+1:step_idx+1] = new_steps
                                            _fallback_injection_count += 1
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
                                if (
                                    _fallback_injection_count >= _MAX_FALLBACK_INJECTIONS
                                    or len(step_queue) + len(fb_result.replacement_steps) > _MAX_PLAN_STEPS
                                ):
                                    console.print(
                                        f"  [yellow]⚠ Limit fallbacków osiągnięty "
                                        f"({_fallback_injection_count}/{_MAX_FALLBACK_INJECTIONS} "
                                        f"injekcji, {len(step_queue)} kroków) — pomijam[/yellow]"
                                    )
                                else:
                                    from nlp2cmd.automation.action_planner import ActionStep
                                    new_steps = []
                                    for rs in self._sanitize_replacement_steps(fb_result.replacement_steps):
                                        new_steps.append(ActionStep(
                                            action=rs["action"],
                                            params=rs.get("params", {}),
                                            description=rs.get("description", ""),
                                            store_as=rs.get("store_as"),
                                        ))
                                    step_queue[step_idx+1:step_idx+1] = new_steps
                                    _fallback_injection_count += 1
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
            if not url or url in ("https://", "http://"):
                raise ValueError(f"navigate: empty or invalid URL '{url}'. Add url parameter.")
            if not url.startswith("http"):
                url = f"https://{url}"
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(1000)

            # Handle security-checkup redirects (e.g. HuggingFace)
            current_url = page.url or ""
            if "security-checkup" in current_url and "security-checkup" not in url:
                _debug(f"navigate: security-checkup redirect detected, trying to pass through")
                # Try clicking common "continue" / "skip" / "confirm" buttons
                _security_passed = False
                for _btn_text in ["Continue", "Skip", "Confirm", "Kontynuuj", "Pomiń", "I understand"]:
                    try:
                        _btn = page.get_by_text(_btn_text, exact=False).first
                        if _btn.is_visible(timeout=1500):
                            _btn.click(timeout=3000)
                            page.wait_for_timeout(2000)
                            _security_passed = True
                            _debug(f"navigate: clicked '{_btn_text}' on security-checkup")
                            break
                    except Exception:
                        continue

                # Re-navigate to original target after passing security check
                new_url = page.url or ""
                if new_url != url and "security-checkup" not in new_url:
                    # Security check redirected us somewhere else — try target again
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=15000)
                        page.wait_for_timeout(1000)
                    except Exception:
                        pass
                elif "security-checkup" in new_url:
                    # Still stuck on security — try direct navigation anyway
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=15000)
                        page.wait_for_timeout(1000)
                    except Exception:
                        pass

        elif action == "discover_service_section":
            service = str(params.get("service") or "service")
            section = str(params.get("section") or "keys").lower()
            base_url = str(params.get("base_url") or "").strip()
            keys_url = str(params.get("keys_url") or "").strip()
            raw_hints = params.get("hints", [])
            if isinstance(raw_hints, str):
                hints = [raw_hints]
            elif isinstance(raw_hints, list):
                hints = [str(h) for h in raw_hints if str(h).strip()]
            else:
                hints = []

            keyword_defaults = [
                "api key", "api keys", "token", "tokens", "access token",
                "developer", "credential", "secret", "settings",
                "klucz", "klucze", "tokeny", "ustawienia",
            ]
            hint_terms = {h.lower() for h in (hints + keyword_defaults) if h}

            current_url = page.url or ""
            if keys_url and keys_url in current_url:
                _debug(f"discover_service_section: already on keys page for {service}")
                return current_url

            # Ensure we are at least on the provider domain before link discovery
            if current_url in ("", "about:blank"):
                seed_url = base_url or keys_url
                if seed_url:
                    if not seed_url.startswith("http"):
                        seed_url = f"https://{seed_url}"
                    page.goto(seed_url, wait_until="domcontentloaded", timeout=15000)
                    page.wait_for_timeout(700)
                    current_url = page.url or ""

            best_link = ""
            best_score = -1
            try:
                links = page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('a[href]')).slice(0, 300).map(a => ({
                        href: a.href || '',
                        text: (a.innerText || a.textContent || '').trim(),
                        aria: (a.getAttribute('aria-label') || '').trim(),
                    }));
                }""")
            except Exception:
                links = []

            if isinstance(links, list):
                for item in links:
                    if not isinstance(item, dict):
                        continue
                    href = str(item.get("href") or "").strip()
                    if not href or href.startswith("javascript:") or href.startswith("mailto:"):
                        continue
                    text_blob = " ".join([
                        href,
                        str(item.get("text") or ""),
                        str(item.get("aria") or ""),
                    ]).lower()
                    score = sum(1 for term in hint_terms if term in text_blob)
                    if section == "keys" and any(k in text_blob for k in ("key", "token", "api", "secret", "credential")):
                        score += 1
                    if score > best_score:
                        best_score = score
                        best_link = href

            candidate_urls: list[str] = []
            if best_link:
                candidate_urls.append(best_link)
            if keys_url:
                candidate_urls.append(keys_url)

            if base_url:
                normalized_base = base_url if base_url.startswith("http") else f"https://{base_url}"
                for path in [
                    "/settings/tokens",
                    "/settings/token",
                    "/settings/keys",
                    "/settings/api-keys",
                    "/settings/access-tokens",
                    "/account/api-tokens",
                    "/account/api-keys",
                    "/account/tokens",
                    "/api-keys",
                    "/tokens",
                    "/keys",
                ]:
                    candidate_urls.append(urljoin(normalized_base, path))

            seen: set[str] = set()
            deduped_candidates: list[str] = []
            for cand in candidate_urls:
                if cand and cand not in seen:
                    seen.add(cand)
                    deduped_candidates.append(cand)

            for cand in deduped_candidates:
                try:
                    page.goto(cand, wait_until="domcontentloaded", timeout=12000)
                    page.wait_for_timeout(600)
                    now_url = (page.url or "").lower()
                    body = (page.text_content("body") or "").lower()
                    score = sum(1 for term in hint_terms if term in (now_url + " " + body))
                    if score > 0 or any(k in now_url for k in ("key", "token", "api", "credential")):
                        resolved = page.url or cand
                        _debug(f"discover_service_section: resolved {service}/{section} -> {resolved}")
                        return resolved
                except Exception:
                    continue

            # Last resort: use PageAnalyzer to scan navigation links
            if page is not None:
                try:
                    from nlp2cmd.automation.feedback_loop import PageAnalyzer
                    pa_url = PageAnalyzer.find_api_keys_section(page)
                    if pa_url:
                        _debug(f"discover_service_section: PageAnalyzer found {pa_url}")
                        page.goto(pa_url, wait_until="domcontentloaded", timeout=12000)
                        page.wait_for_timeout(600)
                        return page.url or pa_url
                except Exception:
                    pass

            _debug(
                f"discover_service_section: could not confidently resolve {service}/{section}; "
                f"staying on {page.url or current_url}"
            )
            return page.url or current_url

        elif action == "new_tab":
            page = context.new_page()

        elif action == "click_radio":
            # Special action for radio button selection (e.g., token type)
            selector = params.get("selector")
            timeout = int(params.get("timeout", 5000))
            if selector:
                page.wait_for_selector(selector, state="visible", timeout=timeout)
                page.click(selector, timeout=timeout)
            else:
                raise ValueError("click_radio requires selector")

        elif action == "click":
            selector = params.get("selector")
            text = params.get("text")
            timeout = int(params.get("timeout", 10000))
            max_retries = int(params.get("retries", 3))

            # Normalize common LLM selector mistake: CSS :contains('...') is not valid.
            # Convert to text-based click when possible.
            if (not text) and isinstance(selector, str) and ":contains(" in selector:
                m = re.search(r":contains\((['\"])(.+?)\1\)", selector)
                if m:
                    text = m.group(2)
                    selector = None
                    _debug(f"click: normalized :contains() -> text={text!r}")

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
            selector = params.get("selector", "input")
            text = params.get("text", "")
            timeout = int(params.get("timeout", 30000))
            alt_selectors = params.get("alt_selectors", [])

            filled = False
            last_err: Exception | None = None

            # Try primary selector
            try:
                page.fill(selector, text, timeout=timeout)
                filled = True
            except Exception as primary_err:
                last_err = primary_err
                _debug(f"type_text: primary selector '{selector}' failed: {primary_err}")

            # Try alternative selectors if primary failed
            if not filled and alt_selectors:
                for alt in alt_selectors:
                    try:
                        _debug(f"type_text: trying alt selector '{alt}'")
                        page.fill(alt, text, timeout=5000)
                        filled = True
                        _debug(f"type_text: alt selector '{alt}' worked")
                        break
                    except Exception:
                        continue

            # Last resort: try first visible text input
            if not filled:
                try:
                    _debug("type_text: trying first visible text input")
                    loc = page.locator("input[type='text']:visible").first
                    loc.fill(text, timeout=5000)
                    filled = True
                    _debug("type_text: first visible text input worked")
                except Exception:
                    pass

            if not filled and last_err:
                raise last_err

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

            # Fallback: try well-known variable names if $ref was empty
            if not value:
                for _fallback_var in ("extracted_key", "api_key", "clipboard_key"):
                    _fv = variables.get(_fallback_var, "")
                    if _fv and len(_fv) >= 10:
                        value = _fv
                        _debug(f"save_env: fallback resolved from ${_fallback_var} ({len(value)} chars)")
                        break

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

            # Skip if key was already extracted in a prior step
            for _var_name in ("extracted_key", "api_key", "clipboard_key"):
                _existing = variables.get(_var_name, "")
                if _existing and len(_existing) >= 10:
                    if key_pattern and (not re.match(key_pattern, str(_existing).strip())):
                        continue
                    _debug(f"prompt_secret: SKIP — key already in ${_var_name} ({len(_existing)} chars)")
                    console.print(f"  [green]✓[/green] Klucz już pobrany (${_var_name}, {len(_existing)} znaków) — pomijam prompt")
                    return _existing

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

            # Interactive mode — prompt with timeout
            timeout_sec = _PROMPT_TIMEOUT
            _debug(f"prompt_secret: TTY available, prompting user (env_var={env_var}, timeout={timeout_sec}s)")

            if timeout_sec > 0:
                console.print(f"  [dim]⏱ Timeout: {timeout_sec}s (ustaw NLP2CMD_PROMPT_TIMEOUT w .env)[/dim]")

            def _getpass_with_timeout(prompt_str: str, timeout: int) -> str | None:
                """Run getpass in a thread with timeout. Returns None on timeout."""
                result_box: list[str | None] = [None]
                error_box: list[Exception | None] = [None]

                def _reader():
                    try:
                        import getpass as _gp
                        result_box[0] = _gp.getpass(prompt_str)
                    except Exception as exc:
                        error_box[0] = exc

                t = threading.Thread(target=_reader, daemon=True)
                t.start()
                t.join(timeout=timeout if timeout > 0 else None)
                if t.is_alive():
                    return None  # timeout
                if error_box[0]:
                    raise error_box[0]
                return result_box[0]

            max_attempts = 3
            for attempt in range(1, max_attempts + 1):
                val = _getpass_with_timeout(prompt, timeout_sec)

                if val is None:
                    # Timeout — skip prompt, fall through to env var or fail gracefully
                    console.print(
                        f"  [yellow]⚠ Timeout ({timeout_sec}s) — użytkownik nie odpowiedział.[/yellow]"
                    )
                    if env_var:
                        env_val = os.environ.get(env_var, "").strip()
                        if env_val:
                            console.print(f"  [dim]ℹ Używam istniejącej wartości {env_var} z os.environ[/dim]")
                            return env_val
                    console.print(f"  [dim]ℹ Pomijam prompt_secret (brak odpowiedzi i brak {env_var} w env)[/dim]")
                    return ""

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
                    _debug(f"check_session: {service} — login page detected")

                    # Try auto-login via password store
                    _auto_logged_in = False
                    try:
                        from nlp2cmd.automation.password_store import get_password_store
                        pw_store = get_password_store()
                        cred = pw_store.get_credentials(service)
                        if cred and cred.username and cred.password:
                            console.print(f"  [dim]🔐 Znaleziono dane logowania ({cred.source}: {cred.username})[/dim]")
                            _debug(f"check_session: auto-login attempt for {service} via {cred.source}")

                            # Fill email/username field
                            _email_selectors = [
                                'input[type="email"]', 'input[name*="email"]',
                                'input[name*="login"]', 'input[name*="user"]',
                                'input[type="text"][autocomplete*="user"]',
                                'input[id*="email"]', 'input[id*="user"]',
                                'input[id*="login"]',
                            ]
                            _filled_user = False
                            for _sel in _email_selectors:
                                try:
                                    _el = page.query_selector(_sel)
                                    if _el and _el.is_visible():
                                        _el.fill(cred.username)
                                        _filled_user = True
                                        _debug(f"check_session: filled username via {_sel}")
                                        break
                                except Exception:
                                    continue

                            # Fill password field
                            _filled_pass = False
                            try:
                                _pw_el = page.query_selector('input[type="password"]')
                                if _pw_el and _pw_el.is_visible():
                                    _pw_el.fill(cred.password)
                                    _filled_pass = True
                                    _debug("check_session: filled password field")
                            except Exception:
                                pass

                            # Submit login form
                            if _filled_user and _filled_pass:
                                _submit_selectors = [
                                    'button[type="submit"]',
                                    'input[type="submit"]',
                                    'button:has-text("Sign in")',
                                    'button:has-text("Log in")',
                                    'button:has-text("Zaloguj")',
                                    'button:has-text("Continue")',
                                ]
                                for _sub_sel in _submit_selectors:
                                    try:
                                        _sub = page.locator(_sub_sel).first
                                        if _sub.is_visible(timeout=2000):
                                            _sub.click(timeout=5000)
                                            page.wait_for_timeout(3000)
                                            _debug(f"check_session: clicked submit via {_sub_sel}")
                                            break
                                    except Exception:
                                        continue

                                # Check if login succeeded
                                page.wait_for_timeout(2000)
                                body_after = page.text_content("body") or ""
                                still_login = any(ind.lower() in body_after.lower() for ind in login_indicators)
                                now_session = any(ind.lower() in body_after.lower() for ind in session_indicators)
                                if now_session and not still_login:
                                    console.print(f"  [green]✓[/green] Auto-login na {service} powiódł się!")
                                    _auto_logged_in = True
                                    # Navigate to keys page
                                    if keys_url:
                                        try:
                                            page.goto(keys_url, wait_until="domcontentloaded", timeout=15000)
                                            page.wait_for_timeout(1000)
                                        except Exception:
                                            pass
                                    return "logged_in"
                                else:
                                    console.print(f"  [yellow]⚠[/yellow] Auto-login nie powiódł się (2FA/captcha?)")
                            elif _filled_user:
                                console.print(f"  [dim]   Wypełniono użytkownika, ale nie znaleziono pola hasła[/dim]")
                        else:
                            backends = pw_store.list_backends()
                            active = [k for k, v in backends.items() if v]
                            console.print(f"  [dim]   Brak danych logowania dla {service} (backends: {', '.join(active)})[/dim]")
                    except ImportError:
                        pass
                    except Exception as _pw_err:
                        _debug(f"check_session: password store error: {_pw_err}")

                    if not _auto_logged_in:
                        console.print(f"  [dim]   Zaloguj się ręcznie w przeglądarce, potem kontynuuj[/dim]")

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

        elif action == "submit_and_extract_key":
            # Composite action: non-blocking JS click on submit + poll for key
            # Solves: blocking click (91s) causes key reveal dialog to close before capture
            submit_selector = params.get("selector", "")
            key_pattern = params.get("key_pattern", "")
            poll_timeout = params.get("timeout", 60000)  # ms
            key_selectors = params.get("selectors", [
                "code", "pre", "input[readonly]", "[data-testid*='key']",
            ])

            console.print(f"  [dim]🔑 Klikam submit i szukam klucza...[/dim]")

            # Click submit (non-blocking — no_wait_after skips navigation wait)
            click_ok = False
            if submit_selector:
                # Try each selector in comma-separated list
                for sel_candidate in submit_selector.split(","):
                    sel_candidate = sel_candidate.strip()
                    if not sel_candidate:
                        continue
                    try:
                        loc = page.locator(sel_candidate).first
                        if loc.is_visible(timeout=2000):
                            loc.click(no_wait_after=True, timeout=5000)
                            _debug(f"submit_and_extract_key: clicked '{sel_candidate}'")
                            click_ok = True
                            break
                    except Exception as e:
                        _debug(f"submit_and_extract_key: selector '{sel_candidate}' failed: {e}")
                        continue

            if not click_ok:
                _debug("submit_and_extract_key: all selectors failed, trying JS fallback")
                try:
                    # JS fallback: find all buttons with "Create" text, click the enabled one
                    page.evaluate("""
                        (() => {
                            const btns = [...document.querySelectorAll('button')];
                            const create = btns.find(b => b.textContent.trim() === 'Create' && !b.disabled);
                            if (create) create.click();
                        })()
                    """)
                    _debug("submit_and_extract_key: JS fallback clicked Create button")
                except Exception as js_err:
                    _debug(f"submit_and_extract_key: JS fallback failed: {js_err}")

            # Poll page body for key pattern
            poll_interval = 500  # ms
            elapsed = 0
            found_key = None
            while elapsed < poll_timeout:
                page.wait_for_timeout(poll_interval)
                elapsed += poll_interval

                # Check DOM selectors first (faster, more precise)
                for sel in key_selectors:
                    try:
                        elements = page.query_selector_all(sel)
                        for el in elements:
                            text = (el.text_content() or "").strip()
                            if text and key_pattern and re.search(key_pattern, text):
                                found_key = re.search(key_pattern, text).group(0)
                                break
                            elif text and not key_pattern and len(text) > 30 and re.match(r'^[a-zA-Z0-9_\-]+$', text):
                                found_key = text
                                break
                    except Exception:
                        continue
                    if found_key:
                        break

                # Fallback: full body regex
                if not found_key and key_pattern:
                    try:
                        body = page.text_content("body") or ""
                        m = re.search(key_pattern, body)
                        if m:
                            found_key = m.group(0)
                    except Exception:
                        pass

                if found_key:
                    console.print(f"  [green]✓[/green] Klucz przechwycony! ({len(found_key)} znaków, {elapsed}ms)")
                    # Copy to clipboard via JS
                    try:
                        page.evaluate(f"navigator.clipboard.writeText({json.dumps(found_key)})")
                    except Exception:
                        pass
                    return found_key

                # Progress indicator every 5s
                if elapsed % 5000 == 0:
                    _debug(f"submit_and_extract_key: polling... {elapsed}ms / {poll_timeout}ms")

            console.print(f"  [yellow]⚠[/yellow] Klucz nie pojawił się w ciągu {poll_timeout/1000:.0f}s")
            return None

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
                    elif key_pattern:
                        console.print(
                            f"  [yellow]⚠[/yellow] Schowek ma {len(clipboard)} znaków, ale NIE pasuje do wzorca"
                        )
                        return None
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

        # Fallback: try new modular dispatcher for any unhandled actions
        # This allows gradual migration from monolithic method to handlers
        try:
            if StepDispatcher.has_handler(action):
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
