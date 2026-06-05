# WaitForCanvasHandler - extracted from drawing.py
"""Drawing and canvas step handlers."""
from __future__ import annotations
import json
from typing import TYPE_CHECKING
from .base import StepHandler, HandlerContext, HandlerResult
from .registry import register_handler
if TYPE_CHECKING:
    pass
@register_handler("wait_for_canvas")
class WaitForCanvasHandler(StepHandler):
    """Wait for canvas element to appear."""
    
    def execute(self, ctx: HandlerContext) -> HandlerResult:
        ctx.page.wait_for_selector("canvas", state="visible", timeout=15000)
        return HandlerResult(success=True)

