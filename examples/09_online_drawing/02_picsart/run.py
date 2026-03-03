#!/usr/bin/env python3
"""
02_picsart — Paint patterns on Picsart Draw via Playwright.

Picsart Draw is a free online drawing tool with brushes, layers, and colors.
This example demonstrates the 3-skill architecture:
- DrawNavigationSkill: Qwen VL canvas discovery (Picsart → fallback chain)
- DrawObjectSkill: pattern rendering with vision feedback
- DrawValidationSkill: Qwen VL validates drawn pattern

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

from _run_utils import ExampleRunner
from _verbose_helper import init_verbose, vlog, dump_page_schema

from nlp2cmd.skills.drawing import (
    DrawingSkill, DrawNavigationSkill, DrawObjectSkill,
    DrawValidationSkill, TaskPlan,
)
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
    parser.add_argument("--no-vision", action="store_true", help="Disable Qwen VL vision")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    init_verbose(args.verbose)
    use_vision = not args.no_vision

    async with ExampleRunner("02_picsart", headless=args.headless,
                              base_dir=_HERE,
                              viewport={"width": 1280, "height": 900}) as runner:
        log = runner.log
        page = runner.page

        shape_type = PATTERN_SHAPES.get(args.pattern, "spiral")

        # ── Skill 1: Navigation ──────────────────────────────────────
        log.step(1, "DrawNavigationSkill: navigating to canvas...")
        nav = DrawNavigationSkill(use_vision=use_vision)
        # Picsart requires login → will auto-fallback to kleki/jspaint
        nav_result = await nav.navigate(page, site="kleki", fallback=True,
                                        verbose=args.verbose)

        if not nav_result.success:
            log.error(f"Navigation failed: {nav_result.error}")
            return

        canvas = nav_result.canvas
        log.success(f"Canvas ready: {canvas.width:.0f}x{canvas.height:.0f} at {canvas.url}")
        if canvas.vision_confirmed:
            log.info(f"  Vision: {canvas.vision_description[:80]}")

        # ── Skill 2: Draw Object ─────────────────────────────────────
        log.step(2, f"DrawObjectSkill: drawing {args.pattern} ({shape_type}) in {args.color}...")
        skill = DrawingSkill()
        skill.init_canvas(canvas.width, canvas.height)
        renderer = PlaywrightRenderer(page)

        drawer = DrawObjectSkill(renderer=renderer, skill=skill, use_vision=use_vision)
        drawer._page = page
        obj_result = await drawer.draw(
            shape_type, color=args.color,
            cx=canvas.width / 2, cy=canvas.height / 2,
            size=min(canvas.width, canvas.height) * 0.35,
            verify=use_vision, verbose=args.verbose,
        )

        if obj_result.status.value in ("drawn", "verified"):
            log.success(f"Drawn: {shape_type} from {obj_result.source} "
                        f"({obj_result.draw_time_ms:.0f}ms)")
        else:
            log.error(f"Draw failed: {obj_result.error}")

        if args.verbose:
            await dump_page_schema(page)

        # ── Skill 3: Validation ──────────────────────────────────────
        log.step(3, "DrawValidationSkill: validating pattern...")
        plan = TaskPlan(description=f"{args.color} {args.pattern}")
        plan.add(shape_type, args.color)

        validator = DrawValidationSkill(use_vision=use_vision)
        report = await validator.validate(page, plan, verbose=args.verbose)

        log.info(f"  Validation: {report.summary()}")
        for action in report.next_actions():
            log.info(f"  → {action}")

        # ── Screenshot + Session ─────────────────────────────────────
        log.step(4, "Saving screenshot and session...")
        ss_name = f"picsart_{args.pattern}_{args.color}.png"
        await runner.screenshot(ss_name, pattern=args.pattern, color=args.color,
                                url=canvas.url)

        session_path = runner.screenshot_dir / f"picsart_{args.pattern}_{args.color}_session.json"
        skill.save_session(str(session_path))
        log.info(f"Session: {session_path} ({skill.event_count} events)")

        # Summary
        state = skill.get_state()
        log.success(f"Done! Pattern: {args.pattern}, Color: {args.color}, "
                    f"Shapes: {state['shapes_count']}, Progress: {report.summary()}")


if __name__ == "__main__":
    asyncio.run(main())
