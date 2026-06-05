# RectangleGenerator - extracted from shapes.py
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

class RectangleGenerator(ShapeGenerator):
    name = "rectangle"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        w = params.get("width", size * 2)
        h = params.get("height", size * 1.4)
        x0, y0 = cx - w / 2, cy - h / 2
        return [[(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h), (x0, y0)]]
