# CrossGenerator - extracted from shapes.py
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

class CrossGenerator(ShapeGenerator):
    name = "cross"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        w = size * 0.3
        pts: PointGroup = [
            (cx - w, cy - size), (cx + w, cy - size),
            (cx + w, cy - w), (cx + size, cy - w),
            (cx + size, cy + w), (cx + w, cy + w),
            (cx + w, cy + size), (cx - w, cy + size),
            (cx - w, cy + w), (cx - size, cy + w),
            (cx - size, cy - w), (cx - w, cy - w),
            (cx - w, cy - size),
        ]
        return [pts]
