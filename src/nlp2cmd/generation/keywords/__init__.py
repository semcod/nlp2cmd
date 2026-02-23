"""
Keywords package for NLP2CMD intent detection.

This package contains keyword-based intent detection components
split into modular patterns and detection logic.
"""

from .keyword_patterns import KeywordPatterns
from .keyword_detector import KeywordIntentDetector, DetectionResult
from nlp2cmd.utils.data_files import find_data_files

__all__ = [
    'KeywordPatterns',
    'KeywordIntentDetector',
    'DetectionResult',
    'find_data_files',
]
