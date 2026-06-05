# StarGenerator - extracted from shapes.py
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

class StarGenerator(ShapeGenerator):
    name = "star"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        points_count = params.get("points_count", 5)
        inner_ratio = params.get("inner_ratio", 0.4)
        pts: PointGroup = []
        for i in range(points_count):
            angle = -math.pi / 2 + 2 * math.pi * i / points_count
            pts.append((cx + size * math.cos(angle), cy + size * math.sin(angle)))
            angle2 = angle + math.pi / points_count
            pts.append((cx + size * inner_ratio * math.cos(angle2),
                        cy + size * inner_ratio * math.sin(angle2)))
        pts.append(pts[0])
        return [pts]
