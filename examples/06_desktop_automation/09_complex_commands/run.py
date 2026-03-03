#!/usr/bin/env python3
"""
09_complex_commands — Decompose and execute complex NL commands.

Usage:
    python3 run.py --query "wejdź na jspaint.app i narysuj biedronkę"
    python3 run.py --query "otwórz przeglądarkę i sprawdź pocztę"
    python3 run.py --plan-only --query "narysuj czerwone koło"
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add examples parent and src to path for shared helpers
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from _verbose_helper import ensure_playwright_browsers_async


async def main():
    parser = argparse.ArgumentParser(description="Complex command planner + executor")
    parser.add_argument("--query", required=True, help="Natural language command")
    parser.add_argument("--plan-only", action="store_true", help="Only show plan, don't execute")
    parser.add_argument("--headless", action="store_true", help="Run browser headless")
    args = parser.parse_args()

    from nlp2cmd.automation.complex_planner import ComplexCommandPlanner

    planner = ComplexCommandPlanner()
    print(f"Query: {args.query}")
    print()

    plan = await planner.plan(args.query)

    print(f"Plan ({plan.source}): {len(plan.steps)} steps")
    print("-" * 60)
    for i, step in enumerate(plan.steps, 1):
        params_str = json.dumps(step.params, ensure_ascii=False) if step.params else ""
        print(f"  {i:2d}. [{step.action:25s}] {step.description}")
        if params_str:
            print(f"      params: {params_str}")
    print("-" * 60)

    if args.plan_only:
        print("\nPlan-only mode — not executing.")
        print(f"\nJSON plan:\n{json.dumps(plan.to_dict(), indent=2, ensure_ascii=False)}")
        return

    # Execute plan steps
    print("\nExecuting plan...")

    has_navigate = any(s.action == "navigate" for s in plan.steps)
    if has_navigate:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            print("ERROR: pip install playwright")
            sys.exit(1)

        # Auto-install browsers if needed
        if not await ensure_playwright_browsers_async(auto_install=True):
            sys.exit(1)

        from nlp2cmd.adapters.canvas import CanvasAdapter

        # Check if this is a canvas plan
        canvas_steps = [s for s in plan.steps if s.action in (
            "select_tool", "set_color", "draw_circle", "draw_ellipse",
            "draw_rectangle", "draw_line", "fill_at", "draw_filled_circle",
            "draw_filled_ellipse",
        )]

        if canvas_steps:
            # Build canvas_dql.v1 JSON and execute
            url = "https://jspaint.app"
            for s in plan.steps:
                if s.action == "navigate" and "url" in s.params:
                    url = s.params["url"]
                    break

            canvas_plan = {
                "dsl": "canvas_dql.v1",
                "app": "jspaint",
                "url": url,
                "steps": [s.to_dict() for s in plan.steps],
            }
            plan_json = json.dumps(canvas_plan, ensure_ascii=False)

            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=args.headless)
                page = await browser.new_page(viewport={"width": 1024, "height": 768})
                result = await CanvasAdapter.execute_drawing_plan(page, plan_json)
                print(f"\nResult: {result}")
                await browser.close()
        else:
            print("Non-canvas browser plans: use 'nlp2cmd -r' for full pipeline execution")
    else:
        print("Desktop/shell plans: use 'nlp2cmd -r' for full pipeline execution")

    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
