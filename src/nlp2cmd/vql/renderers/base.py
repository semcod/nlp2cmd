"""
VQL renderer contract.

Defines the unified ``Renderer.render(program)`` entry point requested by the
architecture: every backend (SVG, Playwright/canvas) consumes a
:class:`VQLProgram` rather than ad-hoc action lists.

To avoid changing the behavior of the existing
``nlp2cmd.skills.drawing.renderers`` backends, this module provides an
*additive* free function :func:`render_program` plus a thin
:class:`VQLRendererAdapter` mixin. Both compile the program to ``ShapeDrawn``
events (via the legacy-compatible compiler) and replay them through any
existing :class:`~nlp2cmd.skills.drawing.renderers.base.Renderer`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from nlp2cmd.vql.compiler.legacy_drawcommand import compile_to_events
from nlp2cmd.vql.schema.program import VQLProgram

if TYPE_CHECKING:  # pragma: no cover - typing only
    from nlp2cmd.skills.drawing.renderers.base import Renderer


@runtime_checkable
class VQLRenderer(Protocol):
    """Structural protocol for any backend able to render a VQL program."""

    async def render(self, program: VQLProgram) -> None: ...


async def render_program(renderer: "Renderer", program: VQLProgram) -> "Renderer":
    """
    Render a VQL program through an existing drawing ``Renderer``.

    Initializes the canvas from the program's scene, then replays the
    compiled ``ShapeDrawn`` events. Returns the renderer for chaining.
    """
    scene = program.scene
    await renderer.init_canvas(
        width=scene.width,
        height=scene.height,
        url=scene.url,
        app=scene.app,
    )
    events = compile_to_events(program)
    await renderer.render_events(events)
    return renderer


class VQLRendererAdapter:
    """
    Mixin granting an existing ``Renderer`` subclass a ``render(program)``
    method without altering its other behavior.

    Usage::

        class SVGVQLRenderer(VQLRendererAdapter, SVGRenderer):
            pass
    """

    async def render(self, program: VQLProgram) -> None:  # type: ignore[override]
        await render_program(self, program)  # type: ignore[arg-type]
