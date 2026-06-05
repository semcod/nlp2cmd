# DotGenerator - extracted from shapes.py
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

class DotGenerator(ShapeGenerator):
    name = "dot"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        radius = params.get("radius", 5)
        steps = 12
        pts: PointGroup = []
        for i in range(steps + 1):
            angle = 2 * math.pi * i / steps
            pts.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
        return [pts]
