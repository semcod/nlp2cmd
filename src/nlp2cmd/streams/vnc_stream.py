"""
VNC Stream Adapter — desktop GUI control via VNC/noVNC + Playwright.

Usage:
    nlp2cmd --source vnc://host:5901 "open terminal"
    nlp2cmd --source novnc://host:6080 "click on calculator"
"""

from __future__ import annotations

from typing import Any, Optional

from nlp2cmd.streams.base import StreamAdapter, StreamResult, SourceURI


class VNCStreamAdapter(StreamAdapter):
    PROTOCOL = "vnc"

    def __init__(self, source: SourceURI):
        super().__init__(source)
        self._page = None
        self._browser = None
        self._pw = None

    def connect(self) -> StreamResult:
        is_novnc = self.source.scheme == "novnc" or (self.source.port and self.source.port in (6080, 6081))
        port = self.source.port or (6080 if is_novnc else 5901)
        host = self.source.host

        if is_novnc:
            # Connect via Playwright to noVNC web client
            try:
                from playwright.sync_api import sync_playwright
                self._pw = sync_playwright().start()
                self._browser = self._pw.chromium.launch(headless=True)
                self._page = self._browser.new_page(viewport={"width": 1280, "height": 800})
                url = f"http://{host}:{port}/vnc.html?autoconnect=true"
                self._page.goto(url, timeout=15000)
                self._page.wait_for_timeout(3000)
                try:
                    self._page.wait_for_selector("canvas", timeout=10000)
                except Exception:
                    pass
                self._connected = True
                return StreamResult(success=True, output=f"Connected to noVNC at {host}:{port}")
            except Exception as e:
                return StreamResult(success=False, error=str(e))
        else:
            self._connected = True
            return StreamResult(
                success=True,
                output=f"VNC target: {host}:{port} (use noVNC bridge for Playwright control)",
                data={"vnc_host": host, "vnc_port": port},
            )

    def execute(self, task: str, **kwargs) -> StreamResult:
        if self._page is None:
            return StreamResult(success=False, error="Not connected via noVNC. Use novnc:// scheme.")

        task_lower = task.lower()
        page = self._page

        if any(w in task_lower for w in ["type", "wpisz", "napisz"]):
            text = task.split(maxsplit=1)[-1] if len(task.split()) > 1 else task
            page.keyboard.type(text, delay=30)
            page.wait_for_timeout(500)
        elif any(w in task_lower for w in ["press", "naciśnij", "enter", "escape", "ctrl", "alt"]):
            key = self._extract_key(task)
            page.keyboard.press(key)
            page.wait_for_timeout(500)
        elif any(w in task_lower for w in ["open", "otwórz", "uruchom", "launch"]):
            page.keyboard.press("Alt+F2")
            page.wait_for_timeout(1000)
            app = task.split()[-1]
            page.keyboard.type(app, delay=50)
            page.keyboard.press("Enter")
            page.wait_for_timeout(2000)
        elif any(w in task_lower for w in ["screenshot", "zrzut"]):
            pass  # just capture below
        else:
            # Default: type as terminal command
            page.keyboard.type(task, delay=20)
            page.keyboard.press("Enter")
            page.wait_for_timeout(1000)

        png = page.screenshot()
        return StreamResult(success=True, output=f"VNC action: {task}", screenshot=png)

    def query(self, question: str, **kwargs) -> StreamResult:
        if self._page:
            png = self._page.screenshot()
            return StreamResult(success=True, output="VNC frame captured", screenshot=png)
        return StreamResult(success=True, output=f"VNC at {self.source.host}")

    def screenshot(self) -> Optional[bytes]:
        if self._page:
            return self._page.screenshot()
        return None

    def disconnect(self) -> None:
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()
        self._page = None
        self._browser = None
        self._pw = None
        self._connected = False

    def _extract_key(self, text: str) -> str:
        import re
        m = re.search(r"((?:ctrl|alt|shift|control|meta|super)\+\w+)", text, re.IGNORECASE)
        if m:
            return m.group(1).replace("ctrl", "Control")
        if "enter" in text.lower():
            return "Enter"
        if "escape" in text.lower() or "esc" in text.lower():
            return "Escape"
        if "tab" in text.lower():
            return "Tab"
        return "Enter"
