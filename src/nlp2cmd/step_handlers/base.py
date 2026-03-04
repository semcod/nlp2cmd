"""Base classes for step handlers."""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Page, BrowserContext


@dataclass
class HandlerContext:
    """Context passed to step handlers during execution."""
    page: "Page"
    context: "BrowserContext"
    params: dict[str, Any]
    variables: dict[str, str]
    console: Any  # Rich console


@dataclass
class HandlerResult:
    """Result from a step handler execution."""
    success: bool = True
    value: Optional[str] = None
    error: Optional[str] = None
    retry_allowed: bool = True


class StepHandler(ABC):
    """Base class for plan step handlers.
    
    Each handler implements a single action type (e.g., 'navigate', 'click').
    Handlers are registered in the HandlerRegistry and called by the dispatcher.
    """
    
    # Action name this handler handles (e.g., 'navigate', 'click')
    action_name: str = ""
    
    @abstractmethod
    def execute(self, ctx: HandlerContext) -> HandlerResult:
        """Execute the step handler.
        
        Args:
            ctx: HandlerContext with page, context, params, variables, console
            
        Returns:
            HandlerResult indicating success/failure and optional return value
        """
        pass
    
    def _resolve_variables(self, value: Any, variables: dict[str, str]) -> Any:
        """Replace $variable references with actual values."""
        if isinstance(value, str) and value.startswith("$"):
            return variables.get(value[1:], value)
        return value
    
    def _debug(self, msg: str, ctx: HandlerContext) -> None:
        """Print debug message if debug mode is enabled."""
        from nlp2cmd.pipeline_runner_utils import _debug
        _debug(msg)
