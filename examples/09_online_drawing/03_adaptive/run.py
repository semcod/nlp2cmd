#!/usr/bin/env python3
"""
03_adaptive — LLM-guided drawing with adaptive model routing.

Demonstrates the full NLP2CMD adaptive learning pipeline:
1. Takes a natural language drawing command (PL or EN)
2. Routes to LLM for drawing plan generation (remote → local fallback)
3. Learns from failures (credit exhaustion, timeouts) and adapts
4. Executes the plan on draw.chat or jspaint.app via Playwright
5. Verifies result with vision model (if available)
6. Comprehensive logging of every step

Usage:
    python3 run.py --query "narysuj dom z czerwonym dachem"
    python3 run.py --query "draw a blue star"
    python3 run.py --query "namaluj kwiat z 6 płatkami" --target jspaint
    python3 run.py --query "draw a circle" --target excalidraw
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

# Setup import paths
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))
sys.path.insert(0, str(_HERE.parents[1]))
sys.path.insert(0, str(_HERE.parents[2] / "src"))

from _run_utils import ExampleRunner, discover_working_url, dismiss_popups, DRAWING_SITES
from _verbose_helper import init_verbose, vlog, dump_page_schema

from nlp2cmd.skills.drawing import DrawingSkill
from nlp2cmd.skills.drawing.renderers.playwright import PlaywrightRenderer

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[3] / ".env")
except ImportError:
    pass


# ---------------------------------------------------------------------------
# LLM-based drawing plan generation (with adaptive routing)
# ---------------------------------------------------------------------------

async def generate_plan_with_llm(query: str, log=None) -> dict | None:
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
            if log:
                log.info(f"  LLM model: {resp.model}")
                log.info(f"  Latency: {resp.latency_ms:.0f}ms")
                if resp.fallback_used:
                    log.warning("  Fallback used — remote model failed")

            try:
                plan = json.loads(resp.content)
                return plan
            except json.JSONDecodeError:
                if log:
                    log.warning("LLM returned invalid JSON, using template fallback")
                return None
        else:
            if log:
                log.warning(f"LLM failed: {resp.error}")
                if resp.error and "402" in resp.error:
                    log.info("  → Credit exhausted — adaptive learner will remember this")
            return None

    except ImportError:
        if log:
            log.info("LLM Router not available, using template fallback")
        return None
    except Exception as e:
        if log:
            log.warning(f"LLM error: {e}")
        return None


async def verify_with_vision(screenshot_path: str, shape: str, color: str, log=None) -> str | None:
    """Try vision verification of the drawing result."""
    try:
        import base64
        from nlp2cmd.llm.router import LLMRouter

        ss_bytes = Path(screenshot_path).read_bytes()
        b64 = base64.b64encode(ss_bytes).decode()

        router = LLMRouter(adaptive_learning=True)
        vresp = await router.vision(
            b64,
            f"Does this image contain a {shape} drawn in {color}? Reply briefly.",
            max_tokens=100,
        )
        if vresp.success:
            if log:
                log.info(f"  Vision says: {vresp.content[:200]}")
                log.info(f"  Model: {vresp.model}, Latency: {vresp.latency_ms:.0f}ms")
            return vresp.content
        else:
            if log:
                log.info(f"  Vision unavailable: {vresp.error}")
            return None
    except Exception as e:
        if log:
            log.info(f"  Vision verification skipped: {e}")
        return None


def get_adaptive_stats(log=None) -> dict | None:
    """Get adaptive learning statistics."""
    try:
        from nlp2cmd.llm.router import LLMRouter
        router = LLMRouter(adaptive_learning=True)
        stats = router.get_stats()
        if "adaptive_learning" in stats:
            return stats["adaptive_learning"]
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

TARGETS = list(DRAWING_SITES.keys())


async def main():
    parser = argparse.ArgumentParser(description="Adaptive LLM-guided drawing")
    parser.add_argument("--query", required=True, help="Natural language drawing command")
    parser.add_argument("--target", default="draw.chat", choices=TARGETS,
                        help="Target drawing tool")
    parser.add_argument("--headless", action="store_true", help="Run headless")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    init_verbose(args.verbose)

    async with ExampleRunner("03_adaptive", headless=args.headless, base_dir=_HERE) as runner:
        log = runner.log
        page = runner.page

        # Step 1: NL parsing via DrawingSkill
        skill = DrawingSkill()
        skill.init_canvas(1024, 768, url="", app=args.target)

        shape = skill.detect_shape(args.query)
        color_hex = skill.detect_color(args.query, default="#0000FF")

        log.step(1, f"NL parsing: shape={shape}, color={color_hex}")
        log.info(f"Query: {args.query}")
        log.info(f"Target: {args.target}")
        log.info(f"Available shapes: {', '.join(DrawingSkill.available_shapes())}")

        # Step 2: Try LLM for advanced plan
        log.step(2, "Trying LLM for drawing plan...")
        t0 = time.time()
        llm_plan = await generate_plan_with_llm(args.query, log)
        plan_time = (time.time() - t0) * 1000

        if llm_plan and "shapes" in llm_plan:
            log.info(f"LLM plan: {len(llm_plan['shapes'])} shapes ({plan_time:.0f}ms)")
        else:
            log.info(f"Using DrawingSkill NL parser ({plan_time:.0f}ms)")

        # Step 3: Execute NL command via DrawingSkill
        log.step(3, "Generating drawing events from NL...")
        events = skill.execute_nl(args.query)
        log.info(f"Generated {len(events)} events, total: {skill.event_count}")

        # Step 4: Navigate to target with intelligent fallback
        log.step(4, f"Navigating to {args.target}...")
        working_url = await runner.navigate(args.target)

        if not working_url:
            # Try fallback to other drawing sites
            log.warning(f"{args.target} unavailable, trying fallback chain...")
            fallback_order = [s for s in TARGETS if s != args.target]
            for fallback in fallback_order:
                log.info(f"Trying fallback: {fallback}")
                working_url, health = await discover_working_url(page, fallback, log=log)
                if working_url:
                    log.success(f"Fallback succeeded: {fallback} → {working_url}")
                    break

            if not working_url:
                log.error("No drawing site available (all fallbacks failed)")
                return

        await page.wait_for_timeout(2000)

        # Step 5: Render via PlaywrightRenderer
        log.step(5, "Rendering via PlaywrightRenderer...")
        renderer = PlaywrightRenderer(page)
        canvas_info = await skill.render(renderer, url="", app=args.target)
        log.info(f"Canvas: {canvas_info.get('width', 0):.0f}x{canvas_info.get('height', 0):.0f}")

        if args.verbose:
            await dump_page_schema(page)

        # Step 6: Screenshot
        log.step(6, "Saving screenshot...")
        safe_target = args.target.replace(".", "_")
        ss_name = f"adaptive_{shape}_{color_hex.replace('#', '')}_{safe_target}.png"
        ss_path = await runner.screenshot(ss_name,
                                           shape=shape, color=color_hex,
                                           target=args.target, query=args.query,
                                           llm_plan=bool(llm_plan))

        # Step 7: Save session
        log.step(7, "Saving session...")
        session_path = runner.screenshot_dir / f"adaptive_{shape}_session.json"
        skill.save_session(str(session_path))
        log.info(f"Session: {session_path} ({skill.event_count} events)")

        # Step 8: Vision verification (optional)
        log.step(8, "Attempting vision verification...")
        if ss_path:
            vision_result = await verify_with_vision(ss_path, shape, color_hex, log)
        else:
            log.info("  No screenshot to verify")

        # Step 9: Adaptive learning stats
        al_stats = get_adaptive_stats(log)
        if al_stats:
            log.step(9, "Adaptive Learning Report:")
            log.info(f"  Models tracked: {len(al_stats.get('models', {}))}")
            log.info(f"  Rules learned: {len(al_stats.get('rules', []))}")
            log.info(f"  Fallback pairs: {al_stats.get('fallback_pairs', {})}")
            if al_stats.get("error_summary"):
                log.info(f"  Error summary: {al_stats['error_summary']}")
        else:
            log.step(9, "Adaptive learning: no stats available (LLM not used or not installed)")

        # Summary
        state = skill.get_state()
        log.success(
            f"Done! Shape: {shape}, Color: {color_hex}, "
            f"Target: {args.target}, Shapes: {state['shapes_count']}"
        )


if __name__ == "__main__":
    asyncio.run(main())
