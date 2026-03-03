#!/usr/bin/env python3
"""
03_adaptive — LLM-guided drawing with adaptive model routing.

Demonstrates the full NLP2CMD adaptive learning pipeline with 3-skill architecture:
- DrawNavigationSkill: Qwen VL canvas discovery with target + fallback chain
- DrawObjectSkill: NL-parsed shape rendering with vision feedback
- DrawValidationSkill: Qwen VL validates result + reports what remains

Usage:
    python3 run.py --query "narysuj dom z czerwonym dachem"
    python3 run.py --query "draw a blue star"
    python3 run.py --query "namaluj kwiat z 6 płatkami" --target jspaint
    python3 run.py --query "draw a circle" --target excalidraw
"""

import argparse
import asyncio
import sys
import time
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
from nlp2cmd.skills.drawing.navigation import DRAWING_SITES

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[3] / ".env")
except ImportError:
    pass


TARGETS = list(DRAWING_SITES.keys())


async def main():
    parser = argparse.ArgumentParser(description="Adaptive LLM-guided drawing")
    parser.add_argument("--query", required=True, help="Natural language drawing command")
    parser.add_argument("--target", default="jspaint", choices=TARGETS,
                        help="Target drawing tool")
    parser.add_argument("--headless", action="store_true", help="Run headless")
    parser.add_argument("--no-vision", action="store_true", help="Disable Qwen VL vision")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    init_verbose(args.verbose)
    use_vision = not args.no_vision

    async with ExampleRunner("03_adaptive", headless=args.headless, base_dir=_HERE) as runner:
        log = runner.log
        page = runner.page

        # Step 1: NL parsing via DrawingSkill
        skill = DrawingSkill()
        shape = skill.detect_shape(args.query)
        color_hex = skill.detect_color(args.query, default="#0000FF")

        log.step(1, f"NL parsing: shape={shape}, color={color_hex}")
        log.info(f"Query: {args.query}")
        log.info(f"Target: {args.target}")

        # ── Skill 1: Navigation ──────────────────────────────────────
        log.step(2, f"DrawNavigationSkill: navigating to {args.target}...")
        nav = DrawNavigationSkill(use_vision=use_vision)
        nav_result = await nav.navigate(page, site=args.target, fallback=True,
                                        verbose=args.verbose)

        if not nav_result.success:
            log.error(f"Navigation failed: {nav_result.error}")
            return

        canvas = nav_result.canvas
        log.success(f"Canvas ready: {canvas.width:.0f}x{canvas.height:.0f} at {canvas.url}")
        if canvas.vision_confirmed:
            log.info(f"  Vision: {canvas.vision_description[:80]}")

        # ── Skill 2: Draw Object ─────────────────────────────────────
        log.step(3, f"DrawObjectSkill: drawing {shape} in {color_hex}...")
        skill.init_canvas(canvas.width, canvas.height)
        renderer = PlaywrightRenderer(page)

        drawer = DrawObjectSkill(renderer=renderer, skill=skill, use_vision=use_vision)
        drawer._page = page

        t0 = time.time()
        obj_result = await drawer.draw(
            shape, color=color_hex,
            cx=canvas.width / 2, cy=canvas.height / 2,
            size=min(canvas.width, canvas.height) * 0.3,
            verify=use_vision, verbose=args.verbose,
        )
        draw_time = (time.time() - t0) * 1000

        if obj_result.status.value in ("drawn", "verified"):
            log.success(f"Drawn: {shape} from {obj_result.source} ({draw_time:.0f}ms)")
            if obj_result.vision_confirmed:
                log.info(f"  Vision: {obj_result.vision_check[:80]}")
        else:
            log.error(f"Draw failed: {obj_result.error}")

        if args.verbose:
            await dump_page_schema(page)

        # ── Skill 3: Validation ──────────────────────────────────────
        log.step(4, "DrawValidationSkill: validating result...")
        plan = TaskPlan(description=args.query)
        plan.add(shape, color_hex)

        validator = DrawValidationSkill(use_vision=use_vision)
        report = await validator.validate(page, plan, verbose=args.verbose)

        log.info(f"  Validation: {report.summary()}")
        if report.scene_description:
            log.info(f"  Scene: {report.scene_description[:100]}")
        for action in report.next_actions():
            log.info(f"  → {action}")

        # ── Screenshot + Session ─────────────────────────────────────
        log.step(5, "Saving screenshot and session...")
        safe_target = args.target.replace(".", "_")
        ss_name = f"adaptive_{shape}_{color_hex.replace('#', '')}_{safe_target}.png"
        await runner.screenshot(ss_name,
                                shape=shape, color=color_hex,
                                target=args.target, query=args.query)

        session_path = runner.screenshot_dir / f"adaptive_{shape}_session.json"
        skill.save_session(str(session_path))
        log.info(f"Session: {session_path} ({skill.event_count} events)")

        # Summary
        state = skill.get_state()
        log.success(
            f"Done! Shape: {shape}, Color: {color_hex}, "
            f"Target: {args.target}, Shapes: {state['shapes_count']}, "
            f"Progress: {report.summary()}"
        )


if __name__ == "__main__":
    asyncio.run(main())
