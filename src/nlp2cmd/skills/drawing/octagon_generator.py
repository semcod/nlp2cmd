# OctagonGenerator - extracted from shapes.py
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

class OctagonGenerator(ShapeGenerator):
    name = "octagon"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        pts: PointGroup = []
        for i in range(9):
            a = 2 * math.pi * i / 8 + math.pi / 8
            pts.append((cx + size * math.cos(a), cy + size * math.sin(a)))
        return [pts]
