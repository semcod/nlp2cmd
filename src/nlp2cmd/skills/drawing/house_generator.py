# HouseGenerator - extracted from shapes.py
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

class HouseGenerator(ShapeGenerator):
    name = "house"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        body = [(cx - size, cy), (cx + size, cy),
                (cx + size, cy + size * 1.2),
                (cx - size, cy + size * 1.2), (cx - size, cy)]
        roof = [(cx - size * 1.1, cy), (cx, cy - size * 0.8), (cx + size * 1.1, cy)]
        door = [(cx - size * 0.2, cy + size * 0.5), (cx + size * 0.2, cy + size * 0.5),
                (cx + size * 0.2, cy + size * 1.2), (cx - size * 0.2, cy + size * 1.2),
                (cx - size * 0.2, cy + size * 0.5)]
        return [body, roof, door]
