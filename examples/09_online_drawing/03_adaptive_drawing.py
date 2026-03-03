#!/usr/bin/env python3
"""
03_adaptive_drawing — LLM-guided drawing with adaptive model routing.

Demonstrates the full NLP2CMD adaptive learning pipeline:
1. Takes a natural language drawing command (PL or EN)
2. Routes to LLM for drawing plan generation (remote → local fallback)
3. Learns from failures (credit exhaustion, timeouts) and adapts
4. Executes the plan on draw.chat or jspaint.app via Playwright
5. Verifies result with vision model (if available)

Usage:
    python3 03_adaptive_drawing.py --query "narysuj dom z czerwonym dachem"
    python3 03_adaptive_drawing.py --query "draw a blue star"
    python3 03_adaptive_drawing.py --query "namaluj kwiat z 6 płatkami" --target jspaint
"""

import argparse
import asyncio
import json
import math
import os
import sys
import time
from pathlib import Path

# Add parent examples directory for _verbose_helper
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from _verbose_helper import init_verbose, vlog, dump_page_schema, dump_selectors, vlog_decision, ensure_playwright_browsers_async, auto_navigate_with_fallback

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Drawing plan generator (template-based fallback when LLM unavailable)
# ---------------------------------------------------------------------------

SHAPE_KEYWORDS = {
    "dom": "house", "house": "house",
    "koło": "circle", "kółko": "circle", "circle": "circle",
    "prostokąt": "rectangle", "rectangle": "rectangle",
    "trójkąt": "triangle", "triangle": "triangle",
    "gwiazda": "star", "gwiazdka": "star", "star": "star",
    "kwiat": "flower", "flower": "flower",
    "serce": "heart", "heart": "heart",
    "spirala": "spiral", "spiral": "spiral",
    "drzewo": "tree", "tree": "tree",
    "słońce": "sun", "sun": "sun",
}

COLOR_KEYWORDS = {
    "czerwony": "red", "red": "red",
    "niebieski": "blue", "blue": "blue",
    "zielony": "green", "green": "green",
    "żółty": "yellow", "yellow": "yellow",
    "czarny": "black", "black": "black",
    "biały": "white", "white": "white",
    "pomarańczowy": "orange", "orange": "orange",
    "fioletowy": "purple", "purple": "purple",
    "różowy": "pink", "pink": "pink",
}


def detect_shape_and_color(query: str) -> tuple[str, str]:
    """Detect shape and color from natural language query."""
    q = query.lower()
    shape = "circle"
    color = "blue"
    for kw, s in SHAPE_KEYWORDS.items():
        if kw in q:
            shape = s
            break
    for kw, c in COLOR_KEYWORDS.items():
        if kw in q:
            color = c
            break
    return shape, color


def generate_shape_points(shape: str, cx: float, cy: float, size: float = 150):
    """Generate drawing points for a shape (template fallback)."""
    if shape == "circle":
        pts = []
        for i in range(36):
            angle = 2 * math.pi * i / 36
            pts.append((cx + size * math.cos(angle), cy + size * math.sin(angle)))
        pts.append(pts[0])  # Close
        return [pts]

    elif shape == "star":
        pts = []
        for i in range(5):
            # Outer point
            angle = -math.pi / 2 + 2 * math.pi * i / 5
            pts.append((cx + size * math.cos(angle), cy + size * math.sin(angle)))
            # Inner point
            angle2 = angle + math.pi / 5
            pts.append((cx + size * 0.4 * math.cos(angle2), cy + size * 0.4 * math.sin(angle2)))
        pts.append(pts[0])
        return [pts]

    elif shape == "triangle":
        return [[(cx, cy - size), (cx - size * 0.87, cy + size * 0.5),
                 (cx + size * 0.87, cy + size * 0.5), (cx, cy - size)]]

    elif shape == "house":
        body = [(cx - size, cy), (cx + size, cy), (cx + size, cy + size * 1.2),
                (cx - size, cy + size * 1.2), (cx - size, cy)]
        roof = [(cx - size * 1.1, cy), (cx, cy - size * 0.8), (cx + size * 1.1, cy)]
        door = [(cx - size * 0.2, cy + size * 0.5), (cx + size * 0.2, cy + size * 0.5),
                (cx + size * 0.2, cy + size * 1.2), (cx - size * 0.2, cy + size * 1.2),
                (cx - size * 0.2, cy + size * 0.5)]
        return [body, roof, door]

    elif shape == "flower":
        groups = []
        for p in range(6):
            petal = []
            base_angle = 2 * math.pi * p / 6
            for i in range(20):
                t = i / 19
                angle = base_angle + (t - 0.5) * (2 * math.pi / 6)
                r = size * math.sin(t * math.pi)
                petal.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
            groups.append(petal)
        return groups

    elif shape == "heart":
        pts = []
        for i in range(60):
            t = 2 * math.pi * i / 60
            x = 16 * math.sin(t) ** 3
            y = -(13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t))
            pts.append((cx + x * size / 16, cy + y * size / 16))
        pts.append(pts[0])
        return [pts]

    elif shape == "spiral":
        pts = []
        for i in range(100):
            t = i / 100
            r = size * t
            angle = t * 6 * math.pi
            pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
        return [pts]

    elif shape == "sun":
        # Circle + rays
        circle = []
        for i in range(36):
            angle = 2 * math.pi * i / 36
            circle.append((cx + size * 0.5 * math.cos(angle), cy + size * 0.5 * math.sin(angle)))
        circle.append(circle[0])
        groups = [circle]
        for i in range(8):
            angle = 2 * math.pi * i / 8
            ray = [
                (cx + size * 0.55 * math.cos(angle), cy + size * 0.55 * math.sin(angle)),
                (cx + size * math.cos(angle), cy + size * math.sin(angle)),
            ]
            groups.append(ray)
        return groups

    elif shape == "tree":
        trunk = [(cx - size * 0.1, cy), (cx + size * 0.1, cy),
                 (cx + size * 0.1, cy + size), (cx - size * 0.1, cy + size),
                 (cx - size * 0.1, cy)]
        crown = []
        for i in range(36):
            angle = 2 * math.pi * i / 36
            crown.append((cx + size * 0.7 * math.cos(angle),
                          cy - size * 0.5 + size * 0.7 * math.sin(angle)))
        crown.append(crown[0])
        return [trunk, crown]

    # Default: rectangle
    return [[(cx - size, cy - size * 0.7), (cx + size, cy - size * 0.7),
             (cx + size, cy + size * 0.7), (cx - size, cy + size * 0.7),
             (cx - size, cy - size * 0.7)]]


# ---------------------------------------------------------------------------
# LLM-based drawing plan generation (with adaptive routing)
# ---------------------------------------------------------------------------

async def generate_plan_with_llm(query: str) -> dict | None:
    """Try to generate a drawing plan using LLM Router with adaptive learning."""
    try:
        from nlp2cmd.llm.router import LLMRouter

        router = LLMRouter(adaptive_learning=True)

        system_prompt = (
            "You are a drawing assistant. Given a natural language description, "
            "generate a JSON drawing plan with shapes and colors.\n"
            "Format: {\"shapes\": [{\"type\": \"circle|rect|line|path\", "
            "\"x\": 350, \"y\": 300, \"size\": 100, \"color\": \"#ff0000\"}]}\n"
            "Reply with ONLY valid JSON."
        )

        resp = await router.completion(
            query,
            task="coding",
            system=system_prompt,
            max_tokens=500,
            temperature=0.1,
            json_mode=True,
        )

        if resp.success and resp.content:
            print(f"  LLM model: {resp.model}")
            print(f"  Latency: {resp.latency_ms:.0f}ms")
            if resp.fallback_used:
                print(f"  (fallback used — remote model failed)")

            try:
                plan = json.loads(resp.content)
                return plan
            except json.JSONDecodeError:
                print(f"  LLM returned invalid JSON, using template fallback")
                return None
        else:
            print(f"  LLM failed: {resp.error}")
            if resp.error and "402" in resp.error:
                print("  → Credit exhausted — adaptive learner will remember this")
            return None

    except ImportError:
        print("  LLM Router not available, using template fallback")
        return None
    except Exception as e:
        print(f"  LLM error: {e}")
        return None


# ---------------------------------------------------------------------------
# Main execution
# ---------------------------------------------------------------------------

COLOR_HEX = {
    "red": "#ff0000", "blue": "#0000ff", "green": "#00ff00",
    "black": "#000000", "yellow": "#ffff00", "orange": "#ff8800",
    "purple": "#8800ff", "white": "#ffffff", "pink": "#ff69b4",
    "cyan": "#00ffff",
}


async def execute_drawing(page, shape_groups, canvas_box, color_hex="#0000ff"):
    """Execute drawing on canvas."""
    ox, oy = canvas_box["x"], canvas_box["y"]

    # Try to set color
    try:
        ci = page.locator('input[type="color"]').first
        if await ci.count() > 0:
            await ci.evaluate(f'el => {{ el.value = "{color_hex}"; el.dispatchEvent(new Event("input")); }}')
    except Exception:
        pass

    for group in shape_groups:
        if len(group) < 2:
            continue
        x0, y0 = group[0]
        await page.mouse.move(ox + x0, oy + y0)
        await page.mouse.down()
        for x, y in group[1:]:
            await page.mouse.move(ox + x, oy + y)
            await page.wait_for_timeout(15)
        await page.mouse.up()
        await page.wait_for_timeout(100)


async def main():
    parser = argparse.ArgumentParser(description="Adaptive LLM-guided drawing")
    parser.add_argument("--query", required=True, help="Natural language drawing command")
    parser.add_argument("--target", default="draw.chat",
                        choices=["draw.chat", "jspaint"],
                        help="Target drawing tool")
    parser.add_argument("--headless", action="store_true", help="Run headless")
    parser.add_argument("--screenshot-dir", default="screenshots")
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

    target_urls = {
        "draw.chat": "https://draw.chat/pl/whiteboard.html",
        "jspaint": "https://jspaint.app",
    }

    print(f"=== Adaptive Drawing ===")
    print(f"Query:  {args.query}")
    print(f"Target: {args.target}")
    print()

    # Step 1: Detect shape and color from query
    shape, color = detect_shape_and_color(args.query)
    color_hex = COLOR_HEX.get(color, "#0000ff")
    print(f"1. Detected: shape={shape}, color={color}")
    vlog_decision(
        f"Shape: {shape}, Color: {color}",
        f"Matched from query keywords",
        alternatives=[list(SHAPE_KEYWORDS.values()), list(COLOR_KEYWORDS.values())],
    )

    # Step 2: Try LLM for advanced plan
    print(f"2. Trying LLM for drawing plan...")
    t0 = time.time()
    llm_plan = await generate_plan_with_llm(args.query)
    plan_time = (time.time() - t0) * 1000

    use_llm_plan = False
    if llm_plan and "shapes" in llm_plan:
        print(f"   LLM plan: {len(llm_plan['shapes'])} shapes ({plan_time:.0f}ms)")
        use_llm_plan = True
    else:
        print(f"   Using template fallback ({plan_time:.0f}ms)")

    # Step 3: Open browser and draw
    print(f"3. Opening {args.target}...")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=args.headless)
        page = await browser.new_page(viewport={"width": 1024, "height": 768})

        # Auto-discover working URL with fallback
        working_url = await auto_navigate_with_fallback(
            page, target_urls, args.target,
            fallback_urls=["https://draw.chat/", "https://draw.chat/pl/", "https://jspaint.app/"],
            required_selector="canvas"
        )
        if not working_url:
            print("ERROR: Could not find working drawing site")
            sys.exit(1)

        await page.wait_for_timeout(3000)
        vlog(f"Page loaded: {page.url}")

        # Dismiss popups
        for text in ["Accept", "Akceptuję", "OK", "Got it", "Close", "×"]:
            try:
                btn = page.get_by_text(text, exact=False).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    vlog(f"Dismissed dialog: '{text}'")
                    await page.wait_for_timeout(300)
            except Exception:
                continue

        # Inspect page schema
        await dump_page_schema(page)

        # Find canvas
        canvas = page.locator("canvas").first
        try:
            await canvas.wait_for(state="visible", timeout=10000)
            vlog("Canvas became visible")
        except Exception:
            vlog("Canvas not visible after 10s, waiting 5s more")
            await page.wait_for_timeout(5000)

        box = await canvas.bounding_box()
        if not box:
            vlog("Canvas bounding_box() returned None — using fallback")
            box = {"x": 50, "y": 50, "width": 900, "height": 650}

        cx = box["width"] / 2
        cy = box["height"] / 2

        print(f"   Canvas: {box['width']:.0f}x{box['height']:.0f}")
        vlog(f"Canvas bbox: x={box['x']:.1f} y={box['y']:.1f} w={box['width']:.1f} h={box['height']:.1f}")

        # Generate shape points (template-based)
        shape_groups = generate_shape_points(shape, cx, cy, size=min(cx, cy) * 0.5)

        print(f"4. Drawing {shape} in {color}...")
        await execute_drawing(page, shape_groups, box, color_hex)

        # Screenshot
        print(f"5. Saving screenshot...")
        ss_dir = Path(args.screenshot_dir)
        ss_dir.mkdir(parents=True, exist_ok=True)
        ss_path = ss_dir / f"adaptive_{shape}_{color}_{args.target.replace('.', '_')}.png"
        await page.screenshot(path=str(ss_path))
        print(f"   Screenshot: {ss_path}")

        # Step 4: Try vision verification (optional)
        print(f"6. Attempting vision verification...")
        try:
            import base64
            from nlp2cmd.llm.router import LLMRouter

            ss_bytes = ss_path.read_bytes()
            b64 = base64.b64encode(ss_bytes).decode()

            router = LLMRouter(adaptive_learning=True)
            vresp = await router.vision(
                b64,
                f"Does this image contain a {shape} drawn in {color}? Reply briefly.",
                max_tokens=100,
            )
            if vresp.success:
                print(f"   Vision says: {vresp.content[:200]}")
                print(f"   Model: {vresp.model}, Latency: {vresp.latency_ms:.0f}ms")
            else:
                print(f"   Vision unavailable: {vresp.error}")
        except Exception as e:
            print(f"   Vision verification skipped: {e}")

        # Show adaptive learning stats
        try:
            from nlp2cmd.llm.router import LLMRouter
            router = LLMRouter(adaptive_learning=True)
            stats = router.get_stats()
            if "adaptive_learning" in stats:
                al = stats["adaptive_learning"]
                print(f"\n7. Adaptive Learning Report:")
                print(f"   Models tracked: {len(al.get('models', {}))}")
                print(f"   Rules learned: {len(al.get('rules', []))}")
                print(f"   Fallback pairs: {al.get('fallback_pairs', {})}")
                if al.get("error_summary"):
                    print(f"   Error summary: {al['error_summary']}")
        except Exception:
            pass

        await browser.close()

    print()
    print(f"Done! Shape: {shape}, Color: {color}, Target: {args.target}")


if __name__ == "__main__":
    asyncio.run(main())
