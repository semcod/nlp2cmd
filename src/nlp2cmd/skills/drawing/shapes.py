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


class ShapeGenerator(ABC):
    """Abstract shape generator — one responsibility: produce point groups."""

    name: str = ""

    @abstractmethod
    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        """
        Generate point groups for this shape.

        Args:
            cx: Center X coordinate
            cy: Center Y coordinate
            size: Base size (radius, half-width, etc.)
            **params: Shape-specific parameters

        Returns:
            List of point groups. Each group is a list of (x, y) tuples
            representing a continuous stroke.
        """
        ...


# ── Concrete Shape Generators ────────────────────────────────────────────

class CircleGenerator(ShapeGenerator):
    name = "circle"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        steps = params.get("steps", 36)
        radius = params.get("radius", size)
        pts: PointGroup = []
        for i in range(steps + 1):
            angle = 2 * math.pi * i / steps
            pts.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
        return [pts]


class EllipseGenerator(ShapeGenerator):
    name = "ellipse"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        steps = params.get("steps", 36)
        rx = params.get("rx", size)
        ry = params.get("ry", size * 0.6)
        pts: PointGroup = []
        for i in range(steps + 1):
            angle = 2 * math.pi * i / steps
            pts.append((cx + rx * math.cos(angle), cy + ry * math.sin(angle)))
        return [pts]


class RectangleGenerator(ShapeGenerator):
    name = "rectangle"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        w = params.get("width", size * 2)
        h = params.get("height", size * 1.4)
        x0, y0 = cx - w / 2, cy - h / 2
        return [[(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h), (x0, y0)]]


class SquareGenerator(ShapeGenerator):
    name = "square"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        s = params.get("side", size * 2)
        x0, y0 = cx - s / 2, cy - s / 2
        return [[(x0, y0), (x0 + s, y0), (x0 + s, y0 + s), (x0, y0 + s), (x0, y0)]]


class TriangleGenerator(ShapeGenerator):
    name = "triangle"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        return [[(cx, cy - size),
                 (cx - size * 0.87, cy + size * 0.5),
                 (cx + size * 0.87, cy + size * 0.5),
                 (cx, cy - size)]]


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


class HeartGenerator(ShapeGenerator):
    name = "heart"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        steps = params.get("steps", 60)
        pts: PointGroup = []
        for i in range(steps + 1):
            t = 2 * math.pi * i / steps
            x = 16 * math.sin(t) ** 3
            y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
            pts.append((cx + x * size / 16, cy + y * size / 16))
        return [pts]


class SpiralGenerator(ShapeGenerator):
    name = "spiral"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        turns = params.get("turns", 3)
        points_per_turn = params.get("points_per_turn", 30)
        total = turns * points_per_turn
        pts: PointGroup = []
        for i in range(total):
            t = i / total
            r = size * t
            angle = t * turns * 2 * math.pi
            pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
        return [pts]


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


class SunGenerator(ShapeGenerator):
    name = "sun"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        rays = params.get("rays", 8)
        circle: PointGroup = []
        for i in range(36 + 1):
            angle = 2 * math.pi * i / 36
            circle.append((cx + size * 0.5 * math.cos(angle), cy + size * 0.5 * math.sin(angle)))
        groups: list[PointGroup] = [circle]
        for i in range(rays):
            angle = 2 * math.pi * i / rays
            ray: PointGroup = [
                (cx + size * 0.55 * math.cos(angle), cy + size * 0.55 * math.sin(angle)),
                (cx + size * math.cos(angle), cy + size * math.sin(angle)),
            ]
            groups.append(ray)
        return groups


class TreeGenerator(ShapeGenerator):
    name = "tree"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        trunk: PointGroup = [
            (cx - size * 0.1, cy), (cx + size * 0.1, cy),
            (cx + size * 0.1, cy + size), (cx - size * 0.1, cy + size),
            (cx - size * 0.1, cy),
        ]
        crown: PointGroup = []
        for i in range(36 + 1):
            angle = 2 * math.pi * i / 36
            crown.append((cx + size * 0.7 * math.cos(angle),
                          cy - size * 0.5 + size * 0.7 * math.sin(angle)))
        return [trunk, crown]


class LineGenerator(ShapeGenerator):
    name = "line"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        dx = params.get("dx", size)
        dy = params.get("dy", 0)
        return [[(cx - dx, cy - dy), (cx + dx, cy + dy)]]


class DotGenerator(ShapeGenerator):
    name = "dot"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        radius = params.get("radius", 5)
        steps = 12
        pts: PointGroup = []
        for i in range(steps + 1):
            angle = 2 * math.pi * i / steps
            pts.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
        return [pts]


class GridGenerator(ShapeGenerator):
    name = "grid"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        cols = params.get("cols", 5)
        rows = params.get("rows", 5)
        x0, y0 = cx - size, cy - size
        x1, y1 = cx + size, cy + size
        dx = (x1 - x0) / cols
        dy = (y1 - y0) / rows
        groups: list[PointGroup] = []
        for c in range(cols + 1):
            x = x0 + c * dx
            groups.append([(x, y0), (x, y1)])
        for r in range(rows + 1):
            y = y0 + r * dy
            groups.append([(x0, y), (x1, y)])
        return groups


class WaveGenerator(ShapeGenerator):
    name = "wave"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        waves = params.get("waves", 3)
        amplitude = params.get("amplitude", size * 0.3)
        points = params.get("points", 60)
        width = size * 2
        x0 = cx - width / 2
        pts: PointGroup = []
        for i in range(points):
            t = i / (points - 1)
            x = x0 + t * width
            y = cy + amplitude * math.sin(t * waves * 2 * math.pi)
            pts.append((x, y))
        return [pts]


# ── Complex Shape Generators ─────────────────────────────────────────────

class CarGenerator(ShapeGenerator):
    name = "car"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        s = size * 0.8
        # Body
        body: PointGroup = [
            (cx - s, cy + s * 0.1), (cx - s, cy - s * 0.2),
            (cx - s * 0.6, cy - s * 0.2), (cx - s * 0.4, cy - s * 0.6),
            (cx + s * 0.4, cy - s * 0.6), (cx + s * 0.6, cy - s * 0.2),
            (cx + s, cy - s * 0.2), (cx + s, cy + s * 0.1),
        ]
        # Left wheel
        lw: PointGroup = []
        for i in range(17):
            a = 2 * math.pi * i / 16
            lw.append((cx - s * 0.55 + s * 0.18 * math.cos(a),
                       cy + s * 0.1 + s * 0.18 * math.sin(a)))
        # Right wheel
        rw: PointGroup = []
        for i in range(17):
            a = 2 * math.pi * i / 16
            rw.append((cx + s * 0.55 + s * 0.18 * math.cos(a),
                       cy + s * 0.1 + s * 0.18 * math.sin(a)))
        # Windshield
        ws: PointGroup = [
            (cx - s * 0.35, cy - s * 0.2), (cx - s * 0.15, cy - s * 0.55),
            (cx + s * 0.15, cy - s * 0.55), (cx + s * 0.35, cy - s * 0.2),
        ]
        return [body, lw, rw, ws]


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


class ButterflyGenerator(ShapeGenerator):
    name = "butterfly"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        s = size * 0.8
        # Upper left wing
        ulw: PointGroup = []
        for i in range(25):
            t = i / 24
            a = math.pi / 2 + t * math.pi
            r = s * (0.5 + 0.3 * math.sin(t * math.pi))
            ulw.append((cx + r * math.cos(a) * 0.8, cy + r * math.sin(a) - s * 0.2))
        # Upper right wing (mirror)
        urw: PointGroup = [(cx - (x - cx), y) for x, y in ulw]
        # Lower left wing
        llw: PointGroup = []
        for i in range(20):
            t = i / 19
            a = -math.pi / 2 - t * math.pi * 0.7
            r = s * (0.3 + 0.2 * math.sin(t * math.pi))
            llw.append((cx + r * math.cos(a) * 0.8, cy + r * math.sin(a) + s * 0.1))
        # Lower right wing (mirror)
        lrw: PointGroup = [(cx - (x - cx), y) for x, y in llw]
        # Body
        body: PointGroup = [
            (cx, cy - s * 0.5), (cx - s * 0.03, cy), (cx, cy + s * 0.4),
            (cx + s * 0.03, cy), (cx, cy - s * 0.5),
        ]
        # Antennae
        ant1: PointGroup = [(cx, cy - s * 0.5), (cx - s * 0.15, cy - s * 0.8)]
        ant2: PointGroup = [(cx, cy - s * 0.5), (cx + s * 0.15, cy - s * 0.8)]
        return [ulw, urw, llw, lrw, body, ant1, ant2]


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


class FishGenerator(ShapeGenerator):
    name = "fish"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        s = size * 0.8
        # Body (ellipse)
        body: PointGroup = []
        for i in range(25):
            a = 2 * math.pi * i / 24
            body.append((cx + s * 0.6 * math.cos(a), cy + s * 0.3 * math.sin(a)))
        # Tail
        tail: PointGroup = [
            (cx - s * 0.55, cy), (cx - s * 0.9, cy - s * 0.35),
            (cx - s * 0.7, cy), (cx - s * 0.9, cy + s * 0.35),
            (cx - s * 0.55, cy),
        ]
        # Eye
        eye: PointGroup = []
        for i in range(13):
            a = 2 * math.pi * i / 12
            eye.append((cx + s * 0.3 + s * 0.05 * math.cos(a),
                        cy - s * 0.05 + s * 0.05 * math.sin(a)))
        # Fin
        fin: PointGroup = [
            (cx, cy - s * 0.3), (cx - s * 0.1, cy - s * 0.6),
            (cx + s * 0.15, cy - s * 0.3),
        ]
        return [body, tail, eye, fin]


class RocketGenerator(ShapeGenerator):
    name = "rocket"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        s = size * 0.8
        # Body
        body: PointGroup = [
            (cx - s * 0.15, cy + s * 0.5), (cx - s * 0.15, cy - s * 0.3),
            (cx, cy - s * 0.8), (cx + s * 0.15, cy - s * 0.3),
            (cx + s * 0.15, cy + s * 0.5), (cx - s * 0.15, cy + s * 0.5),
        ]
        # Left fin
        lf: PointGroup = [
            (cx - s * 0.15, cy + s * 0.3), (cx - s * 0.4, cy + s * 0.6),
            (cx - s * 0.15, cy + s * 0.5),
        ]
        # Right fin
        rf: PointGroup = [
            (cx + s * 0.15, cy + s * 0.3), (cx + s * 0.4, cy + s * 0.6),
            (cx + s * 0.15, cy + s * 0.5),
        ]
        # Window
        window: PointGroup = []
        for i in range(13):
            a = 2 * math.pi * i / 12
            window.append((cx + s * 0.08 * math.cos(a),
                           cy - s * 0.15 + s * 0.08 * math.sin(a)))
        # Flame
        flame: PointGroup = [
            (cx - s * 0.1, cy + s * 0.5), (cx - s * 0.05, cy + s * 0.7),
            (cx, cy + s * 0.6), (cx + s * 0.05, cy + s * 0.75),
            (cx + s * 0.1, cy + s * 0.5),
        ]
        return [body, lf, rf, window, flame]


class CastleGenerator(ShapeGenerator):
    name = "castle"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        s = size * 0.8
        # Main wall
        wall: PointGroup = [
            (cx - s * 0.6, cy + s * 0.5), (cx - s * 0.6, cy - s * 0.2),
            (cx + s * 0.6, cy - s * 0.2), (cx + s * 0.6, cy + s * 0.5),
        ]
        # Battlements
        bm: PointGroup = []
        for i in range(7):
            x = cx - s * 0.6 + i * s * 0.2
            bm.append((x, cy - s * 0.2))
            bm.append((x, cy - s * 0.35))
            bm.append((x + s * 0.1, cy - s * 0.35))
            bm.append((x + s * 0.1, cy - s * 0.2))
        # Left tower
        lt: PointGroup = [
            (cx - s * 0.7, cy + s * 0.5), (cx - s * 0.7, cy - s * 0.5),
            (cx - s * 0.5, cy - s * 0.5), (cx - s * 0.5, cy + s * 0.5),
        ]
        # Right tower
        rt: PointGroup = [
            (cx + s * 0.5, cy + s * 0.5), (cx + s * 0.5, cy - s * 0.5),
            (cx + s * 0.7, cy - s * 0.5), (cx + s * 0.7, cy + s * 0.5),
        ]
        # Left tower roof
        lr: PointGroup = [
            (cx - s * 0.75, cy - s * 0.5), (cx - s * 0.6, cy - s * 0.8),
            (cx - s * 0.45, cy - s * 0.5),
        ]
        # Right tower roof
        rr: PointGroup = [
            (cx + s * 0.45, cy - s * 0.5), (cx + s * 0.6, cy - s * 0.8),
            (cx + s * 0.75, cy - s * 0.5),
        ]
        # Gate
        gate: PointGroup = []
        for i in range(13):
            a = math.pi * i / 12
            gate.append((cx + s * 0.15 * math.cos(a), cy + s * 0.5 - s * 0.25 * math.sin(a)))
        gate.extend([(cx + s * 0.15, cy + s * 0.5), (cx - s * 0.15, cy + s * 0.5)])
        return [wall, bm, lt, rt, lr, rr, gate]


class DiamondGenerator(ShapeGenerator):
    name = "diamond"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        s = size
        # Outline
        outline: PointGroup = [
            (cx, cy - s), (cx + s * 0.6, cy - s * 0.2),
            (cx + s * 0.4, cy + s * 0.8),
            (cx - s * 0.4, cy + s * 0.8),
            (cx - s * 0.6, cy - s * 0.2), (cx, cy - s),
        ]
        # Top facets
        f1: PointGroup = [(cx, cy - s), (cx, cy - s * 0.2)]
        f2: PointGroup = [(cx - s * 0.6, cy - s * 0.2), (cx + s * 0.6, cy - s * 0.2)]
        f3: PointGroup = [(cx - s * 0.3, cy - s * 0.2), (cx - s * 0.4, cy + s * 0.8)]
        f4: PointGroup = [(cx + s * 0.3, cy - s * 0.2), (cx + s * 0.4, cy + s * 0.8)]
        return [outline, f1, f2, f3, f4]


class ArrowGenerator(ShapeGenerator):
    name = "arrow"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        s = size
        direction = params.get("direction", "right")
        if direction == "right":
            pts: PointGroup = [
                (cx - s, cy - s * 0.15), (cx + s * 0.3, cy - s * 0.15),
                (cx + s * 0.3, cy - s * 0.4), (cx + s, cy),
                (cx + s * 0.3, cy + s * 0.4), (cx + s * 0.3, cy + s * 0.15),
                (cx - s, cy + s * 0.15), (cx - s, cy - s * 0.15),
            ]
        elif direction == "up":
            pts = [
                (cx - s * 0.15, cy + s), (cx - s * 0.15, cy - s * 0.3),
                (cx - s * 0.4, cy - s * 0.3), (cx, cy - s),
                (cx + s * 0.4, cy - s * 0.3), (cx + s * 0.15, cy - s * 0.3),
                (cx + s * 0.15, cy + s), (cx - s * 0.15, cy + s),
            ]
        else:
            pts = [
                (cx - s, cy), (cx + s, cy),
                (cx + s * 0.5, cy - s * 0.3),
                (cx + s, cy),
                (cx + s * 0.5, cy + s * 0.3),
            ]
        return [pts]


class PentagonGenerator(ShapeGenerator):
    name = "pentagon"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        pts: PointGroup = []
        for i in range(6):
            a = -math.pi / 2 + 2 * math.pi * i / 5
            pts.append((cx + size * math.cos(a), cy + size * math.sin(a)))
        return [pts]


class HexagonGenerator(ShapeGenerator):
    name = "hexagon"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        pts: PointGroup = []
        for i in range(7):
            a = 2 * math.pi * i / 6
            pts.append((cx + size * math.cos(a), cy + size * math.sin(a)))
        return [pts]


class OctagonGenerator(ShapeGenerator):
    name = "octagon"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        pts: PointGroup = []
        for i in range(9):
            a = 2 * math.pi * i / 8 + math.pi / 8
            pts.append((cx + size * math.cos(a), cy + size * math.sin(a)))
        return [pts]


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


class CrescentGenerator(ShapeGenerator):
    name = "crescent"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        steps = 36
        # Outer circle
        pts: PointGroup = []
        for i in range(steps + 1):
            a = 2 * math.pi * i / steps
            pts.append((cx + size * math.cos(a), cy + size * math.sin(a)))
        # Inner circle (offset to create crescent)
        inner: PointGroup = []
        offset = size * 0.4
        for i in range(steps + 1):
            a = 2 * math.pi * i / steps
            inner.append((cx + offset + size * 0.8 * math.cos(a),
                          cy + size * 0.8 * math.sin(a)))
        return [pts, inner]


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


# ── Shape Registry (OCP) ─────────────────────────────────────────────────

class ShapeRegistry:
    """
    Registry of all available shape generators.

    New shapes can be added at runtime via register().
    This follows the Open/Closed Principle — the registry is open for
    extension but closed for modification.
    """

    _generators: dict[str, ShapeGenerator] = {}

    @classmethod
    def register(cls, generator: ShapeGenerator) -> None:
        """Register a shape generator."""
        cls._generators[generator.name] = generator

    @classmethod
    def get(cls, name: str) -> ShapeGenerator:
        """Get a shape generator by name. Falls back to circle."""
        if not cls._generators:
            cls._init_defaults()
        gen = cls._generators.get(name)
        if gen is None:
            gen = cls._generators.get("circle", CircleGenerator())
        return gen

    @classmethod
    def available(cls) -> list[str]:
        """List all registered shape names."""
        if not cls._generators:
            cls._init_defaults()
        return sorted(cls._generators.keys())

    @classmethod
    def _init_defaults(cls) -> None:
        """Register all built-in shape generators."""
        for gen_class in [
            # Basic shapes
            CircleGenerator, EllipseGenerator, RectangleGenerator, SquareGenerator,
            TriangleGenerator, StarGenerator, HeartGenerator, SpiralGenerator,
            HouseGenerator, FlowerGenerator, SunGenerator, TreeGenerator,
            LineGenerator, DotGenerator, GridGenerator, WaveGenerator,
            # Complex shapes
            CarGenerator, BirdGenerator, ButterflyGenerator, BoatGenerator,
            MountainGenerator, CatGenerator, FishGenerator, RocketGenerator,
            CastleGenerator, DiamondGenerator, ArrowGenerator,
            # Geometric shapes
            PentagonGenerator, HexagonGenerator, OctagonGenerator,
            CrossGenerator, CrescentGenerator, CloudDetailedGenerator,
        ]:
            cls.register(gen_class())
