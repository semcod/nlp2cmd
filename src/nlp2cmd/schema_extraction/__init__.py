"""
Dynamic schema extraction and analysis for NLP2CMD.

This module provides dynamic schema parsing capabilities for:
- OpenAPI/Swagger specifications
- Shell command help output
- Python source code with decorators
- Click applications
- And other command sources

Instead of hardcoded keywords, this module dynamically extracts
command patterns, parameters, and metadata from various sources.
"""

from __future__ import annotations

from .registry import SchemaRegistry, DynamicSchemaRegistry
from .extractors import (
    CommandParameter, 
    CommandSchema, 
    ExtractedSchema,
    OpenAPISchemaExtractor,
    ShellHelpExtractor
)
from .python_extractors import PythonCodeExtractor, ClickExtractor
from .script_extractors import ShellScriptExtractor, MakefileExtractor

# Re-export main classes for backward compatibility
__all__ = [
    "SchemaRegistry",
    "CommandParameter", 
    "CommandSchema",
    "ExtractedSchema",
    "OpenAPISchemaExtractor",
    "ShellHelpExtractor",
    "PythonCodeExtractor",
    "ClickExtractor", 
    "ShellScriptExtractor",
    "MakefileExtractor",
]
