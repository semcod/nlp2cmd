# GridGenerator - extracted from shapes.py
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

class GridGenerator(ShapeGenerator):
    name = "grid"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        cols = params.get("cols", 5)
        rows = params.get("rows", 5)
        x0, y0 = cx - size, cy - size
        x1, y1 = cx + size, cy + size
        dx = (x1 - x0) / cols
        dy = (y1 - y0) / rows
        groups: list[PointGroup] = []
        for c in range(cols + 1):
            x = x0 + c * dx
            groups.append([(x, y0), (x, y1)])
        for r in range(rows + 1):
            y = y0 + r * dy
            groups.append([(x0, y), (x1, y)])
        return groups
