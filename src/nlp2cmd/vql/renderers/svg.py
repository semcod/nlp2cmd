"""
SVG render target for VQL programs.

Reuses the reference :class:`SVGRenderer` from the drawing skill and exposes
both a ``render(program)`` capable subclass and a synchronous convenience
:func:`render_to_svg` helper (handy for tests and previews).
"""

from __future__ import annotations

import asyncio

from nlp2cmd.skills.drawing.renderers.svg import SVGRenderer
from nlp2cmd.vql.renderers.base import VQLRendererAdapter, render_program
from nlp2cmd.vql.schema.program import VQLProgram


class SVGVQLRenderer(VQLRendererAdapter, SVGRenderer):
    """SVG renderer that can consume a :class:`VQLProgram` directly."""


def render_to_svg(program: VQLProgram) -> str:
    """Render a VQL program to an SVG string (synchronous convenience)."""
    renderer = SVGVQLRenderer()
    asyncio.run(render_program(renderer, program))
    return renderer.to_svg()
