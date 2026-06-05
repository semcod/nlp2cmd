"""
Playwright render target for VQL programs.

Wraps the browser-canvas :class:`PlaywrightRenderer` so it can consume a
:class:`VQLProgram` directly via the unified ``render(program)`` contract.
The mouse-control logic itself is unchanged; this adapter only adds the
program entry point (init canvas from scene → replay compiled events).
"""

from __future__ import annotations

from typing import Any

from nlp2cmd.skills.drawing.renderers.playwright import PlaywrightRenderer
from nlp2cmd.vql.renderers.base import VQLRendererAdapter


class PlaywrightVQLRenderer(VQLRendererAdapter, PlaywrightRenderer):
    """Playwright renderer that can consume a :class:`VQLProgram` directly."""

    def __init__(self, page: Any, human_like: bool = True) -> None:
        PlaywrightRenderer.__init__(self, page, human_like=human_like)
