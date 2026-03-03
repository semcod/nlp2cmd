"""
Text-to-Shape — LLM-driven 2D object generation from text descriptions.

When a shape is not found in any database, this skill asks an LLM to generate
mathematical vertex coordinates that form the requested object.

Pipeline:
1. Build specialized prompt with geometry constraints
2. Route to coding LLM (best at structured JSON output)
3. Parse response → validate geometry → normalize coordinates
4. Register as dynamic ShapeGenerator for reuse

Single Responsibility: text description → validated PointGroup coordinates.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from nlp2cmd.skills.drawing.shapes import PointGroup, ShapeGenerator, ShapeRegistry


@dataclass
class GeneratedShape:
    """Result of LLM shape generation."""
    name: str
    points: list[PointGroup]
    description: str = ""
    model_used: str = ""
    generation_time_ms: float = 0.0
    confidence: float = 0.0  # 0..1 based on geometry validation
    raw_response: str = ""


# ── Geometry Validation ──────────────────────────────────────────────────

def validate_geometry(points: list[PointGroup], name: str = "") -> tuple[bool, list[str]]:
    """
    Validate generated geometry for common issues.

    Returns:
        (is_valid, list_of_warnings)
    """
    warnings: list[str] = []

    if not points:
        return False, ["No point groups generated"]

    total_pts = sum(len(g) for g in points)
    if total_pts < 3:
        return False, [f"Too few points ({total_pts}), need at least 3"]

    if total_pts > 2000:
        warnings.append(f"Very high point count ({total_pts}), may be slow to render")

    for i, group in enumerate(points):
        if len(group) < 2:
            warnings.append(f"Group {i} has only {len(group)} point(s)")

        # Check for NaN/Inf
        for x, y in group:
            if math.isnan(x) or math.isnan(y) or math.isinf(x) or math.isinf(y):
                return False, [f"Invalid coordinates (NaN/Inf) in group {i}"]

        # Check bounding box is reasonable (not too tiny or huge)
        xs = [p[0] for p in group]
        ys = [p[1] for p in group]
        w = max(xs) - min(xs)
        h = max(ys) - min(ys)
        if w < 1 and h < 1:
            warnings.append(f"Group {i} is very small ({w:.1f}x{h:.1f})")
        if w > 10000 or h > 10000:
            warnings.append(f"Group {i} is very large ({w:.0f}x{h:.0f})")

    return len(warnings) == 0 or total_pts >= 3, warnings


def normalize_points(points: list[PointGroup], target_size: float = 100.0) -> list[PointGroup]:
    """
    Normalize point groups to fit within [-target_size, target_size] centered at origin.
    """
    all_pts = [p for g in points for p in g]
    if not all_pts:
        return points

    min_x = min(p[0] for p in all_pts)
    max_x = max(p[0] for p in all_pts)
    min_y = min(p[1] for p in all_pts)
    max_y = max(p[1] for p in all_pts)

    cx = (min_x + max_x) / 2
    cy = (min_y + max_y) / 2
    w = max_x - min_x or 1
    h = max_y - min_y or 1
    scale = target_size / max(w, h) * 2

    result: list[PointGroup] = []
    for group in points:
        result.append([((x - cx) * scale, (y - cy) * scale) for x, y in group])
    return result


# ── LLM Prompt Templates ────────────────────────────────────────────────

SHAPE_GENERATION_PROMPT = """Generate 2D vertex coordinates for drawing: "{description}"

Requirements:
- Return ONLY valid JSON (no markdown, no explanation)
- Center the shape at origin (0, 0)
- Size should fit in a ~200x200 bounding box
- Use list of point groups: each group is a continuous stroke
- Coordinates are [x, y] pairs

JSON format:
{{
  "groups": [
    [[x1,y1], [x2,y2], ...],
    [[x1,y1], [x2,y2], ...]
  ],
  "description": "brief description of the shape",
  "parts": ["part1_name", "part2_name"]
}}

Example for "simple house":
{{
  "groups": [
    [[-60,40],[60,40],[60,-20],[-60,-20],[-60,40]],
    [[-60,-20],[0,-70],[60,-20]],
    [[-15,40],[-15,10],[15,10],[15,40]]
  ],
  "description": "house with triangular roof and door",
  "parts": ["walls", "roof", "door"]
}}

Now generate for: "{description}"
"""

COMPLEX_SHAPE_PROMPT = """Generate detailed 2D drawing coordinates for: "{description}"

This is a complex object. Break it into logical parts (body, details, accents).
Use smooth curves by providing many close points for rounded sections.
Each point group is a separate continuous stroke.

Requirements:
- Valid JSON only, no other text
- Center at (0, 0), fit within 200x200 box
- At least 3 point groups for detail
- Rounded parts: use 10+ points per curve segment

JSON format:
{{
  "groups": [[[x,y], ...], ...],
  "description": "what was drawn",
  "parts": ["name of each group"],
  "colors": ["suggested hex color for each group"]
}}

Generate for: "{description}"
"""


# ── Dynamic Shape Generator ─────────────────────────────────────────────

class DynamicShapeGenerator(ShapeGenerator):
    """
    ShapeGenerator created from LLM-generated or fetched point data.
    Can be registered in ShapeRegistry for reuse.
    """

    def __init__(self, shape_name: str, base_points: list[PointGroup]):
        self.name = shape_name
        self._base_points = base_points

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        """Scale and translate base points to requested position and size."""
        scale = size / 100.0  # base points are normalized to ~100 radius
        result: list[PointGroup] = []
        for group in self._base_points:
            scaled = [(cx + x * scale, cy + y * scale) for x, y in group]
            result.append(scaled)
        return result


# ── Text-to-Shape Engine ────────────────────────────────────────────────

class TextToShapeEngine:
    """
    Generates 2D shapes from text descriptions using LLM.

    Uses the LLM Router for model selection (coding category for structured output).
    Falls back to simpler prompts if complex ones fail.

    Usage:
        engine = TextToShapeEngine()
        result = await engine.generate("a cute cat sitting")
        if result:
            # result.points contains drawable point groups
            # Optionally register for reuse:
            engine.register_shape(result)
    """

    def __init__(self, auto_register: bool = True):
        self._auto_register = auto_register
        self._router = None
        self._generation_cache: dict[str, GeneratedShape] = {}

    def _get_router(self):
        """Lazy-init LLM router."""
        if self._router is None:
            try:
                from nlp2cmd.llm.router import get_router
                self._router = get_router()
            except ImportError:
                self._router = None
        return self._router

    async def generate(self, description: str, complex_mode: bool = False,
                       verbose: bool = False) -> Optional[GeneratedShape]:
        """
        Generate shape from text description.

        Args:
            description: Natural language description of the shape
            complex_mode: Use detailed prompt for complex objects
            verbose: Print progress

        Returns:
            GeneratedShape or None
        """
        desc_lower = description.lower().strip()

        # Check cache
        if desc_lower in self._generation_cache:
            return self._generation_cache[desc_lower]

        router = self._get_router()
        if router is None:
            if verbose:
                print("  ⚠ LLM Router not available, cannot generate shape")
            return None

        import time
        t0 = time.time()

        # Build prompt
        prompt = (COMPLEX_SHAPE_PROMPT if complex_mode else SHAPE_GENERATION_PROMPT).format(
            description=description
        )

        if verbose:
            print(f"  🤖 Generating '{description}' via LLM...")

        # Try coding model first (best at structured JSON)
        response = None
        model_used = ""
        for task_cat in ["coding", "text", "fast"]:
            try:
                resp = await router.route_call(
                    prompt=prompt,
                    task_category=task_cat,
                    timeout=30,
                )
                if resp and resp.text:
                    response = resp.text
                    model_used = getattr(resp, 'model', task_cat)
                    break
            except Exception as e:
                if verbose:
                    print(f"  ⚠ {task_cat} failed: {e}")
                continue

        if not response:
            if verbose:
                print("  ✗ All LLM attempts failed")
            return None

        # Parse JSON from response
        points, meta = self._parse_response(response)
        if not points:
            # Retry with simpler prompt if complex failed
            if complex_mode:
                return await self.generate(description, complex_mode=False, verbose=verbose)
            if verbose:
                print("  ✗ Failed to parse LLM response")
            return None

        # Normalize
        points = normalize_points(points)

        # Validate
        valid, warnings = validate_geometry(points, description)
        confidence = 1.0 if valid and not warnings else 0.7 if valid else 0.3
        if verbose:
            n_pts = sum(len(g) for g in points)
            print(f"  ✨ Generated {len(points)} groups, {n_pts} vertices (confidence: {confidence:.0%})")
            for w in warnings:
                print(f"     ⚠ {w}")

        elapsed = (time.time() - t0) * 1000
        result = GeneratedShape(
            name=description,
            points=points,
            description=meta.get("description", ""),
            model_used=model_used,
            generation_time_ms=elapsed,
            confidence=confidence,
            raw_response=response[:500],
        )

        # Cache and auto-register
        self._generation_cache[desc_lower] = result
        if self._auto_register and valid:
            self.register_shape(result)

        return result

    def register_shape(self, shape: GeneratedShape) -> None:
        """Register a generated shape in the global ShapeRegistry."""
        gen = DynamicShapeGenerator(shape.name, shape.points)
        ShapeRegistry.register(gen)

    def _parse_response(self, text: str) -> tuple[list[PointGroup], dict]:
        """Parse LLM response to extract point groups."""
        # Strip markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        # Try to find JSON object
        text = text.strip()
        if not text.startswith("{"):
            # Find first { ... }
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                text = text[start:end + 1]

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Try to fix common issues
            text = re.sub(r',\s*}', '}', text)
            text = re.sub(r',\s*]', ']', text)
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                return [], {}

        # Extract point groups
        groups_raw = data.get("groups", data.get("vertices", data.get("paths", [])))
        if not groups_raw:
            return [], data

        points: list[PointGroup] = []
        for group in groups_raw:
            if not isinstance(group, list):
                continue
            pg: PointGroup = []
            for pt in group:
                if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                    try:
                        pg.append((float(pt[0]), float(pt[1])))
                    except (ValueError, TypeError):
                        continue
            if pg:
                points.append(pg)

        return points, data
