# MountainGenerator - extracted from shapes.py
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

class MountainGenerator(ShapeGenerator):
    name = "mountain"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        s = size
        peaks = params.get("peaks", 2)
        groups: list[PointGroup] = []
        # Main mountain
        main: PointGroup = [
            (cx - s, cy + s * 0.5), (cx - s * 0.2, cy - s * 0.8),
            (cx, cy - s * 0.3), (cx + s * 0.3, cy - s * 0.9),
            (cx + s, cy + s * 0.5), (cx - s, cy + s * 0.5),
        ]
        groups.append(main)
        # Snow cap
        snow: PointGroup = [
            (cx + s * 0.15, cy - s * 0.65), (cx + s * 0.3, cy - s * 0.9),
            (cx + s * 0.45, cy - s * 0.65),
        ]
        groups.append(snow)
        return groups
