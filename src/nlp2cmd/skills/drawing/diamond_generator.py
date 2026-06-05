# DiamondGenerator - extracted from shapes.py
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

class DiamondGenerator(ShapeGenerator):
    name = "diamond"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        s = size
        # Outline
        outline: PointGroup = [
            (cx, cy - s), (cx + s * 0.6, cy - s * 0.2),
            (cx + s * 0.4, cy + s * 0.8),
            (cx - s * 0.4, cy + s * 0.8),
            (cx - s * 0.6, cy - s * 0.2), (cx, cy - s),
        ]
        # Top facets
        f1: PointGroup = [(cx, cy - s), (cx, cy - s * 0.2)]
        f2: PointGroup = [(cx - s * 0.6, cy - s * 0.2), (cx + s * 0.6, cy - s * 0.2)]
        f3: PointGroup = [(cx - s * 0.3, cy - s * 0.2), (cx - s * 0.4, cy + s * 0.8)]
        f4: PointGroup = [(cx + s * 0.3, cy - s * 0.2), (cx + s * 0.4, cy + s * 0.8)]
        return [outline, f1, f2, f3, f4]
