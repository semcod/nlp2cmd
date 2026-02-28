"""Configuration and constants for code2flow."""

from dataclasses import dataclass, field
from typing import List, Set


@dataclass
class Config:
    """Analysis configuration."""
    
    # Path limits
    max_paths_per_function: int = 20
    max_depth_enumeration: int = 10
    max_depth_interprocedural: int = 3
    max_total_paths: int = 1000
    
    # Analysis modes
    mode: str = "hybrid"  # static, dynamic, hybrid, behavioral, reverse
    
    # Output settings
    output_formats: List[str] = field(default_factory=lambda: ["yaml", "mermaid", "png"])
    output_dir: str = "output"
    
    # Visualization
    fig_size: tuple = (16, 12)
    dpi: int = 300
    
    # Pattern detection
    detect_state_machines: bool = True
    detect_recursion: bool = True
    detect_loops: bool = True
    
    # Dynamic analysis
    trace_runtime: bool = False
    skip_packages: Set[str] = field(default_factory=lambda: {
        'site-packages', 'dist-packages', 'venv', '.venv'
    })


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
