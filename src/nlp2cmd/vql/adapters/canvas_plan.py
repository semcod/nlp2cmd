"""
VQL → canvas execution-plan adapter.

This is the integration glue between the VQL IR and ``nlp2cmd``'s canvas
execution layer (Playwright step handlers). It does **not** belong to the VQL
core language — it only lowers a validated :class:`VQLProgram` into the
``canvas_dql.v1`` step vocabulary already understood by
``nlp2cmd.step_handlers`` (``navigate`` → ``draw_polygon`` → ``screenshot``).

Each object's compiled geometry (``ShapeDrawn`` point groups, absolute canvas
coordinates) is converted to center-relative polygons, matching the
``draw_polygon`` handler contract.
"""

from __future__ import annotations

from typing import Any

from vql.compiler.legacy_drawcommand import compile_to_events
from vql.schema.program import VQLProgram


def program_to_canvas_steps(program: VQLProgram) -> list[dict[str, Any]]:
    """
    Lower a VQL program into ``canvas_dql.v1`` steps.

    The geometry is compiled via the shared command path so the canvas render
    matches the SVG render shape-for-shape.
    """
    scene = program.scene
    cx_canvas = scene.width / 2.0
    cy_canvas = scene.height / 2.0

    steps: list[dict[str, Any]] = [
        {"action": "navigate", "url": scene.url or "https://jspaint.app"},
        {"action": "wait", "ms": 3000},
        {"action": "wait_for_canvas"},
        {"action": "get_canvas_info"},
    ]

    last_color: str | None = None
    # compile_to_events emits one event per primitive — align objects per primitive
    events = compile_to_events(program)
    owners = [
        obj
        for obj in scene.iter_objects()
        for _ in obj.primitives
    ]

    for obj, event in zip(owners, events):
        color = obj.style.color
        if color != last_color:
            steps.append({"action": "set_color", "color": color})
            last_color = color

        for group in event.points:
            rel_points = [[x - cx_canvas, y - cy_canvas] for (x, y) in group]
            if len(rel_points) >= 3:
                steps.append(
                    {
                        "action": "draw_polygon",
                        "points": rel_points,
                        "offset": [0, 0],
                        "fill": bool(obj.style.fill),
                        "line_width": obj.style.stroke_width,
                    }
                )
            elif len(rel_points) == 2:
                # 2-point group is a line segment — draw_polygon needs >=3 pts
                steps.append(
                    {
                        "action": "draw_line",
                        "from_offset": rel_points[0],
                        "to_offset": rel_points[1],
                    }
                )

    steps.append({"action": "screenshot", "suffix": scene.app or "vql"})
    return steps


def program_to_canvas_payload(program: VQLProgram) -> dict[str, Any]:
    """Build the full ``canvas_dql.v1`` payload (app/url/steps) from a program."""
    scene = program.scene
    return {
        "dsl": "canvas_dql.v1",
        "app": scene.app or "jspaint",
        "url": scene.url or "https://jspaint.app",
        "steps": program_to_canvas_steps(program),
    }
