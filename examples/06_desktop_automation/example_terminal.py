#!/usr/bin/env python3
"""
Example: Terminal automation via noVNC.

Opens a terminal on the remote desktop, runs several shell commands,
and logs everything to a Markdown report with screenshots.

Prerequisites:
    docker compose -f docker/novnc/docker-compose.yml up -d

Usage:
    python3 examples/06_desktop_automation/example_terminal.py
"""

from __future__ import annotations
import sys, time
from pathlib import Path

# Ensure nlp2cmd src is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from nlp2cmd.cli.session_logger import SessionLogger


def main():
    from playwright.sync_api import sync_playwright

    out = Path(__file__).parent
    logger = SessionLogger("terminal_session", output_dir=out, thumbnail_width=256)
    logger.start("Terminal Automation Example", description="Run shell commands on remote desktop via noVNC")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        # Connect
        page.goto("http://localhost:6080/vnc.html?autoconnect=true", timeout=15000)
        page.wait_for_timeout(4000)
        try:
            page.wait_for_selector("canvas", timeout=10000)
        except Exception:
            pass
        logger.step("Connected to desktop", page=page)

        # Open terminal
        page.keyboard.press("Control+Alt+t")
        page.wait_for_timeout(2000)
        logger.step("Opened terminal (Ctrl+Alt+T)", page=page)

        # Command 1: system info
        commands = [
            ("uname -a", "Show kernel info"),
            ("whoami && id", "Show current user"),
            ("df -h /", "Check disk space"),
            ("free -h", "Check memory usage"),
            ("ps aux | head -10", "List top processes"),
        ]

        for cmd, desc in commands:
            print(f"  Running: {cmd}")
            page.keyboard.type(cmd, delay=20)
            page.keyboard.press("Enter")
            page.wait_for_timeout(1500)
            logger.step(desc, page=page)
            logger.code(cmd)

        page.wait_for_timeout(1000)
        logger.step("All commands completed", page=page)

        browser.close()

    md_path = logger.end(summary={
        "Commands executed": len(commands),
        "Protocol": "noVNC → TigerVNC → XFCE Terminal",
    })
    print(f"\nReport: {md_path}")


if __name__ == "__main__":
    main()
