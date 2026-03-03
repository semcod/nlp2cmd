#!/usr/bin/env python3
"""
02_picsart — Paint patterns on Picsart Draw via Playwright.

Picsart Draw is a free online drawing tool with brushes, layers, and colors.
This example demonstrates:
- Opening Picsart Draw with intelligent URL discovery + fallback
- Pattern drawing via DrawingSkill (spiral, grid, waves, flower)
- Handling login prompts and complex popup chains
- Comprehensive logging and error handling

Usage:
    python3 run.py
    python3 run.py --pattern spiral --color red
    python3 run.py --pattern grid --color green --headless
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Setup import paths
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))
sys.path.insert(0, str(_HERE.parents[1]))
sys.path.insert(0, str(_HERE.parents[2] / "src"))

from _run_utils import ExampleRunner, dismiss_popups, find_canvas, discover_working_url, DRAWING_SITES
from _verbose_helper import init_verbose, vlog, dump_page_schema

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
    parser.add_argument("--pattern", default="spiral", choices=list(PATTERN_SHAPES.keys()),
                        help="Pattern to draw")
    parser.add_argument("--color", default="blue", help="Drawing color (name or hex)")
    parser.add_argument("--headless", action="store_true", help="Run headless")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    init_verbose(args.verbose)

    async with ExampleRunner("02_picsart", headless=args.headless,
                              base_dir=_HERE,
                              viewport={"width": 1280, "height": 900}) as runner:
        log = runner.log
        page = runner.page

        # Step 1: Build drawing plan
        shape_type = PATTERN_SHAPES.get(args.pattern, "spiral")
        log.step(1, f"Building plan: {args.pattern} ({shape_type}) in {args.color}")

        skill = DrawingSkill()
        skill.init_canvas(1280, 900, url="", app="picsart")
        skill.draw(shape_type, color=args.color)

        log.info(f"Shape type: {shape_type}, Events: {skill.event_count}")

        # Step 2: Navigate to Picsart with intelligent fallback
        log.step(2, "Navigating to Picsart Draw...")
        working_url = await runner.navigate("picsart")

        if not working_url:
            # Picsart is known to require login or block headless browsers.
            # Fall back to alternative drawing sites.
            log.warning("Picsart unavailable — trying fallback sites...")

            for fallback_site in ["kleki", "excalidraw", "draw.chat"]:
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

        # Extra popup dismissal for Picsart (aggressive popup chain)
        dismissed = await dismiss_popups(page, log, timeout=5000)
        if dismissed:
            log.info(f"Extra popups dismissed: {dismissed}")

        # Step 3: Render via PlaywrightRenderer
        log.step(3, "Rendering via PlaywrightRenderer...")
        renderer = PlaywrightRenderer(page)
        canvas_info = await skill.render(renderer, url="", app="picsart")
        log.info(f"Canvas: {canvas_info.get('width', 0):.0f}x{canvas_info.get('height', 0):.0f}")

        if args.verbose:
            await dump_page_schema(page)

        # Step 4: Screenshot
        log.step(4, "Saving screenshot...")
        ss_name = f"picsart_{args.pattern}_{args.color}.png"
        await runner.screenshot(ss_name, pattern=args.pattern, color=args.color, url=working_url)

        # Step 5: Save session
        log.step(5, "Saving session...")
        session_path = runner.screenshot_dir / f"picsart_{args.pattern}_{args.color}_session.json"
        skill.save_session(str(session_path))
        log.info(f"Session: {session_path} ({skill.event_count} events)")

        # Summary
        state = skill.get_state()
        log.success(f"Done! Pattern: {args.pattern}, Color: {args.color}, Shapes: {state['shapes_count']}")


if __name__ == "__main__":
    asyncio.run(main())
