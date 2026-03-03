"""
Dynamic Orchestration Engine — core module.

Replaces hardcoded template/pattern matching with LLM-driven:
1. Task planning (decompose NL prompt → step schema)
2. Step execution with retry + LLM repair
3. Reflection / result analysis
4. Adaptive re-planning on failure

This is the core version of the examples/_dynamic_orchestrator.py,
integrated into nlp2cmd's package structure.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from nlp2cmd.orchestration.reflection import (
    ResultAnalyzer,
    ReflectionResult,
    ReflectionVerdict,
    has_error_signals,
)
from nlp2cmd.orchestration.metrics import (
    MetricsCollector,
    PathOptimizer,
    FunctionCache,
)

logger = logging.getLogger(__name__)


# ── Data classes ─────────────────────────────────────────────────────

class StepStatus(Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REPAIRED = "repaired"
    SKIPPED = "skipped"


@dataclass
class StepDef:
    """Definition of a single orchestration step."""
    action: str
    description: str = ""
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = {"action": self.action, "description": self.description}
        d.update(self.params)
        return d


@dataclass
class StepResult:
    """Result of executing a single step."""
    status: StepStatus
    data: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class TaskSchema:
    """LLM-generated execution plan — a dynamic schema for the task."""
    goal: str
    domain: str = "general"  # "code_editor", "drawing", "shell", "web", "general"
    steps: list[StepDef] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    """Final result of orchestrated task execution."""
    success: bool
    goal: str
    steps_executed: int = 0
    steps_total: int = 0
    output: Optional[str] = None
    reflection: Optional[ReflectionResult] = None
    context: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: float = 0.0


# ── Orchestrator ─────────────────────────────────────────────────────

class Orchestrator:
    """LLM-driven orchestration engine with reflection.

    Lifecycle:
        1. plan()   — LLM decomposes prompt into TaskSchema
        2. execute() — run steps with retry + repair
        3. reflect() — LLM validates output, decides if retry needed
        4. result   — TaskResult with success/failure + reflection

    Integration points:
        - Receives step handlers via register_handler()
        - Uses LLMRouter for all LLM calls
        - Uses ResultAnalyzer for reflection
        - Can be called from DecisionRouter, PipelineRunner, or CLI
    """

    MAX_RETRIES = 2
    MAX_REPAIR_ATTEMPTS = 2

    def __init__(
        self,
        router=None,
        handlers: Optional[dict[str, Callable]] = None,
        enable_metrics: bool = True,
    ):
        """
        Args:
            router: LLMRouter instance (lazy-loaded if None).
            handlers: Step action handlers {action_name: async_callable}.
            enable_metrics: Enable metrics collection and path optimization.
        """
        self._router = router
        self._analyzer = ResultAnalyzer(router=router)
        self._handlers: dict[str, Callable] = handlers or {}
        self._context: dict[str, Any] = {}

        # Metrics & optimization (persistent in ~/.nlp2cmd/)
        self._metrics_enabled = enable_metrics
        self._metrics: Optional[MetricsCollector] = None
        self._path_optimizer: Optional[PathOptimizer] = None
        self._func_cache: Optional[FunctionCache] = None
        if enable_metrics:
            try:
                self._metrics = MetricsCollector()
                self._path_optimizer = PathOptimizer()
                self._func_cache = FunctionCache()
            except Exception:
                pass

    # ── Router (lazy) ────────────────────────────────────────────────

    @property
    def router(self):
        if self._router is None:
            try:
                from nlp2cmd.llm.router import LLMRouter
                self._router = LLMRouter()
                self._analyzer = ResultAnalyzer(router=self._router)
            except Exception:
                pass
        return self._router

    # ── Handler registration ─────────────────────────────────────────

    def register_handler(self, action: str, handler: Callable) -> None:
        """Register a step handler for an action type."""
        self._handlers[action] = handler

    # ── Main API ─────────────────────────────────────────────────────

    async def run(
        self,
        prompt: str,
        context: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> TaskResult:
        """Execute a task described by natural language prompt.

        This is the primary entry point for the orchestration engine.

        Args:
            prompt: Natural language task description.
            context: Initial context (e.g. page, cwd, url).
            **kwargs: Passed through to step handlers.

        Returns:
            TaskResult with execution outcome + reflection.
        """
        t0 = time.time()
        self._context = dict(context or {})
        self._context["goal"] = prompt

        # Start metrics
        task_id = ""
        if self._metrics:
            task_id = self._metrics.start_task(prompt)

        # Phase 1 — Plan (check cached paths first)
        plan_source = "llm"
        schema = await self._plan_with_cache(prompt)
        if schema.metadata.get("from_cache"):
            plan_source = "cached_path"
        logger.info("Plan: %s (%d steps, source=%s)", schema.goal, len(schema.steps), plan_source)

        # Phase 2 — Execute
        steps_ok = 0
        for i, step_def in enumerate(schema.steps):
            step_t0 = time.time()
            result = await self._execute_with_retry(step_def, i)
            step_ms = (time.time() - step_t0) * 1000

            if result.status in (StepStatus.SUCCESS, StepStatus.REPAIRED):
                self._context.update(result.data)
                steps_ok += 1
                if self._metrics:
                    self._metrics.record_step(
                        action=step_def.action,
                        status=result.status.value,
                        duration_ms=step_ms,
                    )
                # Cache generated code as reusable function
                self._maybe_cache_function(step_def, result)
                continue

            # Try repair
            repaired = await self._repair_step(step_def, result.error or "unknown")
            if repaired and repaired.status in (StepStatus.SUCCESS, StepStatus.REPAIRED):
                self._context.update(repaired.data)
                steps_ok += 1
                if self._metrics:
                    self._metrics.record_step(
                        action=step_def.action,
                        status="repaired",
                        duration_ms=(time.time() - step_t0) * 1000,
                    )
                continue

            # Unrecoverable
            if self._metrics:
                self._metrics.record_step(
                    action=step_def.action, status="failed",
                    duration_ms=step_ms, error=result.error,
                )
                self._metrics.finish_task(
                    success=False, plan_source=plan_source,
                )
            return TaskResult(
                success=False,
                goal=schema.goal,
                steps_executed=steps_ok,
                steps_total=len(schema.steps),
                error=result.error,
                context=self._context,
                duration_ms=(time.time() - t0) * 1000,
            )

        # Phase 3 — Reflect
        output = self._context.get("output", "")
        reflection = await self._analyzer.analyze(
            goal=prompt,
            output=str(output),
            context=self._context,
        )

        # If reflection says error and we can retry, do one re-plan cycle
        if reflection.should_retry and reflection.verdict == ReflectionVerdict.ERROR:
            logger.info("Reflection triggered retry: %s", reflection.reason)
            retry_result = await self._retry_cycle(prompt, schema)
            if retry_result:
                output = self._context.get("output", output)
                reflection = await self._analyzer.analyze(
                    goal=prompt, output=str(output), context=self._context,
                )

        success = reflection.verdict in (
            ReflectionVerdict.VALID,
            ReflectionVerdict.PARTIAL,
            ReflectionVerdict.INCONCLUSIVE,
        )

        # Phase 4 — Persist metrics + learn path
        if self._metrics:
            task_metric = self._metrics.finish_task(
                success=success,
                reflection_verdict=reflection.verdict.value,
                plan_source=plan_source,
            )
            if success and self._path_optimizer:
                self._path_optimizer.record_success(task_metric)

        return TaskResult(
            success=success,
            goal=schema.goal,
            steps_executed=steps_ok,
            steps_total=len(schema.steps),
            output=str(output) if output else None,
            reflection=reflection,
            context=self._context,
            duration_ms=(time.time() - t0) * 1000,
        )

    # ── Phase 1: Planning (with path cache) ──────────────────────────

    async def _plan_with_cache(self, prompt: str) -> TaskSchema:
        """Try cached path first, then LLM planning."""
        if self._path_optimizer:
            cached = self._path_optimizer.lookup(prompt)
            if cached and cached.success_count >= 1:
                logger.info("Using cached path (used %dx)", cached.success_count)
                steps = [
                    StepDef(
                        action=s.get("action", "unknown"),
                        description=s.get("description", ""),
                        params={k: v for k, v in s.items()
                                if k not in ("action", "description", "status",
                                             "duration_ms", "tokens_in", "tokens_out",
                                             "llm_model", "error")},
                    )
                    for s in cached.steps
                ]
                if steps:
                    return TaskSchema(
                        goal=prompt,
                        domain=cached.domain,
                        steps=steps,
                        metadata={"from_cache": True, "cache_hits": cached.success_count},
                    )
        return await self.plan(prompt)

    def _maybe_cache_function(self, step_def: StepDef, result: StepResult) -> None:
        """Cache generated code as a reusable function."""
        if not self._func_cache:
            return
        if step_def.action != "generate_code":
            return
        code = result.data.get("generated_code", "")
        language = result.data.get("language", "py")
        if not code or len(code) < 10:
            return

        lang_key = "js" if language in ("javascript", "js") else "py"
        goal = self._context.get("goal", "")
        from nlp2cmd.orchestration.metrics import _hash_goal
        func_id = self._func_cache.store(
            code=code,
            language=lang_key,
            name=step_def.description[:40] or "generated",
            description=goal[:200],
            goal_hash=_hash_goal(goal),
            tags=[language, step_def.action],
        )
        if self._metrics:
            self._metrics.record_generated_function(func_id)

    async def plan(self, prompt: str) -> TaskSchema:
        """Use LLM to decompose prompt into a TaskSchema."""
        if not self.router:
            return self._heuristic_plan(prompt)

        planning_prompt = (
            "You are a task planner. Decompose the user's request into steps.\n\n"
            f'Request: "{prompt}"\n\n'
            "Available actions: navigate, inspect, generate_code, inject_code, "
            "find_and_click, wait, capture_output, validate, screenshot, "
            "shell_exec, dismiss_popups\n\n"
            "Respond ONLY with JSON (no markdown):\n"
            '{"goal":"...","domain":"code_editor|drawing|shell|web|general",'
            '"steps":[{"action":"...","description":"...",...}]}'
        )

        try:
            resp = await self.router.completion(
                planning_prompt, task="planning",
                max_tokens=1500, temperature=0.3,
            )
            if resp.success:
                data = _parse_json(resp.content)
                steps = [
                    StepDef(
                        action=s.get("action", "unknown"),
                        description=s.get("description", ""),
                        params={k: v for k, v in s.items()
                                if k not in ("action", "description")},
                    )
                    for s in data.get("steps", [])
                ]
                if steps:
                    schema = TaskSchema(
                        goal=data.get("goal", prompt),
                        domain=data.get("domain", "general"),
                        steps=steps,
                        metadata=data,
                    )
                    return self._sanitize_schema(schema)
        except Exception as exc:
            logger.debug("LLM planning failed: %s", exc)

        return self._heuristic_plan(prompt)

    def _heuristic_plan(self, prompt: str) -> TaskSchema:
        """Fallback plan when LLM is unavailable."""
        return TaskSchema(
            goal=prompt,
            domain="general",
            steps=[
                StepDef("inspect", "Analyze current state"),
                StepDef("generate_code", "Generate code based on prompt",
                        {"task_description": prompt}),
            ],
        )

    def _sanitize_schema(self, schema: TaskSchema) -> TaskSchema:
        """Ensure schema has essential steps for its domain."""
        actions = [s.action for s in schema.steps]

        if schema.domain == "code_editor":
            prefix = []
            if "navigate" not in actions:
                lang = schema.metadata.get("language", "python")
                url = f"https://www.mycompiler.io/new/{lang}"
                prefix.append(StepDef("navigate", f"Open compiler", {"url": url}))
            if "inspect" not in actions:
                prefix.append(StepDef("dismiss_popups", "Dismiss popups"))
                prefix.append(StepDef("inspect", "Analyze page"))

            # Remove duplicate navigate/inspect from LLM output
            core = [s for s in schema.steps
                    if s.action not in ("navigate", "dismiss_popups", "inspect")]
            schema.steps = prefix + core

            # Ensure capture + screenshot at end
            updated = [s.action for s in schema.steps]
            if "capture_output" not in updated:
                if "wait" not in updated:
                    schema.steps.append(StepDef("wait", "Wait for execution",
                                                {"seconds": 12}))
                schema.steps.append(StepDef("capture_output", "Capture output"))
            if "screenshot" not in updated:
                schema.steps.append(StepDef("screenshot", "Save screenshot"))

        return schema

    # ── Phase 2: Execution ───────────────────────────────────────────

    async def _execute_with_retry(
        self, step_def: StepDef, index: int,
    ) -> StepResult:
        """Execute a step with retries."""
        handler = self._handlers.get(step_def.action)
        if not handler:
            logger.warning("No handler for action '%s'", step_def.action)
            return StepResult(StepStatus.SKIPPED,
                              error=f"No handler: {step_def.action}")

        last = StepResult(StepStatus.FAILED, error="not executed")
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                last = await handler(step_def, self._context)
                if last.status == StepStatus.SUCCESS:
                    return last
                if attempt < self.MAX_RETRIES:
                    logger.debug("Step %d attempt %d failed: %s",
                                 index, attempt, last.error)
                    await asyncio.sleep(0.5)
            except Exception as exc:
                last = StepResult(StepStatus.FAILED, error=str(exc))
                if attempt < self.MAX_RETRIES:
                    await asyncio.sleep(0.5)
        return last

    async def _repair_step(
        self, step_def: StepDef, error: str,
    ) -> Optional[StepResult]:
        """Ask LLM for repair strategy and retry."""
        if not self.router:
            return None

        for _ in range(self.MAX_REPAIR_ATTEMPTS):
            suggestion = await self._analyzer.suggest_repair(
                goal=self._context.get("goal", ""),
                output=error,
                code=self._context.get("generated_code", ""),
                error_type=None,
            )
            if not suggestion:
                return None

            logger.info("Repair suggestion: %s", suggestion)

            # Re-try the handler with the original step
            handler = self._handlers.get(step_def.action)
            if handler:
                try:
                    result = await handler(step_def, self._context)
                    if result.status == StepStatus.SUCCESS:
                        result.status = StepStatus.REPAIRED
                        return result
                except Exception:
                    pass
        return None

    # ── Phase 3: Retry cycle (re-generate + re-execute) ──────────────

    async def _retry_cycle(
        self, prompt: str, schema: TaskSchema,
    ) -> bool:
        """Re-generate code and re-execute when output has errors."""
        gen_handler = self._handlers.get("generate_code")
        inject_handler = self._handlers.get("inject_code")
        run_handler = self._handlers.get("find_and_click")
        capture_handler = self._handlers.get("capture_output")

        if not (gen_handler and inject_handler):
            return False

        # Re-generate
        error_output = self._context.get("output", "")
        fix_step = StepDef(
            "generate_code",
            "Fix code based on error",
            {
                "task_description": prompt,
                "error_output": str(error_output)[:1000],
                "fix_mode": True,
            },
        )
        result = await gen_handler(fix_step, self._context)
        if result.status != StepStatus.SUCCESS:
            return False
        self._context.update(result.data)

        # Re-inject
        inject_result = await inject_handler(
            StepDef("inject_code", "Re-inject fixed code"), self._context,
        )
        if inject_result.status != StepStatus.SUCCESS:
            return False
        self._context.update(inject_result.data)

        # Re-run
        if run_handler:
            run_result = await run_handler(
                StepDef("find_and_click", "Click Run", {"purpose": "run"}),
                self._context,
            )
            if run_result.status == StepStatus.SUCCESS:
                self._context.update(run_result.data)

        # Wait + re-capture
        await asyncio.sleep(10)
        if capture_handler:
            cap_result = await capture_handler(
                StepDef("capture_output", "Re-capture output"), self._context,
            )
            if cap_result.status == StepStatus.SUCCESS:
                self._context.update(cap_result.data)
                return not has_error_signals(
                    str(self._context.get("output", "")),
                )
        return False


# ── Helpers ──────────────────────────────────────────────────────────

def _parse_json(text: str) -> dict:
    """Robust JSON extraction from LLM output."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip markdown fences
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        try:
            return json.loads("\n".join(lines))
        except json.JSONDecodeError:
            pass

    # Find first { and match
    start = text.find("{")
    if start >= 0:
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(text)):
            c = text[i]
            if esc:
                esc = False
                continue
            if c == "\\":
                esc = True
                continue
            if c == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    break

    raise ValueError(f"Cannot parse JSON from: {text[:200]}")
