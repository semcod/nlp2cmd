"""Step orchestration with validation, fallback, and retry logic."""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from nlp2cmd.pipeline_runner_utils import _debug


@dataclass
class StepResult:
    """Result of executing a single step."""
    step_index: int
    action: str
    status: str  # ok, ok_retry, ok_fallback, fallback_injected, error, failed, failed_validation
    elapsed_ms: int
    stored: str | None = None
    error: str | None = None
    result_value: Any = None
    note: str | None = None


class StepOrchestrator:
    """Orchestrates step execution with validation, fallback, and retry.
    
    This class manages:
    - Pre and post step validation
    - Dynamic fallback injection
    - Retry on failure
    - Feedback loop integration
    """
    
    def __init__(
        self,
        validator: Any | None = None,
        fallback_engine: Any | None = None,
        feedback_loop: Any | None = None,
        service_config: dict = None,
        service_name: str = "",
        max_fallback_injections: int = 3,
        max_plan_steps: int = 30,
    ):
        self.validator = validator
        self.fallback_engine = fallback_engine
        self.feedback_loop = feedback_loop
        self.service_config = service_config or {}
        self.service_name = service_name
        self.max_fallback_injections = max_fallback_injections
        self.max_plan_steps = max_plan_steps
        
        self._fallback_tried: set[str] = set()
        self._fallback_injection_count = 0
        self.results_log: list[StepResult] = []
        self.variables: dict[str, str] = {}
    
    def execute_step(
        self,
        step: Any,
        step_idx: int,
        step_queue: list,
        page: Any,
        context: Any,
        execute_fn: callable,
        resolve_vars_fn: callable,
        console: Any,
    ) -> tuple[bool, bool]:
        """Execute a single step with full orchestration.
        
        Args:
            step: The step to execute
            step_idx: Current step index
            step_queue: Mutable list of steps (for fallback injection)
            page: Playwright page
            context: Browser context
            execute_fn: Function to execute the step (_execute_plan_step)
            resolve_vars_fn: Function to resolve variables
            console: Console for output
            
        Returns:
            Tuple of (success, should_continue)
        """
        step_desc = step.description or step.action
        total_display = len(step_queue)
        
        console.print(
            f"\n[cyan]▸ Krok {step_idx+1}/{total_display}:[/cyan] {step_desc}"
            f"  [dim]({step.action})[/dim]"
        )
        
        # Handle new_tab action
        if step.action == "new_tab":
            return self._handle_new_tab(step, step_idx, page, context, console)
        
        # Pre-validation
        pre_ok, pre_message = self._pre_validate(step, page, resolve_vars_fn, console)
        
        # Check if already available (for prompt_secret)
        if step.action == "prompt_secret":
            should_skip = self._check_already_available(
                step, step_idx, pre_ok, pre_message, resolve_vars_fn, console
            )
            if should_skip:
                return True, True
        
        # Snapshot clipboard for key-related steps
        if self.validator and step.action in ("extract_key", "prompt_secret", "check_clipboard"):
            self.validator.snapshot_clipboard()
        
        # Execute step
        step_start = time.time()
        try:
            result = execute_fn(page, context, step, self.variables)
            elapsed_ms = (time.time() - step_start) * 1000
            
            # Store result
            if step.store_as and result:
                self.variables[step.store_as] = result
            
            # Post-validation and fallback
            step_status, step_error, fb_applied = self._post_validate_and_fallback(
                step, step_idx, step_queue, page, result, pre_ok, pre_message,
                resolve_vars_fn, console
            )
            
            # Print result
            self._print_step_result(step, step_status, elapsed_ms, console)
            
            # Log result
            self.results_log.append(StepResult(
                step_index=step_idx + 1,
                action=step.action,
                status=step_status,
                elapsed_ms=round(elapsed_ms),
                stored=step.store_as,
                error=step_error or None,
                result_value=result,
            ))
            
            return step_status not in ("error", "failed", "failed_validation"), True
            
        except Exception as e:
            elapsed_ms = (time.time() - step_start) * 1000
            return self._handle_step_error(
                step, step_idx, step_queue, page, context, e, elapsed_ms,
                execute_fn, resolve_vars_fn, console
            )
    
    def _handle_new_tab(
        self,
        step: Any,
        step_idx: int,
        page: Any,
        context: Any,
        console: Any,
    ) -> tuple[bool, bool]:
        """Handle new_tab action."""
        page = context.new_page()
        try:
            page.bring_to_front()
        except Exception:
            pass
        console.print("  [green]✓[/green] OK")
        self.results_log.append(StepResult(
            step_index=step_idx + 1,
            action=step.action,
            status="ok",
            elapsed_ms=0,
            stored=step.store_as,
        ))
        return True, True
    
    def _pre_validate(
        self,
        step: Any,
        page: Any,
        resolve_vars_fn: callable,
        console: Any,
    ) -> tuple[bool, str]:
        """Run pre-validation for a step."""
        if not self.validator:
            return True, ""
        
        params_resolved = resolve_vars_fn(step.params or {}, self.variables)
        pre_result = self.validator.validate_pre(
            step.action, page, params_resolved, self.variables
        )
        
        if not pre_result.passed:
            console.print(f"  [yellow]⚠ Pre-check:[/yellow] {pre_result.message}")
            if pre_result.suggestion:
                console.print(f"  [dim]   💡 {pre_result.suggestion}[/dim]")
            return False, str(pre_result.message or "")
        
        return True, ""
    
    def _check_already_available(
        self,
        step: Any,
        step_idx: int,
        pre_ok: bool,
        pre_message: str,
        resolve_vars_fn: callable,
        console: Any,
    ) -> bool:
        """Check if key is already available for prompt_secret."""
        if not self.validator or step.action != "prompt_secret":
            return False
        
        # Re-run validation to get details
        params_resolved = resolve_vars_fn(step.params or {}, self.variables)
        pre_result = self.validator.validate_pre(
            step.action, None, params_resolved, self.variables
        )
        
        details = pre_result.details or {}
        already_extracted = bool(details.get("already_extracted"))
        already_set = bool(details.get("already_set"))
        already_set_invalid = bool(details.get("already_set_invalid"))
        
        if already_extracted or already_set:
            existing_val = ""
            source = ""
            
            if already_extracted:
                var_name = details.get("var", "api_key")
                existing_val = self.variables.get(var_name, "")
                source = f"${var_name}"
            else:
                env_var = str(params_resolved.get("env_var") or "").strip()
                if env_var:
                    existing_val = __import__('os').environ.get(env_var, "")
                    source = f"os.environ[{env_var}]"
            
            if existing_val and not already_set_invalid:
                console.print(
                    f"  [green]✓[/green] Klucz już dostępny "
                    f"({source}, {len(existing_val)} znaków) — pomijam prompt"
                )
                if step.store_as:
                    self.variables[step.store_as] = existing_val
                self.results_log.append(StepResult(
                    step_index=step_idx + 1,
                    action=step.action,
                    status="ok",
                    elapsed_ms=0,
                    stored=step.store_as,
                    note="skipped_already_available",
                ))
                return True
        
        return False
    
    def _post_validate_and_fallback(
        self,
        step: Any,
        step_idx: int,
        step_queue: list,
        page: Any,
        result: Any,
        pre_ok: bool,
        pre_message: str,
        resolve_vars_fn: callable,
        console: Any,
    ) -> tuple[str, str, bool]:
        """Run post-validation and handle fallback if needed."""
        step_status = "ok"
        step_error = pre_message if not pre_ok else ""
        fb_applied = False
        
        if not self.validator:
            return step_status, step_error, fb_applied
        
        params_resolved = resolve_vars_fn(step.params or {}, self.variables)
        post_result = self.validator.validate_post(
            step.action, page, params_resolved, result
        )
        
        if not post_result.passed:
            console.print(f"  [yellow]⚠ Post-check:[/yellow] {post_result.message}")
            if post_result.suggestion:
                console.print(f"  [dim]   💡 {post_result.suggestion}[/dim]")
            step_status = "failed_validation"
            step_error = str(post_result.message or "")
            
            # Trigger fallback on critical steps
            fb_key = f"post:{step.action}"
            if (
                step.action in ("navigate", "check_session", "extract_key")
                and self.fallback_engine
                and fb_key not in self._fallback_tried
            ):
                fb_applied = self._trigger_fallback(
                    step, step_idx, step_queue, page, post_result,
                    params_resolved, console
                )
                if fb_applied:
                    step_status = "ok_fallback"
                    step_error = ""
        
        return step_status, step_error, fb_applied
    
    def _trigger_fallback(
        self,
        step: Any,
        step_idx: int,
        step_queue: list,
        page: Any,
        post_result: Any,
        params_resolved: dict,
        console: Any,
    ) -> bool:
        """Trigger dynamic fallback for a failed step."""
        fb_key = f"post:{step.action}"
        self._fallback_tried.add(fb_key)
        
        console.print(f"  [cyan]🔄 Uruchamiam dynamiczny fallback...[/cyan]")
        
        try:
            fb_url = page.url if page else ""
            fb_title = page.title() if page else ""
        except Exception:
            fb_url = fb_title = ""
        
        try:
            from nlp2cmd.automation.schema_fallback import FallbackContext
            
            fb_ctx = FallbackContext(
                failed_action=step.action,
                failed_params=params_resolved,
                error_message=post_result.message,
                step_index=step_idx,
                total_steps=len(step_queue),
                variables=dict(self.variables),
                page_url=fb_url,
                page_title=fb_title,
                service_name=self.service_name,
                service_config=self.service_config,
                previous_steps_ok=[
                    r.action for r in self.results_log
                    if r.status in ("ok", "ok_retry", "ok_fallback")
                ],
            )
            
            fb_result = self.fallback_engine.generate_fallback(fb_ctx, page)
            
            if fb_result.success:
                console.print(
                    f"  [green]✓ Fallback:[/green] {fb_result.strategy} — {fb_result.message}"
                )
                
                if fb_result.extracted_value:
                    if step.store_as:
                        self.variables[step.store_as] = fb_result.extracted_value
                    self.variables["extracted_key"] = fb_result.extracted_value
                    console.print(
                        f"  [green]✓[/green] Wyekstrahowano klucz "
                        f"({len(fb_result.extracted_value)} znaków)"
                    )
                    return True
                    
                elif fb_result.replacement_steps:
                    return self._inject_fallback_steps(
                        step, step_idx, step_queue, fb_result.replacement_steps, console
                    )
            else:
                console.print(f"  [dim]   Fallback wyczerpany: {fb_result.message}[/dim]")
                
        except Exception as e:
            _debug(f"Fallback trigger failed: {e}")
        
        return False
    
    def _inject_fallback_steps(
        self,
        step: Any,
        step_idx: int,
        step_queue: list,
        replacement_steps: list,
        console: Any,
    ) -> bool:
        """Inject fallback replacement steps into the queue."""
        if (
            self._fallback_injection_count >= self.max_fallback_injections
            or len(step_queue) + len(replacement_steps) > self.max_plan_steps
        ):
            console.print(
                f"  [yellow]⚠ Limit fallbacków osiągnięty "
                f"({self._fallback_injection_count}/{self.max_fallback_injections} "
                f"injekcji, {len(step_queue)} kroków) — pomijam[/yellow]"
            )
            return False
        
        try:
            from nlp2cmd.automation.action_planner import ActionStep
            
            # Sanitize and create new steps
            new_steps = []
            for rs in replacement_steps:
                new_steps.append(ActionStep(
                    action=rs["action"],
                    params=rs.get("params", {}),
                    description=rs.get("description", ""),
                    store_as=rs.get("store_as"),
                ))
            
            step_queue[step_idx+1:step_idx+1] = new_steps
            self._fallback_injection_count += 1
            console.print(
                f"  [dim]   📝 Wstawiono {len(new_steps)} dodatkowych kroków[/dim]"
            )
            return True
            
        except Exception as e:
            _debug(f"Fallback injection failed: {e}")
            return False
    
    def _print_step_result(
        self,
        step: Any,
        step_status: str,
        elapsed_ms: float,
        console: Any,
    ) -> None:
        """Print step execution result."""
        if step.store_as and step_status in ("ok", "ok_retry", "ok_fallback", "fallback_injected"):
            console.print(f"  [green]✓[/green] Zapisano jako ${step.store_as}")
        elif step_status in ("ok", "ok_retry", "ok_fallback", "fallback_injected"):
            console.print(f"  [green]✓[/green] OK")
        else:
            console.print(f"  [red]✗[/red] Krok nie przeszedł walidacji")
        
        console.print(f"  [dim]   ⏱ {elapsed_ms:.0f}ms[/dim]")
    
    def _handle_step_error(
        self,
        step: Any,
        step_idx: int,
        step_queue: list,
        page: Any,
        context: Any,
        error: Exception,
        elapsed_ms: float,
        execute_fn: callable,
        resolve_vars_fn: callable,
        console: Any,
    ) -> tuple[bool, bool]:
        """Handle step execution error with fallback and retry."""
        console.print(f"  [red]✗[/red] Błąd: {error}")
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
        
        # Log error
        self.results_log.append(StepResult(
            step_index=step_idx + 1,
            action=step.action,
            status="error",
            elapsed_ms=round(elapsed_ms),
            error=str(error),
        ))
        
        # Feedback loop diagnosis
        diagnosis_str = ""
        if self.feedback_loop:
            try:
                params_resolved = resolve_vars_fn(step.params or {}, self.variables)
                diagnosis = self.feedback_loop.classify_failure(
                    action=step.action,
                    error=str(error),
                    page=page,
                    params=params_resolved,
                    service_config=self.service_config,
                )
                diagnosis_str = f"{diagnosis.failure_type.value}: {diagnosis.reason}"
                console.print(f"  [dim]   🔍 Diagnoza: {diagnosis_str}[/dim]")
                if diagnosis.suggested_fix:
                    console.print(f"  [dim]   💡 Sugestia: {diagnosis.suggested_fix}[/dim]")
            except Exception:
                pass
        
        # Dynamic fallback on error
        fallback_handled = self._trigger_error_fallback(
            step, step_idx, step_queue, page, error, diagnosis_str,
            resolve_vars_fn, console
        )
        
        # Detect browser-closed
        browser_dead = "browser has been closed" in str(error).lower()
        
        # Retry if not handled by fallback
        if not fallback_handled and step.retry_on_fail and not browser_dead:
            console.print(f"  [yellow]↻[/yellow] Retry...")
            try:
                page.wait_for_timeout(1000)
                result = execute_fn(page, context, step, self.variables)
                if step.store_as and result:
                    self.variables[step.store_as] = result
                console.print(f"  [green]✓[/green] Retry OK")
                self.results_log[-1].status = "ok_retry"
                return True, True
            except Exception as e2:
                console.print(f"  [red]✗[/red] Retry failed: {e2}")
                self.results_log[-1].status = "failed"
                return False, True
        
        if browser_dead:
            console.print("  [red]⛔ Przeglądarka zamknięta — przerywam wykonanie[/red]")
            return False, False
        
        return False, True
    
    def _trigger_error_fallback(
        self,
        step: Any,
        step_idx: int,
        step_queue: list,
        page: Any,
        error: Exception,
        diagnosis_str: str,
        resolve_vars_fn: callable,
        console: Any,
    ) -> bool:
        """Trigger fallback on step error."""
        fb_key = f"err:{step.action}"
        if not self.fallback_engine or fb_key in self._fallback_tried:
            return False
        
        self._fallback_tried.add(fb_key)
        console.print(f"  [cyan]🔄 Uruchamiam dynamiczny fallback...[/cyan]")
        
        params_resolved = resolve_vars_fn(step.params or {}, self.variables)
        
        try:
            fb_url = page.url if page else ""
            fb_title = page.title() if page else ""
        except Exception:
            fb_url = fb_title = ""
        
        try:
            from nlp2cmd.automation.schema_fallback import FallbackContext
            
            error_msg = str(error)
            if diagnosis_str:
                error_msg += f" [{diagnosis_str}]"
            
            fb_ctx = FallbackContext(
                failed_action=step.action,
                failed_params=params_resolved,
                error_message=error_msg,
                step_index=step_idx,
                total_steps=len(step_queue),
                variables=dict(self.variables),
                page_url=fb_url,
                page_title=fb_title,
                service_name=self.service_name,
                service_config=self.service_config,
                previous_steps_ok=[
                    r.action for r in self.results_log
                    if r.status in ("ok", "ok_retry")
                ],
            )
            
            fb_result = self.fallback_engine.generate_fallback(fb_ctx, page)
            
            if fb_result.success:
                console.print(
                    f"  [green]✓ Fallback:[/green] {fb_result.strategy} — {fb_result.message}"
                )
                
                if fb_result.extracted_value:
                    if step.store_as:
                        self.variables[step.store_as] = fb_result.extracted_value
                    self.variables["extracted_key"] = fb_result.extracted_value
                    self.results_log[-1].status = "ok_fallback"
                    return True
                    
                elif fb_result.replacement_steps:
                    injected = self._inject_fallback_steps(
                        step, step_idx, step_queue, fb_result.replacement_steps, console
                    )
                    if injected:
                        self.results_log[-1].status = "fallback_injected"
                        return True
            else:
                console.print(f"  [dim]   Fallback wyczerpany: {fb_result.message}[/dim]")
                
        except Exception as e:
            _debug(f"Error fallback failed: {e}")
        
        return False
    
    def get_summary(self) -> dict[str, Any]:
        """Get execution summary."""
        ok_count = sum(1 for r in self.results_log if r.status in ("ok", "ok_retry", "ok_fallback", "fallback_injected"))
        fail_count = sum(1 for r in self.results_log if r.status == "failed")
        err_count = sum(1 for r in self.results_log if r.status in ("error", "failed_validation"))
        total_ms = sum(r.elapsed_ms for r in self.results_log)
        
        return {
            "ok_count": ok_count,
            "fail_count": fail_count,
            "err_count": err_count,
            "total_ms": total_ms,
            "total_steps": len(self.results_log),
        }
