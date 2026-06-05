# SquareGenerator - extracted from shapes.py
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

class SquareGenerator(ShapeGenerator):
    name = "square"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        s = params.get("side", size * 2)
        x0, y0 = cx - s / 2, cy - s / 2
        return [[(x0, y0), (x0 + s, y0), (x0 + s, y0 + s), (x0, y0 + s), (x0, y0)]]
