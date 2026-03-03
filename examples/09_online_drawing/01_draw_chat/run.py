#!/usr/bin/env python3
"""
01_draw_chat — Draw shapes on draw.chat whiteboard via Playwright.

draw.chat is a free online whiteboard that works without login.
This example demonstrates the 3-skill architecture:
- DrawNavigationSkill: Qwen VL canvas discovery, popup dismiss, tool select
- DrawObjectSkill: shape resolution + rendering with vision feedback
- DrawValidationSkill: Qwen VL validates what's drawn vs requested

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

from _run_utils import ExampleRunner, get_platform_info
from _verbose_helper import init_verbose, vlog, dump_page_schema

from nlp2cmd.skills.drawing import (
    DrawingSkill, DrawNavigationSkill, DrawObjectSkill,
    DrawValidationSkill, TaskPlan,
)
from nlp2cmd.skills.drawing.renderers.playwright import PlaywrightRenderer


async def main():
    available = DrawingSkill.available_shapes()

    parser = argparse.ArgumentParser(description="Draw on draw.chat whiteboard")
    parser.add_argument("--shape", default="house", choices=available, help="Shape to draw")
    parser.add_argument("--color", default="blue", help="Drawing color (name or hex)")
    parser.add_argument("--headless", action="store_true", help="Run headless")
    parser.add_argument("--no-vision", action="store_true", help="Disable Qwen VL vision")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    init_verbose(args.verbose)
    use_vision = not args.no_vision

    async with ExampleRunner("01_draw_chat", headless=args.headless, base_dir=_HERE) as runner:
        log = runner.log
        page = runner.page

        # ── Skill 1: Navigation ──────────────────────────────────────
        log.step(1, "DrawNavigationSkill: navigating to canvas...")
        nav = DrawNavigationSkill(use_vision=use_vision)
        nav_result = await nav.navigate(page, site="draw.chat", fallback=True,
                                        verbose=args.verbose)

        if not nav_result.success:
            log.error(f"Navigation failed: {nav_result.error}")
            return

        canvas = nav_result.canvas
        log.success(f"Canvas ready: {canvas.width:.0f}x{canvas.height:.0f} at {canvas.url}")
        if canvas.vision_confirmed:
            log.info(f"  Vision: {canvas.vision_description[:80]}")
        log.info(f"  Tool: {canvas.tool_selected}")
        for step in nav_result.steps:
            log.debug(f"  [{step.action}] {'✓' if step.success else '✗'} "
                      f"{step.detail[:60]} ({step.duration_ms:.0f}ms)")

        # ── Skill 2: Draw Object ─────────────────────────────────────
        log.step(2, f"DrawObjectSkill: drawing {args.shape} in {args.color}...")
        skill = DrawingSkill()
        skill.init_canvas(canvas.width, canvas.height)
        renderer = PlaywrightRenderer(page)

        drawer = DrawObjectSkill(renderer=renderer, skill=skill, use_vision=use_vision)
        drawer._page = page
        obj_result = await drawer.draw(
            args.shape, color=args.color,
            cx=canvas.width / 2, cy=canvas.height / 2,
            size=min(canvas.width, canvas.height) * 0.3,
            verify=use_vision, verbose=args.verbose,
        )

        if obj_result.status.value in ("drawn", "verified"):
            log.success(f"Drawn: {args.shape} from {obj_result.source} "
                        f"({obj_result.draw_time_ms:.0f}ms)")
            if obj_result.vision_confirmed:
                log.info(f"  Vision: {obj_result.vision_check[:80]}")
        else:
            log.error(f"Draw failed: {obj_result.error}")

        if args.verbose:
            await dump_page_schema(page)

        # ── Skill 3: Validation ──────────────────────────────────────
        log.step(3, "DrawValidationSkill: validating drawing...")
        plan = TaskPlan(description=f"{args.color} {args.shape}")
        plan.add(args.shape, args.color)

        validator = DrawValidationSkill(use_vision=use_vision)
        report = await validator.validate(page, plan, verbose=args.verbose)

        log.info(f"  Validation: {report.summary()}")
        for action in report.next_actions():
            log.info(f"  → {action}")

        # ── Screenshot + Session ─────────────────────────────────────
        log.step(4, "Saving screenshot and session...")
        ss_name = f"draw_chat_{args.shape}_{args.color}.png"
        await runner.screenshot(ss_name, shape=args.shape, color=args.color,
                                url=canvas.url)

        session_path = runner.screenshot_dir / f"draw_chat_{args.shape}_{args.color}_session.json"
        skill.save_session(str(session_path))
        log.info(f"Session: {session_path} ({skill.event_count} events)")

        # Summary
        state = skill.get_state()
        log.success(f"Done! Shape: {args.shape}, Color: {args.color}, "
                    f"Shapes drawn: {state['shapes_count']}, "
                    f"Progress: {report.summary()}")


if __name__ == "__main__":
    asyncio.run(main())
