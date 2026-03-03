#!/usr/bin/env python3
"""
01_draw_chat — Draw shapes on draw.chat whiteboard via Playwright.

draw.chat is a free online whiteboard that works without login.
This example demonstrates:
- Opening draw.chat in a browser with intelligent URL discovery
- Using DrawingSkill (CQRS + Event Sourcing) for shape generation
- Rendering via PlaywrightRenderer with mouse movements
- Comprehensive logging and error handling
- Platform-independent execution

Usage:
    python3 run.py
    python3 run.py --shape star --color blue
    python3 run.py --shape house --color red --headless
    python3 run.py -v  # verbose mode
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Setup import paths
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))           # 09_online_drawing/
sys.path.insert(0, str(_HERE.parents[1]))        # examples/
sys.path.insert(0, str(_HERE.parents[2] / "src"))  # src/

from _run_utils import ExampleRunner, find_canvas, get_platform_info, discover_working_url
from _verbose_helper import init_verbose, vlog, dump_page_schema

from nlp2cmd.skills.drawing import DrawingSkill
from nlp2cmd.skills.drawing.renderers.playwright import PlaywrightRenderer


async def main():
    available = DrawingSkill.available_shapes()

    parser = argparse.ArgumentParser(description="Draw on draw.chat whiteboard")
    parser.add_argument("--shape", default="house", choices=available, help="Shape to draw")
    parser.add_argument("--color", default="blue", help="Drawing color (name or hex)")
    parser.add_argument("--headless", action="store_true", help="Run headless")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    init_verbose(args.verbose)

    async with ExampleRunner("01_draw_chat", headless=args.headless, base_dir=_HERE) as runner:
        log = runner.log
        page = runner.page

        # Step 1: Build drawing plan via DrawingSkill
        log.step(1, f"Building drawing plan: {args.shape} in {args.color}")
        skill = DrawingSkill()
        skill.init_canvas(1024, 768, url="", app="draw.chat")
        skill.draw(args.shape, color=args.color)

        log.info(f"Events emitted: {skill.event_count}")
        log.info(f"Available shapes: {', '.join(available)}")

        # Step 2: Navigate to draw.chat with fallback chain
        log.step(2, "Navigating to draw.chat...")
        working_url = await runner.navigate("draw.chat")

        if not working_url:
            log.warning("draw.chat unavailable — trying fallback sites...")
            for fallback_site in ["jspaint", "excalidraw", "kleki"]:
                log.info(f"Trying fallback: {fallback_site}")
                working_url, health = await discover_working_url(
                    page, fallback_site, log=log,
                )
                if working_url:
                    log.success(f"Fallback succeeded: {fallback_site} → {working_url}")
                    break

            if not working_url:
                log.error("No drawing site available (all fallbacks failed)")
                return

        await page.wait_for_timeout(2000)

        # Step 3: Render via PlaywrightRenderer
        log.step(3, "Rendering via PlaywrightRenderer...")
        renderer = PlaywrightRenderer(page)
        canvas_info = await skill.render(renderer, url="", app="draw.chat")
        log.info(f"Canvas: {canvas_info.get('width', 0):.0f}x{canvas_info.get('height', 0):.0f}")

        if args.verbose:
            await dump_page_schema(page)

        # Step 4: Screenshot
        log.step(4, "Saving screenshot...")
        ss_name = f"draw_chat_{args.shape}_{args.color}.png"
        await runner.screenshot(ss_name, shape=args.shape, color=args.color, url=working_url)

        # Step 5: Save event sourcing session
        log.step(5, "Saving session...")
        session_path = runner.screenshot_dir / f"draw_chat_{args.shape}_{args.color}_session.json"
        skill.save_session(str(session_path))
        log.info(f"Session: {session_path} ({skill.event_count} events)")

        # Summary
        state = skill.get_state()
        log.success(f"Done! Shape: {args.shape}, Color: {args.color}, Shapes drawn: {state['shapes_count']}")


if __name__ == "__main__":
    asyncio.run(main())
