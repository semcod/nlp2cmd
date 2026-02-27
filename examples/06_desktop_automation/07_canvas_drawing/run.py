#!/usr/bin/env python3
"""
07_canvas_drawing — Draw shapes on jspaint.app via Playwright mouse control.

Usage:
    python3 run.py                          # Draw ladybug (default)
    python3 run.py --shape ladybug          # Draw ladybug
    python3 run.py --shape circle --color red
    python3 run.py --shape rectangle --color blue
    python3 run.py --query "narysuj czerwone koło"
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))


async def main():
    parser = argparse.ArgumentParser(description="Draw on jspaint.app via NLP2CMD")
    parser.add_argument("--shape", default="ladybug", help="Shape to draw (ladybug, circle, rectangle, ellipse, line)")
    parser.add_argument("--color", default="red", help="Primary color")
    parser.add_argument("--url", default="https://jspaint.app", help="Canvas app URL")
    parser.add_argument("--query", default="", help="Natural language drawing command")
    parser.add_argument("--headless", action="store_true", help="Run headless")
    parser.add_argument("--screenshot-dir", default="screenshots", help="Screenshot output dir")
    args = parser.parse_args()

    from nlp2cmd.adapters.canvas import CanvasAdapter

    adapter = CanvasAdapter()

    # Build query from args or use provided query
    if args.query:
        query = args.query
    else:
        color_map = {"red": "czerwony", "blue": "niebieski", "green": "zielony", "black": "czarny"}
        color_pl = color_map.get(args.color, args.color)
        shape_map = {"ladybug": "biedronkę", "circle": "koło", "rectangle": "prostokąt", "ellipse": "elipsę", "line": "linię"}
        shape_pl = shape_map.get(args.shape, args.shape)
        query = f"narysuj {color_pl} {shape_pl} na {args.url}"

    print(f"Query: {query}")
    print(f"URL:   {args.url}")
    print()

    # Generate drawing plan
    plan = {"text": query, "confidence": 0.8}
    dsl_json = adapter.generate(plan)
    plan_data = json.loads(dsl_json)

    print(f"Plan: {len(plan_data.get('steps', []))} steps")
    for i, step in enumerate(plan_data.get("steps", []), 1):
        print(f"  {i:2d}. {step.get('action', '?'):25s} {step}")
    print()

    # Execute with Playwright
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("Playwright required: pip install playwright && playwright install")
        sys.exit(1)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=args.headless)
        page = await browser.new_page(viewport={"width": 1024, "height": 768})

        print("Executing drawing plan...")
        result = await CanvasAdapter.execute_drawing_plan(page, dsl_json)

        print(f"Result: {result}")

        # Save final screenshot
        screenshot_dir = Path(args.screenshot_dir)
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = screenshot_dir / f"{args.shape}_final.png"
        await page.screenshot(path=str(screenshot_path))
        print(f"Screenshot: {screenshot_path}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
