"""Schema-based command generation module.

DEPRECATED: This package has been moved to nlp2cmd.generation.schema (Sprint 4).
This shim re-exports all symbols for backward compatibility.
"""

from nlp2cmd.generation.schema.generator import SchemaBasedGenerator, SchemaRegistry  # noqa: F401
from nlp2cmd.generation.schema.adapter import SchemaDrivenAppSpecAdapter  # noqa: F401

__all__ = [
    'SchemaBasedGenerator',
    'SchemaRegistry',
    'SchemaDrivenAppSpecAdapter',
]
