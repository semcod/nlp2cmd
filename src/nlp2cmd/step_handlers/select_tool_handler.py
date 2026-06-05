# SelectToolHandler - extracted from drawing.py
"""Drawing and canvas step handlers."""
from __future__ import annotations
import json
from typing import TYPE_CHECKING
from .base import StepHandler, HandlerContext, HandlerResult
from .registry import register_handler
if TYPE_CHECKING:
    pass
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

