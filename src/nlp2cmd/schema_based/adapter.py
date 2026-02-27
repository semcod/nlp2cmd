"""Enhanced AppSpec adapter with schema-based generation.

DEPRECATED: Moved to nlp2cmd.generation.schema.adapter (Sprint 4).
This shim re-exports for backward compatibility.
"""

from nlp2cmd.generation.schema.adapter import SchemaDrivenAppSpecAdapter  # noqa: F401

__all__ = ["SchemaDrivenAppSpecAdapter"]
