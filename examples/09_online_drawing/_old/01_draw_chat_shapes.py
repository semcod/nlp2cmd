#!/usr/bin/env python3
"""
01_draw_chat_shapes — Draw shapes on draw.chat whiteboard via Playwright.

draw.chat is a free online whiteboard that works without login.
This example demonstrates:
- Opening draw.chat in a browser
- Using drawing tools (pen, rectangle, ellipse, line)
- Setting colors
- Drawing geometric shapes
- Taking screenshots of the result

Usage:
    python3 01_draw_chat_shapes.py
    python3 01_draw_chat_shapes.py --shape star --color blue
    python3 01_draw_chat_shapes.py --shape house --color red --headless
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


async def main():
    available = DrawingSkill.available_shapes()
    parser = argparse.ArgumentParser(description="Draw on draw.chat whiteboard")
    parser.add_argument("--shape", default="house", choices=available,
                        help="Shape to draw")
    parser.add_argument("--color", default="blue",
                        help="Drawing color (name or hex)")
    parser.add_argument("--headless", action="store_true", help="Run headless")
    parser.add_argument("--screenshot-dir", default="screenshots", help="Output dir")
    parser.add_argument("--url", default="https://draw.chat/pl/index.html",
                        help="draw.chat URL")
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
    skill = DrawingSkill()
    skill.init_canvas(1024, 768, url=args.url, app="draw.chat")
    skill.draw(args.shape, color=args.color)

    print(f"=== draw.chat Drawing: {args.shape} in {args.color} ===")
    print(f"URL: {args.url}")
    print(f"Events emitted: {skill.event_count}")
    print(f"Available shapes: {', '.join(available)}")
    print()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=args.headless)
        page = await browser.new_page(viewport={"width": 1024, "height": 768})

        print("1. Opening draw.chat & rendering via PlaywrightRenderer...")
        renderer = PlaywrightRenderer(page)
        canvas_info = await skill.render(renderer, url=args.url, app="draw.chat")
        print(f"   Canvas: {canvas_info.get('width', 0):.0f}x{canvas_info.get('height', 0):.0f}")
        vlog(f"Canvas info: {canvas_info}")

        # Inspect page schema
        await dump_page_schema(page)

        print("2. Saving screenshot...")
        screenshot_dir = Path(args.screenshot_dir)
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        path = screenshot_dir / f"draw_chat_{args.shape}_{args.color}.png"
        await renderer.screenshot(str(path))
        print(f"   Screenshot: {path}")

        # Save event sourcing session
        session_path = screenshot_dir / f"draw_chat_{args.shape}_{args.color}_session.json"
        skill.save_session(str(session_path))
        print(f"   Session saved: {session_path} ({skill.event_count} events)")

        await browser.close()

    print()
    state = skill.get_state()
    print(f"Done! Shape: {args.shape}, Color: {args.color}, Shapes drawn: {state['shapes_count']}")


if __name__ == "__main__":
    asyncio.run(main())
