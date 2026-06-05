# PowerPlant - extracted from termo2.py
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
class PowerPlant:
    """Elektrownia."""
    id: str
    type: str  # coal, gas, hydro, nuclear
    capacity_mw: float
    min_output_mw: float
    cost_per_mwh: float
    ramp_rate_mw_per_hour: float
    startup_cost: float
    co2_tons_per_mwh: float

