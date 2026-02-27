"""Schema-based command generation module.

Moved from nlp2cmd.schema_based to nlp2cmd.generation.schema (Sprint 4).
"""

from .generator import SchemaBasedGenerator, SchemaRegistry
from .adapter import SchemaDrivenAppSpecAdapter

__all__ = [
    'SchemaBasedGenerator',
    'SchemaRegistry',
    'SchemaDrivenAppSpecAdapter',
]
