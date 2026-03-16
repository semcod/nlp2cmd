"""Desktop Executor Package — Modular desktop automation for Linux.

This package provides modular components for executing desktop automation
tasks via ydotool (Wayland), xdotool (X11), and wmctrl.
"""

from .base import DesktopBackend, ActionResult, ActionStatus, ExecutionConfig
from .backend_detector import BackendDetector
from .window_manager import WindowManager
from .keyboard_controller import KeyboardController
from .browser_controller import BrowserController
from .env_manager import EnvManager
from .desktop_action_executor import DesktopActionExecutor

__all__ = [
    "DesktopBackend",
    "ActionResult",
    "ActionStatus",
    "ExecutionConfig",
    "BackendDetector",
    "WindowManager",
    "KeyboardController",
    "BrowserController",
    "EnvManager",
    "DesktopActionExecutor",
]
