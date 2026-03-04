"""Dispatcher for plan step execution.

Replaces the monolithic _execute_plan_step method with a clean handler registry.
"""

from __future__ import annotations
import re
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Page, BrowserContext

from .base import HandlerContext, HandlerResult
from .registry import HandlerRegistry

# Import all handlers to register them
from . import navigate  # noqa: F401
from . import interaction  # noqa: F401
from . import drawing  # noqa: F401
from . import extraction  # noqa: F401
from . import session  # noqa: F401


class StepDispatcher:
    """Dispatches plan steps to appropriate handlers.
    
    This replaces the monolithic _execute_plan_step method with a clean,
    extensible handler registry pattern.
    """
    
    # Actions that are handled inline (simple ones)
    SIMPLE_ACTIONS = {
        "browser_open": lambda ctx: HandlerResult(success=True),
    }
    
    @classmethod
    def dispatch(
        cls,
        action: str,
        page: "Page",
        context: "BrowserContext",
        params: dict[str, Any],
        variables: dict[str, str],
        console: Any,
    ) -> Optional[str]:
        """Dispatch a step to its handler.
        
        Args:
            action: The action name (e.g., 'navigate', 'click')
            page: Playwright page object
            context: Playwright browser context
            params: Action parameters
            variables: Variables from previous steps
            console: Rich console for output
            
        Returns:
            Handler result value or None
            
        Raises:
            Exception: If handler fails and doesn't return HandlerResult
        """
        # Resolve variable references in params
        resolved_params = cls._resolve_variables(params, variables)
        
        # Create context object
        ctx = HandlerContext(
            page=page,
            context=context,
            params=resolved_params,
            variables=variables,
            console=console,
        )
        
        # Check for simple inline handlers
        if action in cls.SIMPLE_ACTIONS:
            result = cls.SIMPLE_ACTIONS[action](ctx)
            return result.value if result.success else None
        
        # Get registered handler
        handler_class = HandlerRegistry.get(action)
        if handler_class:
            handler = handler_class()
            result = handler.execute(ctx)
            if result.success:
                return result.value
            else:
                if result.error:
                    raise RuntimeError(result.error)
                return None
        
        # No handler found - this is a problem
        raise ValueError(f"Unknown action: {action}")
    
    @classmethod
    def has_handler(cls, action: str) -> bool:
        """Check if a handler exists for an action."""
        if action in cls.SIMPLE_ACTIONS:
            return True
        return HandlerRegistry.get(action) is not None
    
    @classmethod
    def list_actions(cls) -> list[str]:
        """List all available actions."""
        simple = list(cls.SIMPLE_ACTIONS.keys())
        registered = HandlerRegistry.list_actions()
        return sorted(set(simple + registered))
    
    @staticmethod
    def _resolve_variables(params: dict[str, Any], variables: dict[str, str]) -> dict[str, Any]:
        """Replace $variable references with actual values."""
        resolved = {}
        for k, v in params.items():
            if isinstance(v, str) and v.startswith("$"):
                resolved[k] = variables.get(v[1:], v)
            else:
                resolved[k] = v
        return resolved
