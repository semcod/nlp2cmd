"""Backward-compat shim — VQL lives in the standalone ``vql`` package."""

from vql import (
    RenderTarget,
    Scene,
    Style,
    ValidationSpec,
    VQLFacade,
    VQLProgram,
    VQLValidationReport,
    commands_to_program,
    compile_to_events,
    nl_to_program,
    program_to_commands,
    render_program,
    render_to_png,
    render_to_svg,
    validate_program,
)
from vql.facade import VQLResult

from nlp2cmd.vql.adapters.canvas_plan import program_to_canvas_payload, program_to_canvas_steps
from nlp2cmd.vql.adapters.canvas_to_vql import action_plan_to_vql_program

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
    "render_to_png",
    "render_program",
    "validate_program",
    "VQLValidationReport",
    "action_plan_to_vql_program",
    "program_to_canvas_payload",
    "program_to_canvas_steps",
]
