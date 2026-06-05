# ShapeGenerator - extracted from shapes.py
"""
Shape generators — geometry for all supported shapes.

Each shape is a registered ShapeGenerator that produces point groups.
New shapes can be added via ShapeRegistry.register() (Open/Closed Principle).
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import Any


PointGroup = list[tuple[float, float]]
class ShapeGenerator(ABC):
    """Abstract shape generator — one responsibility: produce point groups."""

    name: str = ""

    @abstractmethod
    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        """
        Generate point groups for this shape.

        Args:
            cx: Center X coordinate
            cy: Center Y coordinate
            size: Base size (radius, half-width, etc.)
            **params: Shape-specific parameters

        Returns:
            List of point groups. Each group is a list of (x, y) tuples
            representing a continuous stroke.
        """
        ...
