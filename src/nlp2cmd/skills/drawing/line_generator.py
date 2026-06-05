# LineGenerator - extracted from shapes.py
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
from nlp2cmd.skills.drawing.shape_generator import ShapeGenerator

class LineGenerator(ShapeGenerator):
    name = "line"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        dx = params.get("dx", size)
        dy = params.get("dy", 0)
        return [[(cx - dx, cy - dy), (cx + dx, cy + dy)]]
