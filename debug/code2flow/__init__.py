"""
code2flow - Optimized Python Code Flow Analysis Tool

A high-performance tool for analyzing Python code control flow, data flow,
and call graphs with caching and parallel processing.
"""

__version__ = "0.2.0"
__author__ = "STTS Project"

from .core.analyzer import ProjectAnalyzer
from .core.config import Config, FAST_CONFIG
from .core.models import AnalysisResult, FunctionInfo, ClassInfo, Pattern

__all__ = [
    "ProjectAnalyzer",
    "Config",
    "FAST_CONFIG",
    "AnalysisResult",
    "FunctionInfo",
    "ClassInfo",
    "Pattern",
]
