"""Drawing and canvas step handlers."""

from __future__ import annotations

from .base import HandlerContext, HandlerResult, StepHandler
from .canvas_mixin import CanvasMixin
from .click_canvas_handler import ClickCanvasHandler
from .draw_arc_handler import DrawArcHandler
from .draw_bezier_handler import DrawBezierHandler
from .draw_circle_handler import DrawCircleHandler
from .draw_ellipse_handler import DrawEllipseHandler
from .draw_filled_circle_handler import DrawFilledCircleHandler
from .draw_filled_ellipse_handler import DrawFilledEllipseHandler
from .draw_filled_rectangle_handler import DrawFilledRectangleHandler
from .draw_line_handler import DrawLineHandler
from .draw_polygon_handler import DrawPolygonHandler
from .draw_rectangle_handler import DrawRectangleHandler
from .draw_svg_path_handler import DrawSvgPathHandler
from .fill_at_handler import FillAtHandler
from .get_canvas_center_handler import GetCanvasCenterHandler
from .registry import register_handler
from .select_tool_handler import SelectToolHandler
from .set_color_handler import SetColorHandler
from .set_line_width_handler import SetLineWidthHandler
from .wait_for_canvas_handler import WaitForCanvasHandler

__all__ = [
    "CanvasMixin",
    "WaitForCanvasHandler",
    "GetCanvasCenterHandler",
    "SelectToolHandler",
    "SetColorHandler",
    "SetLineWidthHandler",
    "DrawCircleHandler",
    "DrawFilledCircleHandler",
    "DrawFilledEllipseHandler",
    "DrawFilledRectangleHandler",
    "DrawRectangleHandler",
    "DrawLineHandler",
    "DrawEllipseHandler",
    "DrawArcHandler",
    "DrawPolygonHandler",
    "DrawBezierHandler",
    "DrawSvgPathHandler",
    "FillAtHandler",
    "ClickCanvasHandler",
]


def _create_simple_draw_handler(action_name: str, template: str, error_msg: str):
    """Factory for simple drawing handlers."""

    @register_handler(action_name)
    class SimpleDrawHandler(StepHandler, CanvasMixin):
        def execute(self, ctx: HandlerContext) -> HandlerResult:
            try:
                pick_canvas = self._pick_canvas_js()
                color = self._get_color_js()
                params = ctx.params
                ctx.page.evaluate(
                    template.format(
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
                    )
                )
                ctx.page.wait_for_timeout(200)
                return HandlerResult(success=True)
            except Exception as e:
                return HandlerResult(success=False, error=f"{error_msg}: {e}")

    return SimpleDrawHandler
