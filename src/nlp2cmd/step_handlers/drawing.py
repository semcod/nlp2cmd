"""Drawing and canvas step handlers."""

from __future__ import annotations
import json
from typing import TYPE_CHECKING

from .base import StepHandler, HandlerContext, HandlerResult
from .registry import register_handler

if TYPE_CHECKING:
    pass


# Shared canvas selection helper
class CanvasMixin:
    """Mixin providing canvas selection logic."""
    
    def _pick_canvas_js(self) -> str:
        """Return JavaScript function to select the best canvas element."""
        return """
        () => {
            const all = Array.from(document.querySelectorAll('canvas'));
            if (!all.length) return null;
            const main = document.querySelector('.main-canvas');
            if (main && main instanceof HTMLCanvasElement) return main;
            let best = null;
            let bestArea = -1;
            for (const c of all) {
                if (!(c instanceof HTMLCanvasElement)) continue;
                const r = c.getBoundingClientRect();
                if (!r || r.width <= 64 || r.height <= 64) continue;
                const style = window.getComputedStyle(c);
                if (style && (style.visibility === 'hidden' || style.display === 'none')) continue;
                const area = r.width * r.height;
                if (area > bestArea) {
                    bestArea = area;
                    best = c;
                }
            }
            return best;
        }
        """
    
    def _get_color_js(self) -> str:
        """Return JavaScript to get the current color."""
        return "(window.__nlp2cmd_foreground || (window.colors && window.colors.foreground) || '#000')"


@register_handler("wait_for_canvas")
class WaitForCanvasHandler(StepHandler):
    """Wait for canvas element to appear."""
    
    def execute(self, ctx: HandlerContext) -> HandlerResult:
        ctx.page.wait_for_selector("canvas", state="visible", timeout=15000)
        return HandlerResult(success=True)


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


@register_handler("select_tool")
class SelectToolHandler(StepHandler):
    """Select a drawing tool."""
    
    TOOL_MAP = {
        "ellipse": "ellipse",
        "rectangle": "rectangle",
        "line": "line",
        "brush": "brush",
        "pencil": "pencil",
        "fill": "fill",
        "text": "text",
    }
    
    def execute(self, ctx: HandlerContext) -> HandlerResult:
        tool = ctx.params.get("tool", "")
        mapped = self.TOOL_MAP.get(tool, tool)
        
        try:
            ctx.page.evaluate(f'''
                () => {{
                    const tools = document.querySelectorAll('.tool');
                    for (const t of tools) {{
                        if (t.title && t.title.toLowerCase().includes('{mapped}')) {{
                            t.click();
                            return;
                        }}
                    }}
                }}
            ''')
            ctx.page.wait_for_timeout(500)
            return HandlerResult(success=True)
        except Exception as e:
            return HandlerResult(success=False, error=f"Tool selection error: {e}")


@register_handler("set_color")
class SetColorHandler(StepHandler):
    """Set foreground color for drawing."""
    
    def execute(self, ctx: HandlerContext) -> HandlerResult:
        color = ctx.params.get("color", "#000000")
        
        try:
            ctx.page.evaluate(f'''
                () => {{
                    window.__nlp2cmd_foreground = '{color}';
                    window.__nlp2cmd_background = '{color}';
                    if (window.colors) {{
                        window.colors.foreground = '{color}';
                        window.colors.background = '{color}';
                    }}
                }}
            ''')
            ctx.page.wait_for_timeout(200)
            return HandlerResult(success=True)
        except Exception as e:
            return HandlerResult(success=False, error=f"Color set error: {e}")


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


@register_handler("draw_circle")
class DrawCircleHandler(StepHandler, CanvasMixin):
    """Draw a circle on canvas."""
    
    def execute(self, ctx: HandlerContext) -> HandlerResult:
        radius = float(ctx.params.get("radius", 10))
        offset = ctx.params.get("offset", [0, 0])
        
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
                    const r = {radius} * Math.max(sx, sy);
                    ctx2d.beginPath();
                    ctx2d.arc(cx, cy, r, 0, 2 * Math.PI);
                    ctx2d.fillStyle = {color};
                    ctx2d.fill();
                }}
            ''')
            ctx.page.wait_for_timeout(200)
            return HandlerResult(success=True)
        except Exception as e:
            return HandlerResult(success=False, error=f"Draw circle error: {e}")


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


# Aliases for other simple drawing handlers using the same pattern
def _create_simple_draw_handler(action_name: str, template: str, error_msg: str):
    """Factory for simple drawing handlers."""
    
    @register_handler(action_name)
    class SimpleDrawHandler(StepHandler, CanvasMixin):
        def execute(self, ctx: HandlerContext) -> HandlerResult:
            try:
                pick_canvas = self._pick_canvas_js()
                color = self._get_color_js()
                params = ctx.params
                ctx.page.evaluate(template.format(
                    pick_canvas=pick_canvas,
                    color=color,
                    params=params,
                    offset=params.get("offset", [0, 0]),
                    rx=params.get("rx", 10),
                    ry=params.get("ry", 10),
                    width=params.get("width", 50),
                    height=params.get("height", 50),
                    radius=params.get("radius", 50),
                    start_angle=params.get("start_angle", 0),
                    end_angle=params.get("end_angle", 3.14159),
                    fill="true" if params.get("fill", False) else "false",
                    line_width=params.get("line_width", 2),
                ))
                ctx.page.wait_for_timeout(200)
                return HandlerResult(success=True)
            except Exception as e:
                return HandlerResult(success=False, error=f"{error_msg}: {e}")
    
    return SimpleDrawHandler


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


@register_handler("draw_filled_rectangle")
class DrawFilledRectangleHandler(StepHandler, CanvasMixin):
    """Draw a filled rectangle on canvas."""
    
    def execute(self, ctx: HandlerContext) -> HandlerResult:
        w = float(ctx.params.get("width", 50))
        h = float(ctx.params.get("height", 50))
        offset = ctx.params.get("offset", [0, 0])
        
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
                    const _w = {w} * sx;
                    const _h = {h} * sy;
                    ctx2d.fillStyle = {color};
                    ctx2d.fillRect(cx - _w/2, cy - _h/2, _w, _h);
                }}
            ''')
            ctx.page.wait_for_timeout(200)
            return HandlerResult(success=True)
        except Exception as e:
            return HandlerResult(success=False, error=f"Draw filled rectangle error: {e}")
