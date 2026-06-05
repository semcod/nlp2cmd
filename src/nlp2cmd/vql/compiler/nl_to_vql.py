"""
NL → VQL compiler.

Wraps the existing :class:`NLDrawingParser` so natural language is first
turned into a :class:`VQLProgram` (the contract), instead of being consumed
directly as drawing actions. The legacy parser remains the source of the
shape/color extraction logic; this module only lifts its output into the IR.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nlp2cmd.vql.compiler.legacy_drawcommand import commands_to_program
from nlp2cmd.vql.schema.program import RenderTarget, ValidationSpec, VQLProgram

if TYPE_CHECKING:  # pragma: no cover - typing only
    from nlp2cmd.skills.drawing.nl_parser import NLDrawingParser


def nl_to_program(
    text: str,
    *,
    width: float = 1024.0,
    height: float = 768.0,
    url: str = "",
    app: str = "generic",
    render_target: RenderTarget = RenderTarget.SVG,
    parser: "NLDrawingParser | None" = None,
    with_validation_spec: bool = True,
) -> VQLProgram:
    """
    Parse natural language into a :class:`VQLProgram`.

    Args:
        text: Natural language drawing instruction (PL/EN).
        width/height: Canvas dimensions (for centering).
        url/app: Canvas target metadata.
        render_target: Desired backend.
        parser: Optional pre-built :class:`NLDrawingParser`.
        with_validation_spec: Attach a :class:`ValidationSpec` derived from the
            detected shapes/colors so the result can be validated/corrected.
    """
    from nlp2cmd.skills.drawing.nl_parser import NLDrawingParser

    parser = parser or NLDrawingParser()
    commands = parser.parse(text, canvas_width=width, canvas_height=height)

    program = commands_to_program(
        commands,
        width=width,
        height=height,
        url=url,
        app=app,
        render_target=render_target,
        metadata={"source": "nl", "query": text},
    )

    if with_validation_spec:
        shapes = sorted({obj.primitives[0].shape_type for obj in program.scene.iter_objects() if obj.primitives})
        colors = sorted({obj.style.color for obj in program.scene.iter_objects()})
        program.validation = ValidationSpec(
            description=text,
            expected_shapes=shapes,
            expected_colors=colors,
            min_objects=program.object_count(),
        )

    return program
