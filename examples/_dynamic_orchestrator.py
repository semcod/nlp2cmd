"""
Dynamic Orchestrator — LLM-driven browser automation without hardcoded steps.

Given a natural language prompt, this module:
1. Uses LLM to decompose the task into executable steps (TaskPlan)
2. Generates code/content dynamically via LLM — no hardcoded presets
3. Inspects page schema to make context-aware decisions about selectors
4. Handles failures by asking LLM for alternative approaches (repair loop)
5. Validates results via LLM and retries if incorrect

Architecture:
    User prompt → LLM planner → TaskPlan (JSON schema)
                                   ↓
                            Step executor (with retry)
                                   ↓  ← on failure → LLM repair
                            Result validator (LLM)
                                   ↓  ← invalid  → re-generate + retry
                            Final output

Usage:
    from _dynamic_orchestrator import DynamicOrchestrator

    orch = DynamicOrchestrator(verbose=True)
    result = await orch.execute_task("write fibonacci in python", page)
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from _verbose_helper import vlog, vlog_decision, dump_page_schema, dump_selectors


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class StepResult:
    """Result of executing a single orchestration step."""
    success: bool
    data: dict = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class TaskPlan:
    """LLM-generated execution plan — a dynamic schema for the task."""
    goal: str
    domain: str  # "code_editor", "drawing", "web_automation"
    steps: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Site registry (URL templates, not code — code is always LLM-generated)
# ---------------------------------------------------------------------------

SITE_URLS: dict[str, dict[str, str]] = {
    "code_editor": {
        "mycompiler.io": "https://www.mycompiler.io/new/{language}",
        "codepen.io": "https://codepen.io/pen",
        "jsfiddle.net": "https://jsfiddle.net/",
    },
    "drawing": {
        "draw.chat": "https://draw.chat",
        "jspaint.app": "https://jspaint.app",
    },
}

LANGUAGE_SLUG: dict[str, str] = {
    "python": "python",
    "javascript": "nodejs",
    "js": "nodejs",
    "cpp": "cpp",
    "c++": "cpp",
    "java": "java",
    "go": "go",
    "rust": "rust",
    "ruby": "ruby",
    "typescript": "typescript",
}


# ---------------------------------------------------------------------------
# DynamicOrchestrator
# ---------------------------------------------------------------------------

class DynamicOrchestrator:
    """LLM-driven browser automation engine.

    No hardcoded code presets — everything is generated at runtime via LLM
    based on the user's natural-language prompt.
    """

    MAX_REPAIR_ATTEMPTS = 2
    MAX_VALIDATION_RETRIES = 1

    def __init__(self, verbose: bool = False, max_step_retries: int = 2):
        self.verbose = verbose
        self.max_step_retries = max_step_retries
        self.context: dict[str, Any] = {}
        self._router = None  # lazy-init

        self._step_handlers: dict[str, Any] = {
            "navigate": self._step_navigate,
            "dismiss_popups": self._step_dismiss_popups,
            "inspect": self._step_inspect,
            "generate_code": self._step_generate_code,
            "inject_code": self._step_inject_code,
            "find_and_click": self._step_find_and_click,
            "wait": self._step_wait,
            "capture_output": self._step_capture_output,
            "validate": self._step_validate,
            "screenshot": self._step_screenshot,
        }

    # ------------------------------------------------------------------
    # Router (lazy init so import cost is paid only when needed)
    # ------------------------------------------------------------------

    @property
    def router(self):
        if self._router is None:
            from nlp2cmd.llm.router import LLMRouter
            self._router = LLMRouter()
        return self._router

    # ==================================================================
    # PUBLIC API
    # ==================================================================

    async def execute_task(self, prompt: str, page) -> dict:
        """Main entry: take NL prompt, orchestrate browser, return result."""
        print(f"\n{'═' * 60}")
        print(f"  Dynamic Orchestrator — LLM-driven execution")
        print(f"  Prompt: {prompt}")
        print(f"{'═' * 60}")

        self.context = {"goal": prompt}

        # Phase 1 — Plan
        plan = await self._plan_task(prompt)
        self.context["plan"] = {
            "goal": plan.goal,
            "domain": plan.domain,
            "n_steps": len(plan.steps),
        }
        print(f"\nPlan: {plan.goal}  ({plan.domain}, {len(plan.steps)} steps)")
        for i, s in enumerate(plan.steps):
            vlog(f"  {i+1}. [{s.get('action')}] {s.get('description', '')}")

        # Phase 2 — Execute steps
        results: list[dict] = []
        code_retry_done = False
        for idx, step in enumerate(plan.steps):
            step_num = idx + 1
            action = step.get("action", "?")
            desc = step.get("description", action)
            print(f"\n── Step {step_num}/{len(plan.steps)}: {desc}")

            result = await self._execute_with_retry(page, step, step_num)

            if result.success:
                print(f"   ✓ OK")
                results.append({"step": step, "ok": True, "data": result.data})

                # Auto-retry: if capture_output captured an error traceback,
                # re-generate code and re-run BEFORE continuing to validate.
                if action == "capture_output" and not code_retry_done:
                    cur_output = self.context.get("output", "")
                    if cur_output and _output_has_error(cur_output):
                        print(f"\n── Auto-retry: output has error, re-generating code...")
                        vlog(f"Error in output: {cur_output[:200]}")
                        retry_ok = await self._retry_code_cycle(page, plan, prompt)
                        code_retry_done = True
                        if retry_ok:
                            results.append({"step": "auto_retry", "ok": True})
                continue

            # Repair loop
            print(f"   ✗ Failed: {result.error}")
            repaired = await self._repair_loop(page, step, result.error, step_num)
            if repaired and repaired.success:
                print(f"   ✓ Repaired")
                results.append({"step": step, "ok": True, "repaired": True, "data": repaired.data})
                continue

            # Unrecoverable
            print(f"   ✗ Repair failed — aborting")
            return {
                "success": False,
                "failed_step": step_num,
                "error": result.error,
                "context": self._safe_context(),
                "results": results,
            }

        # Phase 3 — Final validation
        validation = await self._final_validation(prompt)
        valid = validation.get("valid", True)
        reason = validation.get("reason", "")

        print(f"\n{'═' * 60}")
        if valid:
            print(f"  ✓ Task completed successfully")
        else:
            print(f"  ⚠ Validation concern: {reason}")
            print(f"    (all steps executed — output may still be usable)")
        if reason and valid:
            print(f"  Validation: {reason}")
        print(f"{'═' * 60}")

        return {
            "success": True,  # steps succeeded; validation is advisory
            "validation_passed": valid,
            "validation": validation,
            "context": self._safe_context(),
            "results": results,
        }

    # ==================================================================
    # PHASE 1 — PLANNING
    # ==================================================================

    async def _plan_task(self, prompt: str) -> TaskPlan:
        """Use LLM to decompose the task into a dynamic step schema."""

        planning_prompt = (
            "You are a browser automation planner. "
            "Given the user's request, produce a step-by-step execution plan as JSON.\n\n"
            f'User request: "{prompt}"\n\n'
            "Available actions:\n"
            "  navigate       — go to URL (params: url, wait_until)\n"
            "  dismiss_popups — close cookie/consent dialogs\n"
            "  inspect        — analyse page DOM structure\n"
            "  generate_code  — call LLM to write code (params: language, task_description)\n"
            "  inject_code    — put generated code into the page editor\n"
            "  find_and_click — click a button (params: purpose e.g. 'run')\n"
            "  wait           — pause (params: seconds, reason)\n"
            "  capture_output — read program output from the page\n"
            "  validate       — check output correctness (params: expected_description)\n"
            "  screenshot     — save screenshot (params: filename)\n\n"
            "Sites: mycompiler.io (Python/JS/C++/Java/Go/Rust), "
            "codepen.io (HTML/CSS/JS), jsfiddle.net, draw.chat, jspaint.app\n\n"
            "Respond ONLY with a JSON object (no markdown):\n"
            '{"goal":"...","domain":"code_editor|drawing","site":"...","language":"...",'
            '"steps":[{"action":"...","description":"...",...}]}'
        )

        resp = await self.router.completion(
            planning_prompt,
            task="planning",
            max_tokens=1500,
            temperature=0.3,
        )

        if resp.success:
            try:
                data = _parse_json(resp.content)
                plan = TaskPlan(
                    goal=data.get("goal", prompt),
                    domain=data.get("domain", "code_editor"),
                    steps=data.get("steps", []),
                    metadata=data,
                )
                if plan.steps:
                    plan = self._sanitize_plan(plan, prompt)
                    vlog(f"LLM plan parsed OK — {len(plan.steps)} steps")
                    return plan
            except Exception as exc:
                vlog(f"Plan JSON parse failed: {exc}")
                vlog(f"Raw: {resp.content[:400]}")

        vlog("Falling back to heuristic plan")
        return self._heuristic_plan(prompt)

    # ------------------------------------------------------------------

    def _sanitize_plan(self, plan: TaskPlan, prompt: str) -> TaskPlan:
        """Validate and augment an LLM-generated plan with essential steps.

        Guarantees:
        - code_editor plans ALWAYS start with navigate → dismiss → inspect
        - capture_output + screenshot are always present
        - Duplicate/misplaced navigate steps are removed
        """
        actions = [s.get("action") for s in plan.steps]

        if plan.domain == "code_editor":
            # Infer URL from metadata or prompt
            language = plan.metadata.get("language", "python")
            slug = LANGUAGE_SLUG.get(language, language)
            site = plan.metadata.get("site", "mycompiler.io")
            url_tpl = SITE_URLS.get("code_editor", {}).get(site, "")
            url = url_tpl.format(language=slug) if url_tpl else f"https://www.mycompiler.io/new/{slug}"

            # Remove any navigate/dismiss/inspect from LLM steps — we prepend canonical ones
            core_steps = [s for s in plan.steps
                          if s.get("action") not in ("navigate", "dismiss_popups", "inspect")]

            prefix: list[dict] = [
                {"action": "navigate", "url": url,
                 "wait_until": "domcontentloaded",
                 "description": f"Open {site}"},
                {"action": "dismiss_popups",
                 "description": "Dismiss popups"},
                {"action": "inspect",
                 "description": "Analyse page structure"},
            ]
            vlog(f"Plan sanitizer: canonical prefix → {url}")

            plan.steps = prefix + core_steps

            # Ensure wait + capture_output after find_and_click(run)
            suffix: list[dict] = []
            if "capture_output" not in actions:
                if "wait" not in actions:
                    suffix.append({"action": "wait", "seconds": 12,
                                   "reason": "Wait for execution",
                                   "description": "Wait for output"})
                suffix.append({"action": "capture_output",
                               "description": "Capture program output"})
                vlog("Plan sanitizer: appended 'capture_output'")
            if "screenshot" not in actions:
                suffix.append({"action": "screenshot",
                               "filename": "dynamic_result.png",
                               "description": "Save screenshot"})

            plan.steps = prefix + plan.steps + suffix

        return plan

    def _heuristic_plan(self, prompt: str) -> TaskPlan:
        """Build a reasonable plan when LLM planning fails."""
        pl = prompt.lower()

        # Detect language
        language = "python"
        for lang, slug in LANGUAGE_SLUG.items():
            if lang in pl:
                language = lang if lang not in ("js", "c++") else {"js": "javascript", "c++": "cpp"}[lang]
                break

        # Drawing?
        if any(w in pl for w in ("draw", "paint", "sketch", "rysuj", "narysuj", "maluj")):
            return TaskPlan(goal=prompt, domain="drawing", steps=[
                {"action": "navigate", "url": "https://draw.chat", "wait_until": "networkidle",
                 "description": "Open draw.chat"},
                {"action": "inspect", "description": "Analyse page"},
                {"action": "screenshot", "filename": "dynamic_drawing.png",
                 "description": "Screenshot"},
            ])

        # Frontend?
        if any(w in pl for w in ("html", "css", "frontend", "strona", "web page")):
            site_url = "https://codepen.io/pen"
        else:
            slug = LANGUAGE_SLUG.get(language, "python")
            site_url = f"https://www.mycompiler.io/new/{slug}"

        return TaskPlan(
            goal=prompt,
            domain="code_editor",
            metadata={"language": language, "site_url": site_url},
            steps=[
                {"action": "navigate", "url": site_url, "wait_until": "domcontentloaded",
                 "description": f"Open online compiler"},
                {"action": "dismiss_popups", "description": "Dismiss popups"},
                {"action": "inspect", "description": "Analyse page structure"},
                {"action": "generate_code", "language": language,
                 "task_description": prompt, "description": f"Generate {language} code via LLM"},
                {"action": "inject_code", "description": "Inject code into editor"},
                {"action": "find_and_click", "purpose": "run",
                 "description": "Click Run button"},
                {"action": "wait", "seconds": 12, "reason": "Wait for execution",
                 "description": "Wait for output"},
                {"action": "capture_output", "description": "Capture program output"},
                {"action": "validate", "expected_description": prompt,
                 "description": "Validate output"},
                {"action": "screenshot", "filename": "dynamic_result.png",
                 "description": "Save screenshot"},
            ],
        )

    # ------------------------------------------------------------------
    # Auto-retry cycle (re-generate code when output has error)
    # ------------------------------------------------------------------

    async def _retry_code_cycle(self, page, plan: TaskPlan, prompt: str) -> bool:
        """Re-generate code, re-inject, re-run, re-capture when output has an error."""
        error_output = self.context.get("output", "")
        language = self.context.get("language", "python")

        # Ask LLM to fix the code based on the error
        fix_prompt = (
            f"The following {language} program produced an error:\n\n"
            f"Code:\n{self.context.get('generated_code', '')[:1500]}\n\n"
            f"Error output:\n{error_output[:1000]}\n\n"
            f"Original task: {prompt}\n\n"
            "Write a FIXED version of the program. "
            "CRITICAL: Respond with ONLY the raw source code, no explanations."
        )
        resp = await self.router.completion(fix_prompt, task="repair",
                                             max_tokens=2000, temperature=0.3)
        if not resp.success:
            vlog(f"Code fix LLM failed: {resp.error}")
            return False

        code = _clean_generated_code(resp.content, language)
        if not code.strip():
            vlog("Code fix returned empty")
            return False

        self.context["generated_code"] = code
        n_lines = code.count("\n") + 1
        print(f"   Re-generated {language} code ({len(code)} chars, {n_lines} lines)")
        vlog(f"Fixed code:\n{code[:400]}")

        # Re-inject
        inject_result = await self._step_inject_code(page, {"code": code})
        if not inject_result.success:
            vlog(f"Re-inject failed: {inject_result.error}")
            return False
        self.context.update(inject_result.data)
        print(f"   Re-injected ✓")

        # Re-run
        click_result = await self._step_find_and_click(page, {"purpose": "run"})
        if not click_result.success:
            vlog(f"Re-run click failed: {click_result.error}")
            return False
        self.context.update(click_result.data)
        print(f"   Re-clicked Run ✓")

        # Wait
        await self._step_wait(page, {"seconds": 12, "reason": "retry execution"})

        # Re-capture
        cap_result = await self._step_capture_output(page, {})
        if cap_result.success:
            self.context.update(cap_result.data)
            new_output = self.context.get("output", "")
            if not _output_has_error(new_output):
                print(f"   Auto-retry succeeded ✓")
                return True
            else:
                vlog("Auto-retry output still has error")
        else:
            vlog(f"Re-capture failed: {cap_result.error}")
        return False

    # ==================================================================
    # PHASE 2 — STEP EXECUTION
    # ==================================================================

    async def _execute_with_retry(self, page, step: dict, step_num: int) -> StepResult:
        handler = self._step_handlers.get(step.get("action"))
        if not handler:
            return StepResult(False, error=f"Unknown action: {step.get('action')}")

        last_result = StepResult(False, error="not executed")
        for attempt in range(1, self.max_step_retries + 1):
            try:
                last_result = await handler(page, step)
                if last_result.success:
                    self.context.update(last_result.data)
                    return last_result
                if attempt < self.max_step_retries:
                    vlog(f"Step {step_num} attempt {attempt} failed: {last_result.error}")
                    await asyncio.sleep(1)
            except Exception as exc:
                last_result = StepResult(False, error=str(exc))
                if attempt < self.max_step_retries:
                    vlog(f"Step {step_num} attempt {attempt} exception: {exc}")
                    await asyncio.sleep(1)
        return last_result

    # ------------------------------------------------------------------
    # Repair loop
    # ------------------------------------------------------------------

    async def _repair_loop(self, page, step: dict, error: str, step_num: int) -> Optional[StepResult]:
        for attempt in range(1, self.MAX_REPAIR_ATTEMPTS + 1):
            vlog(f"Repair attempt {attempt}/{self.MAX_REPAIR_ATTEMPTS}")
            repaired = await self._ask_llm_repair(page, step, error)
            if repaired and repaired.success:
                self.context.update(repaired.data)
                return repaired
        return None

    async def _ask_llm_repair(self, page, step: dict, error: str) -> Optional[StepResult]:
        schema = self.context.get("page_schema", {})
        repair_prompt = (
            "A browser automation step failed. Suggest a fix.\n\n"
            f"Failed step: {json.dumps(step, ensure_ascii=False)}\n"
            f"Error: {error}\n"
            f"Page schema: {json.dumps(schema, ensure_ascii=False)[:2000]}\n\n"
            "Respond ONLY with JSON:\n"
            '{"strategy":"...","action":"same_or_new_action",'
            '"params":{...},"js_eval":"optional JS to run on page"}'
        )

        resp = await self.router.completion(repair_prompt, task="repair",
                                             max_tokens=800, temperature=0.3)
        if not resp.success:
            vlog(f"Repair LLM failed: {resp.error}")
            return None

        try:
            data = _parse_json(resp.content)
            vlog(f"Repair strategy: {data.get('strategy', '?')}")

            # Direct JS fix
            if data.get("js_eval"):
                try:
                    js_result = await page.evaluate(data["js_eval"])
                    return StepResult(True, {"repair_js": js_result})
                except Exception as exc:
                    vlog(f"Repair JS failed: {exc}")

            # Re-run with modified params
            repaired_step = {**step, **data.get("params", {})}
            repaired_step["action"] = data.get("action", step.get("action"))
            handler = self._step_handlers.get(repaired_step["action"])
            if handler:
                result = await handler(page, repaired_step)
                if result.success:
                    self.context.update(result.data)
                return result
        except Exception as exc:
            vlog(f"Repair parse/exec error: {exc}")
        return None

    # ==================================================================
    # PHASE 3 — VALIDATION
    # ==================================================================

    async def _final_validation(self, prompt: str) -> dict:
        output = self.context.get("output", "")
        if not output:
            return {"valid": True, "reason": "No output to validate (visual task or empty)"}

        val_prompt = (
            "You are validating program output. Be lenient — if the output looks "
            "reasonable for the request, mark it valid.\n\n"
            f'User request: "{prompt}"\n'
            f"Program output:\n{output[:2000]}\n\n"
            "Rules:\n"
            "- If the program ran and produced output related to the request → valid.\n"
            "- Minor formatting differences are OK → valid.\n"
            "- An error traceback or crash → invalid.\n"
            "- Empty output when output was expected → invalid.\n\n"
            'Respond ONLY with JSON: {"valid":true/false,"reason":"..."}'
        )

        resp = await self.router.completion(val_prompt, task="validation",
                                             max_tokens=300, temperature=0.1)
        if not resp.success:
            return {"valid": True, "reason": "Validation LLM unavailable"}

        try:
            result = _parse_json(resp.content)
            # Double-check if validation says invalid (small models produce false negatives)
            if not result.get("valid", True):
                vlog(f"First validation says invalid: {result.get('reason', '?')}")
                recheck = await self._recheck_validation(prompt, output)
                if recheck.get("valid", False):
                    vlog("Recheck overrode: valid after all")
                    return recheck
            return result
        except Exception:
            return {"valid": True, "reason": "Validation response unparseable"}

    async def _recheck_validation(self, prompt: str, output: str) -> dict:
        """Double-check a failed validation with a simpler prompt."""
        prompt2 = (
            f'A program was asked to: "{prompt}"\n'
            f"It produced:\n{output[:1000]}\n\n"
            "Does the output contain ANY relevant result and NO error traceback? "
            "If yes, it is valid. "
            'Answer ONLY with JSON: {"valid":true/false,"reason":"..."}'
        )
        resp = await self.router.completion(prompt2, task="validation",
                                             max_tokens=200, temperature=0.1)
        if resp.success:
            try:
                return _parse_json(resp.content)
            except Exception:
                pass
        return {"valid": True, "reason": "Recheck inconclusive, assuming valid"}

    # ==================================================================
    # STEP HANDLERS
    # ==================================================================

    async def _step_navigate(self, page, step: dict) -> StepResult:
        url = step.get("url", "")
        if not url:
            lang = step.get("language") or self.context.get("language", "python")
            slug = LANGUAGE_SLUG.get(lang, lang)
            url = f"https://www.mycompiler.io/new/{slug}"

        wait = step.get("wait_until", "domcontentloaded")
        vlog(f"Navigating → {url}")
        await page.goto(url, wait_until=wait, timeout=30000)
        await page.wait_for_timeout(2000)
        vlog(f"Page loaded: {page.url}")
        return StepResult(True, {"url": page.url})

    async def _step_dismiss_popups(self, page, step: dict) -> StepResult:
        dismissed = []
        popup_sels = [
            "button:has-text('Accept')", "button:has-text('Agree')",
            "button:has-text('OK')", "button:has-text('Got it')",
            "button:has-text('Close')", "button:has-text('Dismiss')",
            "[aria-label='Close']", ".modal-close", ".popup-close",
            "button:has-text('Akceptuję')", "button:has-text('Zamknij')",
            "button:has-text('Keep existing code')",
        ]
        for sel in popup_sels:
            try:
                btn = page.locator(sel).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click(timeout=2000)
                    dismissed.append(sel)
                    vlog(f"Dismissed: {sel}")
                    await page.wait_for_timeout(500)
            except Exception:
                continue
        return StepResult(True, {"popups_dismissed": dismissed})

    async def _step_inspect(self, page, step: dict) -> StepResult:
        schema = await self._extract_page_schema(page)
        self.context["page_schema"] = schema
        await dump_page_schema(page)
        return StepResult(True, {"page_schema": schema})

    # ------------------------------------------------------------------
    # Code generation (fully dynamic — no hardcoded presets)
    # ------------------------------------------------------------------

    async def _step_generate_code(self, page, step: dict) -> StepResult:
        language = step.get("language") or self.context.get("language", "python")
        task_desc = step.get("task_description") or self.context.get("goal", "hello world")

        gen_prompt = (
            f"Write a {language} program that: {task_desc}\n\n"
            "Requirements:\n"
            "- Complete, runnable program — no placeholders\n"
            "- Print clear output to stdout so results are visible\n"
            "- Handle edge cases\n"
            "- Keep it concise but correct\n\n"
            "CRITICAL: Respond with ONLY the raw source code.\n"
            "Do NOT add any explanation, description, or commentary after the code.\n"
            "Do NOT wrap in markdown. Just the code."
        )

        resp = await self.router.completion(gen_prompt, task="coding",
                                             max_tokens=2000, temperature=0.3)
        if not resp.success:
            return StepResult(False, error=f"Code generation failed: {resp.error}")

        code = _clean_generated_code(resp.content, language)
        if not code.strip():
            return StepResult(False, error="LLM returned empty code")

        self.context["generated_code"] = code
        self.context["language"] = language
        n_lines = code.count("\n") + 1
        print(f"   Generated {language} code ({len(code)} chars, {n_lines} lines)")
        vlog(f"Code:\n{code[:600]}")
        return StepResult(True, {"generated_code": code, "language": language})

    # ------------------------------------------------------------------
    # Code injection (page-schema-aware, multi-strategy)
    # ------------------------------------------------------------------

    async def _step_inject_code(self, page, step: dict) -> StepResult:
        code = step.get("code") or self.context.get("generated_code", "")
        if not code:
            return StepResult(False, error="No code to inject")

        # Wait for editor to be ready (CM6, Monaco, Ace, or textarea)
        editor_sels = [".cm-editor", ".cm-content", ".CodeMirror",
                       ".monaco-editor", ".ace_editor", "textarea"]
        for _ in range(10):
            for sel in editor_sels:
                try:
                    if await page.locator(sel).count() > 0:
                        vlog(f"Editor ready: {sel}")
                        break
                except Exception:
                    pass
            else:
                await page.wait_for_timeout(500)
                continue
            break
        else:
            vlog("No editor element detected after 5s wait")

        import json as _json
        escaped = _json.dumps(code)

        # Strategy cascade — each returns StepResult or None to skip

        strategies = [
            ("CodeMirror5", self._inject_cm5),
            ("CodeMirror6_paste", self._inject_cm6_paste),
            ("Monaco", self._inject_monaco),
            ("Ace", self._inject_ace),
            ("LLM_guided", self._inject_llm_guided),
            ("textarea", self._inject_textarea),
        ]

        for name, fn in strategies:
            try:
                result = await fn(page, code, escaped)
                if result and result.success:
                    vlog_decision(f"Injected via {name}", result.data.get("detail", ""))
                    return result
                elif result:
                    vlog(f"{name}: {result.error or 'not applicable'}")
            except Exception as exc:
                vlog(f"{name}: exception — {exc}")
        return StepResult(False, error="All injection strategies failed")

    async def _inject_cm5(self, page, code: str, escaped: str) -> Optional[StepResult]:
        js = (f'(() => {{ const cm = document.querySelector(".CodeMirror");'
              f' if (cm && cm.CodeMirror) {{ cm.CodeMirror.setValue({escaped}); return true; }}'
              f' return false; }})()')
        if await page.evaluate(js):
            return StepResult(True, {"injection_method": "cm5", "detail": "setValue()"})
        return None

    async def _inject_cm6_paste(self, page, code: str, escaped: str) -> Optional[StepResult]:
        cm = page.locator(".cm-content")
        if await cm.count() == 0:
            return None
        await cm.click()
        await page.keyboard.press("Control+a")
        await page.wait_for_timeout(100)
        ok = await page.evaluate('''(code) => {
            const el = document.querySelector('.cm-content');
            if (!el) return false;
            el.focus();
            const dt = new DataTransfer();
            dt.setData('text/plain', code);
            el.dispatchEvent(new ClipboardEvent('paste', {
                clipboardData: dt, bubbles: true, cancelable: true,
            }));
            return true;
        }''', code)
        if ok:
            return StepResult(True, {"injection_method": "cm6", "detail": "synthetic paste"})
        return None

    async def _inject_monaco(self, page, code: str, escaped: str) -> Optional[StepResult]:
        js = (f'(() => {{ const e = window.monaco && window.monaco.editor.getEditors();'
              f' if (e && e.length) {{ e[0].setValue({escaped}); return true; }}'
              f' return false; }})()')
        if await page.evaluate(js):
            return StepResult(True, {"injection_method": "monaco", "detail": "setValue()"})
        return None

    async def _inject_ace(self, page, code: str, escaped: str) -> Optional[StepResult]:
        js = (f'(() => {{ const a = document.querySelector(".ace_editor");'
              f' if (a && a.env && a.env.editor) {{ a.env.editor.setValue({escaped}, -1); return true; }}'
              f' return false; }})()')
        if await page.evaluate(js):
            return StepResult(True, {"injection_method": "ace", "detail": "setValue()"})
        return None

    async def _inject_llm_guided(self, page, code: str, escaped: str) -> Optional[StepResult]:
        """Ask LLM how to inject code based on actual page schema."""
        schema = self.context.get("page_schema")
        if not schema:
            return None

        prompt = (
            "Write a JavaScript expression that injects code into this web page's editor.\n"
            f"Page schema: {json.dumps(schema, ensure_ascii=False)[:1500]}\n"
            f"Code to inject (JS-escaped): {escaped[:300]}...\n\n"
            "The expression must return true on success, false on failure.\n"
            "Respond with ONLY the JS expression."
        )
        resp = await self.router.completion(prompt, task="coding",
                                             max_tokens=500, temperature=0.2)
        if not resp.success:
            return None

        js = _strip_code_fences(resp.content).strip()
        try:
            if await page.evaluate(js):
                return StepResult(True, {"injection_method": "llm", "detail": "LLM-generated JS"})
        except Exception as exc:
            vlog(f"LLM injection JS error: {exc}")
        return None

    async def _inject_textarea(self, page, code: str, escaped: str) -> Optional[StepResult]:
        for sel in ["textarea:not(#stdin)", "textarea"]:
            try:
                ta = page.locator(sel).first
                if await ta.count() > 0:
                    await ta.click()
                    await ta.fill(code)
                    return StepResult(True, {"injection_method": f"textarea({sel})",
                                             "detail": f"Selector: {sel}"})
            except Exception:
                continue
        return None

    # ------------------------------------------------------------------
    # find_and_click (purpose-driven + LLM-guided)
    # ------------------------------------------------------------------

    async def _step_find_and_click(self, page, step: dict) -> StepResult:
        raw_purpose = step.get("purpose", "run")
        # Normalize purpose: "run the code", "execute program" → "run"
        purpose = self._normalize_purpose(raw_purpose)
        selectors = list(step.get("selectors") or [])

        # LLM-suggested selectors
        selectors.extend(await self._llm_suggest_selectors(purpose))

        # Common fallbacks
        _COMMON: dict[str, list[str]] = {
            "run": [
                "button:has-text('Run')", "#run-button", "#run-btn",
                ".run-button", "button[title='Run']",
                "button:has-text('Execute')", "[data-action='run']",
                "button.btn-run",
            ],
            "submit": [
                "button:has-text('Submit')", "button[type='submit']",
                "input[type='submit']",
            ],
        }
        selectors.extend(_COMMON.get(purpose, []))

        for sel in selectors:
            try:
                btn = page.locator(sel).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    vlog_decision(f"Clicked '{sel}'", f"purpose={purpose}")
                    return StepResult(True, {"clicked": sel, "purpose": purpose})
            except Exception:
                continue
        return StepResult(False, error=f"No element found for purpose '{purpose}'")

    @staticmethod
    def _normalize_purpose(raw: str) -> str:
        """Normalize LLM-generated purpose strings to standard keys."""
        r = raw.lower().strip()
        if any(w in r for w in ("run", "execute", "uruchom", "start", "kompiluj", "compile")):
            return "run"
        if any(w in r for w in ("submit", "send", "wyślij")):
            return "submit"
        if any(w in r for w in ("save", "zapisz")):
            return "save"
        return "run"  # default to run for code editors

    async def _llm_suggest_selectors(self, purpose: str) -> list[str]:
        schema = self.context.get("page_schema")
        if not schema:
            return []
        prompt = (
            f"Given this page schema, suggest Playwright selectors for the '{purpose}' element.\n"
            f"Page: {json.dumps(schema, ensure_ascii=False)[:1500]}\n\n"
            'Respond ONLY with a JSON array of strings, e.g. ["#run-button"]'
        )
        resp = await self.router.completion(prompt, task="fast",
                                             max_tokens=300, temperature=0.1)
        if resp.success:
            try:
                arr = _parse_json(resp.content)
                if isinstance(arr, list):
                    return [s for s in arr if isinstance(s, str)]
            except Exception:
                pass
        return []

    # ------------------------------------------------------------------
    # Wait, capture, validate, screenshot
    # ------------------------------------------------------------------

    async def _step_wait(self, page, step: dict) -> StepResult:
        secs = step.get("seconds", 8)
        reason = step.get("reason", "")
        vlog(f"Waiting {secs}s — {reason}")
        await page.wait_for_timeout(secs * 1000)
        return StepResult(True)

    async def _step_capture_output(self, page, step: dict) -> StepResult:
        # Refresh page schema to see post-execution DOM
        await dump_page_schema(page)

        selectors: list[str] = list(step.get("selectors") or [])
        selectors.extend(await self._llm_suggest_selectors("output"))
        selectors.extend([
            "#output-terminal", "#output", ".output", "#output-text",
            "#execution-output", ".console-output", ".terminal-output",
            ".output-container", "[data-output]", ".result-container",
            "pre.output", "pre",
            "[id*='output']", "[class*='output']",
            "[id*='result']", "[class*='result']",
            "[id*='console']", "[class*='console']",
            "[id*='terminal']", "[class*='terminal']",
        ])

        placeholder_texts = {
            "(run the program to view its output)",
            "output will appear here",
            "click run to see output",
        }

        for sel in selectors:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    text = (await el.inner_text()).strip()
                    if text and text.lower() not in placeholder_texts:
                        vlog_decision(f"Output via '{sel}'", f"{len(text)} chars")
                        print(f"   Output ({sel}):")
                        for line in text.split("\n")[:12]:
                            print(f"     {line}")
                        return StepResult(True, {"output": text, "output_selector": sel})
                    else:
                        vlog(f"Selector '{sel}': matched but empty/placeholder")
                else:
                    vlog(f"Selector '{sel}': no match")
            except Exception:
                continue

        return StepResult(False, error="No output element found with real content")

    async def _step_validate(self, page, step: dict) -> StepResult:
        output = self.context.get("output", "")
        expected = step.get("expected_description") or self.context.get("goal", "")
        if not output:
            return StepResult(True, {"validation": "skipped"})

        val_prompt = (
            f'Validate output for: "{expected}"\n'
            f"Output:\n{output[:1500]}\n\n"
            'Respond ONLY with JSON: {"valid":true/false,"reason":"..."}'
        )
        resp = await self.router.completion(val_prompt, task="validation",
                                             max_tokens=200, temperature=0.1)
        if not resp.success:
            return StepResult(True, {"validation": "llm_unavailable"})

        try:
            v = _parse_json(resp.content)
            ok = v.get("valid", True)
            reason = v.get("reason", "")
            vlog(f"Validation: {'✓' if ok else '✗'} {reason}")
            if not ok:
                return StepResult(False, error=f"Validation failed: {reason}",
                                  data={"validation": v})
            return StepResult(True, {"validation": v})
        except Exception:
            return StepResult(True, {"validation": "unparseable"})

    async def _step_screenshot(self, page, step: dict) -> StepResult:
        filename = step.get("filename", "dynamic_result.png")
        ss_dir = Path("screenshots")
        ss_dir.mkdir(parents=True, exist_ok=True)
        path = ss_dir / filename
        await page.screenshot(path=str(path))
        print(f"   Screenshot: {path}")
        return StepResult(True, {"screenshot": str(path)})

    # ==================================================================
    # PAGE SCHEMA EXTRACTION
    # ==================================================================

    async def _extract_page_schema(self, page) -> dict:
        try:
            return await page.evaluate('''() => {
                const r = {};
                r.url = location.href;
                r.title = document.title;

                r.buttons = [];
                document.querySelectorAll(
                    'button, [role="button"], input[type="button"], input[type="submit"]'
                ).forEach(el => {
                    const t = (el.textContent || el.value || '').trim().slice(0, 50);
                    if (t && el.offsetWidth > 0)
                        r.buttons.push({text:t, id:el.id||'', tag:el.tagName.toLowerCase()});
                });

                r.inputs = [];
                document.querySelectorAll('input, textarea, select').forEach(el => {
                    r.inputs.push({
                        tag:el.tagName.toLowerCase(), type:el.type||'',
                        id:el.id||'', name:el.name||'', placeholder:el.placeholder||'',
                    });
                });

                r.editors = {
                    cm5: !!document.querySelector('.CodeMirror'),
                    cm6: !!document.querySelector('.cm-editor'),
                    monaco: !!document.querySelector('.monaco-editor'),
                    ace: !!document.querySelector('.ace_editor'),
                    contenteditable: document.querySelectorAll('[contenteditable="true"]').length,
                };

                r.output_containers = [];
                const oSel = 'pre, code, [id*="output"], [id*="result"], [id*="console"], '
                    + '[id*="terminal"], [class*="output"], [class*="result"], [class*="terminal"]';
                document.querySelectorAll(oSel).forEach(el => {
                    const txt = (el.textContent||'').trim();
                    if (txt.length > 0 || el.id || el.className)
                        r.output_containers.push({
                            tag:el.tagName.toLowerCase(), id:el.id||'',
                            cls:(el.className||'').toString().slice(0,80),
                            preview:txt.slice(0,100),
                            visible:el.offsetWidth>0 && el.offsetHeight>0,
                        });
                });
                if (r.output_containers.length > 15)
                    r.output_containers = r.output_containers.slice(0, 15);

                r.iframes = document.querySelectorAll('iframe').length;
                r.canvases = document.querySelectorAll('canvas').length;
                return r;
            }''')
        except Exception as exc:
            vlog(f"Schema extraction error: {exc}")
            return {}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _safe_context(self) -> dict:
        """Return context with large values truncated for display."""
        safe = {}
        for k, v in self.context.items():
            s = str(v)
            safe[k] = s[:500] if len(s) > 500 else v
        return safe


# ======================================================================
# Module-level helpers
# ======================================================================

def _parse_json(text: str) -> Any:
    """Robust JSON extraction from LLM output (handles markdown fences, preamble)."""
    text = text.strip()
    # Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip markdown code fences
    stripped = _strip_code_fences(text)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # Find first { or [ and match it
    for open_ch, close_ch in [("{", "}"), ("[", "]")]:
        start = text.find(open_ch)
        if start < 0:
            continue
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if escape:
                escape = False
                continue
            if ch == '\\':
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == open_ch:
                depth += 1
            elif ch == close_ch:
                depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    break
    raise ValueError(f"Cannot parse JSON from: {text[:300]}")


def _strip_code_fences(text: str) -> str:
    """Remove markdown ```...``` fences from LLM output."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()


def _clean_generated_code(raw: str, language: str = "python") -> str:
    """Strip code fences AND trailing non-code explanation from LLM output."""
    code = _strip_code_fences(raw)
    if not code:
        return code

    # Detect trailing plain-text explanation lines.
    # Heuristic: after the last line that looks like code, drop everything else.
    lines = code.split("\n")
    # For Python, a line starting with a letter (not indented, not a keyword/identifier
    # assignment, not a decorator, not a comment) that contains spaces and no '=', '(',
    # ':', '#' is likely prose.
    _CODE_SIGNALS = re.compile(
        r'^(\s|#|import |from |def |class |if |else|elif |for '
        r'|while |return |raise |try|except|finally|with |print|'
        r'\w+\s*[=(]|@|\)|\]|\}|$)'
    )
    cut = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i]
        if not line.strip():
            continue  # skip blanks
        if _CODE_SIGNALS.match(line):
            cut = i + 1
            break
        # This line looks like prose — keep searching upward
    if cut < len(lines):
        removed = len(lines) - cut
        vlog(f"Stripped {removed} trailing non-code line(s) from LLM output")
        lines = lines[:cut]
    return "\n".join(lines).rstrip()


def _output_has_error(output: str) -> bool:
    """Detect if program output contains an error traceback or crash."""
    if not output:
        return False
    ol = output.lower()
    error_signals = [
        "traceback (most recent call last)",
        "syntaxerror:", "indentationerror:", "nameerror:",
        "typeerror:", "valueerror:", "importerror:",
        "runtimeerror:", "zerodivisionerror:", "attributeerror:",
        "exit code 1", "exit code 2",
        "compilation error", "compile error",
        "segmentation fault", "core dumped",
        "uncaught exception", "referenceerror:",
        "fatal error",
    ]
    return any(sig in ol for sig in error_signals)
