#!/usr/bin/env python3
"""
07_shape_gallery — Generate and display all 33+ built-in shapes.

Demonstrates the full shape library by:
1. Listing all registered shapes with metadata
2. Drawing each shape to SVG for preview
3. Optionally drawing all shapes on jspaint.app in a grid layout
4. Generating a gallery HTML page for offline viewing

Usage:
    python3 run.py                          # List all shapes
    python3 run.py --draw                   # Draw all shapes on jspaint.app
    python3 run.py --svg                    # Generate SVG previews
    python3 run.py --html                   # Generate HTML gallery
    python3 run.py --category complex       # Filter by category
    python3 run.py --shape car --shape cat  # Draw specific shapes
"""

from __future__ import annotations

import argparse
import asyncio
import math
import sys
from pathlib import Path

# Setup import paths
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))           # 09_online_drawing/
sys.path.insert(0, str(_HERE.parents[1]))        # examples/
sys.path.insert(0, str(_HERE.parents[2] / "src"))  # src/

# Ensure output dirs exist
(_HERE / "logs").mkdir(exist_ok=True)
(_HERE / "screenshots").mkdir(exist_ok=True)
(_HERE / "gallery").mkdir(exist_ok=True)

from nlp2cmd.skills.drawing import (
    DrawingSkill, ShapeRegistry, ObjectFetcher,
    DrawNavigationSkill, DrawObjectSkill, DrawValidationSkill, TaskPlan,
)
from nlp2cmd.skills.drawing.renderers.playwright import PlaywrightRenderer


# Shape categories for organized display
SHAPE_CATEGORIES = {
    "basic": ["circle", "ellipse", "rectangle", "square", "triangle", "line", "dot"],
    "geometric": ["pentagon", "hexagon", "octagon", "diamond", "cross", "crescent"],
    "nature": ["flower", "sun", "tree", "mountain", "cloud_detailed", "wave"],
    "animals": ["bird", "butterfly", "cat", "fish"],
    "objects": ["house", "car", "boat", "rocket", "castle", "arrow"],
    "decorative": ["star", "heart", "spiral", "grid"],
}


# Vision analysis → shape mapping
VISION_SHAPE_MAP = {
    "circle": ["circle", "dot", "sun"],
    "triangle": ["triangle", "mountain"],
    "square": ["square", "rectangle", "house"],
    "star": ["star"],
    "heart": ["heart"],
    "arrow": ["arrow"],
    "car": ["car", "boat"],
    "cat": ["cat", "fish", "bird"],
    "flower": ["flower", "tree"],
    "rocket": ["rocket"],
    "spiral": ["spiral"],
    "wave": ["wave"],
    "grid": ["grid"],
    "cross": ["cross"],
    "diamond": ["diamond"],
    "castle": ["castle"],
    "boat": ["boat", "ship"],
    "butterfly": ["butterfly"],
}


def map_vision_to_shapes(vision_description: str) -> list[str]:
    """Map vision analysis output to known shapes."""
    description_lower = vision_description.lower()
    matched = set()

    for keyword, shapes in VISION_SHAPE_MAP.items():
        if keyword in description_lower:
            matched.update(shapes)

    available = set(ShapeRegistry.available())
    result = [s for s in matched if s in available]

    # Fallback: if nothing matched, return some default shapes
    if not result:
        return ["circle", "triangle", "square", "star"]

    return result


def list_shapes(category: str | None = None):
    """List all registered shapes organized by category."""
    all_shapes = set(ShapeRegistry.available())

    print(f"🎨 Shape Gallery — {len(all_shapes)} registered shapes")
    print(f"{'='*60}")

    if category:
        cats = {category: SHAPE_CATEGORIES.get(category, [])}
        if not cats[category]:
            print(f"   Unknown category: {category}")
            print(f"   Available: {', '.join(SHAPE_CATEGORIES.keys())}")
            return
    else:
        cats = SHAPE_CATEGORIES

    shown = set()
    for cat_name, shapes in cats.items():
        available = [s for s in shapes if s in all_shapes]
        if not available:
            continue
        print(f"\n📁 {cat_name.upper()} ({len(available)} shapes)")
        for shape in available:
            gen = ShapeRegistry.get(shape)
            pts = gen.generate(0, 0, 50)
            n_groups = len(pts)
            n_points = sum(len(g) for g in pts)
            print(f"   • {shape:<18} {n_groups} groups, {n_points:>3} vertices")
            shown.add(shape)

    # Show uncategorized
    uncategorized = all_shapes - shown
    if uncategorized:
        print(f"\n📁 OTHER ({len(uncategorized)} shapes)")
        for shape in sorted(uncategorized):
            gen = ShapeRegistry.get(shape)
            pts = gen.generate(0, 0, 50)
            n_groups = len(pts)
            n_points = sum(len(g) for g in pts)
            print(f"   • {shape:<18} {n_groups} groups, {n_points:>3} vertices")

    # Fetchable objects
    known = ObjectFetcher.known_objects()
    only_fetchable = sorted(set(known) - all_shapes)
    if only_fetchable:
        print(f"\n🌐 ONLINE ONLY ({len(only_fetchable)} — require fetch)")
        for name in only_fetchable[:10]:
            print(f"   • {name}")
        if len(only_fetchable) > 10:
            print(f"   ... and {len(only_fetchable) - 10} more")

    print(f"\n{'='*60}")
    print(f"Total: {len(all_shapes)} built-in + {len(only_fetchable)} fetchable")


def generate_svg(shape_name: str, size: int = 200) -> str:
    """Generate SVG string for a single shape."""
    gen = ShapeRegistry.get(shape_name)
    groups = gen.generate(size / 2, size / 2, size * 0.35)

    paths = []
    for group in groups:
        if len(group) < 2:
            continue
        d = f"M {group[0][0]:.1f} {group[0][1]:.1f}"
        for x, y in group[1:]:
            d += f" L {x:.1f} {y:.1f}"
        paths.append(f'    <path d="{d}" stroke="#333" stroke-width="2" fill="none"/>')

    return f"""<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{size}" height="{size}" fill="#fafafa" stroke="#ddd"/>
{chr(10).join(paths)}
  <text x="{size//2}" y="{size-8}" text-anchor="middle" font-size="12" fill="#666">{shape_name}</text>
</svg>"""


def generate_svg_files(shapes: list[str] | None = None):
    """Generate individual SVG files for each shape."""
    gallery_dir = _HERE / "gallery"
    all_shapes = shapes or ShapeRegistry.available()

    print(f"🖼️ Generating SVG previews for {len(all_shapes)} shapes...")
    for shape in all_shapes:
        svg = generate_svg(shape)
        path = gallery_dir / f"{shape}.svg"
        path.write_text(svg)
        print(f"   ✓ {path}")

    print(f"\n   SVGs saved to: {gallery_dir}")


def generate_html_gallery(shapes: list[str] | None = None):
    """Generate HTML gallery page with all shapes."""
    all_shapes = shapes or ShapeRegistry.available()

    svgs = []
    for shape in all_shapes:
        svg = generate_svg(shape, size=150)
        svgs.append(f'<div class="shape-card">{svg}</div>')

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>nlp2cmd Shape Gallery — {len(all_shapes)} Shapes</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
               max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
        h1 {{ text-align: center; color: #333; }}
        .subtitle {{ text-align: center; color: #666; margin-bottom: 30px; }}
        .gallery {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
                    gap: 16px; }}
        .shape-card {{ background: white; border-radius: 8px; padding: 8px;
                      box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center;
                      transition: transform 0.2s; }}
        .shape-card:hover {{ transform: scale(1.05); box-shadow: 0 4px 8px rgba(0,0,0,0.15); }}
        .categories {{ display: flex; flex-wrap: wrap; gap: 8px; justify-content: center;
                      margin-bottom: 20px; }}
        .cat-badge {{ background: #e3f2fd; color: #1565c0; padding: 4px 12px;
                     border-radius: 16px; font-size: 13px; }}
        footer {{ text-align: center; color: #999; margin-top: 30px; font-size: 13px; }}
    </style>
</head>
<body>
    <h1>🎨 nlp2cmd Shape Gallery</h1>
    <p class="subtitle">{len(all_shapes)} built-in shapes • Polish & English NL support</p>
    <div class="categories">
        {"".join(f'<span class="cat-badge">{cat}: {len(shapes)}</span>' for cat, shapes in SHAPE_CATEGORIES.items())}
    </div>
    <div class="gallery">
        {"".join(svgs)}
    </div>
    <footer>Generated by nlp2cmd shape gallery • {len(all_shapes)} shapes registered</footer>
</body>
</html>"""

    path = _HERE / "gallery" / "index.html"
    path.write_text(html)
    print(f"🌐 HTML gallery: {path}")
    print(f"   Open in browser: file://{path}")


async def analyze_image_and_draw(image_path: str, headless: bool = False):
    """Analyze image with Qwen VL via DrawValidationSkill and draw matching shapes."""
    from pathlib import Path

    if not Path(image_path).exists():
        print(f"   ⚠ Image not found: {image_path}")
        return

    print(f"🔍 Analyzing image with DrawValidationSkill: {image_path}")

    # Use DrawValidationSkill to analyze the image
    plan = TaskPlan(description="identify all shapes in the image")
    # Add common shapes so the validator checks for them
    for shape in ["circle", "triangle", "square", "star", "heart", "arrow"]:
        plan.add(shape)

    validator = DrawValidationSkill(use_vision=True)
    report = await validator.validate_screenshot(image_path, plan, verbose=True)

    if report.scene_description:
        print(f"\n📝 Qwen VL Analysis:")
        print(f"   {report.scene_description[:200]}")

    # Map found objects to shapes
    found = [a.name for a in report.done]
    shapes = map_vision_to_shapes(report.scene_description or "")
    if found:
        shapes = list(set(shapes + found))
    print(f"\n🎯 Mapped to shapes: {shapes}")

    # Draw the matched shapes
    await draw_on_canvas(shapes, headless=headless, title=f"Vision: {report.scene_description[:50] if report.scene_description else 'analysis'}")


async def draw_on_canvas(shapes: list[str] | None = None, headless: bool = False, title: str = "Shape Gallery"):
    """Draw shapes in a grid on jspaint.app using 3-skill architecture."""
    all_shapes = shapes or ShapeRegistry.available()

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("   ⚠ Playwright not installed")
        return

    colors = ["#FF0000", "#0000FF", "#228B22", "#FF8C00", "#8B008B", "#DC143C",
              "#4169E1", "#2E8B57", "#FF4500", "#6A5ACD", "#D2691E", "#008B8B"]

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})

        # ── Skill 1: Navigation ──────────────────────────────────────
        nav = DrawNavigationSkill(use_vision=False)
        nav_result = await nav.navigate(page, site="jspaint", fallback=True)
        if not nav_result.success:
            print(f"   ❌ Navigation failed: {nav_result.error}")
            await browser.close()
            return

        canvas = nav_result.canvas
        print(f"🎨 Drawing {len(all_shapes)} shapes on {canvas.width:.0f}x{canvas.height:.0f} canvas...")
        print(f"   Title: {title}")

        # ── Skill 2: Draw scene ──────────────────────────────────────
        skill = DrawingSkill()
        skill.init_canvas(canvas.width, canvas.height)
        renderer = PlaywrightRenderer(page)

        drawer = DrawObjectSkill(renderer=renderer, skill=skill, use_vision=False)
        drawer._page = page
        objects = [(name, colors[i % len(colors)]) for i, name in enumerate(all_shapes)]

        scene = await drawer.draw_scene(
            objects,
            canvas_width=canvas.width, canvas_height=canvas.height,
            verify_each=False, verbose=False,
        )

        print(f"   Result: {scene.objects_drawn}/{len(all_shapes)} drawn, "
              f"{scene.objects_failed} failed ({scene.total_time_ms:.0f}ms)")

        # Screenshot + wait — wrapped in try/except because drawing
        # many shapes can cause the page to crash (TargetClosedError)
        try:
            await page.wait_for_timeout(1000)
            path = str(_HERE / "screenshots" / "shape_gallery.png")
            await renderer.screenshot(path)
            print(f"   Screenshot: {path}")
        except Exception as e:
            print(f"   ⚠ Post-draw error (page may have crashed): {e}")

        if not headless:
            print("   Browser open. Press Ctrl+C to close.")
            try:
                await asyncio.sleep(30)
            except (KeyboardInterrupt, asyncio.CancelledError, Exception):
                pass

        await browser.close()


def main():
    parser = argparse.ArgumentParser(description="Shape gallery — list, preview, and draw all shapes")
    parser.add_argument("--draw", action="store_true", help="Draw all shapes on jspaint.app")
    parser.add_argument("--svg", action="store_true", help="Generate SVG preview files")
    parser.add_argument("--html", action="store_true", help="Generate HTML gallery page")
    parser.add_argument("--category", default=None,
                        help=f"Filter by category: {', '.join(SHAPE_CATEGORIES.keys())}")
    parser.add_argument("--shape", action="append", default=None,
                        help="Specific shapes to include (can repeat)")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--analyze-image", default=None, metavar="PATH",
                        help="Analyze image with Qwen VL and draw matching shapes")
    args = parser.parse_args()

    shapes = args.shape  # None = all

    if args.analyze_image:
        asyncio.run(analyze_image_and_draw(args.analyze_image, headless=args.headless))
        return

    if args.svg:
        generate_svg_files(shapes)
        return

    if args.html:
        generate_html_gallery(shapes)
        return

    if args.draw:
        asyncio.run(draw_on_canvas(shapes, headless=args.headless))
        return

    # Default: list all shapes
    list_shapes(category=args.category)


if __name__ == "__main__":
    main()
