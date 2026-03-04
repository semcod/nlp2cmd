"""Action registry for DOM actions."""

from __future__ import annotations
from typing import Optional, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from .base import DomAction


class ActionRegistry:
    """Registry mapping action names to their handlers."""
    
    _handlers: dict[str, Type[DomAction]] = {}
    
    @classmethod
    def register(cls, action_name: str, handler_class: Type[DomAction]) -> None:
        """Register a handler class for an action name."""
        cls._handlers[action_name] = handler_class
    
    @classmethod
    def get(cls, action_name: str) -> Optional[Type[DomAction]]:
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


def register_action(action_name: str):
    """Decorator to register a handler class.
    
    Usage:
        @register_action("goto")
        class GotoAction(DomAction):
            ...
    """
    def decorator(handler_class: Type[DomAction]) -> Type[DomAction]:
        ActionRegistry.register(action_name, handler_class)
        handler_class.action_name = action_name
        return handler_class
    return decorator


def get_action(action_name: str) -> Optional[Type[DomAction]]:
    """Get the handler class for an action name."""
    return ActionRegistry.get(action_name)
