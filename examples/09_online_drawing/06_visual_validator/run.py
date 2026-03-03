#!/usr/bin/env python3
"""
06_visual_validator — Validate drawings with Qwen VL and display corrections.

Demonstrates the 3-skill architecture focused on validation:
- DrawNavigationSkill: navigate to jspaint.app
- DrawObjectSkill: draw the requested shape
- DrawValidationSkill: full task-aware validation (done/remaining/wrong)

Usage:
    python3 run.py --shape star --color red
    python3 run.py --shape "butterfly" --description "blue butterfly"
    python3 run.py --screenshot path/to/image.png --description "red star"
    python3 run.py --demo
"""

from __future__ import annotations

import argparse
import asyncio
import json
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
)
from nlp2cmd.skills.drawing.renderers.playwright import PlaywrightRenderer


DEMO_SCENARIOS = [
    {"shape": "star", "color": "red", "description": "red star"},
    {"shape": "cat", "color": "black", "description": "black cat"},
    {"shape": "house", "color": "brown", "description": "brown house"},
    {"shape": "rocket", "color": "blue", "description": "blue rocket"},
    {"shape": "butterfly", "color": "purple", "description": "purple butterfly"},
]


async def draw_and_validate(shape: str, color: str, description: str,
                            headless: bool = False, correct: bool = False,
                            verbose: bool = True, use_vision: bool = True) -> dict:
    """Draw a shape using 3-skill pipeline and validate with Qwen VL."""
    screenshot_dir = _HERE / "screenshots"
    t0 = time.time()

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("   ⚠ Playwright not installed")
        return {"success": False, "reason": "playwright_not_installed"}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})

        # ── Skill 1: Navigation ──────────────────────────────────────
        print(f"🌐 DrawNavigationSkill: navigating to canvas...")
        nav = DrawNavigationSkill(use_vision=use_vision)
        nav_result = await nav.navigate(page, site="jspaint", fallback=True,
                                        verbose=verbose)

        if not nav_result.success:
            print(f"   ❌ Navigation failed: {nav_result.error}")
            await browser.close()
            return {"success": False, "reason": "navigation_failed"}

        canvas = nav_result.canvas
        print(f"   ✅ Canvas: {canvas.width:.0f}x{canvas.height:.0f}")

        # ── Skill 2: Draw Object ─────────────────────────────────────
        print(f"\n✏️  DrawObjectSkill: drawing {shape} in {color}...")
        skill = DrawingSkill()
        skill.init_canvas(canvas.width, canvas.height)
        renderer = PlaywrightRenderer(page)

        drawer = DrawObjectSkill(renderer=renderer, skill=skill, use_vision=use_vision)
        drawer._page = page
        obj_result = await drawer.draw(
            shape, color=color,
            cx=canvas.width / 2, cy=canvas.height / 2,
            size=min(canvas.width, canvas.height) * 0.3,
            verify=use_vision, verbose=verbose,
        )
        print(f"   Status: {obj_result.status.value} (source: {obj_result.source})")

        # Screenshot
        screenshot_path = str(screenshot_dir / f"validate_{shape}_{color}.png")
        await renderer.screenshot(screenshot_path)

        # ── Skill 3: Validation ──────────────────────────────────────
        print(f"\n🔍 DrawValidationSkill: validating '{description}'...")
        plan = TaskPlan(description=description)
        plan.add(shape, color)

        validator = DrawValidationSkill(use_vision=use_vision)
        report = await validator.validate(page, plan, verbose=verbose)

        # Display report
        print(f"\n{'='*60}")
        print(f"📊 Validation Report")
        print(f"{'='*60}")
        print(f"   Shape:       {shape}")
        print(f"   Color:       {color}")
        print(f"   Description: {description}")
        print(f"   Progress:    {report.summary()}")
        print(f"   Match:       {report.overall_match:.0%}")
        print(f"   Time:        {report.validation_time_ms:.0f}ms")

        if report.scene_description:
            print(f"\n   👁️ What Qwen VL sees:")
            print(f"      {report.scene_description}")

        for a in report.assessments:
            icons = {"drawn": "✅", "missing": "⬜", "wrong": "❌", "partial": "⚠️"}
            icon = icons.get(a.status.value, "?")
            extra = f" — {a.issue}" if a.issue else ""
            print(f"   {icon} {a.name}: {a.status.value}{extra}")

        if report.next_actions():
            print(f"\n   📋 Suggested actions:")
            for action in report.next_actions():
                print(f"      → {action}")

        # Iterative correction if requested
        if correct and not report.all_done:
            print(f"\n🔧 Applying corrections (up to 3 iterations)...")
            for iteration in range(3):
                remaining = report.remaining
                if not remaining:
                    break

                for assessment in remaining:
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

                report = await validator.check_progress(page, plan, report, verbose=verbose)
                print(f"   Iteration {iteration + 1}: {report.summary()}")
                if report.all_done:
                    break

        print(f"{'='*60}")

        elapsed = (time.time() - t0) * 1000

        output = {
            "shape": shape,
            "color": color,
            "description": description,
            "progress": report.summary(),
            "match": report.overall_match,
            "scene_description": report.scene_description,
            "done": [a.name for a in report.done],
            "remaining": [a.name for a in report.remaining],
            "screenshot": screenshot_path,
            "time_ms": elapsed,
        }

        # Save report
        report_path = _HERE / "logs" / f"validation_{shape}_{color}.json"
        with open(report_path, "w") as f:
            json.dump(output, f, indent=2)
        print(f"\n   Report saved: {report_path}")

        if not headless:
            print("   Browser open. Press Ctrl+C to close.")
            try:
                await asyncio.sleep(15)
            except (KeyboardInterrupt, asyncio.CancelledError):
                pass

        await browser.close()

    return output


async def validate_screenshot(screenshot_path: str, description: str,
                              verbose: bool = True, use_vision: bool = True):
    """Validate an existing screenshot without drawing."""
    print(f"🔍 Validating screenshot: {screenshot_path}")
    print(f"   Description: {description}")

    plan = TaskPlan(description=description)
    # Try to detect shape from description
    plan_auto = DrawValidationSkill.plan_from_description(description)
    for obj in plan_auto.objects:
        plan.add(obj["name"], obj.get("color", ""))

    if not plan.objects:
        plan.add("shape", "")  # generic fallback

    validator = DrawValidationSkill(use_vision=use_vision)
    report = await validator.validate_screenshot(screenshot_path, plan, verbose=verbose)

    print(f"\n   Progress: {report.summary()}")
    if report.scene_description:
        print(f"   Sees: {report.scene_description}")
    for action in report.next_actions():
        print(f"   → {action}")


async def run_demo(headless: bool = False, use_vision: bool = True):
    """Run validation on multiple demo scenarios."""
    print("🎯 Visual Validator Demo — 3-skill architecture")
    print(f"   Scenarios: {len(DEMO_SCENARIOS)}")
    print()

    results = []
    for i, scenario in enumerate(DEMO_SCENARIOS, 1):
        print(f"\n{'─'*60}")
        print(f"📋 Scenario {i}/{len(DEMO_SCENARIOS)}: {scenario['description']}")
        print(f"{'─'*60}")
        result = await draw_and_validate(
            shape=scenario["shape"],
            color=scenario["color"],
            description=scenario["description"],
            headless=headless,
            use_vision=use_vision,
            verbose=True,
        )
        results.append(result)

    # Summary
    print(f"\n{'='*60}")
    print(f"📊 Demo Summary")
    print(f"{'='*60}")
    for r in results:
        done = r.get("done", [])
        remaining = r.get("remaining", [])
        icon = "✅" if not remaining else ("⚠️" if done else "❌")
        print(f"   {icon} {r['description']}: {r.get('progress', '?')}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="Visual validation with Qwen VL (3-skill architecture)")
    parser.add_argument("--shape", default="star", help="Shape to draw and validate")
    parser.add_argument("--color", default="red", help="Color of the shape")
    parser.add_argument("--description", default=None,
                        help="What the drawing should look like (default: '{color} {shape}')")
    parser.add_argument("--screenshot", default=None,
                        help="Validate existing screenshot instead of drawing")
    parser.add_argument("--correct", action="store_true",
                        help="Apply corrections if validation fails")
    parser.add_argument("--demo", action="store_true",
                        help="Run demo with multiple scenarios")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--no-vision", action="store_true", help="Disable Qwen VL")
    parser.add_argument("-v", "--verbose", action="store_true", default=True)
    args = parser.parse_args()

    use_vision = not args.no_vision

    if args.demo:
        asyncio.run(run_demo(headless=args.headless, use_vision=use_vision))
        return

    if args.screenshot:
        desc = args.description or f"{args.color} {args.shape}"
        asyncio.run(validate_screenshot(args.screenshot, desc, verbose=args.verbose,
                                        use_vision=use_vision))
        return

    desc = args.description or f"{args.color} {args.shape}"
    asyncio.run(draw_and_validate(
        shape=args.shape,
        color=args.color,
        description=desc,
        headless=args.headless,
        correct=args.correct,
        verbose=args.verbose,
        use_vision=use_vision,
    ))


if __name__ == "__main__":
    main()
