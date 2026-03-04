"""Handler registry for plan step dispatching."""

from __future__ import annotations
from typing import Optional, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from .base import StepHandler


class HandlerRegistry:
    """Registry mapping action names to their handlers."""
    
    _handlers: dict[str, Type[StepHandler]] = {}
    
    @classmethod
    def register(cls, action_name: str, handler_class: Type[StepHandler]) -> None:
        """Register a handler class for an action name."""
        cls._handlers[action_name] = handler_class
    
    @classmethod
    def get(cls, action_name: str) -> Optional[Type[StepHandler]]:
        """Get the handler class for an action name."""
        return cls._handlers.get(action_name)
    
    @classmethod
    def list_actions(cls) -> list[str]:
        """List all registered action names."""
        return list(cls._handlers.keys())
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered handlers (mainly for testing)."""
        cls._handlers.clear()


def register_handler(action_name: str):
    """Decorator to register a handler class.
    
    Usage:
        @register_handler("navigate")
        class NavigateHandler(StepHandler):
            ...
    """
    def decorator(handler_class: Type[StepHandler]) -> Type[StepHandler]:
        HandlerRegistry.register(action_name, handler_class)
        handler_class.action_name = action_name
        return handler_class
    return decorator


def get_handler(action_name: str) -> Optional[Type[StepHandler]]:
    """Get the handler class for an action name."""
    return HandlerRegistry.get(action_name)
