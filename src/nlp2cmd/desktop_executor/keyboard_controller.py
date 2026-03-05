"""Keyboard Controller for keyboard automation."""

from __future__ import annotations
import subprocess
import logging
from typing import Optional

from .base import DesktopBackend, ActionResult

log = logging.getLogger("nlp2cmd.desktop_executor.keyboard")


class KeyboardController:
    """Send keyboard input via desktop automation tools."""
    
    def __init__(self, backend: Optional[DesktopBackend] = None) -> None:
        self.backend = backend
    
    def send_shortcut(
        self,
        keys: str,
        delay_ms: int = 20,
        verbose: bool = False,
    ) -> ActionResult:
        """Send keyboard shortcut.
        
        Args:
            keys: Key combination (e.g., "ctrl+t")
            delay_ms: Key delay in milliseconds
            verbose: Whether to log debug info
            
        Returns:
            ActionResult indicating success/failure
        """
        keys = keys.strip() or "ctrl+t"
        
        if self.backend == DesktopBackend.YDOTOOL:
            return self._send_shortcut_ydotool(keys, verbose)
        elif self.backend == DesktopBackend.XDOTOOL:
            return self._send_shortcut_xdotool(keys, verbose)
        else:
            return ActionResult.failed_result("No keyboard backend available")
    
    def send_key(
        self,
        key: str,
        delay_ms: int = 20,
        verbose: bool = False,
    ) -> ActionResult:
        """Send single key press.
        
        Args:
            key: Key name (e.g., "Return", "Tab")
            delay_ms: Key delay in milliseconds
            verbose: Whether to log debug info
            
        Returns:
            ActionResult indicating success/failure
        """
        key = key.strip() or "Return"
        
        if self.backend == DesktopBackend.YDOTOOL:
            return self._send_key_ydotool(key, verbose)
        elif self.backend == DesktopBackend.XDOTOOL:
            return self._send_key_xdotool(key, verbose)
        else:
            return ActionResult.failed_result("No keyboard backend available")
    
    def type_text(
        self,
        text: str,
        delay_ms: int = 20,
        verbose: bool = False,
    ) -> ActionResult:
        """Type text.
        
        Args:
            text: Text to type
            delay_ms: Typing delay in milliseconds
            verbose: Whether to log debug info
            
        Returns:
            ActionResult indicating success/failure
        """
        if not text.strip():
            return ActionResult.success_result()  # Nothing to type
        
        if self.backend == DesktopBackend.YDOTOOL:
            return self._type_text_ydotool(text, delay_ms, verbose)
        elif self.backend == DesktopBackend.XDOTOOL:
            return self._type_text_xdotool(text, delay_ms, verbose)
        else:
            return ActionResult.failed_result("No keyboard backend available")
    
    def _send_shortcut_ydotool(self, keys: str, verbose: bool) -> ActionResult:
        """Send shortcut via ydotool."""
        try:
            ydotool_keys = self._convert_keys_to_ydotool(keys)
            subprocess.run(["ydotool", "key"] + ydotool_keys, check=True)
            return ActionResult.success_result(backend=DesktopBackend.YDOTOOL)
        except Exception as e:
            return ActionResult.failed_result(str(e), DesktopBackend.YDOTOOL)
    
    def _send_shortcut_xdotool(self, keys: str, verbose: bool) -> ActionResult:
        """Send shortcut via xdotool."""
        try:
            subprocess.run(["xdotool", "key", keys], check=True)
            return ActionResult.success_result(backend=DesktopBackend.XDOTOOL)
        except Exception as e:
            return ActionResult.failed_result(str(e), DesktopBackend.XDOTOOL)
    
    def _send_key_ydotool(self, key: str, verbose: bool) -> ActionResult:
        """Send single key via ydotool."""
        try:
            ydotool_keys = self._convert_keys_to_ydotool(key)
            subprocess.run(["ydotool", "key"] + ydotool_keys, check=True)
            return ActionResult.success_result(backend=DesktopBackend.YDOTOOL)
        except Exception as e:
            return ActionResult.failed_result(str(e), DesktopBackend.YDOTOOL)
    
    def _send_key_xdotool(self, key: str, verbose: bool) -> ActionResult:
        """Send single key via xdotool."""
        try:
            subprocess.run(["xdotool", "key", key], check=True)
            return ActionResult.success_result(backend=DesktopBackend.XDOTOOL)
        except Exception as e:
            return ActionResult.failed_result(str(e), DesktopBackend.XDOTOOL)
    
    def _type_text_ydotool(
        self,
        text: str,
        delay_ms: int,
        verbose: bool,
    ) -> ActionResult:
        """Type text via ydotool."""
        try:
            subprocess.run(
                ["ydotool", "type", "--key-delay", str(delay_ms), text],
                check=True
            )
            return ActionResult.success_result(backend=DesktopBackend.YDOTOOL)
        except Exception as e:
            return ActionResult.failed_result(str(e), DesktopBackend.YDOTOOL)
    
    def _type_text_xdotool(
        self,
        text: str,
        delay_ms: int,
        verbose: bool,
    ) -> ActionResult:
        """Type text via xdotool."""
        try:
            subprocess.run(
                ["xdotool", "type", "--delay", str(delay_ms), text],
                check=True
            )
            return ActionResult.success_result(backend=DesktopBackend.XDOTOOL)
        except Exception as e:
            return ActionResult.failed_result(str(e), DesktopBackend.XDOTOOL)
    
    @staticmethod
    def _convert_keys_to_ydotool(keys: str) -> list[str]:
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
        
        # Letters a-z keycodes
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
