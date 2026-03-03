#!/usr/bin/env python3
"""
02_picsart_painting — Paint on Picsart Draw via Playwright.

Picsart Draw (picsart.com/pl/draw) is a free online drawing tool with
brushes, layers, and color selection — no login required.

Demonstrates:
- Opening Picsart Draw in browser
- Selecting brush tools and colors
- Drawing patterns (spiral, grid, waves, freehand)
- Screenshot capture of the result

Usage:
    python3 02_picsart_painting.py
    python3 02_picsart_painting.py --pattern spiral --color red
    python3 02_picsart_painting.py --pattern grid --color green --headless
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add parent examples directory for _verbose_helper
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from _verbose_helper import init_verbose, vlog, dump_page_schema, ensure_playwright_browsers_async, dump_selectors, vlog_decision
from nlp2cmd.skills.drawing import DrawingSkill
from nlp2cmd.skills.drawing.renderers.playwright import PlaywrightRenderer

# Pattern → shape mapping for the drawing skill
PATTERN_SHAPES = {
    "spiral": "spiral",
    "grid": "grid",
    "waves": "wave",
    "flower": "flower",
}


async def main():
    parser = argparse.ArgumentParser(description="Paint on Picsart Draw")
    parser.add_argument("--pattern", default="spiral",
                        choices=list(PATTERN_SHAPES.keys()),
                        help="Pattern to draw")
    parser.add_argument("--color", default="blue",
                        help="Drawing color (name or hex)")
    parser.add_argument("--headless", action="store_true", help="Run headless")
    parser.add_argument("--screenshot-dir", default="screenshots", help="Output dir")
    parser.add_argument("--url", default="https://picsart.com/pl/draw",
                        help="Picsart Draw URL")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Show page schema, selector matching, and decision logs")
    args = parser.parse_args()

    init_verbose(args.verbose)

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("ERROR: pip install playwright")
        sys.exit(1)

    # Auto-install browsers if needed
    if not await ensure_playwright_browsers_async(auto_install=True):
        sys.exit(1)

    # --- Use DrawingSkill (CQRS + Event Sourcing) ---
    shape_type = PATTERN_SHAPES.get(args.pattern, "spiral")
    skill = DrawingSkill()
    skill.init_canvas(1280, 900, url=args.url, app="picsart")
    skill.draw(shape_type, color=args.color)

    print(f"=== Picsart Draw: {args.pattern} in {args.color} ===")
    print(f"URL: {args.url}")
    print(f"Shape type: {shape_type}, Events: {skill.event_count}")
    print()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=args.headless)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})

        print("1. Opening Picsart Draw & rendering via PlaywrightRenderer...")
        renderer = PlaywrightRenderer(page)
        canvas_info = await skill.render(renderer, url=args.url, app="picsart")
        print(f"   Canvas: {canvas_info.get('width', 0):.0f}x{canvas_info.get('height', 0):.0f}")
        vlog(f"Canvas info: {canvas_info}")

        # Inspect page schema
        await dump_page_schema(page)

        print(f"2. Drew {args.pattern} pattern")

        # Screenshot
        print("3. Saving screenshot...")
        screenshot_dir = Path(args.screenshot_dir)
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        path = screenshot_dir / f"picsart_{args.pattern}_{args.color}.png"
        await renderer.screenshot(str(path))
        print(f"   Screenshot: {path}")

        # Save event sourcing session
        session_path = screenshot_dir / f"picsart_{args.pattern}_{args.color}_session.json"
        skill.save_session(str(session_path))
        print(f"   Session saved: {session_path} ({skill.event_count} events)")

        await browser.close()

    print()
    state = skill.get_state()
    print(f"Done! Pattern: {args.pattern}, Color: {args.color}, Shapes: {state['shapes_count']}")


if __name__ == "__main__":
    asyncio.run(main())
