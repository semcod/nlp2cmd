"""VQL validation — structural + spec validation of programs."""

from nlp2cmd.vql.validation.spec import (
    VQLValidationReport,
    validate_program,
)

__all__ = [
    "VQLValidationReport",
    "validate_program",
]
