#!/usr/bin/env python3
"""
05_dynamic_executor — Fully LLM-driven code execution without hardcoded presets.

Unlike 02_mycompiler_run.py (hardcoded presets) or 03_adaptive_code.py (LLM code
generation but hardcoded automation steps), this script uses LLM for EVERYTHING:

1. Task planning   — LLM decomposes the prompt into executable steps
2. Code generation — LLM writes the code (no presets like fibonacci/factorial)
3. Page analysis   — LLM inspects DOM and decides how to inject/run/capture
4. Failure repair  — LLM suggests alternative approaches on failure
5. Validation      — LLM checks if the output matches the user's intent

Usage:
    # Simple — LLM generates code and runs it
    python3 05_dynamic_executor.py --prompt "write fibonacci in python"
    python3 05_dynamic_executor.py --prompt "napisz quicksort w Pythonie"

    # With verbose logging
    python3 05_dynamic_executor.py --prompt "create a factorial calculator in JS" --verbose

    # Specify site/language explicitly
    python3 05_dynamic_executor.py --prompt "bubble sort" --lang python --verbose

    # Custom wait time
    python3 05_dynamic_executor.py --prompt "generate 100 prime numbers" --wait 20
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

# Module path setup
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from _verbose_helper import init_verbose, vlog, ensure_playwright_browsers_async
from _dynamic_orchestrator import DynamicOrchestrator

# Load .env for API keys
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except ImportError:
    pass


def build_prompt(args) -> str:
    """Build the full prompt from CLI arguments."""
    prompt = args.prompt
    if args.lang and args.lang.lower() not in prompt.lower():
        prompt = f"{prompt} in {args.lang}"
    return prompt


async def main():
    parser = argparse.ArgumentParser(
        description="Dynamic LLM-driven code execution — no hardcoded presets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            '  %(prog)s --prompt "write fibonacci in python"\n'
            '  %(prog)s --prompt "napisz quicksort" --lang python --verbose\n'
            '  %(prog)s --prompt "create a calculator in javascript"\n'
        ),
    )
    parser.add_argument("--prompt", "-p", required=True,
                        help="Natural language description of what to code and run")
    parser.add_argument("--lang", "-l", default=None,
                        help="Programming language (auto-detected if not given)")
    parser.add_argument("--wait", "-w", type=int, default=12,
                        help="Seconds to wait for output (default: 12)")
    parser.add_argument("--headless", action="store_true",
                        help="Run browser in headless mode")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose LLM/page/decision logging")
    parser.add_argument("--screenshot-dir", default="screenshots",
                        help="Directory for screenshots")
    args = parser.parse_args()

    init_verbose(args.verbose)

    prompt = build_prompt(args)
    print(f"Prompt: {prompt}")

    # Create orchestrator
    orchestrator = DynamicOrchestrator(verbose=args.verbose)

    # Override wait time in any generated plan
    _orig_plan = orchestrator._plan_task

    async def _patched_plan(p):
        plan = await _orig_plan(p)
        for step in plan.steps:
            if step.get("action") == "wait":
                step["seconds"] = args.wait
            if step.get("action") == "screenshot":
                step["filename"] = f"dynamic_{args.lang or 'auto'}.png"
        return plan

    orchestrator._plan_task = _patched_plan

    # Launch browser and execute
    t0 = time.time()
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("ERROR: pip install playwright")
        sys.exit(1)

    # Auto-install browsers if needed
    if not await ensure_playwright_browsers_async(auto_install=True):
        sys.exit(1)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=args.headless)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})

        try:
            result = await orchestrator.execute_task(prompt, page)
        finally:
            await browser.close()

    elapsed = time.time() - t0

    # Summary
    print(f"\n{'─' * 60}")
    success = result.get("success", False)
    print(f"Result: {'SUCCESS' if success else 'FAILED'}")
    print(f"Time:   {elapsed:.1f}s")

    output = result.get("context", {}).get("output", "")
    if output:
        print(f"Output: {output[:200]}")

    validation = result.get("validation", {})
    if validation.get("reason"):
        print(f"Valid:  {validation['reason']}")

    if not success:
        err = result.get("error", "unknown")
        step = result.get("failed_step", "?")
        print(f"Error:  Step {step} — {err}")
        sys.exit(1)

    if not result.get("validation_passed", True):
        print("Note:   Validation flagged a concern (see above) but steps completed OK.")


if __name__ == "__main__":
    asyncio.run(main())
