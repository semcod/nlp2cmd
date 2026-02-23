"""
Keywords package for NLP2CMD intent detection.

This package contains keyword-based intent detection components
split into modular patterns and detection logic.
"""

from .keyword_patterns import KeywordPatterns
from .keyword_detector import KeywordIntentDetector, DetectionResult

__all__ = [
    'KeywordPatterns',
    'KeywordIntentDetector', 
    'DetectionResult',
]
