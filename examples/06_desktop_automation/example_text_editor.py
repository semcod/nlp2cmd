#!/usr/bin/env python3
"""
Example: Text editor automation via noVNC.

Opens Mousepad editor, writes a document, saves it, and logs to Markdown.

Prerequisites:
    docker compose -f docker/novnc/docker-compose.yml up -d

Usage:
    python3 examples/06_desktop_automation/example_text_editor.py
"""

from __future__ import annotations
import sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from nlp2cmd.cli.session_logger import SessionLogger


def main():
    from playwright.sync_api import sync_playwright

    out = Path(__file__).parent
    logger = SessionLogger("text_editor_session", output_dir=out, thumbnail_width=256)
    logger.start("Text Editor Automation Example", description="Write and save a document in Mousepad via noVNC")

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

        # Open Mousepad via Alt+F2 run dialog
        page.keyboard.press("Alt+F2")
        page.wait_for_timeout(1000)
        page.keyboard.type("mousepad", delay=50)
        page.keyboard.press("Enter")
        page.wait_for_timeout(2000)
        logger.step("Opened Mousepad text editor", page=page)

        # Write a structured document
        sections = [
            ("# Project Report\n\n", "Heading"),
            ("Author: NLP2CMD Automation\n", "Author line"),
            ("Date: 2026-02-27\n\n", "Date"),
            ("## Summary\n\n", "Section header"),
            ("This report was generated automatically by NLP2CMD\n", "Body text"),
            ("controlling a Linux desktop via noVNC protocol.\n\n", "Body continued"),
            ("## System Info\n\n", "Another section"),
            ("- OS: Ubuntu 22.04 (Docker)\n", "List item 1"),
            ("- Desktop: XFCE4\n", "List item 2"),
            ("- VNC: TigerVNC + noVNC\n", "List item 3"),
            ("- Automation: Playwright\n\n", "List item 4"),
            ("## Conclusion\n\n", "Final section"),
            ("Desktop GUI automation works across any OS.\n", "Conclusion"),
        ]

        for text, desc in sections:
            page.keyboard.type(text, delay=5)
            page.wait_for_timeout(200)

        logger.step("Document written", page=page)
        logger.code("".join(t for t, _ in sections), language="markdown")

        # Save with Ctrl+S
        page.keyboard.press("Control+s")
        page.wait_for_timeout(1500)
        filename = "/home/nlp2cmd/project_report.md"
        page.keyboard.type(filename, delay=30)
        page.keyboard.press("Enter")
        page.wait_for_timeout(1000)
        logger.step("Document saved", page=page, extra={"filename": filename})

        # Select all + copy (to verify content)
        page.keyboard.press("Control+a")
        page.wait_for_timeout(500)
        logger.step("Selected all text (Ctrl+A)", page=page)

        browser.close()

    md_path = logger.end(summary={
        "Lines written": len(sections),
        "Application": "Mousepad",
        "File saved": filename,
    })
    print(f"\nReport: {md_path}")


if __name__ == "__main__":
    main()
