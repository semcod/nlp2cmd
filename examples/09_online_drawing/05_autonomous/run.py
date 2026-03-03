#!/usr/bin/env python3
"""
05_autonomous — Full autonomous drawing pipeline with 3-skill architecture.

Pipeline:
1. DrawNavigationSkill → navigate to jspaint.app (Qwen VL canvas verify)
2. DrawObjectSkill → resolve shapes (registry→DB→LLM) + render with vision
3. DrawValidationSkill → validate what's drawn, report remaining, suggest fixes
4. Loop: re-draw missing objects until all done or max iterations reached

Usage:
    python3 run.py "narysuj czerwonego kota i niebieską rybkę"
    python3 run.py "draw a castle with a dragon"
    python3 run.py --fetch-only butterfly
    python3 run.py --list-shapes
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

# Setup import paths
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))           # 09_online_drawing/
sys.path.insert(0, str(_HERE.parents[1]))        # examples/
sys.path.insert(0, str(_HERE.parents[2] / "src"))  # src/

# Ensure output dirs exist
(_HERE / "logs").mkdir(exist_ok=True)
(_HERE / "screenshots").mkdir(exist_ok=True)

from nlp2cmd.skills.drawing import (
    DrawingSkill, DrawNavigationSkill, DrawObjectSkill,
    DrawValidationSkill, TaskPlan,
    ObjectFetcher, ShapeRegistry,
)
from nlp2cmd.skills.drawing.renderers.playwright import PlaywrightRenderer


# ── Main Pipeline ────────────────────────────────────────────────────────

async def run_autonomous(description: str, headless: bool = False,
                         max_iterations: int = 3, verbose: bool = True,
                         use_vision: bool = True) -> dict:
    """Run the full autonomous drawing pipeline using 3 skills."""
    t0 = time.time()
    screenshot_dir = _HERE / "screenshots"

    print(f"🎨 Autonomous Drawing Pipeline (3-skill architecture)")
    print(f"   Description: {description}")
    print(f"   Max iterations: {max_iterations}")
    print(f"   Vision: {'enabled' if use_vision else 'disabled'}")
    print()

    # Parse NL to detect shapes and colors
    skill = DrawingSkill()
    shape = skill.detect_shape(description)
    color = skill.detect_color(description, default="#000000")

    # Build task plan
    plan = TaskPlan(description=description)
    plan.add(shape, color)
    print(f"   Plan: {', '.join(plan.object_names)} — from NL: \"{description}\"")
    print()

    # ── Skill 1: Navigation ──────────────────────────────────────────
    print("🌐 Skill 1: DrawNavigationSkill...")
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("   ⚠ Playwright not installed. Install: pip install playwright && playwright install")
        return {"success": False, "reason": "playwright_not_installed"}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})

        nav = DrawNavigationSkill(use_vision=use_vision)
        nav_result = await nav.navigate(page, site="jspaint", fallback=True,
                                        verbose=verbose)

        if not nav_result.success:
            print(f"   ❌ Navigation failed: {nav_result.error}")
            await browser.close()
            return {"success": False, "reason": "navigation_failed"}

        canvas = nav_result.canvas
        print(f"   ✅ Canvas: {canvas.width:.0f}x{canvas.height:.0f} at {canvas.url}")
        if canvas.vision_confirmed:
            print(f"   👁️ Vision: {canvas.vision_description[:80]}")
        print()

        # ── Skill 2: Draw Objects ────────────────────────────────────
        print("✏️  Skill 2: DrawObjectSkill...")
        skill.init_canvas(canvas.width, canvas.height)
        renderer = PlaywrightRenderer(page)

        drawer = DrawObjectSkill(renderer=renderer, skill=skill, use_vision=use_vision)
        drawer._page = page

        scene = await drawer.draw_scene(
            [(obj["name"], obj.get("color", "#000000")) for obj in plan.objects],
            canvas_width=canvas.width, canvas_height=canvas.height,
            verify_each=use_vision, verbose=verbose,
        )

        print(f"   {scene.summary()}")
        print()

        # Initial screenshot
        initial_path = str(screenshot_dir / "autonomous_initial.png")
        await renderer.screenshot(initial_path)

        # ── Skill 3: Validation + Iterative Fix Loop ────────────────
        print("🔍 Skill 3: DrawValidationSkill...")
        validator = DrawValidationSkill(use_vision=use_vision)
        report = await validator.validate(page, plan, verbose=verbose)

        print(f"   {report.summary()}")
        print()

        iteration = 0
        while not report.all_done and iteration < max_iterations:
            iteration += 1
            remaining = report.next_actions()
            if not remaining:
                break

            print(f"🔄 Iteration {iteration}: fixing {len(remaining)} issues...")
            for action in remaining[:3]:
                print(f"   → {action}")

            # Re-draw missing objects
            for assessment in report.remaining:
                plan_obj = next(
                    (o for o in plan.objects if o["name"] == assessment.name), None
                )
                obj_color = plan_obj.get("color", "#000000") if plan_obj else "#000000"
                await drawer.draw(
                    assessment.name, color=obj_color,
                    cx=canvas.width / 2, cy=canvas.height / 2,
                    size=min(canvas.width, canvas.height) * 0.25,
                    verify=False, verbose=verbose,
                )

            # Re-validate
            report = await validator.check_progress(page, plan, report, verbose=verbose)
            print(f"   After iteration {iteration}: {report.summary()}")
            print()

        # Final screenshot
        final_path = str(screenshot_dir / "autonomous_final.png")
        await renderer.screenshot(final_path)

        elapsed = (time.time() - t0) * 1000
        result = {
            "description": description,
            "shapes": plan.object_names,
            "progress": report.summary(),
            "all_done": report.all_done,
            "iterations": iteration,
            "total_time_ms": elapsed,
            "screenshots": {"initial": initial_path, "final": final_path},
            "success": report.progress_pct > 0,
        }

        icon = "✅" if report.all_done else ("⚠️" if report.progress_pct > 0 else "❌")
        print(f"{icon} Final: {report.summary()} ({elapsed:.0f}ms)")
        print(f"   Screenshots: {screenshot_dir}")

        if not headless:
            print("\n   Browser open for inspection. Press Ctrl+C to close.")
            try:
                await asyncio.sleep(30)
            except (KeyboardInterrupt, asyncio.CancelledError):
                pass

        await browser.close()

    return result


# ── Fetch-only mode ──────────────────────────────────────────────────────

async def fetch_only(shape_name: str):
    """Just fetch a shape from databases and display info."""
    fetcher = ObjectFetcher()
    print(f"🌐 Fetching '{shape_name}' from online databases...")
    shape = await fetcher.fetch(shape_name, verbose=True)
    if shape:
        n_pts = sum(len(g) for g in shape.points)
        print(f"\n✅ Found '{shape.name}' from {shape.source}")
        print(f"   Groups: {len(shape.points)}, Vertices: {n_pts}")
        print(f"   Fetch time: {shape.fetch_time_ms:.0f}ms")
        if shape.svg_path:
            print(f"   SVG path: {shape.svg_path[:80]}...")
        if shape.metadata:
            print(f"   Metadata: {shape.metadata}")
    else:
        print(f"\n❌ '{shape_name}' not found in any database")


# ── CLI ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Autonomous drawing with 3-skill architecture + Qwen VL",
    )
    parser.add_argument("description", nargs="?", default="",
                        help="Drawing description (PL or EN)")
    parser.add_argument("--fetch-only", metavar="SHAPE",
                        help="Just fetch a shape from databases")
    parser.add_argument("--list-shapes", action="store_true",
                        help="List all available built-in shapes")
    parser.add_argument("--list-fetchable", action="store_true",
                        help="List objects with known database mappings")
    parser.add_argument("--headless", action="store_true",
                        help="Run browser in headless mode")
    parser.add_argument("--max-iterations", type=int, default=3,
                        help="Max draw→validate→fix iterations (default: 3)")
    parser.add_argument("--no-vision", action="store_true",
                        help="Disable Qwen VL vision")

    args = parser.parse_args()

    if args.list_shapes:
        shapes = ShapeRegistry.available()
        print(f"Built-in shapes ({len(shapes)}):")
        for s in shapes:
            print(f"  • {s}")
        return

    if args.list_fetchable:
        known = ObjectFetcher.known_objects()
        print(f"Fetchable objects ({len(known)}):")
        for name in known:
            print(f"  • {name}")
        return

    if args.fetch_only:
        asyncio.run(fetch_only(args.fetch_only))
        return

    if not args.description:
        parser.print_help()
        print("\nExamples:")
        print('  python3 run.py "narysuj czerwonego kota"')
        print('  python3 run.py "draw a blue butterfly and red star"')
        print('  python3 run.py --fetch-only dragon')
        print('  python3 run.py --list-shapes')
        return

    asyncio.run(run_autonomous(
        args.description,
        headless=args.headless,
        max_iterations=args.max_iterations,
        use_vision=not args.no_vision,
    ))


if __name__ == "__main__":
    main()
