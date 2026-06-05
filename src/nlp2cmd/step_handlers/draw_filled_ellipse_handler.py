# DrawFilledEllipseHandler - extracted from drawing.py
"""Drawing and canvas step handlers."""
from __future__ import annotations
import json
from typing import TYPE_CHECKING
from .base import StepHandler, HandlerContext, HandlerResult
from .registry import register_handler
if TYPE_CHECKING:
    pass
from nlp2cmd.step_handlers.canvas_mixin import CanvasMixin

@register_handler("draw_filled_ellipse")
class DrawFilledEllipseHandler(StepHandler, CanvasMixin):
    """Draw a filled ellipse on canvas."""
    
    def execute(self, ctx: HandlerContext) -> HandlerResult:
        rx = float(ctx.params.get("rx", 10))
        ry = float(ctx.params.get("ry", 10))
        offset = ctx.params.get("offset", [0, 0])
        rotation = float(ctx.params.get("rotation", 0))
        
        try:
            pick_canvas = self._pick_canvas_js()
            color = self._get_color_js()
            ctx.page.evaluate(f'''
                () => {{
                    const pickCanvas = {pick_canvas};
                    const canvas = pickCanvas();
                    if (!canvas) throw new Error('No suitable canvas found');
                    const ctx2d = canvas.getContext('2d');
                    if (!ctx2d) throw new Error('Canvas 2D context unavailable');
                    const rect = canvas.getBoundingClientRect();
                    const sx = (canvas.width && rect.width) ? (canvas.width / rect.width) : 1;
                    const sy = (canvas.height && rect.height) ? (canvas.height / rect.height) : 1;
                    const cx = (rect.width / 2 + {offset[0]}) * sx;
                    const cy = (rect.height / 2 + {offset[1]}) * sy;
                    const _rx = {rx} * sx;
                    const _ry = {ry} * sy;
                    ctx2d.beginPath();
                    ctx2d.ellipse(cx, cy, _rx, _ry, {rotation}, 0, 2 * Math.PI);
                    ctx2d.fillStyle = {color};
                    ctx2d.fill();
                }}
            ''')
            ctx.page.wait_for_timeout(200)
            return HandlerResult(success=True)
        except Exception as e:
            return HandlerResult(success=False, error=f"Draw filled ellipse error: {e}")

