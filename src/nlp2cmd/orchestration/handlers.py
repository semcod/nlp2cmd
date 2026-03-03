"""
Step handlers for the Orchestration Engine.

Bridges the Orchestrator's step interface with existing nlp2cmd execution
capabilities (shell, browser, code generation, etc.).

Each handler is an async function:
    async def handler(step: StepDef, context: dict) -> StepResult

Usage:
    from nlp2cmd.orchestration.handlers import register_default_handlers
    orch = Orchestrator()
    register_default_handlers(orch)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
import time
from typing import Any, Optional

from nlp2cmd.orchestration.engine import Orchestrator, StepDef, StepResult, StepStatus

logger = logging.getLogger(__name__)


# ── Shell handler ────────────────────────────────────────────────────

async def handle_shell_exec(step: StepDef, ctx: dict) -> StepResult:
    """Execute a shell command."""
    command = step.params.get("command", "")
    if not command:
        return StepResult(StepStatus.SKIPPED, error="No command specified")

    cwd = step.params.get("cwd") or ctx.get("cwd")
    timeout = step.params.get("timeout", 30)

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout,
        )
        output = stdout.decode("utf-8", errors="replace")
        err_output = stderr.decode("utf-8", errors="replace")

        if proc.returncode == 0:
            return StepResult(StepStatus.SUCCESS, {
                "output": output,
                "shell_stdout": output,
                "shell_stderr": err_output,
                "exit_code": 0,
            })
        else:
            return StepResult(StepStatus.FAILED, {
                "output": output + err_output,
                "exit_code": proc.returncode,
            }, error=f"Exit code {proc.returncode}: {err_output[:200]}")

    except asyncio.TimeoutError:
        return StepResult(StepStatus.FAILED, error=f"Command timed out ({timeout}s)")
    except Exception as exc:
        return StepResult(StepStatus.FAILED, error=str(exc))


# ── Code generation handler ──────────────────────────────────────────

async def handle_generate_code(step: StepDef, ctx: dict) -> StepResult:
    """Generate code via LLM."""
    task_desc = step.params.get("task_description") or ctx.get("goal", "hello world")
    language = step.params.get("language") or ctx.get("language", "python")
    error_output = step.params.get("error_output", "")
    fix_mode = step.params.get("fix_mode", False)

    try:
        from nlp2cmd.llm.router import LLMRouter
        router = LLMRouter()
    except Exception:
        return StepResult(StepStatus.FAILED, error="LLMRouter not available")

    if fix_mode and error_output:
        old_code = ctx.get("generated_code", "")
        prompt = (
            f"Fix this {language} program:\n\n"
            f"Code:\n{old_code[:1500]}\n\n"
            f"Error:\n{error_output[:1000]}\n\n"
            f"Original task: {task_desc}\n\n"
            "CRITICAL: Respond with ONLY the raw source code, no explanations."
        )
        task = "repair"
    else:
        prompt = (
            f"Write a {language} program that: {task_desc}\n\n"
            "Requirements:\n"
            "- Complete, runnable program\n"
            "- Print clear output to stdout\n"
            "- Handle edge cases\n\n"
            "CRITICAL: Respond with ONLY the raw source code. "
            "No markdown, no ``` fences, no explanation."
        )
        task = "coding"

    resp = await router.completion(prompt, task=task, max_tokens=2000, temperature=0.3)
    if not resp.success:
        return StepResult(StepStatus.FAILED, error=f"LLM failed: {resp.error}")

    code = _strip_code_fences(resp.content)
    if not code.strip():
        return StepResult(StepStatus.FAILED, error="LLM returned empty code")

    return StepResult(StepStatus.SUCCESS, {
        "generated_code": code,
        "language": language,
    })


# ── Wait handler ─────────────────────────────────────────────────────

async def handle_wait(step: StepDef, ctx: dict) -> StepResult:
    """Wait for a specified duration."""
    seconds = step.params.get("seconds", 5)
    await asyncio.sleep(seconds)
    return StepResult(StepStatus.SUCCESS)


# ── Inspect handler (page schema extraction) ─────────────────────────

async def handle_inspect(step: StepDef, ctx: dict) -> StepResult:
    """Inspect page DOM structure and store schema in context."""
    page = ctx.get("page")
    if not page:
        return StepResult(StepStatus.SUCCESS, {"page_schema": {}})

    try:
        schema = await page.evaluate('''() => {
            const r = {};
            r.url = location.href;
            r.title = document.title;
            r.buttons = [];
            document.querySelectorAll('button, [role="button"]').forEach(el => {
                const t = (el.textContent || '').trim().slice(0, 50);
                if (t && el.offsetWidth > 0)
                    r.buttons.push({text:t, id:el.id||'', tag:el.tagName.toLowerCase()});
            });
            r.inputs = [];
            document.querySelectorAll('input, textarea, select').forEach(el => {
                r.inputs.push({tag:el.tagName.toLowerCase(), type:el.type||'',
                    id:el.id||'', placeholder:el.placeholder||''});
            });
            r.editors = {
                cm5: !!document.querySelector('.CodeMirror'),
                cm6: !!document.querySelector('.cm-editor'),
                monaco: !!document.querySelector('.monaco-editor'),
                ace: !!document.querySelector('.ace_editor'),
            };
            return r;
        }''')
        return StepResult(StepStatus.SUCCESS, {"page_schema": schema})
    except Exception as exc:
        return StepResult(StepStatus.SUCCESS, {"page_schema": {}, "inspect_error": str(exc)})


# ── Navigate handler ─────────────────────────────────────────────────

async def handle_navigate(step: StepDef, ctx: dict) -> StepResult:
    """Navigate browser page to URL."""
    page = ctx.get("page")
    url = step.params.get("url", "")
    if not page:
        return StepResult(StepStatus.SKIPPED, error="No page in context")
    if not url:
        return StepResult(StepStatus.FAILED, error="No URL specified")

    wait_until = step.params.get("wait_until", "domcontentloaded")
    await page.goto(url, wait_until=wait_until, timeout=30000)
    await page.wait_for_timeout(2000)
    return StepResult(StepStatus.SUCCESS, {"url": page.url})


# ── Dismiss popups handler ───────────────────────────────────────────

async def handle_dismiss_popups(step: StepDef, ctx: dict) -> StepResult:
    """Dismiss cookie banners, consent dialogs, etc."""
    page = ctx.get("page")
    if not page:
        return StepResult(StepStatus.SUCCESS, {"popups_dismissed": []})

    dismissed = []
    sels = [
        "button:has-text('Accept')", "button:has-text('Agree')",
        "button:has-text('OK')", "button:has-text('Got it')",
        "button:has-text('Close')", "button:has-text('Keep existing code')",
        "button:has-text('Akceptuję')", "button:has-text('Zamknij')",
    ]
    for sel in sels:
        try:
            btn = page.locator(sel).first
            if await btn.count() > 0 and await btn.is_visible():
                await btn.click(timeout=2000)
                dismissed.append(sel)
                await page.wait_for_timeout(500)
        except Exception:
            continue
    return StepResult(StepStatus.SUCCESS, {"popups_dismissed": dismissed})


# ── Code injection handler ───────────────────────────────────────────

async def handle_inject_code(step: StepDef, ctx: dict) -> StepResult:
    """Inject code into a web page editor (CM5/CM6/Monaco/Ace/textarea)."""
    page = ctx.get("page")
    code = step.params.get("code") or ctx.get("generated_code", "")
    if not page:
        return StepResult(StepStatus.SKIPPED, error="No page in context")
    if not code:
        return StepResult(StepStatus.FAILED, error="No code to inject")

    escaped = json.dumps(code)

    # CM5
    try:
        js = (f'(() => {{ const cm = document.querySelector(".CodeMirror");'
              f' if (cm && cm.CodeMirror) {{ cm.CodeMirror.setValue({escaped}); return true; }}'
              f' return false; }})()')
        if await page.evaluate(js):
            return StepResult(StepStatus.SUCCESS, {"injection_method": "cm5"})
    except Exception:
        pass

    # CM6 — synthetic paste
    try:
        cm = page.locator(".cm-content")
        if await cm.count() > 0:
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
                return StepResult(StepStatus.SUCCESS, {"injection_method": "cm6"})
    except Exception:
        pass

    # Monaco
    try:
        js = (f'(() => {{ const e = window.monaco && window.monaco.editor.getEditors();'
              f' if (e && e.length) {{ e[0].setValue({escaped}); return true; }}'
              f' return false; }})()')
        if await page.evaluate(js):
            return StepResult(StepStatus.SUCCESS, {"injection_method": "monaco"})
    except Exception:
        pass

    # Ace
    try:
        js = (f'(() => {{ const a = document.querySelector(".ace_editor");'
              f' if (a && a.env && a.env.editor) {{ a.env.editor.setValue({escaped}, -1); return true; }}'
              f' return false; }})()')
        if await page.evaluate(js):
            return StepResult(StepStatus.SUCCESS, {"injection_method": "ace"})
    except Exception:
        pass

    # Textarea fallback
    for sel in ["textarea:not(#stdin)", "textarea"]:
        try:
            ta = page.locator(sel).first
            if await ta.count() > 0:
                await ta.click()
                await ta.fill(code)
                return StepResult(StepStatus.SUCCESS, {"injection_method": f"textarea({sel})"})
        except Exception:
            continue

    return StepResult(StepStatus.FAILED, error="All injection strategies failed")


# ── Find and click handler ───────────────────────────────────────────

_PURPOSE_MAP = {
    "run": [
        "button:has-text('Run')", "#run-button", "#run-btn",
        ".run-button", "button[title='Run']",
        "button:has-text('Execute')", "[data-action='run']",
    ],
    "submit": [
        "button:has-text('Submit')", "button[type='submit']",
    ],
}


async def handle_find_and_click(step: StepDef, ctx: dict) -> StepResult:
    """Find and click a button by purpose."""
    page = ctx.get("page")
    if not page:
        return StepResult(StepStatus.SKIPPED, error="No page in context")

    raw_purpose = step.params.get("purpose", "run")
    purpose = _normalize_purpose(raw_purpose)
    selectors = list(step.params.get("selectors") or [])
    selectors.extend(_PURPOSE_MAP.get(purpose, []))

    # First pass
    for sel in selectors:
        try:
            btn = page.locator(sel).first
            if await btn.count() > 0 and await btn.is_visible():
                await btn.click()
                return StepResult(StepStatus.SUCCESS, {"clicked": sel, "purpose": purpose})
        except Exception:
            continue

    # Second pass — wait up to 5s
    for sel in _PURPOSE_MAP.get(purpose, [])[:3]:
        try:
            btn = page.locator(sel).first
            await btn.wait_for(state="visible", timeout=5000)
            await btn.click()
            return StepResult(StepStatus.SUCCESS, {"clicked": sel, "purpose": purpose})
        except Exception:
            continue

    return StepResult(StepStatus.FAILED, error=f"No element found for purpose '{purpose}'")


def _normalize_purpose(raw: str) -> str:
    r = raw.lower().strip()
    if any(w in r for w in ("run", "execute", "uruchom", "start", "compile")):
        return "run"
    if any(w in r for w in ("submit", "send", "wyślij")):
        return "submit"
    return "run"


# ── Capture output handler ───────────────────────────────────────────

async def handle_capture_output(step: StepDef, ctx: dict) -> StepResult:
    """Capture program output from web page."""
    page = ctx.get("page")
    if not page:
        return StepResult(StepStatus.SKIPPED, error="No page in context")

    selectors = [
        "#output-terminal", "#output", ".output", "#output-text",
        "#execution-output", ".console-output", ".terminal-output",
        ".output-container", "[data-output]", "pre",
        "[id*='output']", "[class*='output']",
        "[id*='terminal']", "[class*='terminal']",
    ]

    placeholders = {
        "(run the program to view its output)",
        "output will appear here",
    }

    for sel in selectors:
        try:
            el = page.locator(sel).first
            if await el.count() > 0:
                text = (await el.inner_text()).strip()
                if text and text.lower() not in placeholders:
                    return StepResult(StepStatus.SUCCESS, {
                        "output": text, "output_selector": sel,
                    })
        except Exception:
            continue

    return StepResult(StepStatus.FAILED, error="No output element found")


# ── Screenshot handler ───────────────────────────────────────────────

async def handle_screenshot(step: StepDef, ctx: dict) -> StepResult:
    """Take a screenshot."""
    page = ctx.get("page")
    if not page:
        return StepResult(StepStatus.SKIPPED, error="No page in context")

    from pathlib import Path
    filename = step.params.get("filename", "orchestrator_result.png")
    ss_dir = Path(step.params.get("dir", "screenshots"))
    ss_dir.mkdir(parents=True, exist_ok=True)
    path = ss_dir / filename
    await page.screenshot(path=str(path))
    return StepResult(StepStatus.SUCCESS, {"screenshot": str(path)})


# ── Validate handler (inline step validation via LLM) ────────────────

async def handle_validate(step: StepDef, ctx: dict) -> StepResult:
    """Validate output via reflection (delegates to ResultAnalyzer)."""
    from nlp2cmd.orchestration.reflection import ResultAnalyzer

    output = ctx.get("output", "")
    goal = step.params.get("expected_description") or ctx.get("goal", "")

    analyzer = ResultAnalyzer()
    result = await analyzer.analyze(goal=goal, output=str(output), context=ctx)

    if result.should_retry:
        return StepResult(StepStatus.FAILED, {"validation": result.__dict__},
                          error=f"Validation: {result.reason}")
    return StepResult(StepStatus.SUCCESS, {"validation": result.__dict__})


# ── Registration ─────────────────────────────────────────────────────

def register_default_handlers(orch: Orchestrator) -> None:
    """Register all default step handlers on an Orchestrator instance."""
    orch.register_handler("shell_exec", handle_shell_exec)
    orch.register_handler("generate_code", handle_generate_code)
    orch.register_handler("wait", handle_wait)
    orch.register_handler("inspect", handle_inspect)
    orch.register_handler("navigate", handle_navigate)
    orch.register_handler("dismiss_popups", handle_dismiss_popups)
    orch.register_handler("inject_code", handle_inject_code)
    orch.register_handler("find_and_click", handle_find_and_click)
    orch.register_handler("capture_output", handle_capture_output)
    orch.register_handler("screenshot", handle_screenshot)
    orch.register_handler("validate", handle_validate)


# ── Helpers ──────────────────────────────────────────────────────────

def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()
