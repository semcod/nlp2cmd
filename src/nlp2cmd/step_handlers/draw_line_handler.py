# DrawLineHandler - extracted from drawing.py
"""Drawing and canvas step handlers."""
from __future__ import annotations
import json
from typing import TYPE_CHECKING
from .base import StepHandler, HandlerContext, HandlerResult
from .registry import register_handler
if TYPE_CHECKING:
    pass
from nlp2cmd.step_handlers.canvas_mixin import CanvasMixin

@register_handler("draw_line")
class DrawLineHandler(StepHandler, CanvasMixin):
    """Draw a line on canvas with simple pixel verification."""

    def execute(self, ctx: HandlerContext) -> HandlerResult:
        fo = ctx.params.get("from_offset", [0, 0])
        to = ctx.params.get("to_offset", [0, 0])

        try:
            pick_canvas = self._pick_canvas_js()
            color = self._get_color_js()
            pixel_stats_js = self._pixel_stats_js()
            before_check = ctx.page.evaluate(pixel_stats_js)

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
                    const cx = (rect.width / 2) * sx;
                    const cy = (rect.height / 2) * sy;
                    ctx2d.beginPath();
                    ctx2d.moveTo(cx + {fo[0]} * sx, cy + {fo[1]} * sy);
                    ctx2d.lineTo(cx + {to[0]} * sx, cy + {to[1]} * sy);
                    ctx2d.strokeStyle = {color};
                    ctx2d.lineWidth = 3;
                    ctx2d.stroke();
                }}
            ''')
            ctx.page.wait_for_timeout(200)

            after_check = ctx.page.evaluate(pixel_stats_js)
            if after_check.get('nonWhitePixels', 0) > before_check.get('nonWhitePixels', 0):
                ctx.console.print(f"  [green]✓ Line drawn: {after_check.get('nonWhitePixels')} non-white pixels[/green]")
            elif after_check.get('isBlank'):
                ctx.console.print(f"  [yellow]⚠ Canvas still blank after line![/yellow]")
            else:
                ctx.console.print(
                    f"  [dim]Canvas pixels: {before_check.get('nonWhitePixels')} → {after_check.get('nonWhitePixels')}[/dim]"
                )

            return HandlerResult(success=True)
        except Exception as e:
            return HandlerResult(success=False, error=f"Draw line error: {e}")

