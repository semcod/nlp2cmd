"""
Desktop GUI Adapter for NLP2CMD.

Enables controlling desktop applications on any OS via:
- VNC/noVNC protocol (Docker containers, remote machines)
- Local xdotool/wmctrl (native Linux desktop)
- Playwright browser automation (multi-tab, persistent context)

Supported protocols:
- noVNC (websocket → VNC, via Docker or remote)
- Local (xdotool + wmctrl for native desktop)
- Direct VNC (future)
- RDP (future, via xfreerdp + noVNC bridge)

Capabilities:
- App launch/close/focus (any desktop app)
- Window management (minimize, maximize, switch, tile)
- Email client control (Thunderbird shortcuts)
- Multi-tab browser control (new tab, switch tab, close tab)
- Keyboard shortcuts and combos
- Desktop screenshot
- xdotool/wmctrl integration for native control

Usage:
    adapter = DesktopAdapter(vnc_url="http://localhost:6080")
    result = adapter.generate({"text": "otwórz Firefox i nowy tab"})
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from nlp2cmd.adapters.base import BaseDSLAdapter as BaseAdapter, SafetyPolicy

_DEBUG = os.environ.get("NLP2CMD_DEBUG", "").lower() in ("1", "true", "yes")


def _debug(msg: str) -> None:
    if _DEBUG:
        print(f"DEBUG [DesktopAdapter] {msg}", file=sys.stderr, flush=True)


@dataclass
class DesktopAction:
    """Structured desktop automation action."""
    app: str = ""
    action: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    fallback_shell: Optional[str] = None


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
    """Adapter for desktop GUI automation via VNC/noVNC + xdotool/wmctrl."""

    DSL_NAME = "desktop"

    # Intent detection keywords (expanded)
    INTENTS = {
        "open_app": [
            "open", "launch", "start", "run", "execute",
            "otwórz", "otworz", "uruchom", "odpal", "włącz", "wlacz",
        ],
        "type_text": [
            "type", "write", "enter", "input",
            "wpisz", "napisz", "wprowadź", "wprowadz",
        ],
        "click": [
            "click", "press", "tap", "select",
            "kliknij", "naciśnij", "naciskij", "wybierz",
        ],
        "navigate_menu": [
            "menu", "go to", "navigate", "find in menu",
            "przejdź", "przejdz", "znajdź w menu", "znajdz w menu",
        ],
        "screenshot": [
            "screenshot", "capture", "snap",
            "zrzut ekranu", "zrzut", "przechwytuj",
        ],
        "close_app": [
            "close", "quit", "exit",
            "zamknij", "zakończ", "zakoncz", "wyjdź", "wyjdz",
        ],
        "keyboard_shortcut": [
            "shortcut", "hotkey", "ctrl+", "alt+", "super+",
            "skrót", "skrot", "kombinacja",
        ],
        # --- New intents ---
        "new_tab": [
            "new tab", "nowy tab", "nowa karta", "nowa zakładka",
            "nowa zakladka", "open tab",
        ],
        "switch_tab": [
            "switch tab", "przełącz tab", "przelacz tab",
            "przełącz na", "przelacz na", "go to tab",
        ],
        "close_tab": [
            "close tab", "zamknij tab", "zamknij kartę", "zamknij karte",
        ],
        "minimize_all": [
            "minimize all", "zminimalizuj wszystko", "pokaż pulpit",
            "pokaz pulpit", "show desktop",
        ],
        "maximize": [
            "maximize", "zmaksymalizuj", "pełny ekran", "pelny ekran",
            "fullscreen", "powiększ", "powieksz",
        ],
        "focus_app": [
            "focus", "switch to", "bring to front",
            "przełącz do", "przelacz do", "skup na",
        ],
        "email_check": [
            "check mail", "check email", "get messages",
            "sprawdź pocztę", "sprawdz poczte", "sprawdź maile",
            "sprawdz maile", "pobierz pocztę", "pobierz poczte",
        ],
        "email_compose": [
            "compose", "new email", "new message", "write email",
            "napisz maila", "napisz email", "nowy mail", "nowa wiadomość",
            "nowa wiadomosc",
        ],
        "email_reply": [
            "reply", "respond", "odpowiedz", "odpisz",
        ],
        "email_forward": [
            "forward", "przekaż", "przekaz", "prześlij", "przeslij",
        ],
    }

    # Expanded app catalog — name → {launch, process, wmclass}
    KNOWN_APPS = {
        # Terminals
        "terminal": {"launch": "xfce4-terminal", "process": "xfce4-terminal", "wmclass": "Xfce4-terminal"},
        "konsola": {"launch": "xfce4-terminal", "process": "xfce4-terminal", "wmclass": "Xfce4-terminal"},
        "gnome-terminal": {"launch": "gnome-terminal", "process": "gnome-terminal", "wmclass": "Gnome-terminal"},
        "kitty": {"launch": "kitty", "process": "kitty", "wmclass": "kitty"},
        "alacritty": {"launch": "alacritty", "process": "alacritty", "wmclass": "Alacritty"},
        # Calculators
        "calculator": {"launch": "galculator", "process": "galculator", "wmclass": "Galculator"},
        "kalkulator": {"launch": "galculator", "process": "galculator", "wmclass": "Galculator"},
        # Editors
        "editor": {"launch": "mousepad", "process": "mousepad", "wmclass": "Mousepad"},
        "edytor": {"launch": "mousepad", "process": "mousepad", "wmclass": "Mousepad"},
        "notepad": {"launch": "mousepad", "process": "mousepad", "wmclass": "Mousepad"},
        "notatnik": {"launch": "mousepad", "process": "mousepad", "wmclass": "Mousepad"},
        "gedit": {"launch": "gedit", "process": "gedit", "wmclass": "Gedit"},
        "kate": {"launch": "kate", "process": "kate", "wmclass": "kate"},
        # File managers
        "file manager": {"launch": "thunar", "process": "thunar", "wmclass": "Thunar"},
        "menedżer plików": {"launch": "thunar", "process": "thunar", "wmclass": "Thunar"},
        "menadzer plikow": {"launch": "thunar", "process": "thunar", "wmclass": "Thunar"},
        "nautilus": {"launch": "nautilus", "process": "nautilus", "wmclass": "Nautilus"},
        "dolphin": {"launch": "dolphin", "process": "dolphin", "wmclass": "dolphin"},
        # Browsers
        "browser": {"launch": "firefox", "process": "firefox", "wmclass": "Firefox"},
        "przeglądarka": {"launch": "firefox", "process": "firefox", "wmclass": "Firefox"},
        "przegladarka": {"launch": "firefox", "process": "firefox", "wmclass": "Firefox"},
        "firefox": {"launch": "firefox", "process": "firefox", "wmclass": "Firefox"},
        "chrome": {"launch": "google-chrome", "process": "chrome", "wmclass": "Google-chrome"},
        "chromium": {"launch": "chromium-browser", "process": "chromium", "wmclass": "Chromium"},
        "brave": {"launch": "brave-browser", "process": "brave", "wmclass": "Brave-browser"},
        # Email clients
        "thunderbird": {"launch": "thunderbird", "process": "thunderbird", "wmclass": "Thunderbird"},
        "poczta": {"launch": "thunderbird", "process": "thunderbird", "wmclass": "Thunderbird"},
        "mail": {"launch": "thunderbird", "process": "thunderbird", "wmclass": "Thunderbird"},
        "evolution": {"launch": "evolution", "process": "evolution", "wmclass": "Evolution"},
        # Office
        "libreoffice": {"launch": "libreoffice", "process": "soffice", "wmclass": "libreoffice"},
        "libreoffice writer": {"launch": "libreoffice --writer", "process": "soffice", "wmclass": "libreoffice"},
        "libreoffice calc": {"launch": "libreoffice --calc", "process": "soffice", "wmclass": "libreoffice"},
        "writer": {"launch": "libreoffice --writer", "process": "soffice", "wmclass": "libreoffice"},
        "calc": {"launch": "libreoffice --calc", "process": "soffice", "wmclass": "libreoffice"},
        # Development
        "vscode": {"launch": "code", "process": "code", "wmclass": "Code"},
        "code": {"launch": "code", "process": "code", "wmclass": "Code"},
        "pycharm": {"launch": "pycharm", "process": "java", "wmclass": "jetbrains-pycharm"},
        # Media
        "vlc": {"launch": "vlc", "process": "vlc", "wmclass": "vlc"},
        "gimp": {"launch": "gimp", "process": "gimp", "wmclass": "Gimp"},
        # Settings
        "settings": {"launch": "xfce4-settings-manager", "process": "xfce4-settings-manager", "wmclass": "Xfce4-settings-manager"},
        "ustawienia": {"launch": "xfce4-settings-manager", "process": "xfce4-settings-manager", "wmclass": "Xfce4-settings-manager"},
    }

    # Backward compat — flat name→command mapping
    APP_COMMANDS = {name: info["launch"] for name, info in KNOWN_APPS.items()}

    # Email client keyboard shortcuts
    EMAIL_SHORTCUTS = {
        "thunderbird": {
            "check_mail": "ctrl+shift+t",
            "new_message": "ctrl+n",
            "reply": "ctrl+r",
            "reply_all": "ctrl+shift+r",
            "forward": "ctrl+l",
            "search": "ctrl+k",
            "address_book": "ctrl+shift+b",
            "send": "ctrl+Return",
        },
        "evolution": {
            "check_mail": "F9",
            "new_message": "ctrl+n",
            "reply": "ctrl+r",
            "forward": "ctrl+l",
            "search": "ctrl+f",
        },
    }

    # Window management commands (for local mode)
    WINDOW_COMMANDS = {
        "minimize_all": "wmctrl -k on",
        "restore_all": "wmctrl -k off",
        "list_windows": "wmctrl -l",
        "close_window": 'wmctrl -c "{title}"',
        "focus_window": 'wmctrl -a "{title}"',
        "maximize_window": 'wmctrl -r "{title}" -b add,maximized_vert,maximized_horz',
        "minimize_window": "xdotool getactivewindow windowminimize",
    }

    def __init__(
        self,
        *,
        vnc_url: str = "http://localhost:6080",
        vnc_password: str = "nlp2cmd",
        safety_policy: Optional[DesktopSafetyPolicy] = None,
        mode: str = "novnc",
    ):
        super().__init__(safety_policy=safety_policy or DesktopSafetyPolicy())
        self.vnc_url = vnc_url
        self.vnc_password = vnc_password
        self.last_action_ir = None
        self.mode = mode  # "novnc" or "local"

    def generate(self, plan: Dict[str, Any]) -> str:
        """Generate a desktop automation DSL command."""
        intent = plan.get("intent", "")
        text = plan.get("text", "")
        entities = plan.get("entities", {})

        _debug(f"generate(): intent={intent}, text='{text[:80]}'")

        # Auto-detect intent if not provided
        if not intent or intent == "unknown":
            intent, _ = self.detect_intent(text)
            _debug(f"auto-detected intent: {intent}")

        actions = self._build_actions(intent, text, entities)

        payload: dict[str, Any] = {
            "dsl": "desktop_dql.v1",
            "protocol": "novnc" if self.mode == "novnc" else "local",
            "actions": actions,
        }
        if self.mode == "novnc":
            payload["vnc_url"] = self.vnc_url

        return json.dumps(payload, ensure_ascii=False)

    def _build_actions(self, intent: str, text: str, entities: dict) -> list[dict]:
        """Build action sequence based on intent."""
        actions: list[dict[str, Any]] = []

        if intent == "open_app":
            app_name = entities.get("app", self._extract_app_name(text))
            launch_cmd = self.APP_COMMANDS.get(app_name.lower(), app_name)
            _debug(f"open_app: {app_name} → {launch_cmd}")

            if self.mode == "local":
                actions.append({"action": "shell", "command": f"{launch_cmd} &"})
            else:
                actions.append({"action": "keyboard_shortcut", "keys": "Alt+F2"})
                actions.append({"action": "wait", "ms": 1000})
                actions.append({"action": "type", "text": launch_cmd})
                actions.append({"action": "key", "key": "Enter"})
            actions.append({"action": "wait", "ms": 2000})

            # Check for follow-up actions in text
            extra = self._detect_followup_actions(text, app_name)
            actions.extend(extra)

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
            if self.mode == "local":
                actions.append({"action": "shell", "command": "gnome-screenshot -f /tmp/nlp2cmd_screenshot.png"})
            else:
                actions.append({"action": "screenshot", "path": "/home/nlp2cmd/screenshot.png"})

        elif intent == "close_app":
            app_name = self._extract_app_name(text)
            close_all = "wszystk" in text.lower() or "all" in text.lower()
            if close_all and self.mode == "local":
                app_info = self.KNOWN_APPS.get(app_name.lower(), {})
                wmclass = app_info.get("wmclass", app_name) if isinstance(app_info, dict) else app_name
                actions.append({"action": "shell", "command": f'wmctrl -c "{wmclass}"'})
            else:
                actions.append({"action": "keyboard_shortcut", "keys": "Alt+F4"})

        elif intent == "new_tab":
            actions.append({"action": "keyboard_shortcut", "keys": "ctrl+t"})
            actions.append({"action": "wait", "ms": 500})
            url = self._extract_url(text)
            if url:
                actions.append({"action": "type", "text": url})
                actions.append({"action": "key", "key": "Enter"})
                actions.append({"action": "wait", "ms": 2000})

        elif intent == "switch_tab":
            tab_filter = entities.get("filter", self._extract_tab_filter(text))
            if tab_filter:
                actions.append({"action": "switch_tab", "filter": tab_filter})
            else:
                actions.append({"action": "keyboard_shortcut", "keys": "ctrl+Tab"})

        elif intent == "close_tab":
            actions.append({"action": "keyboard_shortcut", "keys": "ctrl+w"})

        elif intent == "minimize_all":
            if self.mode == "local":
                actions.append({"action": "shell", "command": "wmctrl -k on"})
            else:
                actions.append({"action": "keyboard_shortcut", "keys": "super+d"})

        elif intent == "maximize":
            if self.mode == "local":
                actions.append({"action": "shell", "command": 'wmctrl -r ":ACTIVE:" -b add,maximized_vert,maximized_horz'})
            else:
                actions.append({"action": "keyboard_shortcut", "keys": "super+Up"})

        elif intent == "focus_app":
            app_name = self._extract_app_name(text)
            app_info = self.KNOWN_APPS.get(app_name.lower(), {})
            wmclass = app_info.get("wmclass", app_name) if isinstance(app_info, dict) else app_name
            if self.mode == "local":
                actions.append({"action": "shell", "command": f'wmctrl -a "{wmclass}"'})
            else:
                launch = app_info.get("launch", app_name) if isinstance(app_info, dict) else app_name
                actions.append({"action": "keyboard_shortcut", "keys": "Alt+F2"})
                actions.append({"action": "wait", "ms": 500})
                actions.append({"action": "type", "text": launch})
                actions.append({"action": "key", "key": "Enter"})

        # --- Email intents ---
        elif intent == "email_check":
            actions.extend(self._build_email_actions("check_mail", text))

        elif intent == "email_compose":
            actions.extend(self._build_email_compose(text, entities))

        elif intent == "email_reply":
            actions.extend(self._build_email_actions("reply", text))

        elif intent == "email_forward":
            actions.extend(self._build_email_actions("forward", text))

        else:
            # Fallback: treat as terminal command
            if self.mode == "local":
                actions.append({"action": "shell", "command": text})
            else:
                actions.append({"action": "keyboard_shortcut", "keys": "Control+Alt+t"})
                actions.append({"action": "wait", "ms": 1500})
                actions.append({"action": "type", "text": text})
                actions.append({"action": "key", "key": "Enter"})

        return actions

    # ── Email helpers ────────────────────────────────────────────────

    def _build_email_actions(self, email_action: str, text: str) -> list[dict]:
        """Build email client action sequence."""
        actions: list[dict[str, Any]] = []

        client = "thunderbird"
        if "evolution" in text.lower():
            client = "evolution"

        shortcuts = self.EMAIL_SHORTCUTS.get(client, {})

        # Launch/focus the email client
        app_info = self.KNOWN_APPS.get(client, {})
        launch = app_info.get("launch", client) if isinstance(app_info, dict) else client
        if self.mode == "local":
            actions.append({"action": "shell", "command": f"{launch} &"})
        else:
            actions.append({"action": "keyboard_shortcut", "keys": "Alt+F2"})
            actions.append({"action": "wait", "ms": 500})
            actions.append({"action": "type", "text": launch})
            actions.append({"action": "key", "key": "Enter"})
        actions.append({"action": "wait", "ms": 2000})

        shortcut = shortcuts.get(email_action)
        if shortcut:
            actions.append({"action": "keyboard_shortcut", "keys": shortcut})
            actions.append({"action": "wait", "ms": 1000})

        return actions

    def _build_email_compose(self, text: str, entities: dict) -> list[dict]:
        """Build email composition sequence with recipient/subject/body."""
        actions = self._build_email_actions("new_message", text)

        recipient = entities.get("recipient") or self._extract_email_address(text)
        if recipient:
            actions.append({"action": "type", "text": recipient})
            actions.append({"action": "key", "key": "Tab"})
            actions.append({"action": "wait", "ms": 300})

        subject = entities.get("subject") or self._extract_email_subject(text)
        if subject:
            actions.append({"action": "key", "key": "Tab"})  # skip CC
            actions.append({"action": "type", "text": subject})
            actions.append({"action": "key", "key": "Tab"})
            actions.append({"action": "wait", "ms": 300})

        body = entities.get("body") or self._extract_email_body(text)
        if body:
            actions.append({"action": "type", "text": body})

        return actions

    def _detect_followup_actions(self, text: str, app_name: str) -> list[dict]:
        """Detect follow-up actions after app launch."""
        extra: list[dict[str, Any]] = []
        text_lower = text.lower()

        # "and type X" pattern
        m = re.search(r"(?:i\s+wpisz|and\s+type|i\s+napisz)\s+(.+?)$", text_lower)
        if m:
            extra.append({"action": "type", "text": m.group(1).strip()})
            extra.append({"action": "key", "key": "Enter"})

        # "and go to URL" pattern
        url = self._extract_url(text)
        if url and app_name.lower() in ("browser", "firefox", "chrome", "przeglądarka", "przegladarka"):
            extra.append({"action": "type", "text": url})
            extra.append({"action": "key", "key": "Enter"})
            extra.append({"action": "wait", "ms": 2000})

        # "and check mail" pattern
        if any(kw in text_lower for kw in ["sprawdź", "sprawdz", "check", "pobierz"]):
            if app_name.lower() in ("thunderbird", "poczta", "mail", "evolution"):
                client = "evolution" if "evolution" in text_lower else "thunderbird"
                shortcut = self.EMAIL_SHORTCUTS.get(client, {}).get("check_mail", "")
                if shortcut:
                    extra.append({"action": "keyboard_shortcut", "keys": shortcut})

        return extra

    # ── Intent & extraction ──────────────────────────────────────────

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
        for app_name in self.KNOWN_APPS:
            if app_name in text_lower:
                return app_name
        m = re.search(
            r"(?:open|launch|start|otwórz|otworz|uruchom|włącz|wlacz)\s+(\S+)",
            text_lower,
        )
        return m.group(1) if m else "terminal"

    def _extract_quoted_text(self, text: str) -> str:
        """Extract text from quotes."""
        m = re.search(r'"([^"]*)"', text)
        if m:
            return m.group(1)
        m = re.search(r"'([^']*)'", text)
        if m:
            return m.group(1)
        m = re.search(r"(?:type|write|wpisz|napisz)\s+(.+)", text, re.IGNORECASE)
        return m.group(1).strip() if m else text

    def _extract_shortcut(self, text: str) -> str:
        """Extract keyboard shortcut from text."""
        m = re.search(r"((?:ctrl|alt|shift|super|control|meta)\+[\w+]+)", text, re.IGNORECASE)
        if m:
            return m.group(1)
        return "Enter"

    @staticmethod
    def _extract_url(text: str) -> Optional[str]:
        """Extract URL from text."""
        m = re.search(r"(https?://\S+)", text, re.IGNORECASE)
        if m:
            return m.group(1).rstrip(".,)")
        m = re.search(
            r"\b([a-z0-9][a-z0-9-]*(?:\.[a-z0-9][a-z0-9-]*)+)(/\S*)?\b",
            text, re.IGNORECASE,
        )
        if m:
            return f"https://{m.group(1)}{m.group(2) or ''}"
        return None

    @staticmethod
    def _extract_tab_filter(text: str) -> Optional[str]:
        """Extract tab filter (e.g. 'tab z gmail' → 'gmail')."""
        patterns = [
            r"(?:tab|kart[aęy]|zakładk[aęi]|zakladk[aei])\s+(?:z|with|na|o)\s+(\S+)",
            r"(?:przełącz|przelacz|switch)\s+(?:na|to|do)\s+(\S+)",
        ]
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                return m.group(1)
        return None

    @staticmethod
    def _extract_email_address(text: str) -> Optional[str]:
        """Extract email address from text."""
        m = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
        return m.group(0) if m else None

    @staticmethod
    def _extract_email_subject(text: str) -> Optional[str]:
        """Extract email subject from text."""
        patterns = [
            r"""(?:z\s+tematem|temat|subject|with\s+subject)\s+['"](.+?)['"]""",
            r"(?:z\s+tematem|temat|subject|with\s+subject)\s+(\S+(?:\s+\S+){0,5})",
        ]
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return None

    @staticmethod
    def _extract_email_body(text: str) -> Optional[str]:
        """Extract email body text from quoted content."""
        patterns = [
            r"""(?:słowami|treścią|treść|body|content)\s+['"](.+?)['"]""",
            r"(?:słowami|z\s+treścią)\s+(.+?)$",
        ]
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return None

    # ── Shell command builders (for local mode) ──────────────────────

    @staticmethod
    def build_xdotool_chain(actions: list[dict]) -> str:
        """Convert action list to xdotool command chain."""
        parts: list[str] = []
        for action in actions:
            act = action.get("action", "")
            if act == "type":
                text = action.get("text", "")
                delay = action.get("delay", 30)
                parts.append(f'xdotool type --delay {delay} "{text}"')
            elif act in ("key", "keyboard_shortcut"):
                key = action.get("key") or action.get("keys", "Return")
                key = key.replace("Control", "ctrl")
                parts.append(f"xdotool key {key}")
            elif act == "wait":
                ms = action.get("ms", 1000)
                parts.append(f"sleep {ms / 1000:.1f}")
            elif act == "shell":
                parts.append(action.get("command", ""))
        return " && ".join(parts)

    @staticmethod
    def build_wmctrl_command(action: DesktopAction) -> str:
        """Build wmctrl command for window management."""
        if action.action == "focus":
            return f'wmctrl -a "{action.app}"'
        elif action.action == "close":
            return f'wmctrl -c "{action.app}"'
        elif action.action == "minimize_all":
            return "wmctrl -k on"
        elif action.action == "maximize":
            return f'wmctrl -r "{action.app}" -b add,maximized_vert,maximized_horz'
        return ""

    def validate_syntax(self, command: str) -> dict[str, Any]:
        """Validate desktop_dql.v1 JSON command."""
        try:
            payload = json.loads(command)
        except Exception as e:
            return {"valid": False, "errors": [f"Invalid JSON: {e}"]}

        if not isinstance(payload, dict) or payload.get("dsl") != "desktop_dql.v1":
            return {"valid": False, "errors": ["Not desktop_dql.v1"]}

        if not isinstance(payload.get("actions"), list):
            return {"valid": False, "errors": ["Missing actions array"]}

        return {"valid": True, "errors": []}

    def get_supported_intents(self) -> list[str]:
        return list(self.INTENTS.keys())
