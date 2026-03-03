#!/usr/bin/env python3
"""
01_draw_chat_shapes — Draw shapes on draw.chat whiteboard via Playwright.

draw.chat is a free online whiteboard that works without login.
This example demonstrates:
- Opening draw.chat in a browser
- Using drawing tools (pen, rectangle, ellipse, line)
- Setting colors
- Drawing geometric shapes
- Taking screenshots of the result

Usage:
    python3 01_draw_chat_shapes.py
    python3 01_draw_chat_shapes.py --shape star --color blue
    python3 01_draw_chat_shapes.py --shape house --color red --headless
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add parent examples directory for _verbose_helper
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from _verbose_helper import init_verbose, vlog, dump_page_schema, ensure_playwright_browsers_async, dump_selectors, vlog_decision

# draw.chat UI selectors
DRAW_CHAT_SELECTORS = {
    "canvas": "canvas",
    "pen_tool": '[data-tool="pen"], .tool-pen, [title*="Pen"], [title*="pen"]',
    "rect_tool": '[data-tool="rect"], .tool-rect, [title*="Rect"], [title*="rect"]',
    "ellipse_tool": '[data-tool="ellipse"], .tool-ellipse, [title*="Ellipse"], [title*="circle"]',
    "line_tool": '[data-tool="line"], .tool-line, [title*="Line"], [title*="line"]',
    "eraser_tool": '[data-tool="eraser"], .tool-eraser, [title*="Eraser"]',
    "color_picker": 'input[type="color"], .color-picker, [data-color]',
}

# Shape drawing plans (canvas coordinate-based)
SHAPE_PLANS = {
    "rectangle": [
        {"action": "drag", "from": (200, 200), "to": (500, 400), "desc": "Draw rectangle"},
    ],
    "circle": [
        {"action": "drag", "from": (250, 200), "to": (450, 400), "desc": "Draw circle/ellipse"},
    ],
    "triangle": [
        {"action": "line", "from": (350, 150), "to": (200, 400), "desc": "Left side"},
        {"action": "line", "from": (200, 400), "to": (500, 400), "desc": "Bottom side"},
        {"action": "line", "from": (500, 400), "to": (350, 150), "desc": "Right side"},
    ],
    "star": [
        {"action": "line", "from": (350, 100), "to": (280, 350), "desc": "Star line 1"},
        {"action": "line", "from": (280, 350), "to": (500, 200), "desc": "Star line 2"},
        {"action": "line", "from": (500, 200), "to": (200, 200), "desc": "Star line 3"},
        {"action": "line", "from": (200, 200), "to": (420, 350), "desc": "Star line 4"},
        {"action": "line", "from": (420, 350), "to": (350, 100), "desc": "Star line 5"},
    ],
    "house": [
        {"action": "drag", "from": (200, 300), "to": (500, 500), "desc": "House body"},
        {"action": "line", "from": (200, 300), "to": (350, 150), "desc": "Roof left"},
        {"action": "line", "from": (350, 150), "to": (500, 300), "desc": "Roof right"},
        {"action": "drag", "from": (310, 380), "to": (390, 500), "desc": "Door"},
        {"action": "drag", "from": (220, 340), "to": (280, 390), "desc": "Window left"},
        {"action": "drag", "from": (420, 340), "to": (480, 390), "desc": "Window right"},
    ],
}

COLOR_HEX = {
    "red": "#ff0000",
    "blue": "#0000ff",
    "green": "#00ff00",
    "black": "#000000",
    "yellow": "#ffff00",
    "orange": "#ff8800",
    "purple": "#8800ff",
    "white": "#ffffff",
    "pink": "#ff69b4",
    "cyan": "#00ffff",
}


async def draw_on_canvas(page, shape_name: str, color: str):
    """Execute a drawing plan on draw.chat canvas."""
    plan = SHAPE_PLANS.get(shape_name, SHAPE_PLANS["rectangle"])
    color_hex = COLOR_HEX.get(color, COLOR_HEX["black"])

    print(f"  Drawing: {shape_name} in {color} ({color_hex})")
    print(f"  Steps: {len(plan)}")
    vlog_decision(
        f"Selected shape plan: {shape_name}",
        f"Plan has {len(plan)} steps, color={color_hex}",
        alternatives=list(SHAPE_PLANS.keys()),
    )

    # Inspect page schema before drawing
    await dump_page_schema(page)
    await dump_selectors(page, DRAW_CHAT_SELECTORS)

    # Try to set color via color picker input
    try:
        color_input = page.locator('input[type="color"]').first
        cp_count = await color_input.count()
        vlog(f"Color picker input[type=color] count: {cp_count}")
        if cp_count > 0:
            await color_input.evaluate(f'el => el.value = "{color_hex}"')
            await color_input.dispatch_event("input")
            print(f"  Color set to {color_hex}")
            vlog_decision(f"Set color via input[type=color]", f"Found {cp_count} picker(s), set to {color_hex}")
        else:
            vlog_decision("Skip color setting", "No input[type=color] found")
    except Exception as e:
        print(f"  Could not set color picker (will use default)")
        vlog(f"Color picker error: {e}")

    # Wait for canvas to be ready
    canvas = page.locator("canvas").first
    await canvas.wait_for(state="visible", timeout=10000)
    box = await canvas.bounding_box()
    if not box:
        print("  ERROR: Canvas not found or not visible")
        vlog("Canvas bounding_box() returned None")
        return False

    cx, cy = box["x"], box["y"]
    print(f"  Canvas at ({cx:.0f}, {cy:.0f}), size {box['width']:.0f}x{box['height']:.0f}")
    vlog(f"Canvas bounding box: x={box['x']:.1f} y={box['y']:.1f} w={box['width']:.1f} h={box['height']:.1f}")

    # Execute each drawing step
    for i, step in enumerate(plan, 1):
        fx, fy = step["from"]
        tx, ty = step["to"]
        desc = step.get("desc", f"Step {i}")

        # Offset by canvas position
        abs_fx, abs_fy = cx + fx, cy + fy
        abs_tx, abs_ty = cx + tx, cy + ty

        print(f"  {i}. {desc}: ({fx},{fy}) → ({tx},{ty})")

        await page.mouse.move(abs_fx, abs_fy)
        await page.mouse.down()
        # Smooth movement with intermediate points
        steps = 10
        for s in range(1, steps + 1):
            t = s / steps
            ix = abs_fx + (abs_tx - abs_fx) * t
            iy = abs_fy + (abs_ty - abs_fy) * t
            await page.mouse.move(ix, iy)
            await page.wait_for_timeout(20)
        await page.mouse.up()
        await page.wait_for_timeout(100)

    print(f"  ✓ Drawing complete")
    return True


async def main():
    parser = argparse.ArgumentParser(description="Draw on draw.chat whiteboard")
    parser.add_argument("--shape", default="house", choices=list(SHAPE_PLANS.keys()),
                        help="Shape to draw")
    parser.add_argument("--color", default="blue", choices=list(COLOR_HEX.keys()),
                        help="Drawing color")
    parser.add_argument("--headless", action="store_true", help="Run headless")
    parser.add_argument("--screenshot-dir", default="screenshots", help="Output dir")
    parser.add_argument("--url", default="https://draw.chat/pl/index.html",
                        help="draw.chat URL")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Show page schema, selector matching, and decision logs")
    args = parser.parse_args()

    init_verbose(args.verbose)

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("ERROR: pip install playwright")
        sys.exit(1)

    # Auto-install browsers if needed
    if not await ensure_playwright_browsers_async(auto_install=True):
        sys.exit(1)

    print(f"=== draw.chat Drawing: {args.shape} in {args.color} ===")
    print(f"URL: {args.url}")
    print()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=args.headless)
        page = await browser.new_page(viewport={"width": 1024, "height": 768})

        print("1. Opening draw.chat...")
        await page.goto(args.url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)
        vlog(f"Page loaded: {page.url}")

        # Accept cookie/privacy dialog if present
        for btn_text in ["Accept", "Akceptuję", "OK", "Got it", "Close"]:
            try:
                btn = page.get_by_text(btn_text, exact=False).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    vlog(f"Dismissed dialog: clicked '{btn_text}'")
                    await page.wait_for_timeout(500)
                    break
            except Exception:
                continue

        print("2. Drawing shape...")
        success = await draw_on_canvas(page, args.shape, args.color)

        print("3. Saving screenshot...")
        screenshot_dir = Path(args.screenshot_dir)
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        path = screenshot_dir / f"draw_chat_{args.shape}_{args.color}.png"
        await page.screenshot(path=str(path))
        print(f"   Screenshot: {path}")

        await browser.close()

    print()
    print(f"Done! Shape: {args.shape}, Color: {args.color}, Success: {success}")


if __name__ == "__main__":
    asyncio.run(main())
