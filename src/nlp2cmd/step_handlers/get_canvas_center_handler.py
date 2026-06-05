# GetCanvasCenterHandler - extracted from drawing.py
"""Drawing and canvas step handlers."""
from __future__ import annotations
import json
from typing import TYPE_CHECKING
from .base import StepHandler, HandlerContext, HandlerResult
from .registry import register_handler
if TYPE_CHECKING:
    pass
from nlp2cmd.step_handlers.canvas_mixin import CanvasMixin

@register_handler("get_canvas_center")
class GetCanvasCenterHandler(StepHandler, CanvasMixin):
    """Get canvas center coordinates."""
    
    def execute(self, ctx: HandlerContext) -> HandlerResult:
        canvas = ctx.page.query_selector("canvas")
        if canvas:
            box = canvas.bounding_box()
            if box:
                self._debug(f"Canvas: {box}", ctx)
                ctx.variables["canvas_cx"] = str(box["x"] + box["width"] / 2)
                ctx.variables["canvas_cy"] = str(box["y"] + box["height"] / 2)
        return HandlerResult(success=True)

