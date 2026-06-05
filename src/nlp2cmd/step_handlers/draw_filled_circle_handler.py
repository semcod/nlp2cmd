# DrawFilledCircleHandler - extracted from drawing.py
"""Drawing and canvas step handlers."""
from __future__ import annotations
import json
from typing import TYPE_CHECKING
from .base import StepHandler, HandlerContext, HandlerResult
from .registry import register_handler
if TYPE_CHECKING:
    pass
from nlp2cmd.step_handlers.canvas_mixin import CanvasMixin

@register_handler("draw_filled_circle")
class DrawFilledCircleHandler(StepHandler, CanvasMixin):
    """Draw a filled circle on canvas with verification."""
    
    def execute(self, ctx: HandlerContext) -> HandlerResult:
        radius = float(ctx.params.get("radius", 10))
        offset = ctx.params.get("offset", [0, 0])
        
        try:
            pick_canvas = self._pick_canvas_js()
            color = self._get_color_js()
            
            # Check canvas before drawing
            before_check = self._check_canvas(ctx, pick_canvas)
            ctx.console.print(f"  [dim]Canvas before: {before_check}[/dim]")
            
            # Draw the circle
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
                    const r = {radius} * Math.max(sx, sy);
                    ctx2d.beginPath();
                    ctx2d.arc(cx, cy, r, 0, 2 * Math.PI);
                    ctx2d.fillStyle = {color};
                    ctx2d.fill();
                }}
            ''')
            ctx.page.wait_for_timeout(200)
            
            # Verify drawing
            after_check = self._check_canvas(ctx, pick_canvas)
            ctx.console.print(f"  [dim]Canvas after: {after_check}[/dim]")
            
            if after_check.get('isBlank') and not before_check.get('isBlank'):
                ctx.console.print(f"  [yellow]⚠ Canvas still blank after drawing![/yellow]")
            elif after_check.get('nonWhitePixels', 0) > before_check.get('nonWhitePixels', 0):
                ctx.console.print(f"  [green]✓ Drawing visible: {after_check.get('nonWhitePixels')} non-white pixels[/green]")
            
            return HandlerResult(success=True)
        except Exception as e:
            return HandlerResult(success=False, error=f"Draw filled circle error: {e}")
    
    def _check_canvas(self, ctx: HandlerContext, pick_canvas_js: str) -> dict:
        """Check canvas pixel state."""
        try:
            return ctx.page.evaluate(f'''
                () => {{
                    const pickCanvas = {pick_canvas_js};
                    const canvas = pickCanvas();
                    if (!canvas) return {{error: 'No canvas found'}};
                    const ctx2d = canvas.getContext('2d');
                    const imageData = ctx2d.getImageData(0, 0, canvas.width, canvas.height);
                    let nonWhite = 0;
                    for (let i = 0; i < imageData.data.length; i += 400) {{
                        if (imageData.data[i] !== 255 || imageData.data[i+1] !== 255 || imageData.data[i+2] !== 255) {{
                            nonWhite++;
                        }}
                    }}
                    return {{nonWhitePixels: nonWhite, isBlank: nonWhite <= 10, width: canvas.width, height: canvas.height}};
                }}
            ''')
        except Exception:
            return {}

