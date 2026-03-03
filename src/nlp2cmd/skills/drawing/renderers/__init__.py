"""
Drawing renderers — environment-specific rendering backends.

Each renderer implements the Renderer protocol (DIP — Dependency Inversion).
"""

from nlp2cmd.skills.drawing.renderers.base import Renderer

__all__ = ["Renderer"]
