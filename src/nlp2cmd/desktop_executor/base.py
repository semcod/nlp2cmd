"""Base classes for desktop execution."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class DesktopBackend(Enum):
    """Available desktop automation backends."""
    YDOTOOL = "ydotool"  # Wayland
    XDOTOOL = "xdotool"  # X11
    WMCTRL = "wmctrl"    # X11 window management
    NONE = "none"        # No backend available


class ActionStatus(Enum):
    """Status of action execution."""
    SUCCESS = "success"
    FAILED = "failed"
    UNSUPPORTED = "unsupported"
    NO_BACKEND = "no_backend"
    SKIPPED = "skipped"


@dataclass
class ActionResult:
    """Result of action execution."""
    success: bool = False
    status: ActionStatus = ActionStatus.FAILED
    result: Optional[str] = None
    error: Optional[str] = None
    backend_used: DesktopBackend = DesktopBackend.NONE
    
    @classmethod
    def success_result(cls, result: Optional[str] = None, backend: DesktopBackend = DesktopBackend.NONE) -> "ActionResult":
        """Create a success result."""
        return cls(success=True, status=ActionStatus.SUCCESS, result=result, backend_used=backend)
    
    @classmethod
    def failed_result(cls, error: str, backend: DesktopBackend = DesktopBackend.NONE) -> "ActionResult":
        """Create a failed result."""
        return cls(success=False, status=ActionStatus.FAILED, error=error, backend_used=backend)
    
    @classmethod
    def unsupported_result(cls, action: str) -> "ActionResult":
        """Create an unsupported action result."""
        return cls(success=False, status=ActionStatus.UNSUPPORTED, error=f"Unsupported action: {action}")


@dataclass
class ExecutionConfig:
    """Configuration for desktop execution."""
    # Key delay for typing (ms)
    key_delay: int = 20
    # Wait time after window focus (s)
    focus_wait: float = 0.3
    # Wait time for check_session (s)
    session_wait: float = 2.0
    # Default wait timeout (ms)
    default_wait_ms: int = 500
    # Window search candidates
    window_candidates: list[tuple[str, str]] = field(default_factory=lambda: [
        ("--name", "Mozilla Firefox"),
        ("--class", "firefox"),
        ("--class", "Navigator"),
    ])
