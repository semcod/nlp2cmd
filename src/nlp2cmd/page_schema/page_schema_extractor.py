"""Main page schema extractor that coordinates all extractors."""

from __future__ import annotations
from typing import Any
import logging

from .base import PageSchema
from .button_extractor import ButtonExtractor
from .form_extractor import FormExtractor
from .radio_extractor import RadioExtractor
from .token_extractor import TokenExtractor
from .copy_button_extractor import CopyButtonExtractor

log = logging.getLogger("nlp2cmd.page_schema")


class PageSchemaExtractor:
    """Extract complete page schema using multiple specialized extractors.
    
    This is the main entry point for page schema extraction, coordinating
    multiple extractors to build a comprehensive schema of actionable elements.
    
    Replaces the monolithic _extract_page_schema method in schema_fallback.py.
    """
    
    def __init__(self) -> None:
        self._extractors = {
            "buttons": ButtonExtractor(),
            "forms": FormExtractor(),
            "radio_buttons": RadioExtractor(),
            "tokens": TokenExtractor(),
            "copy_buttons": CopyButtonExtractor(),
        }
    
    def extract(self, page: Any) -> PageSchema:
        """Extract complete page schema.
        
        Args:
            page: Playwright page object
            
        Returns:
            PageSchema with all extracted elements
        """
        schema = PageSchema()
        
        try:
            schema.buttons = self._extractors["buttons"].extract(page)
        except Exception as e:
            log.debug("Button extraction failed: %s", e)
        
        try:
            schema.forms = self._extractors["forms"].extract(page)
        except Exception as e:
            log.debug("Form extraction failed: %s", e)
        
        try:
            schema.radio_buttons = self._extractors["radio_buttons"].extract(page)
        except Exception as e:
            log.debug("Radio extraction failed: %s", e)
        
        try:
            schema.tokens = self._extractors["tokens"].extract(page)
        except Exception as e:
            log.debug("Token extraction failed: %s", e)
        
        try:
            schema.copy_buttons = self._extractors["copy_buttons"].extract(page)
        except Exception as e:
            log.debug("Copy button extraction failed: %s", e)
        
        return schema
    
    def extract_dict(self, page: Any) -> dict[str, list[dict[str, str]]]:
        """Extract page schema as dictionary.
        
        This is a convenience method for backward compatibility with
        the original _extract_page_schema return format.
        """
        schema = self.extract(page)
        return schema.to_dict()
