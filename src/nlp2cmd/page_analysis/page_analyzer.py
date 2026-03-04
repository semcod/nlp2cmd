"""Main page analyzer orchestrator."""

from __future__ import annotations
from typing import Any, Optional
import logging

from .base import PageAnalysisResult, FieldInfo
from .form_analyzer import FormAnalyzer
from .field_classifier import FieldClassifier
from .iframe_analyzer import IframeAnalyzer
from .link_extractor import LinkExtractor

log = logging.getLogger("nlp2cmd.page_analysis")


class PageAnalyzer:
    """Main orchestrator for page analysis.
    
    Coordinates multiple analyzers to extract comprehensive page information.
    """
    
    def __init__(
        self,
        max_links: int = 10,
        max_inputs: int = 30,
        max_textareas: int = 15,
        max_iframes: int = 3,
    ) -> None:
        self.form_analyzer = FormAnalyzer(max_inputs=max_inputs, max_textareas=max_textareas)
        self.field_classifier = FieldClassifier()
        self.iframe_analyzer = IframeAnalyzer(max_iframes=max_iframes)
        self.link_extractor = LinkExtractor(max_links=max_links)
    
    def analyze(self, page: Any, url: str) -> PageAnalysisResult:
        """Analyze page comprehensively.
        
        Args:
            page: Playwright page object
            url: Page URL
            
        Returns:
            PageAnalysisResult with all extracted information
        """
        result = PageAnalysisResult(url=url)
        
        # Extract title
        try:
            result.title = page.title() or ""
        except Exception:
            pass
        
        # Analyze forms
        form_count, visible_count, inputs, textareas, selects = self.form_analyzer.analyze(page)
        result.form_count = form_count
        result.has_form = form_count > 0
        
        # Extract and classify fields
        field_nodes = self.form_analyzer.get_field_nodes(inputs, textareas)
        fields: list[FieldInfo] = []
        
        for node in field_nodes:
            field_info = self.form_analyzer.extract_field_info(node)
            if field_info:
                fields.append(field_info)
        
        # Classify fields
        contact_count, junk_count = self.field_classifier.classify_batch(fields)
        result.fields = fields
        result.contact_field_count = contact_count
        result.junk_field_count = junk_count
        
        # Check for forms in iframes (if no forms found on main page)
        if not result.has_form:
            has_iframe_form, iframe_field_count = self.iframe_analyzer.analyze(page)
            if has_iframe_form:
                result.has_form = True
                result.form_count += iframe_field_count
        
        # Extract links
        result.links = self.link_extractor.extract(page, url)
        
        log.debug(
            "Page analysis complete: %s - forms=%d, contact_fields=%d, junk_fields=%d, links=%d",
            url, result.form_count, result.contact_field_count, result.junk_field_count, len(result.links)
        )
        
        return result
    
    def analyze_quick(self, page: Any, url: str) -> PageAnalysisResult:
        """Quick analysis with reduced limits.
        
        Args:
            page: Playwright page object
            url: Page URL
            
        Returns:
            PageAnalysisResult with basic information
        """
        # Temporarily reduce limits
        original_max_inputs = self.form_analyzer.max_inputs
        original_max_textareas = self.form_analyzer.max_textareas
        original_max_links = self.link_extractor.max_links
        
        self.form_analyzer.max_inputs = 10
        self.form_analyzer.max_textareas = 5
        self.link_extractor.max_links = 5
        
        try:
            result = self.analyze(page, url)
        finally:
            # Restore original limits
            self.form_analyzer.max_inputs = original_max_inputs
            self.form_analyzer.max_textareas = original_max_textareas
            self.link_extractor.max_links = original_max_links
        
        return result
