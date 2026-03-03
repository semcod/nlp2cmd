#!/usr/bin/env python3
"""
02_picsart_painting — Paint on Picsart Draw via Playwright.

Picsart Draw (picsart.com/pl/draw) is a free online drawing tool with
brushes, layers, and color selection — no login required.

Demonstrates:
- Opening Picsart Draw in browser
- Selecting brush tools and colors
- Drawing patterns (spiral, grid, waves, freehand)
- Screenshot capture of the result

Usage:
    python3 02_picsart_painting.py
    python3 02_picsart_painting.py --pattern spiral --color red
    python3 02_picsart_painting.py --pattern grid --color green --headless
"""

import argparse
import asyncio
import math
import os
import sys
from pathlib import Path

# Add parent examples directory for _verbose_helper
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from _verbose_helper import init_verbose, vlog, dump_page_schema, dump_selectors, vlog_decision

COLOR_HEX = {
    "red": "#ff0000", "blue": "#0000ff", "green": "#00ff00",
    "black": "#000000", "yellow": "#ffff00", "orange": "#ff8800",
    "purple": "#8800ff", "white": "#ffffff", "pink": "#ff69b4",
    "cyan": "#00ffff",
}


def generate_spiral_points(cx, cy, radius=150, turns=3, points_per_turn=30):
    """Generate spiral path points."""
    points = []
    total = turns * points_per_turn
    for i in range(total):
        t = i / total
        r = radius * t
        angle = t * turns * 2 * math.pi
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        points.append((x, y))
    return points


def generate_grid_points(x0, y0, x1, y1, cols=5, rows=5):
    """Generate grid line segments."""
    segments = []
    dx = (x1 - x0) / cols
    dy = (y1 - y0) / rows
    # Vertical lines
    for c in range(cols + 1):
        x = x0 + c * dx
        segments.append(((x, y0), (x, y1)))
    # Horizontal lines
    for r in range(rows + 1):
        y = y0 + r * dy
        segments.append(((x0, y), (x1, y)))
    return segments


def generate_wave_points(x0, y0, width=400, amplitude=50, waves=3, points=60):
    """Generate sine wave path points."""
    pts = []
    for i in range(points):
        t = i / (points - 1)
        x = x0 + t * width
        y = y0 + amplitude * math.sin(t * waves * 2 * math.pi)
        pts.append((x, y))
    return pts


def generate_flower_points(cx, cy, radius=100, petals=6, points_per_petal=20):
    """Generate flower petal path points."""
    all_points = []
    for p in range(petals):
        petal_pts = []
        base_angle = (2 * math.pi * p) / petals
        for i in range(points_per_petal):
            t = i / (points_per_petal - 1)
            angle = base_angle + (t - 0.5) * (2 * math.pi / petals)
            r = radius * math.sin(t * math.pi)
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            petal_pts.append((x, y))
        all_points.append(petal_pts)
    return all_points


async def draw_path(page, points, canvas_box):
    """Draw a continuous path on the canvas."""
    if not points:
        return
    ox, oy = canvas_box["x"], canvas_box["y"]
    x0, y0 = points[0]
    await page.mouse.move(ox + x0, oy + y0)
    await page.mouse.down()
    for x, y in points[1:]:
        await page.mouse.move(ox + x, oy + y)
        await page.wait_for_timeout(10)
    await page.mouse.up()


async def draw_segments(page, segments, canvas_box):
    """Draw line segments on the canvas."""
    ox, oy = canvas_box["x"], canvas_box["y"]
    for (x0, y0), (x1, y1) in segments:
        await page.mouse.move(ox + x0, oy + y0)
        await page.mouse.down()
        steps = 5
        for s in range(1, steps + 1):
            t = s / steps
            await page.mouse.move(ox + x0 + (x1 - x0) * t, oy + y0 + (y1 - y0) * t)
            await page.wait_for_timeout(10)
        await page.mouse.up()
        await page.wait_for_timeout(50)


async def main():
    parser = argparse.ArgumentParser(description="Paint on Picsart Draw")
    parser.add_argument("--pattern", default="spiral",
                        choices=["spiral", "grid", "waves", "flower"],
                        help="Pattern to draw")
    parser.add_argument("--color", default="blue", choices=list(COLOR_HEX.keys()),
                        help="Drawing color")
    parser.add_argument("--headless", action="store_true", help="Run headless")
    parser.add_argument("--screenshot-dir", default="screenshots", help="Output dir")
    parser.add_argument("--url", default="https://picsart.com/pl/draw",
                        help="Picsart Draw URL")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Show page schema, selector matching, and decision logs")
    args = parser.parse_args()

    init_verbose(args.verbose)

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("ERROR: Playwright required: pip install playwright && playwright install chromium")
        sys.exit(1)

    print(f"=== Picsart Draw: {args.pattern} in {args.color} ===")
    print(f"URL: {args.url}")
    print()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=args.headless)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})

        print("1. Opening Picsart Draw...")
        await page.goto(args.url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        vlog(f"Page loaded: {page.url}")

        # Dismiss popups/cookie banners
        for selector in [
            "button:has-text('Accept')", "button:has-text('OK')",
            "button:has-text('Akceptuję')", "button:has-text('Got it')",
            "[data-testid='cookie-accept']", ".cookie-accept",
        ]:
            try:
                btn = page.locator(selector).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    vlog(f"Dismissed dialog via: {selector}")
                    await page.wait_for_timeout(500)
            except Exception:
                continue

        await page.wait_for_timeout(2000)

        # Inspect page schema
        await dump_page_schema(page)

        # Find the canvas element
        canvas = page.locator("canvas").first
        try:
            await canvas.wait_for(state="visible", timeout=10000)
            vlog("Canvas became visible")
        except Exception:
            print("  Canvas not immediately visible, waiting longer...")
            vlog("Canvas not visible after 10s, waiting 5s more")
            await page.wait_for_timeout(5000)

        box = await canvas.bounding_box()
        if not box:
            print("  WARNING: Canvas bounding box not available, using viewport center")
            vlog("Canvas bounding_box() returned None — using fallback coords")
            box = {"x": 100, "y": 100, "width": 800, "height": 600}

        print(f"  Canvas: {box['width']:.0f}x{box['height']:.0f} at ({box['x']:.0f}, {box['y']:.0f})")
        vlog(f"Canvas bbox: x={box['x']:.1f} y={box['y']:.1f} w={box['width']:.1f} h={box['height']:.1f}")

        # Try to set color
        hex_val = COLOR_HEX.get(args.color, "#000000")
        try:
            color_input = page.locator('input[type="color"]').first
            cp_count = await color_input.count()
            vlog(f"Color picker input[type=color] count: {cp_count}")
            if cp_count > 0:
                await color_input.evaluate(f'el => {{ el.value = "{hex_val}"; el.dispatchEvent(new Event("input")); }}')
                print(f"  Color: {args.color} ({hex_val})")
                vlog_decision(f"Set color to {hex_val}", "Found input[type=color]")
            else:
                vlog_decision("Skip color setting", "No input[type=color] found")
        except Exception as e:
            print(f"  Color picker not found, using default")
            vlog(f"Color picker error: {e}")

        # Generate and draw pattern
        w, h = box["width"], box["height"]
        cx, cy = w / 2, h / 2

        print(f"2. Drawing pattern: {args.pattern}...")

        if args.pattern == "spiral":
            points = generate_spiral_points(cx, cy, radius=min(w, h) * 0.35)
            await draw_path(page, points, box)
            print(f"   Drew spiral with {len(points)} points")

        elif args.pattern == "grid":
            margin = 50
            segments = generate_grid_points(margin, margin, w - margin, h - margin)
            await draw_segments(page, segments, box)
            print(f"   Drew grid with {len(segments)} lines")

        elif args.pattern == "waves":
            for i, offset_y in enumerate(range(100, int(h - 50), 80)):
                points = generate_wave_points(50, offset_y, width=w - 100)
                await draw_path(page, points, box)
            print(f"   Drew waves")

        elif args.pattern == "flower":
            petal_groups = generate_flower_points(cx, cy, radius=min(w, h) * 0.3)
            for i, petal_pts in enumerate(petal_groups):
                await draw_path(page, petal_pts, box)
            print(f"   Drew flower with {len(petal_groups)} petals")

        # Screenshot
        print("3. Saving screenshot...")
        screenshot_dir = Path(args.screenshot_dir)
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        path = screenshot_dir / f"picsart_{args.pattern}_{args.color}.png"
        await page.screenshot(path=str(path))
        print(f"   Screenshot: {path}")

        await browser.close()

    print()
    print(f"Done! Pattern: {args.pattern}, Color: {args.color}")


if __name__ == "__main__":
    asyncio.run(main())
