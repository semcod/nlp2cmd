"""Step handlers package for plan execution.

This package contains modular handlers for each action type in the plan execution pipeline.
Each handler is a self-contained unit that can be tested independently.
"""

from typing import Optional, Type
from .base import StepHandler, HandlerContext, HandlerResult
from .registry import HandlerRegistry, get_handler, register_handler
from .dispatcher import StepDispatcher

# Import all handler modules to register them
from . import navigate  # noqa: F401
from . import interaction  # noqa: F401
from . import drawing  # noqa: F401
from . import extraction  # noqa: F401
from . import session  # noqa: F401

__all__ = [
    "StepHandler",
    "HandlerContext",
    "HandlerResult",
    "HandlerRegistry",
    "get_handler",
    "register_handler",
    "StepDispatcher",
]
