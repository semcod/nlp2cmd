#!/usr/bin/env python3
"""
NLP2CMD Desktop GUI Automation Demo via noVNC.

Demonstrates controlling a Linux desktop environment through natural language:
- Opens applications (calculator, terminal, file manager, text editor)
- Types text, clicks buttons, fills forms in desktop apps
- Records video of the entire session

Prerequisites:
    docker compose -f docker/novnc/docker-compose.yml up -d
    # Wait ~10s for desktop to start
    # Open http://localhost:6080/vnc.html to watch live

Usage:
    python3 docker/novnc/demos/demo_desktop_gui.py
    python3 docker/novnc/demos/demo_desktop_gui.py --record
    python3 docker/novnc/demos/demo_desktop_gui.py --headless
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional


def ensure_playwright():
    """Ensure playwright is available."""
    try:
        from playwright.sync_api import sync_playwright
        return True
    except ImportError:
        print("Installing playwright...")
        subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        return True


def start_recording(container: str = "nlp2cmd-desktop", duration: int = 60) -> Optional[subprocess.Popen]:
    """Start ffmpeg video recording inside the Docker container."""
    cmd = [
        "docker", "exec", container, "bash", "-c",
        f"ffmpeg -y -f x11grab -video_size 1280x800 -framerate 10 "
        f"-i :1 -t {duration} -c:v libx264 -preset ultrafast "
        f"/home/nlp2cmd/recordings/demo_session.mp4 &"
    ]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"Recording started (max {duration}s)")
        return proc
    except Exception as e:
        print(f"Could not start recording: {e}")
        return None


def stop_recording(container: str = "nlp2cmd-desktop"):
    """Stop ffmpeg recording."""
    subprocess.run(
        ["docker", "exec", container, "bash", "-c", "pkill -f ffmpeg || true"],
        capture_output=True,
    )
    print("Recording stopped → docker/novnc/recordings/demo_session.mp4")


def _connect_novnc(page, novnc_url: str, logger) -> bool:
    """Connect to noVNC with retry logic. Returns True if connected."""
    vnc_page = f"{novnc_url}/vnc.html?autoconnect=true"
    for attempt in range(1, 11):
        try:
            page.goto(vnc_page, wait_until="load", timeout=8000)
            return True
        except Exception as e:
            err = str(e)
            if "ERR_CONNECTION_REFUSED" in err or "net::" in err:
                msg = f"Retry {attempt}/10..." if attempt > 1 else "Container not ready, retrying..."
                print(f"  {msg}")
                logger.info(msg)
                time.sleep(3)
            else:
                logger.warning(f"Connection error: {e}")
                return False
    return False


def run_demo(*, record: bool = False, headless: bool = False, novnc_url: str = "http://localhost:6080"):
    """Run the desktop GUI automation demo with markdown session logging."""
    from playwright.sync_api import sync_playwright

    # Add src to path so SessionLogger is importable
    src_path = str(Path(__file__).resolve().parents[3] / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    from nlp2cmd.cli.session_logger import SessionLogger

    output_dir = Path("docker/novnc/recordings")
    output_dir.mkdir(parents=True, exist_ok=True)

    logger = SessionLogger(
        "desktop_gui_demo",
        output_dir=output_dir,
        thumbnail_width=256,
    )
    logger.start(
        "NLP2CMD Desktop GUI Automation Demo",
        description="Controlling Linux XFCE desktop via noVNC + Playwright",
    )

    recorder = None
    if record:
        recorder = start_recording()
        time.sleep(2)
        logger.info("Video recording started (ffmpeg inside Docker)")

    print("\n" + "=" * 60)
    print("NLP2CMD Desktop GUI Automation Demo")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            record_video_dir=str(output_dir) if record else None,
        )
        page = context.new_page()

        # --- Step 1: Connect ---
        print(f"\n[1/6] Connecting to noVNC at {novnc_url}...")
        if not _connect_novnc(page, novnc_url, logger):
            print("\n  ERROR: Could not connect to noVNC.")
            print("    docker compose -f docker/novnc/docker-compose.yml up -d")
            logger.warning("Could not connect to noVNC — container not running?")
            md_path = logger.end()
            print(f"  Partial log: {md_path}")
            context.close()
            browser.close()
            if record:
                stop_recording()
            return

        page.wait_for_timeout(3000)
        try:
            page.wait_for_selector("canvas", timeout=15000)
            print("  Connected to desktop via noVNC")
        except Exception:
            print("  Warning: VNC canvas not found, continuing...")

        logger.step("Connected to XFCE desktop via noVNC", page=page, extra={
            "url": novnc_url,
            "resolution": "1280x800",
            "protocol": "noVNC (websocket → VNC)",
        })

        # --- Step 2: Terminal ---
        print("\n[2/6] Opening terminal...")
        page.keyboard.press("Control+Alt+t")
        page.wait_for_timeout(2000)
        logger.step("Opened terminal (Ctrl+Alt+T)", page=page)

        cmd = "echo 'Hello from NLP2CMD! Autonomous desktop control.'"
        print(f"  Typing: {cmd}")
        page.keyboard.type(cmd, delay=30)
        page.wait_for_timeout(300)
        page.keyboard.press("Enter")
        page.wait_for_timeout(1000)
        logger.step("Executed shell command", page=page)
        logger.code(cmd)

        # --- Step 3: Calculator ---
        print("\n[3/6] Opening calculator...")
        page.keyboard.type("galculator &", delay=30)
        page.keyboard.press("Enter")
        page.wait_for_timeout(2000)
        logger.step("Opened galculator", page=page)

        calc_expr = "42*137"
        print(f"  Calculating: {calc_expr}")
        page.keyboard.type(calc_expr, delay=100)
        page.wait_for_timeout(300)
        page.keyboard.press("Enter")
        page.wait_for_timeout(1000)
        logger.step(f"Calculated {calc_expr} = 5754", page=page, extra={
            "expression": calc_expr,
            "expected_result": 5754,
        })

        # --- Step 4: Text editor ---
        print("\n[4/6] Opening text editor...")
        page.keyboard.press("Alt+F2")
        page.wait_for_timeout(1000)
        page.keyboard.type("mousepad", delay=50)
        page.keyboard.press("Enter")
        page.wait_for_timeout(2000)
        logger.step("Opened Mousepad text editor (Alt+F2)", page=page)

        doc_text = (
            "NLP2CMD Desktop Automation Report\n"
            "==================================\n\n"
            "Date: 2026-02-27\n"
            "System: Linux (XFCE via noVNC)\n\n"
            "This document was created autonomously by NLP2CMD.\n"
        )
        print("  Typing document...")
        page.keyboard.type(doc_text, delay=8)
        page.wait_for_timeout(500)
        logger.step("Typed document content", page=page)
        logger.code(doc_text, language="text")

        print("  Saving (Ctrl+S)...")
        page.keyboard.press("Control+s")
        page.wait_for_timeout(1500)
        page.keyboard.type("/home/nlp2cmd/nlp2cmd_report.txt", delay=30)
        page.keyboard.press("Enter")
        page.wait_for_timeout(1000)
        logger.step("Saved document via Ctrl+S", page=page, extra={
            "filename": "/home/nlp2cmd/nlp2cmd_report.txt",
        })

        # --- Step 5: File manager ---
        print("\n[5/6] Opening file manager...")
        page.keyboard.press("Alt+F2")
        page.wait_for_timeout(1000)
        page.keyboard.type("thunar /home/nlp2cmd", delay=50)
        page.keyboard.press("Enter")
        page.wait_for_timeout(2000)
        logger.step("Opened Thunar file manager", page=page, extra={
            "path": "/home/nlp2cmd",
        })

        # --- Step 6: Firefox ---
        print("\n[6/6] Opening Firefox...")
        page.keyboard.press("Alt+F2")
        page.wait_for_timeout(1000)
        url = "https://github.com/wronai/nlp2cmd"
        page.keyboard.type(f"firefox {url}", delay=30)
        page.keyboard.press("Enter")
        page.wait_for_timeout(5000)
        logger.step("Opened Firefox browser", page=page, extra={"url": url})

        # --- Final ---
        page.wait_for_timeout(2000)
        logger.step("Final desktop state", page=page)

        context.close()
        browser.close()

    if record:
        stop_recording()
        logger.info("Video saved: docker/novnc/recordings/demo_session.mp4")

    md_path = logger.end(summary={
        "Apps controlled": "Terminal, Calculator, Text Editor, File Manager, Firefox",
        "Protocol": "Playwright → noVNC (websocket) → TigerVNC → XFCE4",
        "OS": "Ubuntu 22.04 in Docker",
    })

    print("\n" + "=" * 60)
    print("Demo Results")
    print("=" * 60)
    print(f"  Markdown report: {md_path}")
    print(f"  Screenshots: {output_dir}/desktop_gui_demo_screenshots/")
    if record:
        print(f"  Video: {output_dir}/demo_session.mp4")
    print("\n  Open the .md file to see the full report with inline thumbnails.")


def main():
    parser = argparse.ArgumentParser(description="NLP2CMD Desktop GUI Automation Demo")
    parser.add_argument("--record", action="store_true", help="Record video of the demo session")
    parser.add_argument("--headless", action="store_true", help="Run Playwright in headless mode")
    parser.add_argument("--url", default="http://localhost:6080", help="noVNC URL (default: http://localhost:6080)")
    args = parser.parse_args()

    ensure_playwright()
    run_demo(record=args.record, headless=args.headless, novnc_url=args.url)


if __name__ == "__main__":
    main()
