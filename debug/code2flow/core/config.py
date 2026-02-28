"""Configuration and constants for code2flow."""

from dataclasses import dataclass, field
from typing import List, Set
from enum import Enum


class AnalysisMode(str, Enum):
    """Available analysis modes."""
    STATIC = "static"
    DYNAMIC = "dynamic"
    HYBRID = "hybrid"
    BEHAVIORAL = "behavioral"
    REVERSE = "reverse"


@dataclass
class PerformanceConfig:
    """Performance optimization settings."""
    enable_cache: bool = True
    cache_dir: str = ".code2flow_cache"
    cache_ttl_hours: int = 24
    parallel_workers: int = 4
    parallel_enabled: bool = True
    max_memory_mb: int = 2048
    max_nodes_per_file: int = 1000
    max_total_nodes: int = 10000
    max_edges: int = 50000
    fast_mode: bool = False
    skip_data_flow: bool = False
    skip_pattern_detection: bool = False


@dataclass
class FilterConfig:
    """Filtering options to reduce analysis scope."""
    exclude_tests: bool = True
    exclude_patterns: List[str] = field(default_factory=lambda: [
        "*test*", "*__pycache__*", "*.pyc", "*venv*", "*.venv*",
        "*node_modules*", "*.git*", "*build*", "*dist*",
        "*_test.py", "test_*.py", "conftest.py"
    ])
    include_patterns: List[str] = field(default_factory=list)
    min_function_lines: int = 2
    skip_private: bool = False
    skip_properties: bool = True
    skip_accessors: bool = True


@dataclass
class DepthConfig:
    """Depth limiting for control flow analysis."""
    max_cfg_depth: int = 5
    max_call_depth: int = 3
    max_data_flow_depth: int = 2
    max_interprocedural_depth: int = 2


@dataclass
class OutputConfig:
    """Output formatting options."""
    compact: bool = True
    include_source: bool = False
    max_label_length: int = 50
    group_by_module: bool = True


@dataclass
class Config:
    """Analysis configuration with performance optimizations."""
    
    # Analysis mode
    mode: str = "hybrid"
    
    # Sub-configs for performance
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    filters: FilterConfig = field(default_factory=FilterConfig)
    depth: DepthConfig = field(default_factory=DepthConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    
    # Legacy path limits (for compatibility)
    max_paths_per_function: int = 20
    max_depth_enumeration: int = 10
    max_depth_interprocedural: int = 3
    max_total_paths: int = 1000
    
    # Output settings
    output_formats: List[str] = field(default_factory=lambda: ["yaml", "mermaid", "png"])
    output_dir: str = "output"
    
    # Visualization
    fig_size: tuple = (16, 12)
    dpi: int = 300
    layout: str = "sfdp"  # dot, neato, fdp, sfdp, circo, twopi
    
    # Pattern detection
    detect_state_machines: bool = True
    detect_recursion: bool = True
    detect_loops: bool = True
    
    # Dynamic analysis
    trace_runtime: bool = False
    skip_packages: Set[str] = field(default_factory=lambda: {
        'site-packages', 'dist-packages', 'venv', '.venv'
    })
    
    # Logging
    verbose: bool = False
    quiet: bool = False


# Predefined fast configuration
FAST_CONFIG = Config(
    mode="static",
    performance=PerformanceConfig(
        fast_mode=True,
        skip_data_flow=True,
        skip_pattern_detection=True,
        parallel_enabled=True,
        parallel_workers=8,
        max_nodes_per_file=500,
        max_total_nodes=5000,
    ),
    filters=FilterConfig(
        exclude_tests=True,
        skip_private=True,
        skip_properties=True,
        skip_accessors=True,
        min_function_lines=3,
    ),
    depth=DepthConfig(
        max_cfg_depth=3,
        max_call_depth=2,
        max_data_flow_depth=1,
        max_interprocedural_depth=1,
    ),
    output=OutputConfig(compact=True, include_source=False),
    layout="dot",
)


# Analysis modes descriptions
ANALYSIS_MODES = {
    'static': 'AST-based control and data flow analysis',
    'dynamic': 'Runtime execution tracing',
    'hybrid': 'Combined static + dynamic analysis',
    'behavioral': 'Behavioral pattern extraction',
    'reverse': 'Reverse engineering ready output'
}


# Node types
NODE_TYPES = {
    'FUNC': 'Function definition',
    'CALL': 'Function call',
    'IF': 'Conditional branch',
    'FOR': 'For loop',
    'WHILE': 'While loop',
    'ASSIGN': 'Variable assignment',
    'RETURN': 'Return statement',
    'ENTRY': 'Entry point',
    'EXIT': 'Exit point',
}


# Colors for visualization
NODE_COLORS = {
    'FUNC': '#4CAF50',
    'CALL': '#2196F3',
    'IF': '#FF9800',
    'FOR': '#9C27B0',
    'WHILE': '#9C27B0',
    'ASSIGN': '#607D8B',
    'RETURN': '#E91E63',
    'ENTRY': '#00BCD4',
    'EXIT': '#F44336',
}
