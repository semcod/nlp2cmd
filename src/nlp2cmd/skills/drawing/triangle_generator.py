# TriangleGenerator - extracted from shapes.py
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

class TriangleGenerator(ShapeGenerator):
    name = "triangle"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        return [[(cx, cy - size),
                 (cx - size * 0.87, cy + size * 0.5),
                 (cx + size * 0.87, cy + size * 0.5),
                 (cx, cy - size)]]
