# CatGenerator - extracted from shapes.py
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

class CatGenerator(ShapeGenerator):
    name = "cat"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        s = size * 0.7
        # Body (oval)
        body: PointGroup = []
        for i in range(25):
            a = 2 * math.pi * i / 24
            body.append((cx + s * 0.4 * math.cos(a), cy + s * 0.5 * math.sin(a) + s * 0.2))
        # Head (circle)
        head: PointGroup = []
        for i in range(25):
            a = 2 * math.pi * i / 24
            head.append((cx + s * 0.3 * math.cos(a), cy - s * 0.4 + s * 0.3 * math.sin(a)))
        # Left ear
        le: PointGroup = [
            (cx - s * 0.2, cy - s * 0.6), (cx - s * 0.25, cy - s * 0.95),
            (cx - s * 0.05, cy - s * 0.65),
        ]
        # Right ear
        re_: PointGroup = [
            (cx + s * 0.2, cy - s * 0.6), (cx + s * 0.25, cy - s * 0.95),
            (cx + s * 0.05, cy - s * 0.65),
        ]
        # Tail
        tail: PointGroup = []
        for i in range(15):
            t = i / 14
            tail.append((cx + s * 0.4 + s * 0.5 * t,
                         cy + s * 0.3 - s * 0.5 * math.sin(t * math.pi)))
        # Whiskers
        w1: PointGroup = [(cx + s * 0.1, cy - s * 0.35), (cx + s * 0.5, cy - s * 0.45)]
        w2: PointGroup = [(cx + s * 0.1, cy - s * 0.3), (cx + s * 0.5, cy - s * 0.3)]
        w3: PointGroup = [(cx - s * 0.1, cy - s * 0.35), (cx - s * 0.5, cy - s * 0.45)]
        w4: PointGroup = [(cx - s * 0.1, cy - s * 0.3), (cx - s * 0.5, cy - s * 0.3)]
        return [body, head, le, re_, tail, w1, w2, w3, w4]
