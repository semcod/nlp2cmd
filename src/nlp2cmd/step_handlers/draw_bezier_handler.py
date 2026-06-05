# DrawBezierHandler - extracted from drawing.py
"""Drawing and canvas step handlers."""
from __future__ import annotations
import json
from typing import TYPE_CHECKING
from .base import StepHandler, HandlerContext, HandlerResult
from .registry import register_handler
if TYPE_CHECKING:
    pass
from nlp2cmd.step_handlers.canvas_mixin import CanvasMixin

@register_handler("draw_bezier")
class DrawBezierHandler(StepHandler, CanvasMixin):
    """Draw a bezier path on canvas."""

    def execute(self, ctx: HandlerContext) -> HandlerResult:
        curves = ctx.params.get("curves", [])
        offset = ctx.params.get("offset", [0, 0])
        fill = bool(ctx.params.get("fill", False))
        close = bool(ctx.params.get("close", False))
        line_width = float(ctx.params.get("line_width", 2))

        if not curves:
            return HandlerResult(success=True)

        try:
            pick_canvas = self._pick_canvas_js()
            color = self._get_color_js()
            fill_js = "true" if fill else "false"
            close_js = "true" if close else "false"
            curves_js = json.dumps(curves)
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
                    const curves = {curves_js};
                    ctx2d.beginPath();
                    for (let i = 0; i < curves.length; i++) {{
                        const c = curves[i];
                        if (c.type === 'M' || (i === 0 && !c.type)) {{
                            ctx2d.moveTo(cx + c.x * sx, cy + c.y * sy);
                        }} else if (c.type === 'L') {{
                            ctx2d.lineTo(cx + c.x * sx, cy + c.y * sy);
                        }} else if (c.type === 'Q') {{
                            ctx2d.quadraticCurveTo(cx + c.cpx * sx, cy + c.cpy * sy, cx + c.x * sx, cy + c.y * sy);
                        }} else if (c.type === 'C') {{
                            ctx2d.bezierCurveTo(cx + c.cp1x * sx, cy + c.cp1y * sy, cx + c.cp2x * sx, cy + c.cp2y * sy, cx + c.x * sx, cy + c.y * sy);
                        }}
                    }}
                    if ({close_js}) ctx2d.closePath();
                    ctx2d.lineWidth = {line_width} * Math.max(sx, sy);
                    const col = {color};
                    ctx2d.strokeStyle = col;
                    ctx2d.fillStyle = col;
                    if ({fill_js}) {{
                        ctx2d.fill();
                    }} else {{
                        ctx2d.stroke();
                    }}
                }}
            ''')
            ctx.page.wait_for_timeout(200)
            return HandlerResult(success=True)
        except Exception as e:
            return HandlerResult(success=False, error=f"Draw bezier error: {e}")

