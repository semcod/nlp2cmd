"""Iframe analyzer for detecting forms inside iframes."""

from __future__ import annotations
from typing import Any, Optional
import logging

log = logging.getLogger("nlp2cmd.page_analysis.iframe")


class IframeAnalyzer:
    """Analyze iframes for embedded forms (common for contact widgets)."""
    
    def __init__(self, max_iframes: int = 3) -> None:
        self.max_iframes = max_iframes
    
    def analyze(self, page: Any) -> tuple[bool, int]:
        """Check for forms inside iframes.
        
        Returns:
            Tuple of (has_form_in_iframe, field_count)
        """
        try:
            iframes = page.query_selector_all('iframe')
            
            for i, iframe in enumerate(iframes[:self.max_iframes]):
                try:
                    frame = iframe.content_frame()
                    if frame:
                        # Count inputs in iframe
                        iframe_inputs = frame.query_selector_all('input:not([type="hidden"])')
                        iframe_textareas = frame.query_selector_all('textarea')
                        
                        field_count = len(iframe_inputs) + len(iframe_textareas)
                        
                        if field_count > 0:
                            log.debug("Found form in iframe %d with %d fields", i, field_count)
                            return True, field_count
                            
                except Exception:
                    continue
                    
        except Exception as e:
            log.debug("Iframe analysis failed: %s", e)
        
        return False, 0
