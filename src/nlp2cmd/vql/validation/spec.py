"""
VQL structural validation.

Validates a :class:`VQLProgram` against its :class:`ValidationSpec` — i.e.
checks that the program actually contains the shapes/colors/object-count it
claims to. This is the schema-level gate that runs *before* (and complements)
the screenshot-based :class:`VisualValidator`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from nlp2cmd.vql.schema.program import ValidationSpec, VQLProgram


@dataclass
class VQLValidationReport:
    """Outcome of validating a program against a spec."""

    passed: bool
    issues: list[str] = field(default_factory=list)
    matched_shapes: list[str] = field(default_factory=list)
    matched_colors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "issues": list(self.issues),
            "matched_shapes": list(self.matched_shapes),
            "matched_colors": list(self.matched_colors),
        }


def _program_shapes(program: VQLProgram) -> set[str]:
    return {
        prim.shape_type
        for obj in program.scene.iter_objects()
        for prim in obj.primitives
    }


def _program_colors(program: VQLProgram) -> set[str]:
    return {obj.style.color.upper() for obj in program.scene.iter_objects()}


def _match_items(expected: list[str], present: set[str], label: str, *, upper: bool) -> tuple[list[str], list[str]]:
    """Return (matched, issues) for an expected/present comparison."""
    matched: list[str] = []
    issues: list[str] = []
    for item in expected:
        key = item.upper() if upper else item
        if key in present:
            matched.append(item)
        else:
            issues.append(f"expected {label} '{item}' not present in program")
    return matched, issues


def validate_program(program: VQLProgram, spec: ValidationSpec | None = None) -> VQLValidationReport:
    """
    Validate a program structurally and against a spec.

    If ``spec`` is omitted, the program's own ``validation`` spec is used.
    Structural errors (invalid scene) always fail the report.
    """
    issues: list[str] = list(program.validate())
    spec = spec or program.validation
    matched_shapes: list[str] = []
    matched_colors: list[str] = []

    if spec is not None:
        matched_shapes, shape_issues = _match_items(
            spec.expected_shapes, _program_shapes(program), "shape", upper=False
        )
        matched_colors, color_issues = _match_items(
            spec.expected_colors, _program_colors(program), "color", upper=True
        )
        issues.extend(shape_issues)
        issues.extend(color_issues)
        if program.object_count() < spec.min_objects:
            issues.append(
                f"object count {program.object_count()} below minimum {spec.min_objects}"
            )

    return VQLValidationReport(
        passed=not issues,
        issues=issues,
        matched_shapes=matched_shapes,
        matched_colors=matched_colors,
    )
