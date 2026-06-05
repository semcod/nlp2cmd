# DrawSvgPathHandler - extracted from drawing.py
"""Drawing and canvas step handlers."""
from __future__ import annotations
import json
from typing import TYPE_CHECKING
from .base import StepHandler, HandlerContext, HandlerResult
from .registry import register_handler
if TYPE_CHECKING:
    pass
from nlp2cmd.step_handlers.canvas_mixin import CanvasMixin

@register_handler("draw_svg_path")
class DrawSvgPathHandler(StepHandler, CanvasMixin):
    """Draw an SVG path on canvas."""

    def execute(self, ctx: HandlerContext) -> HandlerResult:
        path_d = str(ctx.params.get("d", "") or "")
        offset = ctx.params.get("offset", [0, 0])
        fill = bool(ctx.params.get("fill", True))
        scale = float(ctx.params.get("scale", 1.0))
        line_width = float(ctx.params.get("line_width", 2))

        if not path_d:
            return HandlerResult(success=True)

        try:
            pick_canvas = self._pick_canvas_js()
            color = self._get_color_js()
            fill_js = "true" if fill else "false"
            path_js = json.dumps(path_d)
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
                    ctx2d.save();
                    ctx2d.translate(cx, cy);
                    ctx2d.scale({scale} * sx, {scale} * sy);
                    const p = new Path2D({path_js});
                    ctx2d.lineWidth = ({line_width} / {scale}) * Math.max(sx, sy);
                    const col = {color};
                    ctx2d.strokeStyle = col;
                    ctx2d.fillStyle = col;
                    if ({fill_js}) {{
                        ctx2d.fill(p);
                    }} else {{
                        ctx2d.stroke(p);
                    }}
                    ctx2d.restore();
                }}
            ''')
            ctx.page.wait_for_timeout(200)
            return HandlerResult(success=True)
        except Exception as e:
            return HandlerResult(success=False, error=f"Draw SVG path error: {e}")

