# BoatGenerator - extracted from shapes.py
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

class BoatGenerator(ShapeGenerator):
    name = "boat"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        s = size * 0.8
        # Hull
        hull: PointGroup = [
            (cx - s, cy), (cx - s * 0.8, cy + s * 0.4),
            (cx + s * 0.8, cy + s * 0.4), (cx + s, cy), (cx - s, cy),
        ]
        # Mast
        mast: PointGroup = [(cx, cy), (cx, cy - s * 0.9)]
        # Sail
        sail: PointGroup = [
            (cx, cy - s * 0.85), (cx + s * 0.6, cy - s * 0.2), (cx, cy - s * 0.1),
        ]
        # Flag
        flag: PointGroup = [
            (cx, cy - s * 0.9), (cx + s * 0.2, cy - s * 0.8),
            (cx, cy - s * 0.7),
        ]
        return [hull, mast, sail, flag]
