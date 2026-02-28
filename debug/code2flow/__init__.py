"""
code2flow - Python Code Flow Analysis Tool

A comprehensive tool for analyzing Python code control flow, data flow,
and call graphs for reverse engineering and code understanding.
"""

__version__ = "0.1.0"
__author__ = "STTS Project"

from .core.analyzer import ProjectAnalyzer
from .core.config import Config
from .extractors.cfg_extractor import CFGExtractor
from .extractors.dfg_extractor import DFGExtractor
from .extractors.call_graph import CallGraphExtractor

__all__ = [
    "ProjectAnalyzer",
    "Config", 
    "CFGExtractor",
    "DFGExtractor",
    "CallGraphExtractor",
]
