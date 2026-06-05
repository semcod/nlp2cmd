"""
VQL facade — the high-level entry point ``nlp2cmd`` calls for drawing intents.

The facade hides the internal pipeline (parse → compile → validate → render)
behind a small, stable surface. ``nlp2cmd`` only needs to:

    from nlp2cmd.vql import VQLFacade

    result = VQLFacade().run("narysuj czerwone koło")
    result.program     # the VQLProgram (source of truth)
    result.svg         # rendered SVG artifact
    result.report      # structural validation report

It does not need to know about shape generators, the event store, SVG markup,
or the visual validator internals.
"""

from __future__ import annotations

from dataclasses import dataclass

from nlp2cmd.vql.compiler.legacy_drawcommand import compile_to_events, program_to_commands
from nlp2cmd.vql.compiler.nl_to_vql import nl_to_program
from nlp2cmd.vql.renderers.svg import render_to_png, render_to_svg
from nlp2cmd.vql.schema.program import RenderTarget, VQLProgram
from nlp2cmd.vql.validation.spec import VQLValidationReport, validate_program


@dataclass
class VQLResult:
    """Bundle returned by :meth:`VQLFacade.run`."""

    program: VQLProgram
    report: VQLValidationReport
    svg: str | None = None


class VQLFacade:
    """Stateless high-level entry point for the VQL pipeline."""

    def compile(
        self,
        text: str,
        *,
        width: float = 1024.0,
        height: float = 768.0,
        url: str = "",
        app: str = "generic",
        render_target: RenderTarget = RenderTarget.SVG,
    ) -> VQLProgram:
        """Compile natural language into a :class:`VQLProgram`."""
        return nl_to_program(
            text,
            width=width,
            height=height,
            url=url,
            app=app,
            render_target=render_target,
        )

    def validate(self, program: VQLProgram) -> VQLValidationReport:
        """Validate a program structurally and against its spec."""
        return validate_program(program)

    def render_svg(self, program: VQLProgram) -> str:
        """Render a program to an SVG string."""
        return render_to_svg(program)

    def render_png(self, program: VQLProgram, path: str, *, scale: float = 1.0) -> str:
        """Render a program to a raster PNG file (requires the ``vql`` extra)."""
        return render_to_png(program, path, scale=scale)

    def to_commands(self, program: VQLProgram):
        """Lower a program to the legacy ``DrawCommand`` sequence."""
        return program_to_commands(program)

    def to_events(self, program: VQLProgram):
        """Compile a program to ``ShapeDrawn`` events."""
        return compile_to_events(program)

    def run(
        self,
        text: str,
        *,
        width: float = 1024.0,
        height: float = 768.0,
        url: str = "",
        app: str = "generic",
        render: bool = True,
    ) -> VQLResult:
        """Full pipeline: NL → VQL → validate → (optional) render SVG."""
        program = self.compile(text, width=width, height=height, url=url, app=app)
        report = self.validate(program)
        svg = self.render_svg(program) if render else None
        return VQLResult(program=program, report=report, svg=svg)
