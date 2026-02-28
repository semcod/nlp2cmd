"""
code2flow - Optimized Python Code Flow Analysis Tool

A high-performance tool for analyzing Python code control flow, data flow,
and call graphs with caching and parallel processing.

Includes NLP Processing Pipeline for query normalization, intent matching,
and entity resolution with multilingual support.
"""

__version__ = "0.2.1"
__author__ = "STTS Project"

# Core analysis components
from .core.analyzer import ProjectAnalyzer
from .core.config import Config, FAST_CONFIG
from .core.models import AnalysisResult, FunctionInfo, ClassInfo, Pattern

# NLP Processing Pipeline
from .nlp import (
    NLPPipeline,
    QueryNormalizer,
    IntentMatcher,
    EntityResolver,
    NLPConfig,
    FAST_NLP_CONFIG,
    PRECISE_NLP_CONFIG,
)

__all__ = [
    # Core
    "ProjectAnalyzer",
    "Config",
    "FAST_CONFIG",
    "AnalysisResult",
    "FunctionInfo",
    "ClassInfo",
    "Pattern",
    # NLP Pipeline
    "NLPPipeline",
    "QueryNormalizer",
    "IntentMatcher",
    "EntityResolver",
    "NLPConfig",
    "FAST_NLP_CONFIG",
    "PRECISE_NLP_CONFIG",
]
