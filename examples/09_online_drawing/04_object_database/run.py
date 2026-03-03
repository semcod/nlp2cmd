#!/usr/bin/env python3
"""
04_object_database — Multi-object scene drawing with 3-skill architecture.

Demonstrates drawing multiple objects from various sources:
- DrawNavigationSkill: navigate to jspaint.app
- DrawObjectSkill: resolve each object (registry→Iconify/SVGRepo→LLM) + render
- DrawValidationSkill: validate the complete scene

Shape resolution cascade:
  33 built-in → 44 Iconify/SVGRepo mapped → LLM text-to-2DObject

Usage:
    python3 run.py
    python3 run.py --objects "car, tree, house, cloud" --headless
    python3 run.py --scene "forest with trees, birds, sun"
    python3 run.py --show-database
"""

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
    Gemini3ProShapeGenerator,  # LLM fallback
)
from nlp2cmd.skills.drawing.renderers.playwright import PlaywrightRenderer


# Default colors for common objects
OBJECT_COLORS = {
    "tree": "#228B22", "house": "#8B4513", "car": "#DC143C",
    "cloud": "#87CEEB", "sun": "#FFD700", "star": "#FFD700",
    "heart": "#FF69B4", "bird": "#4169E1", "flower": "#FF1493",
    "mountain": "#696969", "boat": "#4682B4", "fish": "#FF6347",
    "cat": "#333333", "butterfly": "#9932CC", "rocket": "#FF4500",
    "castle": "#A0522D", "diamond": "#00CED1", "arrow": "#2F4F4F",
    "submarine": "#DC143C",  # Red submarine
}


def parse_objects_from_scene(scene: str) -> list[str]:
    """Parse object names from a scene description."""
    parts = scene.replace(" with ", ",").replace(" and ", ",").replace(";", ",")
    names = [p.strip().lower() for p in parts.split(",") if p.strip()]
    # Filter out non-shape words
    stop_words = {"a", "the", "in", "on", "forest", "garden", "scene", "picture"}
    return [n for n in names if n not in stop_words and len(n) > 1]


async def run_scene(objects: list[tuple[str, str]], headless: bool = False,
                    use_vision: bool = True, verbose: bool = True) -> dict:
    """Draw a multi-object scene using the 3-skill architecture."""
    t0 = time.time()
    screenshot_dir = _HERE / "screenshots"

    print(f"🎨 Multi-Object Scene Drawing (3-skill architecture)")
    print(f"   Objects: {', '.join(name for name, _ in objects)}")
    print(f"   Vision: {'enabled' if use_vision else 'disabled'}")
    print()

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("   ⚠ Playwright not installed")
        return {"success": False, "reason": "playwright_not_installed"}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})

        # ── Skill 1: Navigation ──────────────────────────────────────
        print("🌐 Skill 1: DrawNavigationSkill...")
        nav = DrawNavigationSkill(use_vision=use_vision)
        nav_result = await nav.navigate(page, site="jspaint", fallback=True,
                                        verbose=verbose)

        if not nav_result.success:
            print(f"   ❌ Navigation failed: {nav_result.error}")
            await browser.close()
            return {"success": False, "reason": "navigation_failed"}

        canvas = nav_result.canvas
        print(f"   ✅ Canvas: {canvas.width:.0f}x{canvas.height:.0f}")
        print()

        # ── Skill 2: Draw Scene ──────────────────────────────────────
        print(f"✏️  Skill 2: DrawObjectSkill — drawing {len(objects)} objects...")
        skill = DrawingSkill()
        skill.init_canvas(canvas.width, canvas.height)
        renderer = PlaywrightRenderer(page)

        drawer = DrawObjectSkill(renderer=renderer, skill=skill, use_vision=use_vision)
        drawer._page = page

        scene = await drawer.draw_scene(
            objects,
            canvas_width=canvas.width, canvas_height=canvas.height,
            verify_each=False, verbose=verbose,
        )

        print(f"\n   Scene result: {scene.summary()}")
        print(f"   Drawn: {scene.objects_drawn}, Failed: {scene.objects_failed}")
        for obj in scene.objects:
            icon = {"verified": "✅", "drawn": "✓", "failed": "✗"}.get(
                obj.status.value, "?"
            )
            print(f"   {icon} {obj.shape_name} — {obj.source} ({obj.draw_time_ms:.0f}ms)")
        print()

        # Screenshot
        ss_path = str(screenshot_dir / "scene.png")
        await renderer.screenshot(ss_path)

        # ── Skill 3: Validation ──────────────────────────────────────
        print("🔍 Skill 3: DrawValidationSkill...")
        plan = TaskPlan(description=", ".join(name for name, _ in objects))
        for name, color in objects:
            plan.add(name, color)

        validator = DrawValidationSkill(use_vision=use_vision)
        report = await validator.validate(page, plan, verbose=verbose)

        print(f"   {report.summary()}")
        if report.scene_description:
            print(f"   Scene: {report.scene_description[:100]}")
        for action in report.next_actions()[:5]:
            print(f"   → {action}")
        print()

        elapsed = (time.time() - t0) * 1000
        result = {
            "objects": [name for name, _ in objects],
            "drawn": scene.objects_drawn,
            "failed": scene.objects_failed,
            "progress": report.summary(),
            "total_time_ms": elapsed,
            "screenshot": ss_path,
            "success": scene.objects_drawn > 0,
        }

        icon = "✅" if scene.objects_failed == 0 else "⚠️"
        print(f"{icon} Done: {scene.objects_drawn}/{len(objects)} drawn ({elapsed:.0f}ms)")
        print(f"   Screenshot: {ss_path}")

        if not headless:
            print("\n   Browser open. Press Ctrl+C to close.")
            try:
                await asyncio.sleep(30)
            except (KeyboardInterrupt, asyncio.CancelledError):
                pass

        await browser.close()

    return result


def show_database():
    """Show all available shape sources."""
    built_in = ShapeRegistry.available()
    fetchable = ObjectFetcher.known_objects()
    only_fetch = sorted(set(fetchable) - set(built_in))

    print(f"🗄️ Shape Database Overview")
    print(f"{'='*60}")
    print(f"\n📦 Built-in shapes ({len(built_in)}):")
    for s in built_in:
        print(f"   • {s}")
    print(f"\n🌐 Online-only shapes ({len(only_fetch)}):")
    for s in only_fetch:
        print(f"   • {s}")
    print(f"\n💾 Cache: ~/.nlp2cmd/shape_cache/")
    print(f"   Sources: Iconify (200k+ icons), SimpleIcons (3000+ brands), SVGRepo")
    print(f"{'='*60}")
    print(f"Total: {len(built_in)} built-in + {len(only_fetch)} fetchable + LLM fallback")


async def main():
    parser = argparse.ArgumentParser(
        description="Multi-object scene drawing with 3-skill architecture",
    )
    parser.add_argument("--scene", default="forest with trees, house, sun, clouds",
                       help="Scene description (objects separated by commas)")
    parser.add_argument("--objects", default=None,
                       help="Specific objects to draw (comma-separated)")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--no-vision", action="store_true", help="Disable Qwen VL vision")
    parser.add_argument("--show-database", action="store_true",
                       help="Show available shape sources")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    if args.show_database:
        show_database()
        return

    if args.objects:
        object_names = [o.strip().lower() for o in args.objects.split(",") if o.strip()]
    else:
        object_names = parse_objects_from_scene(args.scene)

    # Assign colors
    objects = [
        (name, OBJECT_COLORS.get(name, "#808080"))
        for name in object_names
    ]

    print(f"   Parsed {len(objects)} objects from input")
    await run_scene(
        objects, headless=args.headless,
        use_vision=not args.no_vision, verbose=args.verbose,
    )


if __name__ == "__main__":
    asyncio.run(main())
