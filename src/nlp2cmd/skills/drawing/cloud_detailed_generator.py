# CloudDetailedGenerator - extracted from shapes.py
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

class CloudDetailedGenerator(ShapeGenerator):
    name = "cloud_detailed"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        s = size
        pts: PointGroup = []
        # Bottom flat
        pts.append((cx - s * 0.7, cy + s * 0.2))
        pts.append((cx + s * 0.7, cy + s * 0.2))
        # Right bumps
        for i in range(10):
            t = i / 9
            a = -math.pi / 2 + t * math.pi
            pts.append((cx + s * 0.5 + s * 0.3 * math.cos(a),
                        cy - s * 0.1 + s * 0.3 * math.sin(a)))
        # Top bumps
        for i in range(15):
            t = i / 14
            a = t * math.pi
            pts.append((cx + s * 0.3 - s * 0.6 * t + s * 0.25 * math.cos(a),
                        cy - s * 0.3 - s * 0.2 * math.sin(a * 2)))
        # Left bumps
        for i in range(10):
            t = i / 9
            a = math.pi / 2 + t * math.pi
            pts.append((cx - s * 0.5 + s * 0.25 * math.cos(a),
                        cy - s * 0.1 + s * 0.25 * math.sin(a)))
        pts.append((cx - s * 0.7, cy + s * 0.2))
        return [pts]
