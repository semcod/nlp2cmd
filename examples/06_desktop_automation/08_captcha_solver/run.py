#!/usr/bin/env python3
"""
08_captcha_solver — Detect and solve CAPTCHAs via LLM vision.

Usage:
    python3 run.py --url "https://example.com/login"
    python3 run.py --url "https://example.com" --detect-only
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add examples parent and src to path for shared helpers
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from _verbose_helper import ensure_playwright_browsers_async


async def main():
    parser = argparse.ArgumentParser(description="CAPTCHA detection and solving via LLM vision")
    parser.add_argument("--url", required=True, help="URL of page with CAPTCHA")
    parser.add_argument("--detect-only", action="store_true", help="Only detect, don't solve")
    parser.add_argument("--headless", action="store_true", help="Run browser headless")
    parser.add_argument("--model", default=None, help="LLM model override")
    parser.add_argument("--screenshot-dir", default="screenshots", help="Screenshot output dir")
    args = parser.parse_args()

    import os
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("Error: OPENROUTER_API_KEY environment variable is required")
        print("  export OPENROUTER_API_KEY='sk-or-v1-...'")
        sys.exit(1)

    from nlp2cmd.automation.captcha_solver import CaptchaSolver

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("ERROR: pip install playwright")
        sys.exit(1)

    # Auto-install browsers if needed
    if not await ensure_playwright_browsers_async(auto_install=True):
        sys.exit(1)

    solver = CaptchaSolver(api_key=api_key, model=args.model)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=args.headless)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})

        print(f"Navigating to: {args.url}")
        await page.goto(args.url, wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(2000)

        # Save initial screenshot
        screenshot_dir = Path(args.screenshot_dir)
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(screenshot_dir / "page_initial.png"))

        # Detect CAPTCHA
        print("Detecting CAPTCHA...")
        captcha_info = await solver.detect_captcha(page)

        if not captcha_info:
            print("No CAPTCHA detected on this page.")
            await browser.close()
            return

        print(f"Detected: {captcha_info.captcha_type} (confidence: {captcha_info.confidence:.0%})")

        if args.detect_only:
            print("Detection only mode — not solving.")
            await browser.close()
            return

        # Solve
        print(f"Solving {captcha_info.captcha_type} CAPTCHA...")
        result = await solver.solve(page, captcha_info)

        if result["success"]:
            print(f"✅ CAPTCHA solved!")
        else:
            print(f"❌ Failed: {result.get('error', 'unknown')}")

        # Save final screenshot
        await page.screenshot(path=str(screenshot_dir / "page_after_solve.png"))
        print(f"Screenshots saved to: {screenshot_dir}/")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
