"""DOM action handlers package for browser automation.

This package contains modular handlers for DOM actions in the browser execution pipeline.
"""

from .base import DomAction, ActionContext, ActionResult
from .registry import ActionRegistry, register_action, get_action
from .dispatcher import ActionDispatcher

# Import all handler modules to ensure registration
from . import navigation  # noqa: F401
from . import forms  # noqa: F401
from . import companies  # noqa: F401
from . import save  # noqa: F401

__all__ = [
    "DomAction",
    "ActionContext",
    "ActionResult",
    "ActionRegistry",
    "register_action",
    "get_action",
    "ActionDispatcher",
]
