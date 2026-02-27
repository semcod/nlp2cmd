#!/usr/bin/env python3
"""
Example: Calculator automation via noVNC.

Opens galculator on the remote desktop, performs calculations,
and logs results to Markdown with screenshots.

Prerequisites:
    docker compose -f docker/novnc/docker-compose.yml up -d

Usage:
    python3 examples/06_desktop_automation/example_calculator.py
"""

from __future__ import annotations
import sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from nlp2cmd.cli.session_logger import SessionLogger


def main():
    from playwright.sync_api import sync_playwright

    out = Path(__file__).parent
    logger = SessionLogger("calculator_session", output_dir=out, thumbnail_width=256)
    logger.start("Calculator Automation Example", description="Control galculator app via noVNC")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        page.goto("http://localhost:6080/vnc.html?autoconnect=true", timeout=15000)
        page.wait_for_timeout(4000)
        try:
            page.wait_for_selector("canvas", timeout=10000)
        except Exception:
            pass
        logger.step("Connected to desktop", page=page)

        # Open terminal first, then launch calculator
        page.keyboard.press("Control+Alt+t")
        page.wait_for_timeout(2000)
        page.keyboard.type("galculator &", delay=30)
        page.keyboard.press("Enter")
        page.wait_for_timeout(2000)
        logger.step("Launched galculator from terminal", page=page)

        # Perform calculations
        calculations = [
            ("2+2", "4", "Basic addition"),
            ("100/7", "14.285...", "Division"),
            ("256*256", "65536", "Power of 2 squared"),
            ("999-42", "957", "Subtraction"),
        ]

        for expr, expected, desc in calculations:
            print(f"  Calculating: {expr} = {expected}")
            # Clear previous result
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
            page.keyboard.type(expr, delay=80)
            page.wait_for_timeout(300)
            page.keyboard.press("Enter")
            page.wait_for_timeout(800)
            logger.step(f"{desc}: {expr} = {expected}", page=page, extra={
                "expression": expr,
                "expected": expected,
            })

        browser.close()

    md_path = logger.end(summary={
        "Calculations performed": len(calculations),
        "Application": "galculator",
    })
    print(f"\nReport: {md_path}")


if __name__ == "__main__":
    main()
