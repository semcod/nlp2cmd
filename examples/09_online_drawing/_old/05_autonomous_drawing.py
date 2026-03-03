#!/usr/bin/env python3
"""
05_autonomous_drawing — Full autonomous drawing pipeline with all new skills.

Pipeline:
1. Parse NL description (PL/EN) → detect shapes & colors
2. For unknown shapes: fetch from Iconify/SimpleIcons/SVGRepo databases
3. If not found: generate via LLM (text-to-2DObject)
4. Compose scene & draw on jspaint.app via Playwright
5. Screenshot → validate via vision LLM
6. If issues found → correction engine fixes & re-validates

Usage:
    python 05_autonomous_drawing.py "narysuj czerwonego kota i niebieską rybkę"
    python 05_autonomous_drawing.py "draw a castle with a dragon"
    python 05_autonomous_drawing.py --fetch-only butterfly
    python 05_autonomous_drawing.py --list-shapes
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

# Ensure src/ is on path
_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_root / "src"))

from nlp2cmd.skills.drawing import (
    AutonomousDrawingPipeline,
    CorrectionEngine,
    DrawingSkill,
    ObjectFetcher,
    ShapeRegistry,
    TextToShapeEngine,
    VisualValidator,
)
from nlp2cmd.skills.drawing.renderers.playwright import PlaywrightRenderer


# ── Shape Resolution (DB → LLM fallback) ────────────────────────────────

async def resolve_shapes(description: str, verbose: bool = False) -> list[str]:
    """
    Resolve shape names from description.
    For unknown shapes, try online databases then LLM generation.
    """
    skill = DrawingSkill()
    parser = skill._parser

    # Detect shapes from NL
    shapes = parser._extract_shapes(description.lower())
    if not shapes:
        shapes = ["circle"]  # default

    registered = set(ShapeRegistry.available())
    resolved: list[str] = []

    fetcher = ObjectFetcher()
    engine = TextToShapeEngine(auto_register=True)

    for shape in shapes:
        if shape in registered:
            resolved.append(shape)
            if verbose:
                print(f"  ✓ '{shape}' — built-in shape")
            continue

        # Try online databases
        if verbose:
            print(f"  🌐 '{shape}' not built-in, searching databases...")
        fetched = await fetcher.fetch(shape, verbose=verbose)
        if fetched and fetched.points:
            from nlp2cmd.skills.drawing.text_to_shape import DynamicShapeGenerator
            gen = DynamicShapeGenerator(shape, fetched.points)
            ShapeRegistry.register(gen)
            resolved.append(shape)
            if verbose:
                print(f"  ✓ '{shape}' — fetched from {fetched.source}")
            continue

        # Try LLM generation
        if verbose:
            print(f"  🤖 '{shape}' not in databases, generating via LLM...")
        generated = await engine.generate(shape, complex_mode=True, verbose=verbose)
        if generated and generated.points:
            resolved.append(shape)
            if verbose:
                print(f"  ✓ '{shape}' — generated via LLM ({generated.model_used})")
            continue

        if verbose:
            print(f"  ⚠ '{shape}' — could not resolve, using circle fallback")
        resolved.append("circle")

    return resolved


# ── Main Pipeline ────────────────────────────────────────────────────────

async def run_autonomous(description: str, headless: bool = False,
                         max_corrections: int = 3, verbose: bool = True) -> dict:
    """Run the full autonomous drawing pipeline."""
    t0 = time.time()
    screenshot_dir = Path(__file__).parent / "screenshots"
    screenshot_dir.mkdir(exist_ok=True)

    print(f"🎨 Autonomous Drawing Pipeline")
    print(f"   Description: {description}")
    print(f"   Max corrections: {max_corrections}")
    print()

    # Step 1: Resolve shapes
    print("📦 Step 1: Resolving shapes...")
    resolved = await resolve_shapes(description, verbose=verbose)
    print(f"   Shapes: {resolved}")
    print()

    # Step 2: Build drawing
    print("✏️  Step 2: Building drawing commands...")
    skill = DrawingSkill()
    skill.init_canvas(1024, 768)
    events = skill.execute_nl(description)
    shape_events = [e for e in events if hasattr(e, 'shape_type')]
    print(f"   Generated {len(shape_events)} shapes")
    for e in shape_events:
        print(f"     • {e.shape_type} ({e.color})")
    print()

    # Step 3: Render on browser canvas
    print("🌐 Step 3: Rendering on jspaint.app...")
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("   ⚠ Playwright not installed. Install with: pip install playwright && playwright install")
        print("   Showing shape data instead:")
        for s in skill.get_shapes():
            n_pts = sum(len(g) for g in s["points"])
            print(f"     {s['shape_type']}: {n_pts} vertices, color={s['color']}")
        return {"success": False, "reason": "playwright_not_installed"}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})
        renderer = PlaywrightRenderer(page)

        # Draw
        canvas_info = await skill.render(renderer, url="https://jspaint.app", app="jspaint")
        print(f"   Canvas: {canvas_info.get('width', '?')}x{canvas_info.get('height', '?')}")
        await page.wait_for_timeout(1000)

        # Screenshot
        initial_path = str(screenshot_dir / "autonomous_initial.png")
        await renderer.screenshot(initial_path)
        print(f"   Screenshot: {initial_path}")
        print()

        # Step 4: Validate
        print("🔍 Step 4: Visual validation...")
        validator = VisualValidator()
        validation = await validator.validate(
            screenshot_path=initial_path,
            description=description,
            verbose=verbose,
        )
        print()

        # Step 5: Correct if needed
        result = {
            "description": description,
            "shapes": [e.shape_type for e in shape_events],
            "initial_verdict": validation.verdict.value,
            "initial_confidence": validation.confidence,
        }

        if validation.needs_correction and max_corrections > 0:
            print(f"🔧 Step 5: Applying corrections ({len(validation.corrections)} issues)...")
            correction_engine = CorrectionEngine(skill, renderer, validator)
            correction_result = await correction_engine.correct(
                validation_result=validation,
                description=description,
                screenshot_dir=str(screenshot_dir),
                max_iterations=max_corrections,
                verbose=verbose,
            )
            result["final_verdict"] = correction_result.final_verdict.value
            result["corrections_applied"] = correction_result.corrections_applied
            result["correction_iterations"] = correction_result.iterations
            result["success"] = correction_result.success
        else:
            result["final_verdict"] = validation.verdict.value
            result["success"] = (validation.verdict.value == "correct")

        # Final screenshot
        final_path = str(screenshot_dir / "autonomous_final.png")
        await renderer.screenshot(final_path)
        result["screenshots"] = {
            "initial": initial_path,
            "final": final_path,
        }

        elapsed = (time.time() - t0) * 1000
        result["total_time_ms"] = elapsed

        print()
        icons = {"correct": "✅", "partial": "⚠️", "wrong": "❌", "empty": "🔲", "error": "💥"}
        icon = icons.get(result["final_verdict"], "?")
        print(f"{icon} Final: {result['final_verdict']} ({elapsed:.0f}ms)")
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
        description="Autonomous drawing with database fetch + LLM + visual validation",
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
    parser.add_argument("--max-corrections", type=int, default=3,
                        help="Max correction iterations (default: 3)")
    parser.add_argument("--no-validate", action="store_true",
                        help="Skip visual validation")

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
        print('  python 05_autonomous_drawing.py "narysuj czerwonego kota"')
        print('  python 05_autonomous_drawing.py "draw a blue butterfly and red star"')
        print('  python 05_autonomous_drawing.py --fetch-only dragon')
        print('  python 05_autonomous_drawing.py --list-shapes')
        return

    max_corrections = 0 if args.no_validate else args.max_corrections
    asyncio.run(run_autonomous(
        args.description,
        headless=args.headless,
        max_corrections=max_corrections,
    ))


if __name__ == "__main__":
    main()
