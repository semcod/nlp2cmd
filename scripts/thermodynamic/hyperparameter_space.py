# HyperparameterSpace - extracted from termo2.py
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
class HyperparameterSpace:
    """Przestrzeń hiperparametrów do optymalizacji."""
    learning_rate: tuple = (0.0001, 0.1)
    batch_size: tuple = (16, 256)
    num_layers: tuple = (2, 10)
    dropout: tuple = (0.0, 0.5)
    hidden_dim: tuple = (64, 512)

