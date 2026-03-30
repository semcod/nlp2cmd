"""Main PlanExecutor class for executing ActionPlans."""

from __future__ import annotations
import sys
import time
from pathlib import Path
from typing import Any, Callable, Optional

from rich.console import Console

from nlp2cmd.pipeline_runner_utils import (
    _debug,
    RunnerResult,
    VideoRecorder,
    ask_for_video_recording,
    get_timestamp,
)
from .browser_setup import BrowserSetup
from .step_orchestrator import StepOrchestrator
from nlp2cmd.step_handlers import StepDispatcher


class PlanExecutor:
    """Main executor for ActionPlans with browser automation.
    
    This class orchestrates the full plan execution:
    - Browser setup (Firefox/Chromium with session management)
    - Step-by-step execution with validation, fallback, retry
    - Video recording and screenshot capture
    - Summary generation
    
    This replaces the monolithic execute_action_plan method.
    """
    
    def __init__(
        self,
        headless: bool = True,
        execute_step_fn: Callable[[Any, Any, Any, dict[str, str]], Any] | None = None,
        resolve_variables_fn: Callable[[dict[str, Any], dict[str, str]], dict[str, Any]] | None = None,
        desktop_step_fn: Callable[[Any, dict[str, str]], Any] | None = None,
    ):
        self.headless = headless
        self.browser_setup = BrowserSetup(headless=headless)
        self._execute_step_fn = execute_step_fn
        self._resolve_variables_fn = resolve_variables_fn
        self._desktop_step_fn = desktop_step_fn
        self.console: Any | None = None
        self.video_recorder: VideoRecorder | None = None
        self.video_saved_path: str | None = None
        self.screenshot_path: str | None = None
    
    def execute(
        self,
        plan: Any,
        *,
        dry_run: bool = False,
        video_fmt: Optional[str] = None,
        video_dir: Optional[str] = None,
        confirm: bool = False,
    ) -> RunnerResult:
        """Execute an ActionPlan.
        
        Args:
            plan: ActionPlan instance with steps to execute
            dry_run: If True, only show the plan without executing
            video_fmt: Video format for recording
            video_dir: Directory for video recordings
            confirm: If True, user has confirmed execution
            
        Returns:
            RunnerResult with execution status and data
        """
        from nlp2cmd.automation.action_planner import ActionPlan
        from nlp2cmd.pipeline_runner_utils import _MarkdownConsoleWrapper
        
        console = Console()
        console_wrapper = _MarkdownConsoleWrapper(console, enable_markdown=True)
        self.console = console
        
        # Detect desktop steps
        has_desktop_steps = self._detect_desktop_steps(plan)
        
        # Display plan
        self._display_plan(plan, console)
        
        if dry_run:
            return RunnerResult(
                success=True,
                kind="action_plan",
                data={"dry_run": True, "steps": [s.to_dict() for s in plan.steps]},
            )
        
        # Setup video recording
        should_record_video, effective_video_dir = self._setup_video_recording(
            video_fmt, video_dir, confirm, console
        )
        
        # Handle desktop-only mode
        if has_desktop_steps:
            return self._execute_desktop_mode(
                plan, console_wrapper, should_record_video, effective_video_dir
            )
        
        # Browser automation mode
        return self._execute_browser_mode(
            plan, console_wrapper, should_record_video, effective_video_dir
        )

    @staticmethod
    def _resolve_plan_variables(params: dict[str, Any], variables: dict[str, str]) -> dict[str, Any]:
        """Replace $variable references with values from prior steps."""
        resolved = {}
        for k, v in params.items():
            if isinstance(v, str) and v.startswith("$"):
                resolved[k] = variables.get(v[1:], v)
            else:
                resolved[k] = v
        return resolved

    def _execute_step_with_dispatch(
        self,
        page: Any,
        context: Any,
        step: Any,
        variables: dict[str, str],
    ) -> Optional[str]:
        """Execute a step using the modular dispatcher when no callback was injected."""
        action = str(getattr(step, "action", "") or "")
        params = self._resolve_plan_variables(getattr(step, "params", {}) or {}, variables)

        if not StepDispatcher.has_handler(action):
            return None

        console = Console()
        return StepDispatcher.dispatch(
            action=action,
            page=page,
            context=context,
            params=params,
            variables=variables,
            console=console,
        )
    
    def _detect_desktop_steps(self, plan: Any) -> bool:
        """Detect if plan contains desktop-only steps."""
        _DESKTOP_ACTIONS = frozenset({"open_firefox_tab", "desktop_wait"})
        try:
            steps_iter = getattr(plan, "steps", None) or []
            return any(
                str(getattr(s, "action", "")).startswith("desktop_")
                or str(getattr(s, "action", "")) in _DESKTOP_ACTIONS
                for s in steps_iter
            )
        except Exception:
            return False
    
    def _display_plan(self, plan: Any, console: Console) -> None:
        """Display plan information."""
        console.print(f"\n[bold]🎯 Plan wykonania ({len(plan.steps)} kroków):[/bold]")
        console.print(
            f"  [dim]Źródło: {getattr(plan, 'source', '?')} | "
            f"Pewność: {getattr(plan, 'confidence', 0):.0%} | "
            f"Est. czas: {getattr(plan, 'estimated_time_ms', 0)/1000:.1f}s[/dim]"
        )
        for i, step in enumerate(plan.steps, 1):
            action_tag = f"[cyan]{step.action}[/cyan]" if hasattr(step, 'action') else ""
            console.print(f"  {i}. {step.description or step.action} {action_tag}")
    
    def _setup_video_recording(
        self,
        video_fmt: str | None,
        video_dir: str | None,
        confirm: bool,
        console: Console,
    ) -> tuple[bool, str]:
        """Setup video recording if enabled."""
        effective_video_dir = video_dir or "./recordings"
        
        if video_fmt:
            should_record_video = True
            _debug(f"Video recording enabled for ActionPlan via --video {video_fmt}")
        else:
            try:
                is_tty = bool(getattr(sys.stdin, "isatty", lambda: False)())
            except Exception:
                is_tty = False
            should_record_video = confirm and is_tty and ask_for_video_recording(console)[0]
            if should_record_video:
                effective_video_dir = ask_for_video_recording(console)[1]
        
        if should_record_video:
            self.video_recorder = VideoRecorder(output_dir=effective_video_dir)
            video_path = self.video_recorder.start_recording(name_prefix="action_plan_automation")
            if video_path:
                console.print(f"[dim]🎥 Nagrywanie wideo: {video_path}[/dim]")
        
        return should_record_video, effective_video_dir
    
    def _execute_desktop_mode(
        self,
        plan: Any,
        console_wrapper: Any,
        should_record_video: bool,
        video_dir: str,
    ) -> RunnerResult:
        """Execute plan in desktop-only mode (no browser)."""
        variables: dict[str, str] = {}
        results_log: list[dict] = []
        
        # Store key pattern in variables
        try:
            from nlp2cmd.automation.action_planner import KNOWN_SERVICES
            for svc_name, svc in KNOWN_SERVICES.items():
                if svc_name in (getattr(plan, "query", "") or "").lower():
                    variables["_key_pattern"] = svc.get("key_pattern", "")
                    break
        except Exception:
            pass
        
        _CRITICAL_ACTIONS = frozenset({"prompt_secret", "save_env"})
        plan_aborted = False
        
        try:
            for i, step in enumerate(plan.steps):
                step_desc = step.description or step.action
                step_start = time.time()
                console_wrapper.print(
                    f"\n[cyan]▸ Krok {i+1}/{len(plan.steps)}:[/cyan] {step_desc}"
                    f"  [dim]({step.action})[/dim]"
                )
                
                if step.params:
                    safe_params = {
                        k: ("***" if "secret" in k or "password" in k or "key" in k.lower() else v)
                        for k, v in step.params.items()
                    }
                    _debug(f"  params: {safe_params}")
                
                try:
                    # Execute desktop step
                    result = self._execute_desktop_step(step, variables)
                    elapsed_ms = (time.time() - step_start) * 1000
                    
                    if step.store_as and result:
                        variables[step.store_as] = result
                        console_wrapper.print(f"  [green]✓[/green] Zapisano jako ${step.store_as}")
                    else:
                        console_wrapper.print(f"  [green]✓[/green] OK")
                    
                    console_wrapper.print(f"  [dim]   ⏱ {elapsed_ms:.0f}ms[/dim]")
                    
                    results_log.append({
                        "step": i + 1,
                        "action": step.action,
                        "status": "ok",
                        "stored": step.store_as,
                        "elapsed_ms": round(elapsed_ms),
                    })
                    
                except Exception as e:
                    elapsed_ms = (time.time() - step_start) * 1000
                    console_wrapper.print(f"  [red]✗[/red] Błąd: {e}")
                    console_wrapper.print(f"  [dim]   ⏱ {elapsed_ms:.0f}ms[/dim]")
                    
                    results_log.append({
                        "step": i + 1,
                        "action": step.action,
                        "status": "error",
                        "error": str(e),
                        "elapsed_ms": round(elapsed_ms),
                    })
                    
                    if step.retry_on_fail:
                        console_wrapper.print("  [yellow]↻[/yellow] Retry...")
                        time.sleep(1)
                        try:
                            result = self._execute_desktop_step(step, variables)
                            if step.store_as and result:
                                variables[step.store_as] = result
                            console_wrapper.print("  [green]✓[/green] Retry OK")
                            results_log[-1]["status"] = "ok_retry"
                        except Exception as e2:
                            console_wrapper.print(f"  [red]✗[/red] Retry failed: {e2}")
                            results_log[-1]["status"] = "failed"
                    
                    # Abort on critical failures
                    if step.action in _CRITICAL_ACTIONS and results_log[-1]["status"] == "failed":
                        console_wrapper.print(
                            f"\n  [bold red]⛔ PRZERWANIE PLANU[/bold red]: "
                            f"Krytyczny krok '{step.action}' nie powiódł się.\n"
                            f"  [dim]Nie ma sensu kontynuować — napraw problem i uruchom ponownie.[/dim]"
                        )
                        plan_aborted = True
                        break
                
                # Status assessment
                self._assess_step_status(step, variables, console_wrapper)
            
            # Video recording note
            if self.video_recorder and self.video_recorder.is_recording:
                self.video_recorder.stop_recording(None)
                console_wrapper.print(
                    "[dim]⚠️ Uwaga: Nagrywanie wideo jest niedostępne w trybie 'desktop' "
                    "(wymaga pełnego silnika Playwright).[/dim]"
                )
            
            # Final summary
            ok_count = sum(1 for r in results_log if r["status"] in ("ok", "ok_retry"))
            fail_count = sum(1 for r in results_log if r["status"] == "failed")
            err_count = sum(1 for r in results_log if r["status"] == "error")
            total_ms = sum(r.get("elapsed_ms", 0) for r in results_log)
            
            console_wrapper.print(f"\n[bold]📊 Podsumowanie planu:[/bold]")
            console_wrapper.print(
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
    
    def _execute_desktop_step(self, step: Any, variables: dict[str, str]) -> str | None:
        """Execute a single desktop step."""
        if self._desktop_step_fn is not None:
            return self._desktop_step_fn(step, variables)
        raise NotImplementedError("Desktop step execution requires an injected desktop_step_fn")
    
    def _assess_step_status(self, step: Any, variables: dict[str, str], console: Any) -> None:
        """Assess status after step execution."""
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
    
    def _execute_browser_mode(
        self,
        plan: Any,
        console_wrapper: Any,
        should_record_video: bool,
        video_dir: str,
    ) -> RunnerResult:
        """Execute plan using browser automation."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as e:
            return RunnerResult(
                success=False,
                kind="action_plan",
                error=f"Playwright not available: {e}",
            )
        
        # Setup Firefox sessions
        self.browser_setup.setup_firefox_sessions(console_wrapper)
        
        with sync_playwright() as pw:
            ctx_opts = self.browser_setup.create_context_options(
                video_dir=video_dir if should_record_video else None,
                record_video=should_record_video,
            )
            
            # Launch browser
            context = self.browser_setup.launch_context(pw, ctx_opts, console_wrapper)
            page = context.pages[0] if context.pages else context.new_page()
            
            # Inject cookies
            self.browser_setup.inject_cookies(context, console_wrapper)
            
            # Initialize orchestrator
            orchestrator = self._create_orchestrator(plan)
            
            # Build step queue
            step_queue = list(plan.steps)
            step_idx = 0
            
            while step_idx < len(step_queue):
                step = step_queue[step_idx]
                success, should_continue = orchestrator.execute_step(
                    step=step,
                    step_idx=step_idx,
                    step_queue=step_queue,
                    page=page,
                    context=context,
                    execute_fn=self._get_execute_fn(),
                    resolve_vars_fn=self._get_resolve_fn(),
                    console=console_wrapper,
                )
                
                if not should_continue:
                    break
                
                step_idx += 1
            
            # Validation summary
            if orchestrator.validator:
                summary = orchestrator.validator.summary()
                if summary.get("failed", 0) > 0:
                    console_wrapper.print(
                        f"\n[bold yellow]⚠ Walidacja:[/bold yellow] "
                        f"{summary['failed']} kroków nie przeszło walidacji"
                    )
            
            # Final summary
            self._print_final_summary(orchestrator, plan.steps, console_wrapper)
            
            # Cleanup
            self._cleanup(context, page, video_dir, console_wrapper)
            
            # Build result
            result_data = {
                "steps": [self._step_result_to_dict(r) for r in orchestrator.results_log],
                "variables": orchestrator.variables,
                "mode": "playwright",
            }
            if self.video_saved_path:
                result_data["video"] = self.video_saved_path
            if self.screenshot_path:
                result_data["screenshot"] = self.screenshot_path
            
            return RunnerResult(
                success=all(r.status not in ("failed", "error", "failed_validation") for r in orchestrator.results_log),
                kind="action_plan",
                data=result_data,
            )
    
    def _create_orchestrator(self, plan: Any) -> StepOrchestrator:
        """Create step orchestrator with all dependencies."""
        # Try to import optional components
        validator = None
        fallback_engine = None
        feedback_loop = None
        
        try:
            from nlp2cmd.automation.step_validator import StepValidator
            validator = StepValidator()
        except ImportError:
            pass
        
        try:
            from nlp2cmd.automation.schema_fallback import SchemaFallback
            fallback_engine = SchemaFallback()
        except ImportError:
            pass
        
        try:
            from nlp2cmd.automation.feedback_loop import FeedbackLoop
            feedback_loop = FeedbackLoop()
        except ImportError:
            pass
        
        # Resolve service config
        service_config: dict = {}
        service_name: str = ""
        try:
            from nlp2cmd.automation.action_planner import KNOWN_SERVICES
            for sn, sc in KNOWN_SERVICES.items():
                if sn in (getattr(plan, "query", "") or "").lower():
                    service_config = sc
                    service_name = sn
                    break
        except Exception:
            pass
        
        max_fallback = int(__import__('os').environ.get("NLP2CMD_MAX_FALLBACK_INJECTIONS", "3"))
        max_steps = int(__import__('os').environ.get("NLP2CMD_MAX_PLAN_STEPS", "30"))
        
        return StepOrchestrator(
            validator=validator,
            fallback_engine=fallback_engine,
            feedback_loop=feedback_loop,
            service_config=service_config,
            service_name=service_name,
            max_fallback_injections=max_fallback,
            max_plan_steps=max_steps,
        )
    
    def _get_execute_fn(self) -> callable:
        """Get the step execution function."""
        return self._execute_step_fn or self._execute_step_with_dispatch
    
    def _get_resolve_fn(self) -> callable:
        """Get the variable resolution function."""
        return self._resolve_variables_fn or self._resolve_plan_variables
    
    def _print_final_summary(self, orchestrator: StepOrchestrator, plan_steps: list, console: Any) -> None:
        """Print final execution summary."""
        summary = orchestrator.get_summary()
        
        console.print(f"\n[bold]📊 Podsumowanie planu:[/bold]")
        console.print(
            f"  Kroki: {summary['ok_count']}✓ {summary['err_count']}⚠ {summary['fail_count']}✗ "
            f"z {len(plan_steps)} | Czas: {summary['total_ms']/1000:.1f}s"
        )
    
    def _cleanup(self, context: Any, page: Any, video_dir: str, console: Any) -> None:
        """Cleanup resources including video and screenshots."""
        # Capture final screenshot
        try:
            if not page.is_closed():
                timestamp = get_timestamp()
                self.screenshot_path = str(Path(video_dir) / f"action_plan_final_{timestamp}.png")
                page.screenshot(path=self.screenshot_path)
                console.print(f"[dim]📸 Zrzut ekranu zapisany: {self.screenshot_path}[/dim]")
        except Exception as e:
            _debug(f"Failed to capture final screenshot: {e}")
        
        # Close context
        try:
            context.close()
        except Exception:
            pass
        
        # Save video
        if self.video_recorder and self.video_recorder.is_recording:
            try:
                pw_video = page.video
                if pw_video:
                    target = self.video_recorder.video_path or str(Path(video_dir) / "action_plan_automation.webm")
                    try:
                        pw_video.save_as(target)
                        self.video_saved_path = target
                    except Exception:
                        try:
                            self.video_saved_path = pw_video.path()
                        except Exception:
                            self.video_saved_path = None
                    if self.video_saved_path:
                        console.print(f"[green]🎥 Video saved: {self.video_saved_path}[/green]")
            except Exception as ve:
                _debug(f"Video save_as failed: {ve}")
            self.video_recorder.stop_recording(console, saved_path=self.video_saved_path)
    
    def _step_result_to_dict(self, result: Any) -> dict:
        """Convert StepResult to dict."""
        return {
            "step": result.step_index,
            "action": result.action,
            "status": result.status,
            "elapsed_ms": result.elapsed_ms,
            "stored": result.stored,
            **({"error": result.error} if result.error else {}),
        }
