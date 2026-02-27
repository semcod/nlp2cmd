"""Schema-based command generator without hardcoded templates.

DEPRECATED: Moved to nlp2cmd.generation.schema.generator (Sprint 4).
This shim re-exports for backward compatibility.
"""

from nlp2cmd.generation.schema.generator import (  # noqa: F401
    SchemaBasedGenerator,
    SchemaRegistry,
)

__all__ = ["SchemaBasedGenerator", "SchemaRegistry"]
