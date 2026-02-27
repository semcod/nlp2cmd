"""
Desktop GUI Adapter for NLP2CMD.

Enables controlling desktop applications on any OS via VNC/noVNC protocol.
Playwright connects to a noVNC web client, which proxies to a VNC server
running inside a Docker container or remote machine.

Supported protocols:
- noVNC (websocket → VNC, via Docker or remote)
- Direct VNC (future)
- RDP (future, via xfreerdp + noVNC bridge)

Usage:
    adapter = DesktopAdapter(vnc_url="http://localhost:6080")
    nlp = NLP2CMD(adapter=adapter)
    result = nlp.transform("open calculator and type 2+2")
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from nlp2cmd.adapters.base import BaseAdapter, SafetyPolicy


class DesktopSafetyPolicy(SafetyPolicy):
    """Safety policy for desktop GUI automation."""

    # Actions that require confirmation
    DANGEROUS_PATTERNS = [
        r"\bshutdown\b",
        r"\breboot\b",
        r"\brm\s+-rf\b",
        r"\bformat\b",
        r"\bfdisk\b",
        r"\bmkfs\b",
        r"\bdd\s+if=",
        r"\bsudo\s+rm\b",
    ]

    def validate(self, command: str) -> dict[str, Any]:
        cmd_lower = command.lower()
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, cmd_lower):
                return {
                    "safe": False,
                    "reason": f"Dangerous desktop command detected: {pattern}",
                    "requires_confirm": True,
                }
        return {"safe": True}


class DesktopAdapter(BaseAdapter):
    """Adapter for desktop GUI automation via VNC/noVNC."""

    DSL_NAME = "desktop"

    # Intent detection keywords
    INTENTS = {
        "open_app": [
            "open", "launch", "start", "run", "execute",
            "otwórz", "uruchom", "odpal", "włącz",
        ],
        "type_text": [
            "type", "write", "enter", "input",
            "wpisz", "napisz", "wprowadź",
        ],
        "click": [
            "click", "press", "tap", "select",
            "kliknij", "naciśnij", "wybierz",
        ],
        "navigate_menu": [
            "menu", "go to", "navigate", "find in menu",
            "przejdź", "znajdź w menu",
        ],
        "screenshot": [
            "screenshot", "capture", "snap",
            "zrzut ekranu", "przechwytuj",
        ],
        "close_app": [
            "close", "quit", "exit",
            "zamknij", "zakończ", "wyjdź",
        ],
        "keyboard_shortcut": [
            "shortcut", "hotkey", "ctrl+", "alt+", "super+",
            "skrót", "kombinacja",
        ],
    }

    # Common app name → launch command mapping
    APP_COMMANDS = {
        "terminal": "xfce4-terminal",
        "konsola": "xfce4-terminal",
        "calculator": "galculator",
        "kalkulator": "galculator",
        "editor": "mousepad",
        "edytor": "mousepad",
        "notepad": "mousepad",
        "notatnik": "mousepad",
        "file manager": "thunar",
        "menedżer plików": "thunar",
        "browser": "firefox",
        "przeglądarka": "firefox",
        "firefox": "firefox",
        "chrome": "google-chrome",
        "settings": "xfce4-settings-manager",
        "ustawienia": "xfce4-settings-manager",
    }

    def __init__(
        self,
        *,
        vnc_url: str = "http://localhost:6080",
        vnc_password: str = "nlp2cmd",
        safety_policy: Optional[DesktopSafetyPolicy] = None,
    ):
        super().__init__(safety_policy=safety_policy or DesktopSafetyPolicy())
        self.vnc_url = vnc_url
        self.vnc_password = vnc_password
        self.last_action_ir = None

    def generate(self, plan: Dict[str, Any]) -> str:
        """Generate a desktop automation DSL command."""
        intent = plan.get("intent", "")
        text = plan.get("text", "")
        entities = plan.get("entities", {})

        actions = []

        if intent == "open_app":
            app_name = entities.get("app", self._extract_app_name(text))
            launch_cmd = self.APP_COMMANDS.get(app_name.lower(), app_name)
            actions.append({"action": "keyboard_shortcut", "keys": "Alt+F2"})
            actions.append({"action": "wait", "ms": 1000})
            actions.append({"action": "type", "text": launch_cmd})
            actions.append({"action": "key", "key": "Enter"})
            actions.append({"action": "wait", "ms": 2000})

        elif intent == "type_text":
            text_to_type = entities.get("text", self._extract_quoted_text(text))
            actions.append({"action": "type", "text": text_to_type, "delay": 30})

        elif intent == "click":
            target = entities.get("target", "")
            actions.append({"action": "click_text", "text": target})

        elif intent == "keyboard_shortcut":
            keys = entities.get("keys", self._extract_shortcut(text))
            actions.append({"action": "keyboard_shortcut", "keys": keys})

        elif intent == "screenshot":
            actions.append({"action": "screenshot", "path": "/home/nlp2cmd/screenshot.png"})

        elif intent == "close_app":
            actions.append({"action": "keyboard_shortcut", "keys": "Alt+F4"})

        else:
            # Fallback: treat as terminal command
            actions.append({"action": "keyboard_shortcut", "keys": "Control+Alt+t"})
            actions.append({"action": "wait", "ms": 1500})
            actions.append({"action": "type", "text": text})
            actions.append({"action": "key", "key": "Enter"})

        payload = {
            "dsl": "desktop_dql.v1",
            "protocol": "novnc",
            "vnc_url": self.vnc_url,
            "actions": actions,
        }

        return json.dumps(payload, ensure_ascii=False)

    def detect_intent(self, text: str) -> tuple[str, float]:
        """Detect desktop automation intent from text."""
        text_lower = text.lower()
        best_intent = "unknown"
        best_score = 0.0

        for intent, keywords in self.INTENTS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > best_score:
                best_score = score
                best_intent = intent

        confidence = min(best_score / 2.0, 1.0) if best_score > 0 else 0.0
        return best_intent, confidence

    def _extract_app_name(self, text: str) -> str:
        """Extract application name from text."""
        text_lower = text.lower()
        for app_name in self.APP_COMMANDS:
            if app_name in text_lower:
                return app_name
        # Fallback: extract word after "open"/"launch"
        m = re.search(r"(?:open|launch|start|otwórz|uruchom)\s+(\w+)", text_lower)
        return m.group(1) if m else "terminal"

    def _extract_quoted_text(self, text: str) -> str:
        """Extract text from quotes."""
        m = re.search(r'"([^"]*)"', text)
        if m:
            return m.group(1)
        m = re.search(r"'([^']*)'", text)
        if m:
            return m.group(1)
        # Fallback: everything after "type"/"write"
        m = re.search(r"(?:type|write|wpisz|napisz)\s+(.+)", text, re.IGNORECASE)
        return m.group(1).strip() if m else text

    def _extract_shortcut(self, text: str) -> str:
        """Extract keyboard shortcut from text."""
        m = re.search(r"((?:ctrl|alt|shift|super|control|meta)\+[\w+]+)", text, re.IGNORECASE)
        if m:
            return m.group(1)
        return "Enter"

    def get_supported_intents(self) -> list[str]:
        return list(self.INTENTS.keys())
