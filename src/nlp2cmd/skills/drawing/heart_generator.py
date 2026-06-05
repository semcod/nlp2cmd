# HeartGenerator - extracted from shapes.py
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

class HeartGenerator(ShapeGenerator):
    name = "heart"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        steps = params.get("steps", 60)
        pts: PointGroup = []
        for i in range(steps + 1):
            t = 2 * math.pi * i / steps
            x = 16 * math.sin(t) ** 3
            y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
            pts.append((cx + x * size / 16, cy + y * size / 16))
        return [pts]
