#!/usr/bin/env python3
"""
Universal task runner — the simplest way to use nlp2cmd orchestration.

Takes any natural language prompt and executes it dynamically via LLM.
No hardcoded presets, no domain-specific setup.

Usage:
    # Shell tasks (no browser needed)
    python3 run_task.py "list all python files in current directory"
    python3 run_task.py "count lines of code in src/"

    # Code execution on mycompiler.io
    python3 run_task.py "write fibonacci in python and run it" --browser

    # With metrics report
    python3 run_task.py "generate 10 prime numbers in python" --browser --metrics
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nlp2cmd.orchestration import (
    Orchestrator,
    register_default_handlers,
    MetricsCollector,
)


async def main():
    parser = argparse.ArgumentParser(
        description="Universal NLP2CMD task runner",
    )
    parser.add_argument("prompt", help="Natural language task description")
    parser.add_argument("--browser", action="store_true",
                        help="Enable browser automation (requires playwright)")
    parser.add_argument("--headless", action="store_true",
                        help="Run browser in headless mode")
    parser.add_argument("--metrics", action="store_true",
                        help="Show metrics summary after execution")
    args = parser.parse_args()

    orch = Orchestrator()
    register_default_handlers(orch)

    context = {}
    page = None
    browser = None
    pw_ctx = None

    if args.browser:
        try:
            from playwright.async_api import async_playwright
            pw_ctx = await async_playwright().__aenter__()
            browser = await pw_ctx.chromium.launch(headless=args.headless)
            page = await browser.new_page(viewport={"width": 1280, "height": 900})
            context["page"] = page
        except ImportError:
            print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
            sys.exit(1)

    try:
        result = await orch.run(args.prompt, context=context)

        print(f"\n{'─' * 50}")
        print(f"Result:  {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Steps:   {result.steps_executed}/{result.steps_total}")
        print(f"Time:    {result.duration_ms:.0f}ms")
        if result.output:
            print(f"Output:  {result.output[:300]}")
        if result.error:
            print(f"Error:   {result.error}")
        if result.reflection:
            print(f"Verdict: {result.reflection.verdict.value} — {result.reflection.reason}")

        if args.metrics:
            mc = MetricsCollector()
            summary = mc.get_summary()
            print(f"\n{'─' * 50}")
            print(f"Metrics (all-time):")
            print(f"  Tasks:        {summary['total_tasks']}")
            print(f"  Success rate: {summary['success_rate']:.0%}")
            print(f"  Avg time:     {summary['avg_duration_ms']:.0f}ms")
            print(f"  LLM calls:    {summary['total_llm_calls']}")
            print(f"  Tokens:       {summary['total_tokens_in'] + summary['total_tokens_out']}")

        sys.exit(0 if result.success else 1)

    finally:
        if browser:
            await browser.close()
        if pw_ctx:
            await pw_ctx.__aexit__(None, None, None)


if __name__ == "__main__":
    asyncio.run(main())
