"""Dispatcher for DOM actions.

Replaces the monolithic _run_dom_multi_action method with a clean handler registry.
"""

from __future__ import annotations
import time
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Page, BrowserContext

from .base import ActionContext, ActionResult
from .registry import ActionRegistry

# Import all handlers to register them
from . import navigation  # noqa: F401
from . import forms  # noqa: F401
from . import companies  # noqa: F401
from . import save  # noqa: F401


class ActionDispatcher:
    """Dispatches DOM actions to appropriate handlers.
    
    This replaces the monolithic _run_dom_multi_action method with a clean,
    extensible handler registry pattern.
    """
    
    @classmethod
    def dispatch(
        cls,
        action: str,
        action_spec: dict[str, Any],
        page: "Page",
        context: "BrowserContext",
        url: str,
        console: Any,
        schema_loader: Any,
        extracted_data: list[dict[str, str]],
    ) -> ActionResult:
        """Dispatch a DOM action to its handler.
        
        Args:
            action: The action name (e.g., 'goto', 'fill_form')
            action_spec: Full action specification dict
            page: Playwright page object
            context: Playwright browser context
            url: Current URL
            console: Console wrapper for output
            schema_loader: FormDataLoader instance
            extracted_data: Mutable list for data accumulation
            
        Returns:
            ActionResult indicating success/failure and control flow
        """
        handler_class = ActionRegistry.get(action)
        if not handler_class:
            return ActionResult(
                success=False,
                error=f"Unsupported action: {action}",
                should_continue=False
            )
        
        # Create context object
        ctx = ActionContext(
            page=page,
            context=context,
            url=url,
            action_spec=action_spec,
            console=console,
            schema_loader=schema_loader,
            extracted_data=extracted_data,
        )
        
        # Execute handler
        handler = handler_class()
        return handler.execute(ctx)
    
    @classmethod
    def has_handler(cls, action: str) -> bool:
        """Check if a handler exists for an action."""
        return ActionRegistry.get(action) is not None
    
    @classmethod
    def list_actions(cls) -> list[str]:
        """List all available actions."""
        return ActionRegistry.list_actions()
    
    @classmethod
    def execute_actions_sequence(
        cls,
        actions: list[dict[str, Any]],
        page: "Page",
        context: "BrowserContext",
        url: str,
        console: Any,
        schema_loader: Any,
    ) -> dict[str, Any]:
        """Execute a sequence of DOM actions.
        
        Args:
            actions: List of action specifications
            page: Playwright page
            context: Browser context
            url: Starting URL
            console: Console wrapper
            schema_loader: FormDataLoader
            
        Returns:
            Dict with success status, extracted_data, and metadata
        """
        extracted_data: list[dict[str, str]] = []
        executed = 0
        
        for i, action_spec in enumerate(actions):
            action = action_spec.get("action")
            if not action:
                continue
            
            _action_t0 = time.perf_counter()
            
            result = cls.dispatch(
                action=action,
                action_spec=action_spec,
                page=page,
                context=context,
                url=url,
                console=console,
                schema_loader=schema_loader,
                extracted_data=extracted_data,
            )
            
            _action_elapsed = (time.perf_counter() - _action_t0) * 1000
            
            if not result.success:
                return {
                    "success": False,
                    "error": result.error,
                    "action_index": i,
                    "action": action,
                    "extracted_data": extracted_data,
                }
            
            executed += 1
            
            if not result.should_continue:
                break
            
            # Update URL if action returned new URL
            if result.data and result.data.get("url"):
                url = result.data["url"]
        
        return {
            "success": True,
            "actions_executed": executed,
            "extracted_data": extracted_data,
        }
