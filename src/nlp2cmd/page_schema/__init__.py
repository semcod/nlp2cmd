"""Page Schema Extraction Package — Modular DOM element extractors.

This package provides modular components for extracting actionable elements
from browser page DOM. Used by SchemaFallback for dynamic fallback generation.
"""

from .base import ExtractorBase, PageSchema
from .button_extractor import ButtonExtractor
from .form_extractor import FormExtractor
from .radio_extractor import RadioExtractor
from .token_extractor import TokenExtractor
from .copy_button_extractor import CopyButtonExtractor
from .page_schema_extractor import PageSchemaExtractor

__all__ = [
    "ExtractorBase",
    "PageSchema",
    "ButtonExtractor",
    "FormExtractor",
    "RadioExtractor",
    "TokenExtractor",
    "CopyButtonExtractor",
    "PageSchemaExtractor",
]
