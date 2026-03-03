"""
Drawing skill for nlp2cmd.

SOLID + CQRS + Event Sourcing architecture for drawing arbitrary shapes
in any environment (browser canvas, SVG, etc.).

Usage:
    from nlp2cmd.skills.drawing import DrawingSkill, PlaywrightRenderer

    skill = DrawingSkill()
    skill.execute_nl("narysuj czerwone koło")
    # or with explicit renderer:
    renderer = PlaywrightRenderer(page)
    await skill.render(renderer)
"""

from nlp2cmd.skills.drawing.events import (
    CanvasCleared,
    CanvasInitialized,
    ColorChanged,
    DrawingEvent,
    ShapeDrawn,
    ToolSelected,
)
from nlp2cmd.skills.drawing.event_store import EventStore
from nlp2cmd.skills.drawing.commands import (
    ClearCanvas,
    CommandBus,
    DrawCommand,
    DrawShape,
    InitCanvas,
    SetColor,
)
from nlp2cmd.skills.drawing.queries import (
    GetCanvasState,
    GetDrawingHistory,
    GetShapePoints,
    QueryBus,
)
from nlp2cmd.skills.drawing.shapes import (
    ShapeGenerator,
    ShapeRegistry,
)
from nlp2cmd.skills.drawing.colors import ColorResolver
from nlp2cmd.skills.drawing.nl_parser import NLDrawingParser
from nlp2cmd.skills.drawing.renderers.base import Renderer
from nlp2cmd.skills.drawing.skill import DrawingSkill
from nlp2cmd.skills.drawing.object_fetcher import ObjectFetcher, FetchedShape, parse_svg_path
from nlp2cmd.skills.drawing.text_to_shape import TextToShapeEngine, GeneratedShape, DynamicShapeGenerator
from nlp2cmd.skills.drawing.visual_validator import (
    VisualValidator, ValidationResult, ValidationVerdict, DrawingCorrection,
)
from nlp2cmd.skills.drawing.correction_engine import (
    CorrectionEngine, CorrectionResult, AutonomousDrawingPipeline,
)

__all__ = [
    # Skill facade
    "DrawingSkill",
    # Events
    "DrawingEvent",
    "ShapeDrawn",
    "ColorChanged",
    "ToolSelected",
    "CanvasInitialized",
    "CanvasCleared",
    # Event store
    "EventStore",
    # Commands (CQRS write side)
    "DrawCommand",
    "DrawShape",
    "SetColor",
    "InitCanvas",
    "ClearCanvas",
    "CommandBus",
    # Queries (CQRS read side)
    "GetCanvasState",
    "GetDrawingHistory",
    "GetShapePoints",
    "QueryBus",
    # Domain
    "ShapeGenerator",
    "ShapeRegistry",
    "ColorResolver",
    "NLDrawingParser",
    # Renderers
    "Renderer",
    # New skills: database fetching
    "ObjectFetcher",
    "FetchedShape",
    "parse_svg_path",
    # New skills: LLM shape generation
    "TextToShapeEngine",
    "GeneratedShape",
    "DynamicShapeGenerator",
    # New skills: visual validation
    "VisualValidator",
    "ValidationResult",
    "ValidationVerdict",
    "DrawingCorrection",
    # New skills: correction engine
    "CorrectionEngine",
    "CorrectionResult",
    "AutonomousDrawingPipeline",
]
