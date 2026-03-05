"""Backend Detector for identifying available desktop automation tools."""

from __future__ import annotations
import shutil
import logging
from typing import Optional

from .base import DesktopBackend

log = logging.getLogger("nlp2cmd.desktop_executor.backend")


class BackendDetector:
    """Detect available desktop automation backends."""
    
    def __init__(self) -> None:
        self._cached_backend: Optional[DesktopBackend] = None
    
    def detect(self) -> DesktopBackend:
        """Detect the best available backend.
        
        Priority: ydotool (Wayland) > xdotool (X11) > none
        
        Returns:
            DesktopBackend enum value
        """
        if self._cached_backend is not None:
            return self._cached_backend
        
        # Check for ydotool (Wayland)
        if shutil.which("ydotool") is not None:
            self._cached_backend = DesktopBackend.YDOTOOL
            log.debug("Detected ydotool backend (Wayland)")
            return self._cached_backend
        
        # Check for xdotool (X11)
        if shutil.which("xdotool") is not None:
            self._cached_backend = DesktopBackend.XDOTOOL
            log.debug("Detected xdotool backend (X11)")
            return self._cached_backend
        
        # No backend available
        self._cached_backend = DesktopBackend.NONE
        log.debug("No desktop automation backend detected")
        return self._cached_backend
    
    def detect_with_fallback(self) -> tuple[DesktopBackend, Optional[DesktopBackend]]:
        """Detect primary backend with optional fallback.
        
        Returns:
            Tuple of (primary_backend, fallback_backend or None)
        """
        primary = self.detect()
        
        if primary == DesktopBackend.YDOTOOL:
            # ydotool can use wmctrl for window management
            if shutil.which("wmctrl") is not None:
                return primary, DesktopBackend.WMCTRL
            return primary, None
        
        if primary == DesktopBackend.XDOTOOL:
            # xdotool can use wmctrl as fallback for window management
            if shutil.which("wmctrl") is not None:
                return primary, DesktopBackend.WMCTRL
            return primary, None
        
        # No primary backend, check for wmctrl only
        if shutil.which("wmctrl") is not None:
            return DesktopBackend.WMCTRL, None
        
        return DesktopBackend.NONE, None
    
    def is_available(self) -> bool:
        """Check if any backend is available.
        
        Returns:
            True if at least one backend is available
        """
        backend = self.detect()
        return backend != DesktopBackend.NONE
    
    def get_error_message(self) -> str:
        """Get installation instructions for missing backends.
        
        Returns:
            Error message with installation instructions
        """
        return (
            "No desktop automation tool available. "
            "On Wayland: sudo apt install ydotool && sudo systemctl enable --now ydotool. "
            "On X11: sudo apt install xdotool wmctrl."
        )
    
    def reset_cache(self) -> None:
        """Reset cached backend detection (for testing)."""
        self._cached_backend = None
