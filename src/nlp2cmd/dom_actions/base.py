"""Base classes for DOM action handlers."""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Page, BrowserContext


@dataclass
class ActionContext:
    """Context passed to DOM action handlers."""
    page: "Page"
    context: "BrowserContext"
    url: str
    action_spec: dict[str, Any]
    console: Any  # Rich console or wrapper
    schema_loader: Any  # FormDataLoader
    extracted_data: list[dict[str, str]]  # Mutable list for data accumulation


@dataclass
class ActionResult:
    """Result from a DOM action handler."""
    success: bool = True
    error: Optional[str] = None
    data: Optional[dict[str, Any]] = None
    should_continue: bool = True  # If False, stop action processing


class DomAction(ABC):
    """Base class for DOM action handlers.
    
    Each handler implements a single action type (e.g., 'goto', 'fill_form').
    """
    
    action_name: str = ""
    
    @abstractmethod
    def execute(self, ctx: ActionContext) -> ActionResult:
        """Execute the DOM action.
        
        Args:
            ctx: ActionContext with page, url, action_spec, etc.
            
        Returns:
            ActionResult indicating success/failure and control flow
        """
        pass
    
    def _dismiss_popups(self, page, schema_loader) -> None:
        """Helper to dismiss common popups and cookie consents."""
        try:
            if hasattr(schema_loader, 'dismiss_cookie_consent'):
                schema_loader.dismiss_cookie_consent(page)
        except Exception:
            pass
    
    def _debug(self, msg: str) -> None:
        """Print debug message."""
        from nlp2cmd.pipeline_runner_utils import _debug
        _debug(msg)
