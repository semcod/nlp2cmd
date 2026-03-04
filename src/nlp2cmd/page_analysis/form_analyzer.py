"""Form analyzer for detecting and extracting form information."""

from __future__ import annotations
from typing import Any, Optional
import logging

from .base import FieldInfo

log = logging.getLogger("nlp2cmd.page_analysis.form")


class FormAnalyzer:
    """Analyze page for forms and form fields."""
    
    def __init__(self, max_inputs: int = 30, max_textareas: int = 15) -> None:
        self.max_inputs = max_inputs
        self.max_textareas = max_textareas
    
    def analyze(self, page: Any) -> tuple[int, int, list[Any], list[Any], list[Any]]:
        """Analyze page for forms.
        
        Returns:
            Tuple of (form_count, visible_field_count, inputs, textareas, selects)
        """
        inputs: list[Any] = []
        textareas: list[Any] = []
        selects: list[Any] = []
        
        try:
            inputs = page.query_selector_all('input:not([type="hidden"])')
            textareas = page.query_selector_all('textarea')
            selects = page.query_selector_all('select')
            
            form_count = len(inputs) + len(textareas) + len(selects)
            
            return form_count, form_count, inputs, textareas, selects
            
        except Exception as e:
            log.debug("Form analysis failed: %s", e)
            return 0, 0, [], [], []
    
    def extract_field_info(self, node: Any) -> Optional[FieldInfo]:
        """Extract field information from a DOM node."""
        try:
            tag = self._get_tag(node)
            field_type = self._get_field_type(node, tag)
            name = self._get_attribute(node, 'name')
            field_id = self._get_attribute(node, 'id')
            placeholder = self._get_attribute(node, 'placeholder')
            aria_label = self._get_attribute(node, 'aria-label')
            
            return FieldInfo(
                tag=tag,
                field_type=field_type,
                name=name,
                field_id=field_id,
                placeholder=placeholder,
                aria_label=aria_label,
            )
        except Exception as e:
            log.debug("Failed to extract field info: %s", e)
            return None
    
    def _get_tag(self, node: Any) -> str:
        """Get tag name from node."""
        try:
            return (node.evaluate('el => el.tagName.toLowerCase()') or "").strip().lower()
        except Exception:
            return "input"
    
    def _get_field_type(self, node: Any, tag: str) -> str:
        """Get field type from node."""
        try:
            return node.get_attribute('type') or ("textarea" if tag == "textarea" else "text")
        except Exception:
            return "text"
    
    def _get_attribute(self, node: Any, attr: str) -> str:
        """Get attribute from node."""
        try:
            return node.get_attribute(attr) or ""
        except Exception:
            return ""
    
    def get_field_nodes(self, inputs: list[Any], textareas: list[Any]) -> list[Any]:
        """Get combined list of field nodes with limits."""
        nodes: list[Any] = []
        
        # Add inputs up to limit
        try:
            nodes.extend(inputs[:self.max_inputs])
        except Exception:
            nodes.extend(inputs)
        
        # Add textareas up to limit
        try:
            nodes.extend(textareas[:self.max_textareas])
        except Exception:
            nodes.extend(textareas)
        
        return nodes
