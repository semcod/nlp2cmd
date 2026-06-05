# BirdGenerator - extracted from shapes.py
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

class BirdGenerator(ShapeGenerator):
    name = "bird"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        s = size * 0.7
        # Body (oval)
        body: PointGroup = []
        for i in range(25):
            a = 2 * math.pi * i / 24
            body.append((cx + s * 0.5 * math.cos(a), cy + s * 0.3 * math.sin(a)))
        # Left wing
        lw: PointGroup = [
            (cx - s * 0.1, cy), (cx - s * 0.8, cy - s * 0.7),
            (cx - s * 0.5, cy - s * 0.2), (cx - s * 0.1, cy),
        ]
        # Right wing
        rw: PointGroup = [
            (cx + s * 0.1, cy), (cx + s * 0.8, cy - s * 0.7),
            (cx + s * 0.5, cy - s * 0.2), (cx + s * 0.1, cy),
        ]
        # Beak
        beak: PointGroup = [
            (cx + s * 0.5, cy - s * 0.05), (cx + s * 0.8, cy),
            (cx + s * 0.5, cy + s * 0.05),
        ]
        # Tail
        tail: PointGroup = [
            (cx - s * 0.5, cy), (cx - s * 0.9, cy - s * 0.15),
            (cx - s * 0.85, cy + s * 0.1), (cx - s * 0.5, cy),
        ]
        return [body, lw, rw, beak, tail]
