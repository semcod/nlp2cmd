"""
VQL — Visual Query Language for nlp2cmd.

A self-contained domain package providing an intermediate representation (IR)
for drawing/graphics tasks. ``nlp2cmd`` treats VQL as one of its target IRs
(alongside shell, DOM, Docker, Kubernetes): it detects a drawing intent,
compiles natural language into a :class:`VQLProgram`, validates it, and
compiles it to a render backend (SVG today, Playwright/canvas next).

Public surface (import from here or from ``nlp2cmd.vql.api``):

    from nlp2cmd.vql import VQLFacade, VQLProgram, render_to_svg

Internal modules (generators, event store, correction internals) remain
private to the package and reachable only through the facade/api.
"""

from nlp2cmd.vql.api import (
    RenderTarget,
    Scene,
    Style,
    ValidationSpec,
    VQLFacade,
    VQLProgram,
    VQLResult,
    VQLValidationReport,
    commands_to_program,
    compile_to_events,
    nl_to_program,
    program_to_commands,
    render_program,
    render_to_svg,
    validate_program,
)

__all__ = [
    "VQLFacade",
    "VQLResult",
    "VQLProgram",
    "Scene",
    "Style",
    "ValidationSpec",
    "RenderTarget",
    "nl_to_program",
    "program_to_commands",
    "commands_to_program",
    "compile_to_events",
    "render_to_svg",
    "render_program",
    "validate_program",
    "VQLValidationReport",
]
