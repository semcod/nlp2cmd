"""
Legacy compatibility compiler — bridges VQL programs and the existing
``DrawCommand`` / ``ShapeDrawn`` pipeline.

This adapter lets the new VQL IR coexist with the working drawing pipeline:

* :func:`program_to_commands` lowers a :class:`VQLProgram` into the ordered
  ``DrawCommand`` sequence the existing ``CommandBus`` understands.
* :func:`commands_to_program` lifts a ``DrawCommand`` sequence back into a
  :class:`VQLProgram` (used to wrap the legacy ``NLDrawingParser`` output).
* :func:`compile_to_events` reuses the real ``CommandBus`` so the geometry of
  the VQL path is byte-for-byte identical to the legacy path.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nlp2cmd.vql.schema.program import (
    Layer,
    Object,
    Primitive,
    Scene,
    Style,
    VQLProgram,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from nlp2cmd.skills.drawing.commands import DrawCommand
    from nlp2cmd.skills.drawing.events import ShapeDrawn


def program_to_commands(program: VQLProgram) -> list["DrawCommand"]:
    """Lower a VQL program into a legacy ``DrawCommand`` sequence."""
    from nlp2cmd.skills.drawing.commands import (
        DrawShape,
        InitCanvas,
        SetColor,
    )

    scene = program.scene
    commands: list["DrawCommand"] = [
        InitCanvas(
            width=scene.width,
            height=scene.height,
            url=scene.url,
            app=scene.app,
        )
    ]

    last_color: str | None = None
    for obj in scene.iter_objects():
        color = obj.style.color
        if color != last_color:
            commands.append(SetColor(color=color))
            last_color = color
        for prim in obj.primitives:
            commands.append(
                DrawShape(
                    shape_type=prim.shape_type,
                    color=color,
                    fill=obj.style.fill,
                    center_x=obj.center_x,
                    center_y=obj.center_y,
                    params=dict(prim.params),
                )
            )

    return commands


def commands_to_program(
    commands: list["DrawCommand"],
    *,
    width: float = 1024.0,
    height: float = 768.0,
    url: str = "",
    app: str = "generic",
    render_target=None,
    metadata: dict | None = None,
) -> VQLProgram:
    """Lift a legacy ``DrawCommand`` sequence into a VQL program."""
    from nlp2cmd.skills.drawing.commands import (
        ClearCanvas,
        DrawShape,
        InitCanvas,
        SetColor,
    )
    from nlp2cmd.vql.schema.program import RenderTarget

    scene = Scene(width=width, height=height, url=url, app=app)
    layer = Layer(id="default")
    scene.layers.append(layer)

    current_color = "#000000"
    obj_index = 0

    for cmd in commands:
        if isinstance(cmd, InitCanvas):
            scene.width = cmd.width
            scene.height = cmd.height
            scene.url = cmd.url
            scene.app = cmd.app
        elif isinstance(cmd, SetColor):
            current_color = cmd.color
        elif isinstance(cmd, ClearCanvas):
            layer.objects.clear()
        elif isinstance(cmd, DrawShape):
            layer.objects.append(
                Object(
                    id=f"obj_{obj_index}",
                    primitives=[Primitive(shape_type=cmd.shape_type, params=dict(cmd.params))],
                    style=Style(color=cmd.color or current_color, fill=cmd.fill),
                    center_x=cmd.center_x,
                    center_y=cmd.center_y,
                )
            )
            obj_index += 1

    return VQLProgram(
        scene=scene,
        render_target=render_target or RenderTarget.SVG,
        metadata=dict(metadata or {}),
    )


def compile_to_events(program: VQLProgram) -> list["ShapeDrawn"]:
    """
    Compile a VQL program into ``ShapeDrawn`` events by replaying the lowered
    commands through the real ``CommandBus`` (identical geometry to legacy).
    """
    from nlp2cmd.skills.drawing.commands import CommandBus
    from nlp2cmd.skills.drawing.event_store import EventStore
    from nlp2cmd.skills.drawing.events import ShapeDrawn

    bus = CommandBus(EventStore())
    events: list["ShapeDrawn"] = []
    for cmd in program_to_commands(program):
        event = bus.dispatch(cmd)
        if isinstance(event, ShapeDrawn):
            events.append(event)
    return events
