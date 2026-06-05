# FlowerGenerator - extracted from shapes.py
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

class FlowerGenerator(ShapeGenerator):
    name = "flower"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        petals = params.get("petals", 6)
        points_per_petal = params.get("points_per_petal", 20)
        groups: list[PointGroup] = []
        for p in range(petals):
            petal: PointGroup = []
            base_angle = 2 * math.pi * p / petals
            for i in range(points_per_petal):
                t = i / (points_per_petal - 1)
                angle = base_angle + (t - 0.5) * (2 * math.pi / petals)
                r = size * math.sin(t * math.pi)
                petal.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
            groups.append(petal)
        return groups
