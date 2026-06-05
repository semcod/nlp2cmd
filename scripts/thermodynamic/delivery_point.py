# DeliveryPoint - extracted from termo2.py
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
class DeliveryPoint:
    """Punkt dostawy."""
    id: str
    x: float
    y: float
    demand: int
    time_window: tuple[int, int] = (0, 24)

