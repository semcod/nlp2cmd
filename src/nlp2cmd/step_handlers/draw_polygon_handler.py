# DrawPolygonHandler - extracted from drawing.py
"""Drawing and canvas step handlers."""
from __future__ import annotations
import json
from typing import TYPE_CHECKING
from .base import StepHandler, HandlerContext, HandlerResult
from .registry import register_handler
if TYPE_CHECKING:
    pass
from nlp2cmd.step_handlers.canvas_mixin import CanvasMixin

@register_handler("draw_polygon")
class DrawPolygonHandler(StepHandler, CanvasMixin):
    """Draw a polygon on canvas."""

    def execute(self, ctx: HandlerContext) -> HandlerResult:
        points = ctx.params.get("points", [])
        offset = ctx.params.get("offset", [0, 0])
        fill = bool(ctx.params.get("fill", True))
        line_width = float(ctx.params.get("line_width", 2))

        if len(points) < 3:
            return HandlerResult(success=True)

        try:
            pick_canvas = self._pick_canvas_js()
            color = self._get_color_js()
            fill_js = "true" if fill else "false"
            pts_js = json.dumps(points)
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
                    const pts = {pts_js}.map(p => [p[0] * sx, p[1] * sy]);
                    ctx2d.beginPath();
                    ctx2d.moveTo(cx + pts[0][0], cy + pts[0][1]);
                    for (let i = 1; i < pts.length; i++) {{
                        ctx2d.lineTo(cx + pts[i][0], cy + pts[i][1]);
                    }}
                    ctx2d.closePath();
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
            return HandlerResult(success=False, error=f"Draw polygon error: {e}")

