"""
VQL schema — domain models for the Visual Query Language intermediate
representation (IR).

VQL is the single source of truth for *what* should be drawn, decoupled
from *how* it is rendered (SVG, Playwright/canvas, ...). ``nlp2cmd`` produces
a :class:`VQLProgram`, validates it, and only then compiles it into renderer
actions.

The models are plain dataclasses (matching the existing drawing domain style)
with ``to_dict`` / ``from_dict`` round-tripping and structural ``validate``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ── Enums ──────────────────────────────────────────────────────────────────

class RenderTarget(str, Enum):
    """Supported render backends for a VQL program."""

    SVG = "svg"
    PLAYWRIGHT = "playwright"
    CANVAS = "canvas"


# ── Leaf value objects ───────────────────────────────────────────────────────

@dataclass
class Style:
    """Visual style for an object/primitive."""

    color: str = "#000000"
    fill: bool = False
    stroke_width: float = 2.0
    opacity: float = 1.0

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.color:
            errors.append("style.color is required")
        if self.stroke_width < 0:
            errors.append("style.stroke_width must be >= 0")
        if not (0.0 <= self.opacity <= 1.0):
            errors.append("style.opacity must be in [0, 1]")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "color": self.color,
            "fill": self.fill,
            "stroke_width": self.stroke_width,
            "opacity": self.opacity,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Style:
        return cls(
            color=data.get("color", "#000000"),
            fill=bool(data.get("fill", False)),
            stroke_width=float(data.get("stroke_width", 2.0)),
            opacity=float(data.get("opacity", 1.0)),
        )


@dataclass
class Transform:
    """Affine transform applied to an object."""

    translate_x: float = 0.0
    translate_y: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    rotate_deg: float = 0.0

    def is_identity(self) -> bool:
        return (
            self.translate_x == 0.0
            and self.translate_y == 0.0
            and self.scale_x == 1.0
            and self.scale_y == 1.0
            and self.rotate_deg == 0.0
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "translate_x": self.translate_x,
            "translate_y": self.translate_y,
            "scale_x": self.scale_x,
            "scale_y": self.scale_y,
            "rotate_deg": self.rotate_deg,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Transform:
        return cls(
            translate_x=float(data.get("translate_x", 0.0)),
            translate_y=float(data.get("translate_y", 0.0)),
            scale_x=float(data.get("scale_x", 1.0)),
            scale_y=float(data.get("scale_y", 1.0)),
            rotate_deg=float(data.get("rotate_deg", 0.0)),
        )


@dataclass
class Anchor:
    """A named reference point on the canvas/object."""

    name: str = ""
    x: float = 0.0
    y: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "x": self.x, "y": self.y}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Anchor:
        return cls(
            name=data.get("name", ""),
            x=float(data.get("x", 0.0)),
            y=float(data.get("y", 0.0)),
        )


@dataclass
class Constraint:
    """A declarative constraint on an object (placeholder for solver)."""

    kind: str = ""
    args: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "args": self.args}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Constraint:
        return cls(kind=data.get("kind", ""), args=dict(data.get("args", {})))


@dataclass
class Relation:
    """A relation between two objects (placeholder for layout engine)."""

    kind: str = ""
    source: str = ""
    target: str = ""
    args: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "source": self.source,
            "target": self.target,
            "args": self.args,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Relation:
        return cls(
            kind=data.get("kind", ""),
            source=data.get("source", ""),
            target=data.get("target", ""),
            args=dict(data.get("args", {})),
        )


# ── Geometry ─────────────────────────────────────────────────────────────────

@dataclass
class Primitive:
    """
    A drawable primitive — the smallest unit of geometry.

    ``shape_type`` matches the names registered in the shape registry
    (e.g. ``"circle"``, ``"star"``, ``"house"``). ``params`` carries shape
    specific options (size, points_count, petals, ...).
    """

    shape_type: str = "circle"
    params: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        if not self.shape_type:
            return ["primitive.shape_type is required"]
        return []

    def to_dict(self) -> dict[str, Any]:
        return {"shape_type": self.shape_type, "params": self.params}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Primitive:
        return cls(
            shape_type=data.get("shape_type", "circle"),
            params=dict(data.get("params", {})),
        )


@dataclass
class Object:
    """
    A logical drawing object — one or more primitives sharing a style,
    center, and transform.
    """

    id: str = ""
    primitives: list[Primitive] = field(default_factory=list)
    style: Style = field(default_factory=Style)
    transform: Transform = field(default_factory=Transform)
    center_x: float = 0.0
    center_y: float = 0.0
    anchors: list[Anchor] = field(default_factory=list)
    constraints: list[Constraint] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.primitives:
            errors.append(f"object '{self.id}' has no primitives")
        for prim in self.primitives:
            errors.extend(prim.validate())
        errors.extend(self.style.validate())
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "primitives": [p.to_dict() for p in self.primitives],
            "style": self.style.to_dict(),
            "transform": self.transform.to_dict(),
            "center_x": self.center_x,
            "center_y": self.center_y,
            "anchors": [a.to_dict() for a in self.anchors],
            "constraints": [c.to_dict() for c in self.constraints],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Object:
        return cls(
            id=data.get("id", ""),
            primitives=[Primitive.from_dict(p) for p in data.get("primitives", [])],
            style=Style.from_dict(data.get("style", {})),
            transform=Transform.from_dict(data.get("transform", {})),
            center_x=float(data.get("center_x", 0.0)),
            center_y=float(data.get("center_y", 0.0)),
            anchors=[Anchor.from_dict(a) for a in data.get("anchors", [])],
            constraints=[Constraint.from_dict(c) for c in data.get("constraints", [])],
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class Layer:
    """An ordered group of objects."""

    id: str = "default"
    objects: list[Object] = field(default_factory=list)
    visible: bool = True

    def validate(self) -> list[str]:
        errors: list[str] = []
        for obj in self.objects:
            errors.extend(obj.validate())
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "objects": [o.to_dict() for o in self.objects],
            "visible": self.visible,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Layer:
        return cls(
            id=data.get("id", "default"),
            objects=[Object.from_dict(o) for o in data.get("objects", [])],
            visible=bool(data.get("visible", True)),
        )


@dataclass
class Scene:
    """The root container — canvas dimensions, background, and layers."""

    width: float = 1024.0
    height: float = 768.0
    background: str = "#FFFFFF"
    url: str = ""
    app: str = "generic"
    layers: list[Layer] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.width <= 0:
            errors.append("scene.width must be positive")
        if self.height <= 0:
            errors.append("scene.height must be positive")
        for layer in self.layers:
            errors.extend(layer.validate())
        return errors

    def iter_objects(self):
        """Yield all objects across all layers, in order."""
        for layer in self.layers:
            yield from layer.objects

    def to_dict(self) -> dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "background": self.background,
            "url": self.url,
            "app": self.app,
            "layers": [layer.to_dict() for layer in self.layers],
            "relations": [r.to_dict() for r in self.relations],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Scene:
        return cls(
            width=float(data.get("width", 1024.0)),
            height=float(data.get("height", 768.0)),
            background=data.get("background", "#FFFFFF"),
            url=data.get("url", ""),
            app=data.get("app", "generic"),
            layers=[Layer.from_dict(layer) for layer in data.get("layers", [])],
            relations=[Relation.from_dict(r) for r in data.get("relations", [])],
        )


# ── Validation spec ───────────────────────────────────────────────────────────

@dataclass
class ValidationSpec:
    """
    Declarative expectation describing what a correct render must contain.

    Used by the visual/structural validators to decide pass/fail and to
    drive the correction loop.
    """

    description: str = ""
    expected_shapes: list[str] = field(default_factory=list)
    expected_colors: list[str] = field(default_factory=list)
    min_objects: int = 0
    custom: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "expected_shapes": list(self.expected_shapes),
            "expected_colors": list(self.expected_colors),
            "min_objects": self.min_objects,
            "custom": self.custom,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ValidationSpec:
        return cls(
            description=data.get("description", ""),
            expected_shapes=list(data.get("expected_shapes", [])),
            expected_colors=list(data.get("expected_colors", [])),
            min_objects=int(data.get("min_objects", 0)),
            custom=dict(data.get("custom", {})),
        )


# ── Program ────────────────────────────────────────────────────────────────────

VQL_VERSION = "1.0"


@dataclass
class VQLProgram:
    """
    Top-level VQL program — the contract between NL parsing and rendering.

    A program bundles the :class:`Scene` to draw, an optional
    :class:`ValidationSpec`, the desired :class:`RenderTarget`, and free-form
    metadata (source query, intent, etc.).
    """

    scene: Scene = field(default_factory=Scene)
    validation: ValidationSpec | None = None
    render_target: RenderTarget = RenderTarget.SVG
    metadata: dict[str, Any] = field(default_factory=dict)
    version: str = VQL_VERSION

    def validate(self) -> list[str]:
        """Return structural validation errors (empty list = valid)."""
        return self.scene.validate()

    def is_valid(self) -> bool:
        return not self.validate()

    def object_count(self) -> int:
        return sum(len(layer.objects) for layer in self.scene.layers)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "render_target": self.render_target.value,
            "scene": self.scene.to_dict(),
            "validation": self.validation.to_dict() if self.validation else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VQLProgram:
        validation = data.get("validation")
        return cls(
            scene=Scene.from_dict(data.get("scene", {})),
            validation=ValidationSpec.from_dict(validation) if validation else None,
            render_target=RenderTarget(data.get("render_target", RenderTarget.SVG.value)),
            metadata=dict(data.get("metadata", {})),
            version=data.get("version", VQL_VERSION),
        )
