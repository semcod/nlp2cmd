# SetColorHandler - extracted from drawing.py
"""Drawing and canvas step handlers."""
from __future__ import annotations
import json
from typing import TYPE_CHECKING
from .base import StepHandler, HandlerContext, HandlerResult
from .registry import register_handler
if TYPE_CHECKING:
    pass
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

