# PipelineStep - extracted from termo2.py
"""
NLP2CMD - Przykłady zastosowań w różnych dziedzinach.

Ten moduł zawiera praktyczne przykłady użycia NLP2CMD
w IT, nauce i biznesie.
"""
import asyncio
from dataclasses import dataclass
from typing import Any, Optional
import numpy as np
@dataclass
class PipelineStep:
    """Krok w pipeline genomicznym."""
    name: str
    time_per_gb: float  # minuty per GB
    memory_gb: int
    cpu_cores: int
    depends_on: list[str]

