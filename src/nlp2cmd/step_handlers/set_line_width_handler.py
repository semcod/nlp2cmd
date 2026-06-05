# SetLineWidthHandler - extracted from drawing.py
"""Drawing and canvas step handlers."""
from __future__ import annotations
import json
from typing import TYPE_CHECKING
from .base import StepHandler, HandlerContext, HandlerResult
from .registry import register_handler
if TYPE_CHECKING:
    pass
from nlp2cmd.step_handlers.canvas_mixin import CanvasMixin

@register_handler("set_line_width")
class SetLineWidthHandler(StepHandler, CanvasMixin):
    """Set line width for drawing."""
    
    def execute(self, ctx: HandlerContext) -> HandlerResult:
        width = float(ctx.params.get("width", 2))
        
        try:
            pick_canvas = self._pick_canvas_js()
            ctx.page.evaluate(f'''
                () => {{
                    const pickCanvas = {pick_canvas};
                    const canvas = pickCanvas();
                    if (!canvas) throw new Error('No suitable canvas found');
                    const ctx = canvas.getContext('2d');
                    if (!ctx) throw new Error('Canvas 2D context unavailable');
                    const rect = canvas.getBoundingClientRect();
                    const sx = (canvas.width && rect.width) ? (canvas.width / rect.width) : 1;
                    const sy = (canvas.height && rect.height) ? (canvas.height / rect.height) : 1;
                    ctx.lineWidth = {width} * Math.max(sx, sy);
                }}
            ''')
            return HandlerResult(success=True)
        except Exception as e:
            return HandlerResult(success=False, error=f"Set line width error: {e}")

