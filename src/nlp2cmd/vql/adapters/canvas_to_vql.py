"""ActionPlan → VQLProgram adapter (analysis-oriented, best-effort)."""

from __future__ import annotations

from typing import Any

from nlp2cmd.vql.schema.program import (
    Layer,
    Object,
    Primitive,
    Scene,
    Style,
    Transform,
    VQLProgram,
)


def _offset(params: dict[str, Any]) -> tuple[float, float]:
    off = params.get("offset") or [0, 0]
    if isinstance(off, (list, tuple)) and len(off) >= 2:
        return float(off[0]), float(off[1])
    return 0.0, 0.0


def _action_to_primitive(action: str, params: dict[str, Any]) -> Primitive:
    if action == "draw_filled_circle" or action == "draw_circle":
        return Primitive(shape_type="circle", params={"radius": params.get("radius", 10)})
    if action == "draw_filled_ellipse" or action == "draw_ellipse":
        return Primitive(
            shape_type="ellipse",
            params={"rx": params.get("rx", 10), "ry": params.get("ry", 10)},
        )
    if action == "draw_filled_rectangle" or action == "draw_rectangle":
        return Primitive(
            shape_type="rectangle",
            params={"width": params.get("width", 10), "height": params.get("height", 10)},
        )
    if action == "draw_polygon":
        return Primitive(shape_type="polygon", params={"points": params.get("points", [])})
    if action == "draw_line":
        return Primitive(
            shape_type="line",
            params={
                "from_offset": params.get("from_offset", [0, 0]),
                "to_offset": params.get("to_offset", [0, 0]),
            },
        )
    if action == "draw_bezier":
        return Primitive(shape_type="bezier", params={"curves": params.get("curves", [])})
    if action == "draw_arc":
        return Primitive(
            shape_type="arc",
            params={
                "radius": params.get("radius", 10),
                "start_angle": params.get("start_angle", 0),
                "end_angle": params.get("end_angle", 0),
            },
        )
    return Primitive(shape_type=action.removeprefix("draw_"), params=dict(params))


def action_plan_to_vql_program(plan: Any, *, canvas_width: float = 683, canvas_height: float = 384) -> VQLProgram:
    """Lower canvas ActionPlan steps into a VQLProgram for analysis and replay metadata."""
    steps = getattr(plan, "steps", None) or []
    url = "https://jspaint.app"
    for step in steps:
        if getattr(step, "action", "") == "navigate":
            url = str((getattr(step, "params", None) or {}).get("url") or url)
            break

    scene = Scene(
        app="jspaint",
        url=url,
        width=canvas_width,
        height=canvas_height,
        layers=[],
    )
    layer = Layer(id="automation", objects=[])
    current_color = "#000000"
    fill = True
    line_width = 2.0

    for idx, step in enumerate(steps):
        action = getattr(step, "action", "") or ""
        params = dict(getattr(step, "params", None) or {})
        desc = getattr(step, "description", "") or action

        if action == "set_color":
            current_color = str(params.get("color") or current_color)
            continue
        if action == "set_line_width":
            line_width = float(params.get("width") or line_width)
            continue
        if not action.startswith("draw_"):
            continue

        ox, oy = _offset(params)
        rotation = float(params.get("rotation") or 0.0)
        layer.objects.append(
            Object(
                id=f"step_{idx:03d}_{action}",
                primitives=[_action_to_primitive(action, params)],
                style=Style(color=current_color, fill=fill, stroke_width=line_width),
                transform=Transform(translate_x=ox, translate_y=oy, rotate_deg=rotation * 57.2958 if abs(rotation) < 7 else rotation),
                center_x=ox,
                center_y=oy,
                metadata={
                    "description": desc,
                    "source_action": action,
                    "params": params,
                },
            )
        )

    scene.layers = [layer]
    return VQLProgram(
        scene=scene,
        metadata={
            "derived_from": "action_plan",
            "query": getattr(plan, "query", ""),
            "source": getattr(plan, "source", ""),
            "step_count": len(steps),
            "draw_object_count": len(layer.objects),
        },
    )
