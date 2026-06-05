"""
VQL library — canonical access point for shape templates, the shape registry,
color resolution, and SVG-path parsing.

These primitives are the building blocks the compiler uses to turn a
:class:`~nlp2cmd.vql.schema.program.VQLProgram` into concrete geometry. For
now they are re-exported from ``nlp2cmd.skills.drawing`` (the existing
implementation) so the VQL namespace is stable without a risky physical move;
a later PR can relocate the implementation under ``vql/library/`` and flip the
re-export direction.
"""

from nlp2cmd.skills.drawing.colors import ColorResolver
from nlp2cmd.skills.drawing.shape_registry import ShapeRegistry
from nlp2cmd.skills.drawing.shapes import PointGroup, ShapeGenerator
from nlp2cmd.skills.drawing.svg_path_parser import parse_svg_path

__all__ = [
    "ColorResolver",
    "ShapeRegistry",
    "ShapeGenerator",
    "PointGroup",
    "parse_svg_path",
]
