# ShapeRegistry - extracted from shapes.py
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
from nlp2cmd.skills.drawing.arrow_generator import ArrowGenerator
from nlp2cmd.skills.drawing.bird_generator import BirdGenerator
from nlp2cmd.skills.drawing.boat_generator import BoatGenerator
from nlp2cmd.skills.drawing.butterfly_generator import ButterflyGenerator
from nlp2cmd.skills.drawing.car_generator import CarGenerator
from nlp2cmd.skills.drawing.castle_generator import CastleGenerator
from nlp2cmd.skills.drawing.cat_generator import CatGenerator
from nlp2cmd.skills.drawing.circle_generator import CircleGenerator
from nlp2cmd.skills.drawing.cloud_detailed_generator import CloudDetailedGenerator
from nlp2cmd.skills.drawing.crescent_generator import CrescentGenerator
from nlp2cmd.skills.drawing.cross_generator import CrossGenerator
from nlp2cmd.skills.drawing.diamond_generator import DiamondGenerator
from nlp2cmd.skills.drawing.dot_generator import DotGenerator
from nlp2cmd.skills.drawing.ellipse_generator import EllipseGenerator
from nlp2cmd.skills.drawing.fish_generator import FishGenerator
from nlp2cmd.skills.drawing.flower_generator import FlowerGenerator
from nlp2cmd.skills.drawing.grid_generator import GridGenerator
from nlp2cmd.skills.drawing.heart_generator import HeartGenerator
from nlp2cmd.skills.drawing.hexagon_generator import HexagonGenerator
from nlp2cmd.skills.drawing.house_generator import HouseGenerator
from nlp2cmd.skills.drawing.line_generator import LineGenerator
from nlp2cmd.skills.drawing.mountain_generator import MountainGenerator
from nlp2cmd.skills.drawing.octagon_generator import OctagonGenerator
from nlp2cmd.skills.drawing.pentagon_generator import PentagonGenerator
from nlp2cmd.skills.drawing.rectangle_generator import RectangleGenerator
from nlp2cmd.skills.drawing.rocket_generator import RocketGenerator
from nlp2cmd.skills.drawing.shape_generator import ShapeGenerator
from nlp2cmd.skills.drawing.spiral_generator import SpiralGenerator
from nlp2cmd.skills.drawing.square_generator import SquareGenerator
from nlp2cmd.skills.drawing.star_generator import StarGenerator
from nlp2cmd.skills.drawing.sun_generator import SunGenerator
from nlp2cmd.skills.drawing.tree_generator import TreeGenerator
from nlp2cmd.skills.drawing.triangle_generator import TriangleGenerator
from nlp2cmd.skills.drawing.wave_generator import WaveGenerator

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
