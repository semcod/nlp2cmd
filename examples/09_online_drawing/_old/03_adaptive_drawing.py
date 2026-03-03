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
import os
import sys
import time
from pathlib import Path

# Add parent examples directory for _verbose_helper
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from _verbose_helper import init_verbose, vlog, dump_page_schema, dump_selectors, vlog_decision, ensure_playwright_browsers_async, auto_navigate_with_fallback
from nlp2cmd.skills.drawing import DrawingSkill
from nlp2cmd.skills.drawing.renderers.playwright import PlaywrightRenderer

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except ImportError:
    pass


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

    # --- Use DrawingSkill (CQRS + Event Sourcing + NL parsing) ---
    skill = DrawingSkill()
    skill.init_canvas(1024, 768, url=target_urls.get(args.target, ""), app=args.target)

    # Step 1: NL parsing via DrawingSkill
    shape = skill.detect_shape(args.query)
    color_hex = skill.detect_color(args.query, default="#0000FF")

    print(f"=== Adaptive Drawing ===")
    print(f"Query:  {args.query}")
    print(f"Target: {args.target}")
    print(f"Detected: shape={shape}, color={color_hex}")
    print(f"Available shapes: {', '.join(DrawingSkill.available_shapes())}")
    print()

    # Step 2: Try LLM for advanced plan
    print(f"1. Trying LLM for drawing plan...")
    t0 = time.time()
    llm_plan = await generate_plan_with_llm(args.query)
    plan_time = (time.time() - t0) * 1000

    if llm_plan and "shapes" in llm_plan:
        print(f"   LLM plan: {len(llm_plan['shapes'])} shapes ({plan_time:.0f}ms)")
    else:
        print(f"   Using DrawingSkill NL parser ({plan_time:.0f}ms)")

    # Step 3: Execute NL command via DrawingSkill
    print(f"2. Generating drawing events from NL...")
    events = skill.execute_nl(args.query)
    print(f"   Generated {len(events)} events, total: {skill.event_count}")

    # Step 4: Open browser and render
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

        # Render via PlaywrightRenderer
        print(f"4. Rendering via PlaywrightRenderer...")
        renderer = PlaywrightRenderer(page)
        canvas_info = await skill.render(renderer, url=working_url, app=args.target)
        print(f"   Canvas: {canvas_info.get('width', 0):.0f}x{canvas_info.get('height', 0):.0f}")
        vlog(f"Canvas info: {canvas_info}")

        # Inspect page schema
        await dump_page_schema(page)

        # Screenshot
        print(f"5. Saving screenshot...")
        ss_dir = Path(args.screenshot_dir)
        ss_dir.mkdir(parents=True, exist_ok=True)
        ss_path = ss_dir / f"adaptive_{shape}_{color_hex.replace('#', '')}_{args.target.replace('.', '_')}.png"
        await renderer.screenshot(str(ss_path))
        print(f"   Screenshot: {ss_path}")

        # Save event sourcing session
        session_path = ss_dir / f"adaptive_{shape}_session.json"
        skill.save_session(str(session_path))
        print(f"   Session saved: {session_path} ({skill.event_count} events)")

        # Step 5: Try vision verification (optional)
        print(f"6. Attempting vision verification...")
        try:
            import base64
            from nlp2cmd.llm.router import LLMRouter

            ss_bytes = Path(str(ss_path)).read_bytes()
            b64 = base64.b64encode(ss_bytes).decode()

            router = LLMRouter(adaptive_learning=True)
            vresp = await router.vision(
                b64,
                f"Does this image contain a {shape} drawn in {color_hex}? Reply briefly.",
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
    state = skill.get_state()
    print(f"Done! Shape: {shape}, Color: {color_hex}, Target: {args.target}, Shapes: {state['shapes_count']}")


if __name__ == "__main__":
    asyncio.run(main())
