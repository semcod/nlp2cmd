#!/usr/bin/env python3
"""
06_visual_validator — Validate drawings with vision LLM and display corrections.

Demonstrates the visual validation skill:
1. Draw a shape on jspaint.app via Playwright
2. Take a screenshot
3. Send to vision LLM for validation
4. Display what the model sees, match verdict, and corrections
5. Optionally apply corrections and re-validate

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
    DrawingSkill,
    ShapeRegistry,
    VisualValidator,
    ValidationVerdict,
    CorrectionEngine,
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
                            verbose: bool = True) -> dict:
    """Draw a shape, screenshot it, validate with vision LLM."""
    screenshot_dir = _HERE / "screenshots"
    t0 = time.time()

    # Step 1: Generate drawing
    print(f"✏️  Drawing: {shape} in {color}")
    skill = DrawingSkill()
    skill.init_canvas(1024, 768)
    nl_cmd = f"narysuj {color} {shape}" if color else f"narysuj {shape}"
    events = skill.execute_nl(nl_cmd)
    shape_events = [e for e in events if hasattr(e, 'shape_type')]

    if not shape_events:
        # Direct draw if NL didn't parse
        event = skill.draw(shape, color=color)
        shape_events = [event]

    print(f"   Generated {len(shape_events)} shapes")

    # Step 2: Render on canvas
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("   ⚠ Playwright not installed")
        return {"success": False, "reason": "playwright_not_installed"}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})
        renderer = PlaywrightRenderer(page)

        canvas_info = await skill.render(renderer, url="https://jspaint.app", app="jspaint")
        await page.wait_for_timeout(1500)

        # Step 3: Screenshot
        screenshot_path = str(screenshot_dir / f"validate_{shape}_{color}.png")
        await renderer.screenshot(screenshot_path)
        print(f"   Screenshot: {screenshot_path}")

        # Step 4: Validate
        print(f"\n🔍 Validating: '{description}'")
        validator = VisualValidator()
        result = await validator.validate(
            screenshot_path=screenshot_path,
            description=description,
            verbose=verbose,
        )

        # Display result
        print(f"\n{'='*60}")
        print(f"📊 Validation Report")
        print(f"{'='*60}")
        print(f"   Shape:       {shape}")
        print(f"   Color:       {color}")
        print(f"   Description: {description}")
        print(f"   Verdict:     {result.verdict.value}")
        print(f"   Confidence:  {result.confidence:.0%}")
        print(f"   Model:       {result.model_used}")
        print(f"   Time:        {result.validation_time_ms:.0f}ms")

        if result.description:
            print(f"\n   👁️ What the model sees:")
            print(f"      {result.description}")

        if result.corrections:
            print(f"\n   🔧 Corrections needed ({len(result.corrections)}):")
            for i, c in enumerate(result.corrections, 1):
                prio = ["", "🔴", "🟡", "🟢"][min(c.priority, 3)]
                print(f"      {i}. {prio} [{c.action}] {c.target}: {c.issue}")
                if c.details:
                    print(f"         Details: {c.details}")

        # Step 5: Correct if requested
        correction_result = None
        if correct and result.needs_correction:
            print(f"\n🔧 Applying corrections...")
            engine = CorrectionEngine(skill, renderer, validator)
            correction_result = await engine.correct(
                validation_result=result,
                description=description,
                screenshot_dir=str(screenshot_dir),
                max_iterations=3,
                verbose=verbose,
            )
            print(f"   Final verdict: {correction_result.final_verdict.value}")
            print(f"   Iterations: {correction_result.iterations}")

        print(f"{'='*60}")

        elapsed = (time.time() - t0) * 1000

        output = {
            "shape": shape,
            "color": color,
            "description": description,
            "verdict": result.verdict.value,
            "confidence": result.confidence,
            "model": result.model_used,
            "what_model_sees": result.description,
            "corrections": len(result.corrections),
            "screenshot": screenshot_path,
            "time_ms": elapsed,
        }

        if correction_result:
            output["correction_verdict"] = correction_result.final_verdict.value
            output["correction_iterations"] = correction_result.iterations

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


async def validate_screenshot(screenshot_path: str, description: str, verbose: bool = True):
    """Validate an existing screenshot without drawing."""
    print(f"🔍 Validating screenshot: {screenshot_path}")
    print(f"   Description: {description}")

    validator = VisualValidator()
    result = await validator.validate(
        screenshot_path=screenshot_path,
        description=description,
        verbose=verbose,
    )

    print(f"\n   Verdict: {result.verdict.value} ({result.confidence:.0%})")
    if result.description:
        print(f"   Sees: {result.description}")
    if result.corrections:
        for c in result.corrections:
            print(f"   Fix: [{c.action}] {c.target} — {c.issue}")


async def run_demo(headless: bool = False):
    """Run validation on multiple demo scenarios."""
    print("🎯 Visual Validator Demo — Testing multiple shapes")
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
            verbose=True,
        )
        results.append(result)

    # Summary
    print(f"\n{'='*60}")
    print(f"📊 Demo Summary")
    print(f"{'='*60}")
    for r in results:
        icon = {"correct": "✅", "partial": "⚠️", "wrong": "❌", "empty": "🔲", "error": "💥"}.get(r.get("verdict", ""), "?")
        print(f"   {icon} {r['description']}: {r['verdict']} ({r.get('confidence', 0):.0%})")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="Visual validation of drawings with vision LLM")
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
    parser.add_argument("-v", "--verbose", action="store_true", default=True)
    args = parser.parse_args()

    if args.demo:
        asyncio.run(run_demo(headless=args.headless))
        return

    if args.screenshot:
        desc = args.description or f"{args.color} {args.shape}"
        asyncio.run(validate_screenshot(args.screenshot, desc, verbose=args.verbose))
        return

    desc = args.description or f"{args.color} {args.shape}"
    asyncio.run(draw_and_validate(
        shape=args.shape,
        color=args.color,
        description=desc,
        headless=args.headless,
        correct=args.correct,
        verbose=args.verbose,
    ))


if __name__ == "__main__":
    main()
