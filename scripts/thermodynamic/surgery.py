# Surgery - extracted from termo2.py
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
class Surgery:
    """Operacja do zaplanowania."""
    id: str
    duration_min: int
    priority: int  # 1 = urgent, 5 = elective
    required_equipment: list[str]
    surgeon: str

