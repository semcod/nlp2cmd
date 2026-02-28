from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from rich.console import Console

from nlp2cmd.pipeline_runner_utils import (
    _debug,
    _DEBUG,
    _with_epipe_retry,
    _field_attrs,
    _is_junk_field,
    _is_contact_relevant_field,
    _looks_like_comment_form,
    _filter_form_fields,
    _MarkdownConsoleWrapper,
    ShellExecutionPolicy,
    RunnerResult,
    get_timestamp,
    ensure_dir,
    ask_for_screenshot,
    take_screenshot,
    VideoRecorder,
    ask_for_video_recording,
)
from nlp2cmd.utils.yaml_compat import yaml


class DesktopExecutionMixin:
    """Desktop automation and static utility methods for PipelineRunner."""

    @staticmethod
    def _dismiss_popups(page, schema_loader=None) -> None:
        """Try to dismiss common popups and cookie consents."""
        from nlp2cmd.web_schema.form_data_loader import FormDataLoader
        
        # Load dismiss selectors from schema
        loader = schema_loader if schema_loader is not None else FormDataLoader()
        dismiss_selectors = loader.get_dismiss_selectors()
        
        for selector in dismiss_selectors:
            try:
                page.wait_for_selector(selector, state="visible", timeout=1000)
                page.click(selector, timeout=1000)
                page.wait_for_timeout(500)

                try:
                    loader.add_dismiss_selector(selector)
                except Exception:
                    pass
                break
            except:
                continue

    @staticmethod
    def _extract_json_from_llm_response(text: str) -> Optional[dict[str, Any]]:
        if not isinstance(text, str) or not text.strip():
            return None

        raw = text.strip()
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, flags=re.DOTALL | re.IGNORECASE)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass

        # Fallback: try parsing the whole text as JSON
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

        # Fallback: find first { ... } block
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(raw[start:end + 1])
            except Exception:
                pass

        return None

    @staticmethod
    def _detect_desktop_backend() -> str:
        """Detect best desktop automation backend: 'ydotool', 'xdotool', or 'none'."""
        session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
        is_wayland = session_type == "wayland" or bool(os.environ.get("WAYLAND_DISPLAY"))
        if is_wayland and shutil.which("ydotool"):
            return "ydotool"
        if shutil.which("xdotool"):
            return "xdotool"
        if shutil.which("wmctrl"):
            return "wmctrl"  # wmctrl only for focus, not type/key
        return "none"

    def _execute_desktop_plan_step(self, step, variables: dict) -> Optional[str]:
        """Execute an ActionPlan step via local desktop automation.

        Supports three backends:
        - ydotool: works on Wayland (requires ydotoold daemon)
        - xdotool: works on X11
        - wmctrl: X11 window management only
        """
        params = self._resolve_plan_variables(getattr(step, "params", {}) or {}, variables)
        action = str(getattr(step, "action", "") or "")
        backend = self._detect_desktop_backend()

        if backend == "none":
            raise ValueError(
                "No desktop automation tool available. "
                "On Wayland: sudo apt install ydotool && sudo systemctl enable --now ydotool. "
                "On X11: sudo apt install xdotool wmctrl."
            )

        if action == "desktop_focus_app":
            title = str(params.get("title") or "Firefox")
            if backend == "ydotool":
                # ydotool can't focus windows; try gdbus on GNOME
                _debug(f"desktop_focus_app: ydotool can't focus windows, trying Alt+Tab")
                subprocess.run(["ydotool", "key", "56:1", "15:1", "15:0", "56:0"], check=False)
                time.sleep(0.3)
                return None
            if shutil.which("wmctrl") is not None:
                subprocess.run(["wmctrl", "-a", title], check=True)
                return None
            # xdotool fallback
            candidates = [
                ("--name", title),
                ("--name", "Mozilla Firefox"),
                ("--class", title),
                ("--class", "firefox"),
                ("--class", "Navigator"),
            ]
            win_id = ""
            for flag, value in candidates:
                try:
                    out = subprocess.check_output(
                        ["xdotool", "search", "--onlyvisible", flag, value],
                        stderr=subprocess.DEVNULL,
                        text=True,
                    )
                    win_id = (out.strip().splitlines() or [""])[0].strip()
                    if win_id:
                        break
                except Exception:
                    continue
            if win_id:
                subprocess.run(["xdotool", "windowactivate", "--sync", win_id], check=True)
            else:
                _debug(f"desktop_focus_app: could not find visible window for '{title}', continuing")
            return None

        if action == "desktop_shortcut":
            keys = str(params.get("keys") or "").strip() or "ctrl+t"
            if backend == "ydotool":
                ydotool_keys = self._xdotool_keys_to_ydotool(keys)
                subprocess.run(["ydotool", "key"] + ydotool_keys, check=True)
            else:
                subprocess.run(["xdotool", "key", keys], check=True)
            return None

        if action == "desktop_key":
            key = str(params.get("key") or "Return").strip() or "Return"
            if backend == "ydotool":
                ydotool_keys = self._xdotool_keys_to_ydotool(key)
                subprocess.run(["ydotool", "key"] + ydotool_keys, check=True)
            else:
                subprocess.run(["xdotool", "key", key], check=True)
            return None

        if action == "desktop_type":
            txt = str(params.get("text") or "")
            if not txt.strip():
                return None
            if backend == "ydotool":
                subprocess.run(["ydotool", "type", "--key-delay", "20", txt], check=True)
            else:
                subprocess.run(["xdotool", "type", "--delay", "20", txt], check=True)
            return None

        if action == "wait":
            ms = int(params.get("ms", 500))
            time.sleep(max(ms, 0) / 1000.0)
            return None

        if action == "desktop_wait":
            ms = int(params.get("ms", 500))
            time.sleep(max(ms, 0) / 1000.0)
            return None

        if action == "open_firefox_tab":
            url = str(params.get("url") or "").strip()
            if not url:
                return None
            if shutil.which("firefox") is None:
                raise ValueError("Firefox executable not found in PATH")

            # Open a new tab in existing Firefox instance (remote command).
            # This is more reliable than synthetic key events.
            try:
                subprocess.run(["firefox", "--new-tab", url], check=True)
            except Exception:
                subprocess.run(["firefox", "--new-window", url], check=True)
            return None

        if action == "check_session":
            # In desktop mode we opened the URL in the user's real Firefox.
            # We don't have a Playwright page to inspect, so just inform the user.
            service = params.get("service", "unknown")
            console = Console()
            console.print(f"  [dim]🔍 Strona {service} została otwarta w Twojej przeglądarce.[/dim]")
            console.print(f"  [dim]   Sprawdź, czy jesteś zalogowany. Jeśli nie — zaloguj się teraz.[/dim]")
            # Give user time to check
            time.sleep(2)
            return "desktop_skipped"

        # Reuse safe non-desktop steps
        if action == "echo":
            msg = str(params.get("message", "") or params.get("text", ""))
            if msg:
                _debug(msg)
                console = Console()
                for line in msg.split("\n"):
                    console.print(f"  [dim]{line}[/dim]")
            return None

        if action == "prompt_secret":
            from nlp2cmd.automation.action_planner import ActionStep as _ActionStep
            _step = _ActionStep(
                action="prompt_secret",
                params=params,
                store_as=getattr(step, "store_as", None),
                retry_on_fail=getattr(step, "retry_on_fail", False),
            )
            console = Console()
            console.print(f"  [dim]🔐 prompt_secret: env_var={params.get('env_var', '?')}[/dim]")
            result = self._execute_plan_step(page=None, context=None, step=_step, variables=variables)
            if result:
                console.print(f"  [dim]   ✓ Otrzymano klucz ({len(result)} znaków)[/dim]")
                # Validate key pattern if available in variables
                key_pattern = variables.get("_key_pattern", "")
                if key_pattern:
                    import re as _re
                    if _re.match(key_pattern, result):
                        console.print(f"  [green]   ✓ Klucz pasuje do wzorca: {key_pattern}[/green]")
                    else:
                        console.print(f"  [yellow]   ⚠ Klucz NIE pasuje do wzorca: {key_pattern}[/yellow]")
                        console.print(f"  [yellow]     Kontynuuję mimo to — sprawdź poprawność klucza.[/yellow]")
            else:
                console.print(f"  [red]   ✗ Nie otrzymano klucza![/red]")
            return result

        if action == "save_env":
            from nlp2cmd.automation.action_planner import ActionStep as _ActionStep
            _step = _ActionStep(
                action="save_env",
                params=params,
                store_as=getattr(step, "store_as", None),
                retry_on_fail=getattr(step, "retry_on_fail", False),
            )
            console = Console()
            var_name = params.get("var_name", "?")
            file_path = params.get("file", ".env")
            console.print(f"  [dim]💾 save_env: {var_name} → {file_path}[/dim]")
            result = self._execute_plan_step(page=None, context=None, step=_step, variables=variables)
            if result:
                console.print(f"  [green]   ✓ Zapisano {var_name} ({len(result)} znaków) do {file_path}[/green]")
            else:
                console.print(f"  [red]   ✗ Nie zapisano wartości![/red]")
            return result

        if action == "verify_env":
            console = Console()
            var_name = params.get("var_name", "UNKNOWN")
            file_path = params.get("file", ".env")
            return self._do_verify_env(console, var_name, file_path, variables)

        raise ValueError(f"Unsupported desktop plan action: {action}")

    @staticmethod
    def _xdotool_keys_to_ydotool(keys: str) -> list[str]:
        """Convert xdotool key names to ydotool keycode sequences.

        ydotool uses Linux input event keycodes (evdev), not X11 keysyms.
        Format: keycode:1 (press), keycode:0 (release).
        """
        _KEYMAP = {
            "ctrl": "29", "control": "29",
            "alt": "56", "shift": "42", "super": "125",
            "return": "28", "enter": "28",
            "tab": "15", "escape": "1", "esc": "1",
            "space": "57", "backspace": "14", "delete": "111",
            "up": "103", "down": "108", "left": "105", "right": "106",
            "home": "102", "end": "107",
            "pageup": "104", "page_up": "104",
            "pagedown": "109", "page_down": "109",
            "f1": "59", "f2": "60", "f3": "61", "f4": "62",
            "f5": "63", "f6": "64", "f7": "65", "f8": "66",
            "f9": "67", "f10": "68", "f11": "87", "f12": "88",
        }
        # Letters a-z
        for i, c in enumerate("abcdefghijklmnopqrstuvwxyz"):
            _KEYMAP[c] = str(30 + i if i < 12 else 44 + i - 12 if i < 24 else 50 + i - 24)
        # More accurate letter keycodes
        _LETTER_CODES = {
            "a": "30", "b": "48", "c": "46", "d": "32", "e": "18", "f": "33",
            "g": "34", "h": "35", "i": "23", "j": "36", "k": "37", "l": "38",
            "m": "50", "n": "49", "o": "24", "p": "25", "q": "16", "r": "19",
            "s": "31", "t": "20", "u": "22", "v": "47", "w": "17", "x": "45",
            "y": "21", "z": "44",
        }
        _KEYMAP.update(_LETTER_CODES)

        parts = keys.lower().replace("+", " ").split()
        codes = [_KEYMAP.get(p, p) for p in parts]

        # Build press-all then release-all sequence
        result = []
        for code in codes:
            result.append(f"{code}:1")
        for code in reversed(codes):
            result.append(f"{code}:0")
        return result

    @staticmethod
    def _normalize_llm_article_selector_payload(payload: dict[str, Any]) -> dict[str, list[str]]:
        def _clean_list(value: Any) -> list[str]:
            if not isinstance(value, list):
                return []
            out: list[str] = []
            for s in value:
                if isinstance(s, str) and s.strip():
                    out.append(s.strip())
            return out

        link_selectors = _clean_list(payload.get("article_link_selectors"))
        content_selectors = _clean_list(payload.get("article_content_selectors"))
        return {
            "article_link_selectors": link_selectors,
            "article_content_selectors": content_selectors,
        }

    @staticmethod
    def _collect_page_links_for_llm(page, *, limit: int = 40) -> list[dict[str, str]]:
        try:
            items = page.evaluate(
                r"""(limit) => {
  const out = [];
  const nodes = Array.from(document.querySelectorAll('a[href]'));
  for (const a of nodes) {
    if (out.length >= limit) break;
    const href = a.getAttribute('href') || '';
    const text = (a.textContent || '').trim().replace(/\s+/g, ' ');
    if (!href) continue;
    out.push({href, text});
  }
  return out;
}""",
                limit,
            )
        except Exception:
            return []

        if not isinstance(items, list):
            return []
        out: list[dict[str, str]] = []
        for it in items:
            if not isinstance(it, dict):
                continue
            href = it.get("href")
            text = it.get("text")
            if isinstance(href, str) and isinstance(text, str):
                out.append({"href": href, "text": text})
        return out

