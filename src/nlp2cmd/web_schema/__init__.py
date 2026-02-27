"""
Web schema extraction and learning module.

Provides:
- Schema extraction from web pages (Opcja B)
- Interaction history tracking (Opcja C)
- Schema learning from user behavior
- Site exploration for automatic form discovery
"""

from nlp2cmd.web_schema.extractor import WebSchemaExtractor, extract_web_schema
from nlp2cmd.web_schema.history import InteractionHistory, InteractionRecord
from nlp2cmd.web_schema.site_explorer import (
    SiteExplorer, 
    quick_find_form, 
    quick_find_content,
    ExplorationResult,
    PageInfo,
)

__all__ = [
    "WebSchemaExtractor",
    "extract_web_schema",
    "InteractionHistory",
    "InteractionRecord",
    "SiteExplorer",
    "quick_find_form",
    "quick_find_content",
    "ExplorationResult",
    "PageInfo",
]
