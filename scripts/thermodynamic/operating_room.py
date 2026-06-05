# OperatingRoom - extracted from termo2.py
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
class OperatingRoom:
    """Sala operacyjna."""
    id: str
    equipment: list[str]
    available_hours: tuple[int, int] = (7, 19)  # 7:00 - 19:00

