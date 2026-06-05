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


def render_to_png(program: VQLProgram, path: str, *, scale: float = 1.0) -> str:
    """
    Render a VQL program to a raster PNG file.

    Requires the optional ``vql`` extra (``pip install nlp2cmd[vql]``), which
    pulls in ``cairosvg``. Raises a clear error if it is unavailable.
    """
    from pathlib import Path

    svg = render_to_svg(program)
    try:
        import cairosvg  # type: ignore
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        raise RuntimeError(
            "PNG export requires the 'vql' extra. Install it with: "
            "pip install 'nlp2cmd[vql]'"
        ) from exc

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=str(out), scale=scale)
    return str(out)
