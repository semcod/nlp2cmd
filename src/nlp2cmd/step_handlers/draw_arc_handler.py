# DrawArcHandler - extracted from drawing.py
"""Drawing and canvas step handlers."""
from __future__ import annotations
import json
from typing import TYPE_CHECKING
from .base import StepHandler, HandlerContext, HandlerResult
from .registry import register_handler
if TYPE_CHECKING:
    pass
from nlp2cmd.step_handlers.canvas_mixin import CanvasMixin

@register_handler("draw_arc")
class DrawArcHandler(StepHandler, CanvasMixin):
    """Draw an arc on canvas."""

    def execute(self, ctx: HandlerContext) -> HandlerResult:
        radius = float(ctx.params.get("radius", 50))
        start_angle = float(ctx.params.get("start_angle", 0))
        end_angle = float(ctx.params.get("end_angle", 3.14159))
        offset = ctx.params.get("offset", [0, 0])
        fill = bool(ctx.params.get("fill", False))
        line_width = float(ctx.params.get("line_width", 2))

        try:
            pick_canvas = self._pick_canvas_js()
            color = self._get_color_js()
            fill_js = "true" if fill else "false"
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
                    const rr = {radius} * Math.max(sx, sy);
                    ctx2d.beginPath();
                    ctx2d.arc(cx, cy, rr, {start_angle}, {end_angle});
                    ctx2d.lineWidth = {line_width} * Math.max(sx, sy);
                    const col = {color};
                    ctx2d.strokeStyle = col;
                    ctx2d.fillStyle = col;
                    if ({fill_js}) {{
                        ctx2d.lineTo(cx, cy);
                        ctx2d.closePath();
                        ctx2d.fill();
                    }} else {{
                        ctx2d.stroke();
                    }}
                }}
            ''')
            ctx.page.wait_for_timeout(200)
            return HandlerResult(success=True)
        except Exception as e:
            return HandlerResult(success=False, error=f"Draw arc error: {e}")

