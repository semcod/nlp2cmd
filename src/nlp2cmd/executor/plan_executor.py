"""PlanExecutor - extracted from __init__.py."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional
from nlp2cmd.registry import ActionRegistry, ActionResult, get_registry
from nlp2cmd.executor.execution_context import ExecutionContext
from nlp2cmd.executor.execution_plan import ExecutionPlan
from nlp2cmd.executor.execution_result import ExecutionResult
from nlp2cmd.executor.plan_step import PlanStep
from nlp2cmd.executor.plan_validator import PlanValidator
from nlp2cmd.executor.step_result import StepResult
from nlp2cmd.executor.step_status import StepStatus

class PlanExecutor:
    """
    Executes multi-step plans.
    
    Features:
    - Sequential and parallel execution
    - Foreach loops with item/index context
    - Variable substitution
    - Conditional execution
    - Retry with backoff
    - Timeout handling
    - Dry-run mode
    """
    
    def __init__(
        self,
        registry: Optional[ActionRegistry] = None,
        action_handlers: Optional[dict[str, Callable]] = None,
    ):
        """
        Initialize executor.
        
        Args:
            registry: Action registry for validation
            action_handlers: Custom action handlers
        """
        self.registry = registry or get_registry()
        self.validator = PlanValidator(self.registry)
        self.action_handlers = action_handlers or {}
        
        # Register default handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self) -> None:
        """Register default action handlers for testing."""
        # These are stub handlers - real implementations would do actual work
        
        def summarize_results(data: Any, format: str = "text") -> str:
            if isinstance(data, list):
                return f"Summary: {len(data)} items"
            return f"Summary: {data}"
        
        def filter_results(data: list, condition: str) -> list:
            # Simple filtering - real implementation would parse condition
            return data
        
        def sort_results(data: list, key: str, reverse: bool = False) -> list:
            if data and isinstance(data[0], dict) and key in data[0]:
                return sorted(data, key=lambda x: x.get(key), reverse=reverse)
            return data
        
        self.action_handlers["summarize_results"] = summarize_results
        self.action_handlers["filter_results"] = filter_results
        self.action_handlers["sort_results"] = sort_results
    
    def execute(
        self,
        plan: ExecutionPlan,
        initial_context: Optional[dict[str, Any]] = None,
        dry_run: bool = False,
        on_step_complete: Optional[Callable[[StepResult], None]] = None,
    ) -> ExecutionResult:
        """
        Execute a plan.
        
        Args:
            plan: Plan to execute
            initial_context: Initial variables
            dry_run: If True, validate but don't execute
            on_step_complete: Callback after each step
            
        Returns:
            ExecutionResult with all step results
        """
        start_time = time.time()
        
        # Validate plan
        is_valid, errors = self.validator.validate(plan)
        if not is_valid:
            return ExecutionResult(
                trace_id="invalid",
                success=False,
                steps=[],
                error=f"Plan validation failed: {'; '.join(errors)}",
            )
        
        # Initialize context
        ctx = ExecutionContext(dry_run=dry_run)
        if initial_context:
            ctx.variables.update(initial_context)
        
        logger.info(f"[{ctx.trace_id}] Starting plan execution ({len(plan.steps)} steps)")
        
        # Execute steps
        for i, step in enumerate(plan.steps):
            ctx.current_step = i
            
            try:
                result = self._execute_step(step, i, ctx)
                ctx.results.append(result)
                
                if on_step_complete:
                    on_step_complete(result)
                
                # Handle step failure
                if result.status == StepStatus.FAILED:
                    if step.on_error == "stop":
                        logger.error(f"[{ctx.trace_id}] Step {i + 1} failed, stopping execution")
                        break
                    elif step.on_error == "skip":
                        logger.warning(f"[{ctx.trace_id}] Step {i + 1} failed, skipping")
                        continue
                    # "continue" - just keep going
                
            except Exception as e:
                logger.exception(f"[{ctx.trace_id}] Step {i + 1} raised exception")
                ctx.results.append(StepResult(
                    step_index=i,
                    action=step.action,
                    status=StepStatus.FAILED,
                    error=str(e),
                ))
                if step.on_error == "stop":
                    break
        
        # Determine overall success
        all_success = all(
            r.status in (StepStatus.SUCCESS, StepStatus.SKIPPED)
            for r in ctx.results
        )
        
        # Get final result (last successful step's result)
        final_result = None
        for result in reversed(ctx.results):
            if result.status == StepStatus.SUCCESS and result.result is not None:
                final_result = result.result
                break
        
        total_duration = (time.time() - start_time) * 1000
        
        return ExecutionResult(
            trace_id=ctx.trace_id,
            success=all_success,
            steps=ctx.results,
            final_result=final_result,
            total_duration_ms=total_duration,
            metadata={"dry_run": dry_run},
        )
    
    def _execute_step(
        self,
        step: PlanStep,
        index: int,
        ctx: ExecutionContext,
    ) -> StepResult:
        """Execute a single step."""
        start_time = time.time()
        
        logger.debug(f"[{ctx.trace_id}] Executing step {index + 1}: {step.action}")
        
        # Check condition
        if step.condition and not self._evaluate_condition(step.condition, ctx):
            logger.debug(f"[{ctx.trace_id}] Step {index + 1} skipped (condition not met)")
            return StepResult(
                step_index=index,
                action=step.action,
                status=StepStatus.SKIPPED,
                metadata={"reason": "condition_not_met"},
            )
        
        # Dry run - just validate
        if ctx.dry_run:
            return StepResult(
                step_index=index,
                action=step.action,
                status=StepStatus.SUCCESS,
                metadata={"dry_run": True},
            )
        
        # Handle foreach
        if step.foreach:
            return self._execute_foreach(step, index, ctx)
        
        # Resolve params
        resolved_params = self._resolve_params(step.params, ctx)
        
        # Execute with retry
        last_error = None
        for attempt in range(step.retry + 1):
            try:
                result = self._call_action(step.action, resolved_params, step.timeout)
                
                # Store result
                if step.store_as:
                    ctx.set(step.store_as, result)
                
                duration = (time.time() - start_time) * 1000
                
                return StepResult(
                    step_index=index,
                    action=step.action,
                    status=StepStatus.SUCCESS,
                    result=result,
                    duration_ms=duration,
                    metadata={"attempt": attempt + 1},
                )
                
            except Exception as e:
                last_error = str(e)
                if attempt < step.retry:
                    logger.warning(
                        f"[{ctx.trace_id}] Step {index + 1} attempt {attempt + 1} failed, retrying"
                    )
                    time.sleep(0.1 * (attempt + 1))  # Simple backoff
        
        duration = (time.time() - start_time) * 1000
        
        return StepResult(
            step_index=index,
            action=step.action,
            status=StepStatus.FAILED,
            error=last_error,
            duration_ms=duration,
            metadata={"attempts": step.retry + 1},
        )
    
    def _execute_foreach(
        self,
        step: PlanStep,
        index: int,
        ctx: ExecutionContext,
    ) -> StepResult:
        """Execute step as foreach loop."""
        start_time = time.time()
        
        # Resolve the iterable
        try:
            iterable = ctx.resolve_reference(f"${step.foreach}")
        except ValueError as e:
            return StepResult(
                step_index=index,
                action=step.action,
                status=StepStatus.FAILED,
                error=str(e),
            )
        
        if not isinstance(iterable, (list, tuple)):
            return StepResult(
                step_index=index,
                action=step.action,
                status=StepStatus.FAILED,
                error=f"foreach target is not iterable: {type(iterable)}",
            )
        
        results = []
        
        for i, item in enumerate(iterable):
            # Set loop context
            ctx.set("item", item)
            ctx.set("index", i)
            
            # Resolve params with loop context
            resolved_params = self._resolve_params(step.params, ctx)
            
            try:
                result = self._call_action(step.action, resolved_params, step.timeout)
                results.append(result)
            except Exception as e:
                logger.warning(f"[{ctx.trace_id}] foreach iteration {i} failed: {e}")
                if step.on_error == "stop":
                    break
        
        # Clean up loop context
        ctx.variables.pop("item", None)
        ctx.variables.pop("index", None)
        
        # Store aggregated results
        if step.store_as:
            ctx.set(step.store_as, results)
        
        duration = (time.time() - start_time) * 1000
        
        return StepResult(
            step_index=index,
            action=step.action,
            status=StepStatus.SUCCESS,
            result=results,
            duration_ms=duration,
            iterations=len(iterable),
        )
    
    def _resolve_params(
        self,
        params: dict[str, Any],
        ctx: ExecutionContext,
    ) -> dict[str, Any]:
        """Resolve variable references in params."""
        resolved = {}
        
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("$"):
                resolved[key] = ctx.resolve_reference(value)
            elif isinstance(value, dict):
                resolved[key] = self._resolve_params(value, ctx)
            elif isinstance(value, list):
                resolved[key] = [
                    ctx.resolve_reference(v) if isinstance(v, str) and v.startswith("$") else v
                    for v in value
                ]
            else:
                resolved[key] = value
        
        return resolved
    
    def _evaluate_condition(self, condition: str, ctx: ExecutionContext) -> bool:
        """Evaluate a condition expression."""
        # Simple condition evaluation
        # Real implementation would use a proper expression parser
        
        # Replace variable references
        expr = condition
        for match in re.finditer(r"\$(\w+(?:\.\w+)*)", condition):
            ref = match.group(0)
            try:
                value = ctx.resolve_reference(ref)
                if isinstance(value, str):
                    expr = expr.replace(ref, f"'{value}'")
                else:
                    expr = expr.replace(ref, str(value))
            except ValueError:
                return False
        
        try:
            # Safe eval for simple conditions
            return eval(expr, {"__builtins__": {}}, {})
        except Exception:
            return False
    
    def _call_action(
        self,
        action: str,
        params: dict[str, Any],
        timeout: Optional[float] = None,
    ) -> Any:
        """Call an action handler."""
        if action in self.action_handlers:
            handler = self.action_handlers[action]
            return handler(**params)
        
        # Check registry for handler
        registry_handler = self.registry.get_handler(action)
        if registry_handler:
            result = registry_handler.execute(params)
            if result.success:
                return result.data
            raise RuntimeError(result.error)
        
        raise NotImplementedError(f"No handler for action: {action}")
    
    def register_handler(
        self,
        action: str,
        handler: Callable[..., Any],
    ) -> None:
        """Register a custom action handler."""
        self.action_handlers[action] = handler

