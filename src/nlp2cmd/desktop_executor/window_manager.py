"""Window Manager for focusing and managing application windows."""

from __future__ import annotations
import subprocess
import shutil
import time
import logging
from typing import Optional

from .base import DesktopBackend, ActionResult

log = logging.getLogger("nlp2cmd.desktop_executor.window")


class WindowManager:
    """Manage application windows via desktop automation tools."""
    
    def __init__(self, backend: Optional[DesktopBackend] = None) -> None:
        self.backend = backend
        # Window search candidates for fallback
        self._search_candidates = [
            ("--name", "Mozilla Firefox"),
            ("--class", "firefox"),
            ("--class", "Navigator"),
        ]
    
    def focus_window(
        self,
        title: str,
        wait: float = 0.3,
        verbose: bool = False,
    ) -> ActionResult:
        """Focus window by title.
        
        Args:
            title: Window title to focus
            wait: Time to wait after focus (s)
            verbose: Whether to log debug info
            
        Returns:
            ActionResult indicating success/failure
        """
        if self.backend == DesktopBackend.YDOTOOL:
            return self._focus_with_ydotool(wait, verbose)
        elif self.backend == DesktopBackend.XDOTOOL:
            return self._focus_with_xdotool(title, wait, verbose)
        elif self.backend == DesktopBackend.WMCTRL:
            return self._focus_with_wmctrl(title, verbose)
        else:
            return ActionResult.failed_result("No window management backend available")
    
    def _focus_with_ydotool(self, wait: float, verbose: bool) -> ActionResult:
        """Focus using ydotool (Alt+Tab fallback)."""
        try:
            # ydotool can't focus windows directly; use Alt+Tab
            if verbose:
                log.debug("ydotool: using Alt+Tab for window focus")
            
            subprocess.run(
                ["ydotool", "key", "56:1", "15:1", "15:0", "56:0"],
                check=False
            )
            time.sleep(wait)
            return ActionResult.success_result(backend=DesktopBackend.YDOTOOL)
        except Exception as e:
            return ActionResult.failed_result(str(e), DesktopBackend.YDOTOOL)
    
    def _focus_with_wmctrl(self, title: str, verbose: bool) -> ActionResult:
        """Focus using wmctrl."""
        try:
            if shutil.which("wmctrl") is not None:
                if verbose:
                    log.debug(f"wmctrl: focusing window '{title}'")
                subprocess.run(["wmctrl", "-a", title], check=True)
                return ActionResult.success_result(backend=DesktopBackend.WMCTRL)
            return ActionResult.failed_result("wmctrl not available")
        except Exception as e:
            return ActionResult.failed_result(str(e), DesktopBackend.WMCTRL)
    
    def _focus_with_xdotool(
        self,
        title: str,
        wait: float,
        verbose: bool,
    ) -> ActionResult:
        """Focus using xdotool with fallback search candidates."""
        try:
            # Try wmctrl first if available
            if shutil.which("wmctrl") is not None:
                try:
                    subprocess.run(["wmctrl", "-a", title], check=True)
                    return ActionResult.success_result(backend=DesktopBackend.WMCTRL)
                except Exception:
                    pass  # Fall through to xdotool
            
            # Try xdotool with various search strategies
            candidates = [("--name", title)] + self._search_candidates
            
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
                subprocess.run(
                    ["xdotool", "windowactivate", "--sync", win_id],
                    check=True
                )
                time.sleep(wait)
                return ActionResult.success_result(backend=DesktopBackend.XDOTOOL)
            else:
                msg = f"Could not find visible window for '{title}'"
                if verbose:
                    log.debug(msg)
                return ActionResult.failed_result(msg, DesktopBackend.XDOTOOL)
                
        except Exception as e:
            return ActionResult.failed_result(str(e), DesktopBackend.XDOTOOL)
