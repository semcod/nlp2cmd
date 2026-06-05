# ClickCanvasHandler - extracted from drawing.py
"""Drawing and canvas step handlers."""
from __future__ import annotations
import json
from typing import TYPE_CHECKING
from .base import StepHandler, HandlerContext, HandlerResult
from .registry import register_handler
if TYPE_CHECKING:
    pass
from nlp2cmd.step_handlers.canvas_mixin import CanvasMixin

@register_handler("click_canvas")
class ClickCanvasHandler(StepHandler, CanvasMixin):
    """Click the canvas at an offset."""

    def execute(self, ctx: HandlerContext) -> HandlerResult:
        offset = ctx.params.get("offset", [0, 0])

        try:
            pick_canvas = self._pick_canvas_js()
            ctx.page.evaluate(f'''
                () => {{
                    const pickCanvas = {pick_canvas};
                    const canvas = pickCanvas();
                    if (!canvas) throw new Error('No suitable canvas found');
                    const rect = canvas.getBoundingClientRect();
                    const cx = rect.width / 2 + {offset[0]};
                    const cy = rect.height / 2 + {offset[1]};
                    const ev = new MouseEvent('pointerdown', {{
                        clientX: rect.left + cx,
                        clientY: rect.top + cy,
                        bubbles: true
                    }});
                    canvas.dispatchEvent(ev);
                    setTimeout(() => {{
                        const up = new MouseEvent('pointerup', {{
                            clientX: rect.left + cx,
                            clientY: rect.top + cy,
                            bubbles: true
                        }});
                        canvas.dispatchEvent(up);
                    }}, 50);
                }}
            ''')
            ctx.page.wait_for_timeout(200)
            return HandlerResult(success=True)
        except Exception as e:
            return HandlerResult(success=False, error=f"Click canvas error: {e}")

