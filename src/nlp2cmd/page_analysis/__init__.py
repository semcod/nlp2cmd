"""Page Analysis Package — Modular page content analysis for web scraping.

This package provides modular components for analyzing web pages, including
form detection, field classification, iframe analysis, and link extraction.
"""

from .base import PageAnalysisResult, FieldInfo
from .form_analyzer import FormAnalyzer
from .field_classifier import FieldClassifier
from .iframe_analyzer import IframeAnalyzer
from .link_extractor import LinkExtractor
from .page_analyzer import PageAnalyzer

__all__ = [
    "PageAnalysisResult",
    "FieldInfo",
    "FormAnalyzer",
    "FieldClassifier",
    "IframeAnalyzer",
    "LinkExtractor",
    "PageAnalyzer",
]
