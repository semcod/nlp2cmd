"""
Unit tests for new drawing skills:
- ObjectFetcher + SVG path parser
- TextToShapeEngine + geometry validation
- VisualValidator + validation parsing
- CorrectionEngine + correction planning
- New shape generators (car, bird, butterfly, etc.)
"""

import asyncio
import json
import math
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nlp2cmd.skills.drawing.object_fetcher import (
    FetchedShape,
    IconifyFetcher,
    ObjectFetcher,
    SimpleIconsFetcher,
    parse_svg_path,
)
from nlp2cmd.skills.drawing.text_to_shape import (
    DynamicShapeGenerator,
    GeneratedShape,
    TextToShapeEngine,
    normalize_points,
    validate_geometry,
)
from nlp2cmd.skills.drawing.visual_validator import (
    DrawingCorrection,
    ValidationResult,
    ValidationVerdict,
    VisualValidator,
)
from nlp2cmd.skills.drawing.correction_engine import (
    CorrectionEngine,
    CorrectionPlan,
    CorrectionStep,
)
from nlp2cmd.skills.drawing.shapes import ShapeRegistry
from nlp2cmd.skills.drawing.nl_parser import NLDrawingParser
from nlp2cmd.skills.drawing.skill import DrawingSkill


# ── SVG Path Parser Tests ────────────────────────────────────────────────

class TestSVGPathParser:
    """Tests for parse_svg_path()."""

    def test_simple_triangle(self):
        pts = parse_svg_path("M10 10 L20 20 L30 10 Z")
        assert len(pts) == 1
        assert len(pts[0]) >= 3

    def test_empty_path(self):
        assert parse_svg_path("") == []
        assert parse_svg_path("  ") == []

    def test_moveto_lineto(self):
        pts = parse_svg_path("M0 0 L100 0 L100 100 L0 100 Z")
        assert len(pts) == 1
        assert len(pts[0]) >= 4

    def test_relative_commands(self):
        pts = parse_svg_path("m10 10 l20 0 l0 20 l-20 0 z")
        assert len(pts) == 1
        assert len(pts[0]) >= 4

    def test_horizontal_vertical(self):
        pts = parse_svg_path("M0 0 H100 V100 H0 Z")
        assert len(pts) == 1
        assert len(pts[0]) >= 4

    def test_cubic_bezier(self):
        pts = parse_svg_path("M0 0 C10 20 30 20 40 0")
        assert len(pts) >= 1
        total = sum(len(g) for g in pts)
        assert total >= 3  # start + bezier sample points

    def test_quadratic_bezier(self):
        pts = parse_svg_path("M0 0 Q20 30 40 0")
        assert len(pts) >= 1

    def test_centering(self):
        pts = parse_svg_path("M100 100 L200 100 L200 200 L100 200 Z", center=True)
        assert len(pts) == 1
        # Centered points should be roughly around 0,0
        avg_x = sum(p[0] for p in pts[0]) / len(pts[0])
        avg_y = sum(p[1] for p in pts[0]) / len(pts[0])
        assert abs(avg_x) < 50
        assert abs(avg_y) < 50

    def test_scale_factor(self):
        pts1 = parse_svg_path("M0 0 L10 0 L10 10 Z", scale=1.0)
        pts2 = parse_svg_path("M0 0 L10 0 L10 10 Z", scale=2.0)
        # Scaled version should have larger coordinates
        max1 = max(abs(p[0]) for p in pts1[0])
        max2 = max(abs(p[0]) for p in pts2[0])
        assert max2 > max1

    def test_multiple_subpaths(self):
        pts = parse_svg_path("M0 0 L10 10 Z M20 20 L30 30 Z")
        assert len(pts) == 2

    def test_complex_icon_path(self):
        # Simplified Material Design icon path
        d = "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"
        pts = parse_svg_path(d)
        assert len(pts) >= 1
        total = sum(len(g) for g in pts)
        assert total > 3


# ── Geometry Validation Tests ────────────────────────────────────────────

class TestGeometryValidation:
    """Tests for validate_geometry() and normalize_points()."""

    def test_valid_geometry(self):
        points = [[(0, 0), (10, 0), (10, 10), (0, 10)]]
        valid, warnings = validate_geometry(points)
        assert valid

    def test_empty_geometry(self):
        valid, warnings = validate_geometry([])
        assert not valid

    def test_too_few_points(self):
        valid, warnings = validate_geometry([[(0, 0), (1, 1)]])
        # 2 points total — should still be "valid" but with warnings
        assert not valid

    def test_nan_coordinates(self):
        valid, warnings = validate_geometry([[(0, 0), (float('nan'), 1), (2, 2)]])
        assert not valid
        assert any("NaN" in w or "Invalid" in w for w in warnings)

    def test_inf_coordinates(self):
        valid, warnings = validate_geometry([[(0, 0), (float('inf'), 1), (2, 2)]])
        assert not valid

    def test_normalize_centers(self):
        points = [[(100, 100), (200, 100), (200, 200), (100, 200)]]
        norm = normalize_points(points, target_size=50)
        # Should be centered around 0
        avg_x = sum(p[0] for p in norm[0]) / len(norm[0])
        avg_y = sum(p[1] for p in norm[0]) / len(norm[0])
        assert abs(avg_x) < 5
        assert abs(avg_y) < 5

    def test_normalize_scales(self):
        points = [[(0, 0), (1000, 0), (1000, 1000)]]
        norm = normalize_points(points, target_size=100)
        for group in norm:
            for x, y in group:
                assert abs(x) <= 110  # within target_size + margin
                assert abs(y) <= 110

    def test_normalize_empty(self):
        assert normalize_points([]) == []
        assert normalize_points([[]]) == [[]]


# ── DynamicShapeGenerator Tests ──────────────────────────────────────────

class TestDynamicShapeGenerator:
    """Tests for DynamicShapeGenerator."""

    def test_generate_at_center(self):
        base = [[(0, 0), (100, 0), (100, 100), (0, 100)]]
        gen = DynamicShapeGenerator("test_shape", base)
        result = gen.generate(500, 400, 200)
        assert len(result) == 1
        assert len(result[0]) == 4

    def test_scaling(self):
        base = [[(0, 0), (100, 0)]]
        gen = DynamicShapeGenerator("test", base)
        # size=100 → scale=1.0, size=200 → scale=2.0
        r1 = gen.generate(0, 0, 100)
        r2 = gen.generate(0, 0, 200)
        assert r2[0][1][0] > r1[0][1][0]  # larger x

    def test_name(self):
        gen = DynamicShapeGenerator("my_custom_shape", [[]])
        assert gen.name == "my_custom_shape"


# ── New Shape Generators Tests ───────────────────────────────────────────

class TestNewShapeGenerators:
    """Tests for all newly added shape generators."""

    COMPLEX_SHAPES = [
        "car", "bird", "butterfly", "boat", "mountain", "cat", "fish",
        "rocket", "castle", "diamond", "arrow", "pentagon", "hexagon",
        "octagon", "cross", "crescent", "cloud_detailed",
    ]

    @pytest.mark.parametrize("shape_name", COMPLEX_SHAPES)
    def test_shape_registered(self, shape_name):
        assert shape_name in ShapeRegistry.available()

    @pytest.mark.parametrize("shape_name", COMPLEX_SHAPES)
    def test_shape_generates_points(self, shape_name):
        gen = ShapeRegistry.get(shape_name)
        result = gen.generate(500, 400, 100)
        assert isinstance(result, list)
        assert len(result) > 0
        for group in result:
            assert len(group) >= 2
            for pt in group:
                assert len(pt) == 2
                assert isinstance(pt[0], (int, float))
                assert isinstance(pt[1], (int, float))

    @pytest.mark.parametrize("shape_name", COMPLEX_SHAPES)
    def test_shape_no_nan(self, shape_name):
        gen = ShapeRegistry.get(shape_name)
        result = gen.generate(500, 400, 100)
        for group in result:
            for x, y in group:
                assert not math.isnan(x), f"{shape_name}: NaN x"
                assert not math.isnan(y), f"{shape_name}: NaN y"
                assert not math.isinf(x), f"{shape_name}: Inf x"
                assert not math.isinf(y), f"{shape_name}: Inf y"

    def test_total_registered_shapes(self):
        shapes = ShapeRegistry.available()
        assert len(shapes) >= 33  # 16 basic + 17 new


# ── NL Parser New Shapes Tests ───────────────────────────────────────────

class TestNLParserNewShapes:
    """Tests for NL parser recognizing new shapes."""

    def setup_method(self):
        self.parser = NLDrawingParser()

    def test_polish_car(self):
        assert self.parser.detect_shape("narysuj samochód") == "car"

    def test_polish_bird(self):
        assert self.parser.detect_shape("narysuj ptaka") == "bird"

    def test_polish_butterfly(self):
        assert self.parser.detect_shape("narysuj motyla") == "butterfly"

    def test_polish_boat(self):
        assert self.parser.detect_shape("narysuj łódkę") == "boat"

    def test_polish_cat(self):
        assert self.parser.detect_shape("narysuj kota") == "cat"

    def test_polish_fish(self):
        assert self.parser.detect_shape("rybka") == "fish"

    def test_polish_rocket(self):
        assert self.parser.detect_shape("narysuj rakietę") == "rocket"

    def test_polish_castle(self):
        assert self.parser.detect_shape("zamek") == "castle"

    def test_polish_mountain(self):
        assert self.parser.detect_shape("góra") == "mountain"

    def test_polish_cross(self):
        assert self.parser.detect_shape("krzyż") == "cross"

    def test_polish_cloud(self):
        assert self.parser.detect_shape("chmurka") == "cloud_detailed"

    def test_english_car(self):
        assert self.parser.detect_shape("draw a car") == "car"

    def test_english_butterfly(self):
        assert self.parser.detect_shape("butterfly") == "butterfly"

    def test_english_rocket(self):
        assert self.parser.detect_shape("rocket") == "rocket"

    def test_english_castle(self):
        assert self.parser.detect_shape("draw a castle") == "castle"

    def test_english_pentagon(self):
        assert self.parser.detect_shape("pentagon") == "pentagon"

    def test_english_hexagon(self):
        assert self.parser.detect_shape("hexagon") == "hexagon"


# ── ObjectFetcher Tests ──────────────────────────────────────────────────

class TestObjectFetcher:
    """Tests for ObjectFetcher (caching, known objects)."""

    def test_known_objects(self):
        known = ObjectFetcher.known_objects()
        assert "car" in known
        assert "butterfly" in known
        assert "castle" in known
        assert len(known) > 30

    def test_cache_dir_creation(self):
        with tempfile.TemporaryDirectory() as d:
            cache = Path(d) / "test_cache"
            fetcher = ObjectFetcher(cache_dir=cache)
            assert cache.exists()

    def test_clear_cache(self):
        with tempfile.TemporaryDirectory() as d:
            cache = Path(d) / "test_cache"
            fetcher = ObjectFetcher(cache_dir=cache)
            # Write a dummy cache file
            (cache / "test.json").write_text('{"name": "test"}')
            count = fetcher.clear_cache()
            assert count == 1
            assert not list(cache.glob("*.json"))

    def test_cache_save_and_load(self):
        with tempfile.TemporaryDirectory() as d:
            cache = Path(d) / "test_cache"
            fetcher = ObjectFetcher(cache_dir=cache)
            shape = FetchedShape(
                name="test_obj",
                points=[[(0, 0), (10, 0), (10, 10)]],
                source="test",
                svg_path="M0 0L10 0L10 10",
            )
            fetcher._save_cache("test_obj", shape)
            loaded = fetcher._load_cache("test_obj")
            assert loaded is not None
            assert loaded.name == "test_obj"
            assert len(loaded.points) == 1
            assert len(loaded.points[0]) == 3

    def test_cache_ttl_expired(self):
        with tempfile.TemporaryDirectory() as d:
            cache = Path(d) / "test_cache"
            fetcher = ObjectFetcher(cache_dir=cache, cache_ttl=0)
            shape = FetchedShape(name="x", points=[[(0, 0), (1, 1), (2, 2)]], source="t")
            fetcher._save_cache("x", shape)
            # TTL=0 means immediately expired
            import time
            time.sleep(0.01)
            loaded = fetcher._load_cache("x")
            assert loaded is None


# ── TextToShapeEngine Tests ──────────────────────────────────────────────

class TestTextToShapeEngine:
    """Tests for TextToShapeEngine response parsing."""

    def setup_method(self):
        self.engine = TextToShapeEngine(auto_register=False)

    def test_parse_valid_json(self):
        response = json.dumps({
            "groups": [[[0, 0], [10, 0], [10, 10], [0, 10]]],
            "description": "a square",
        })
        points, meta = self.engine._parse_response(response)
        assert len(points) == 1
        assert len(points[0]) == 4
        assert meta.get("description") == "a square"

    def test_parse_json_in_markdown(self):
        response = '```json\n{"groups": [[[0,0],[1,1],[2,0]]]}\n```'
        points, meta = self.engine._parse_response(response)
        assert len(points) == 1
        assert len(points[0]) == 3

    def test_parse_json_with_text(self):
        response = 'Here is the shape:\n{"groups": [[[0,0],[5,5],[10,0]]]}\nHope this helps!'
        points, meta = self.engine._parse_response(response)
        assert len(points) == 1

    def test_parse_invalid_json(self):
        points, meta = self.engine._parse_response("not json at all")
        assert points == []

    def test_parse_trailing_comma(self):
        response = '{"groups": [[[0,0],[1,1],[2,0],],]}'
        points, meta = self.engine._parse_response(response)
        assert len(points) == 1

    def test_parse_alternate_keys(self):
        response = json.dumps({"vertices": [[[0, 0], [1, 1], [2, 0]]]})
        points, meta = self.engine._parse_response(response)
        assert len(points) == 1

    def test_register_shape(self):
        shape = GeneratedShape(
            name="llm_cat",
            points=[[(0, 0), (10, 0), (10, 10)]],
        )
        # Should not raise
        self.engine.register_shape(shape)
        gen = ShapeRegistry.get("llm_cat")
        assert gen.name == "llm_cat"


# ── VisualValidator Tests ────────────────────────────────────────────────

class TestVisualValidator:
    """Tests for VisualValidator parsing and heuristics."""

    def setup_method(self):
        self.validator = VisualValidator()

    def test_parse_correct_validation(self):
        text = json.dumps({
            "what_i_see": "a red star on white background",
            "match": "yes",
            "confidence": 0.95,
            "issues": [],
        })
        import time
        result = self.validator._parse_validation(text, "test-model", time.time())
        assert result.verdict == ValidationVerdict.CORRECT
        assert result.confidence == 0.95
        assert result.matches_request
        assert len(result.corrections) == 0

    def test_parse_partial_validation(self):
        text = json.dumps({
            "what_i_see": "a star, but it's black not red",
            "match": "partially",
            "confidence": 0.7,
            "issues": [{
                "problem": "wrong color",
                "action": "recolor",
                "target": "star",
                "priority": 1,
                "details": {"expected_color": "#FF0000"},
            }],
        })
        import time
        result = self.validator._parse_validation(text, "test", time.time())
        assert result.verdict == ValidationVerdict.PARTIAL
        assert result.needs_correction
        assert len(result.corrections) == 1
        assert result.corrections[0].action == "recolor"
        assert result.corrections[0].target == "star"

    def test_parse_empty_canvas(self):
        text = json.dumps({
            "what_i_see": "blank white canvas",
            "match": "empty",
            "confidence": 0.99,
            "issues": [],
        })
        import time
        result = self.validator._parse_validation(text, "test", time.time())
        assert result.verdict == ValidationVerdict.EMPTY
        assert result.needs_correction

    def test_parse_wrong_drawing(self):
        text = json.dumps({
            "what_i_see": "a circle",
            "match": "no",
            "confidence": 0.8,
            "issues": [
                {"problem": "wrong shape", "action": "redraw", "target": "all", "priority": 1},
            ],
        })
        import time
        result = self.validator._parse_validation(text, "test", time.time())
        assert result.verdict == ValidationVerdict.WRONG
        assert result.needs_correction
        assert len(result.critical_corrections) == 1

    def test_heuristic_small_file(self):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"x" * 100)  # very small "image"
            f.flush()
            import time
            result = self.validator._heuristic_validate(Path(f.name), "test", time.time())
            assert result.verdict == ValidationVerdict.EMPTY

    def test_heuristic_normal_file(self):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"x" * 50000)  # reasonable size
            f.flush()
            import time
            result = self.validator._heuristic_validate(Path(f.name), "test", time.time())
            assert result.verdict == ValidationVerdict.PARTIAL

    def test_parse_json_in_markdown(self):
        text = '```json\n{"what_i_see":"star","match":"yes","confidence":0.9,"issues":[]}\n```'
        import time
        result = self.validator._parse_validation(text, "test", time.time())
        assert result.verdict == ValidationVerdict.CORRECT


# ── DrawingCorrection Tests ──────────────────────────────────────────────

class TestDrawingCorrection:
    """Tests for DrawingCorrection dataclass."""

    def test_correction_repr(self):
        c = DrawingCorrection(
            issue="wrong color",
            action="recolor",
            target="star",
        )
        assert "recolor" in repr(c)
        assert "star" in repr(c)

    def test_correction_priority(self):
        c = DrawingCorrection(issue="x", action="redraw", target="y", priority=1)
        assert c.priority == 1

    def test_correction_details(self):
        c = DrawingCorrection(
            issue="too small", action="resize", target="circle",
            details={"scale": 2.0},
        )
        assert c.details["scale"] == 2.0


# ── CorrectionEngine Tests ──────────────────────────────────────────────

class TestCorrectionEngine:
    """Tests for CorrectionEngine correction planning."""

    def test_redraw_all_correction(self):
        skill = MagicMock()
        renderer = MagicMock()
        engine = CorrectionEngine(skill, renderer)
        correction = DrawingCorrection(
            issue="completely wrong", action="redraw", target="all", priority=1,
        )
        steps = engine._correction_to_steps(correction, "red star")
        assert len(steps) == 2
        assert steps[0].action == "clear"
        assert steps[1].action == "draw_from_description"

    def test_recolor_correction(self):
        skill = MagicMock()
        renderer = MagicMock()
        engine = CorrectionEngine(skill, renderer)
        correction = DrawingCorrection(
            issue="wrong color", action="recolor", target="star",
            details={"color": "#FF0000"},
        )
        steps = engine._correction_to_steps(correction, "red star")
        assert any(s.action == "set_color" for s in steps)
        assert any(s.action == "draw_shape" for s in steps)

    def test_add_correction(self):
        skill = MagicMock()
        renderer = MagicMock()
        engine = CorrectionEngine(skill, renderer)
        correction = DrawingCorrection(
            issue="missing door", action="add", target="door",
            details={"color": "#8B4513"},
        )
        steps = engine._correction_to_steps(correction, "house with door")
        assert len(steps) == 1
        assert steps[0].action == "draw_shape"

    def test_resize_correction(self):
        skill = MagicMock()
        renderer = MagicMock()
        engine = CorrectionEngine(skill, renderer)
        correction = DrawingCorrection(
            issue="too small", action="resize", target="star",
            details={"scale": 2.0},
        )
        steps = engine._correction_to_steps(correction, "big star")
        assert steps[0].action == "clear"
        assert steps[1].action == "draw_from_description"

    def test_empty_correction(self):
        skill = MagicMock()
        renderer = MagicMock()
        engine = CorrectionEngine(skill, renderer)
        correction = DrawingCorrection(
            issue="unknown", action="unknown_action", target="x",
        )
        steps = engine._correction_to_steps(correction, "test")
        assert len(steps) == 0


# ── ValidationResult Properties Tests ────────────────────────────────────

class TestValidationResult:
    """Tests for ValidationResult properties."""

    def test_needs_correction_partial(self):
        r = ValidationResult(verdict=ValidationVerdict.PARTIAL)
        assert r.needs_correction

    def test_needs_correction_wrong(self):
        r = ValidationResult(verdict=ValidationVerdict.WRONG)
        assert r.needs_correction

    def test_needs_correction_empty(self):
        r = ValidationResult(verdict=ValidationVerdict.EMPTY)
        assert r.needs_correction

    def test_no_correction_correct(self):
        r = ValidationResult(verdict=ValidationVerdict.CORRECT)
        assert not r.needs_correction

    def test_critical_corrections(self):
        r = ValidationResult(
            verdict=ValidationVerdict.PARTIAL,
            corrections=[
                DrawingCorrection(issue="a", action="redraw", target="x", priority=1),
                DrawingCorrection(issue="b", action="recolor", target="y", priority=2),
                DrawingCorrection(issue="c", action="add", target="z", priority=1),
            ],
        )
        assert len(r.critical_corrections) == 2


# ── Integration: DrawingSkill + New Shapes ───────────────────────────────

class TestDrawingSkillNewShapes:
    """Integration tests: DrawingSkill with new shape types."""

    def test_draw_car(self):
        skill = DrawingSkill()
        skill.init_canvas(1024, 768)
        event = skill.draw("car", color="#FF0000")
        assert event.shape_type == "car"
        assert len(event.points) >= 3  # body + 2 wheels minimum

    def test_draw_butterfly(self):
        skill = DrawingSkill()
        skill.init_canvas(1024, 768)
        event = skill.draw("butterfly")
        assert event.shape_type == "butterfly"
        assert len(event.points) >= 5  # wings + body + antennae

    def test_draw_castle(self):
        skill = DrawingSkill()
        skill.init_canvas(1024, 768)
        event = skill.draw("castle")
        assert len(event.points) >= 5  # wall + towers + roofs + gate

    def test_draw_rocket(self):
        skill = DrawingSkill()
        skill.init_canvas(1024, 768)
        event = skill.draw("rocket", color="#0000FF")
        assert event.color == "#0000FF"
        assert len(event.points) >= 4  # body + fins + window + flame

    def test_nl_draw_polish_car(self):
        skill = DrawingSkill()
        skill.init_canvas(1024, 768)
        events = skill.execute_nl("narysuj czerwony samochód")
        shape_events = [e for e in events if hasattr(e, 'shape_type')]
        assert len(shape_events) == 1
        assert shape_events[0].shape_type == "car"

    def test_nl_draw_english_butterfly(self):
        skill = DrawingSkill()
        skill.init_canvas(1024, 768)
        events = skill.execute_nl("draw a blue butterfly")
        shape_events = [e for e in events if hasattr(e, 'shape_type')]
        assert len(shape_events) == 1
        assert shape_events[0].shape_type == "butterfly"

    def test_multiple_new_shapes(self):
        skill = DrawingSkill()
        skill.init_canvas(1024, 768)
        events = skill.execute_nl("narysuj kota i rybkę")
        shape_events = [e for e in events if hasattr(e, 'shape_type')]
        shape_types = {e.shape_type for e in shape_events}
        assert "cat" in shape_types
        assert "fish" in shape_types

    def test_shapes_saved_in_session(self):
        skill = DrawingSkill()
        skill.init_canvas(1024, 768)
        skill.draw("rocket")
        skill.draw("castle")
        shapes = skill.get_shapes()
        assert len(shapes) == 2
        assert shapes[0]["shape_type"] == "rocket"
        assert shapes[1]["shape_type"] == "castle"


# ── FetchedShape Tests ───────────────────────────────────────────────────

class TestFetchedShape:
    """Tests for FetchedShape dataclass."""

    def test_creation(self):
        s = FetchedShape(
            name="test", points=[[(0, 0), (1, 1)]], source="iconify",
        )
        assert s.name == "test"
        assert s.source == "iconify"
        assert s.fetch_time_ms == 0.0

    def test_metadata(self):
        s = FetchedShape(
            name="x", points=[], source="y",
            metadata={"icon_id": "mdi:car"},
        )
        assert s.metadata["icon_id"] == "mdi:car"


# ── IconifyFetcher Shape Map Tests ───────────────────────────────────────

class TestIconifyShapeMap:
    """Tests for Iconify shape name mappings."""

    def test_common_shapes_mapped(self):
        for name in ["car", "tree", "house", "bird", "cat", "star", "heart"]:
            assert name in IconifyFetcher.SHAPE_MAP, f"{name} not in SHAPE_MAP"

    def test_game_icons_included(self):
        # Game Icons set has great RPG/fantasy shapes
        dragon = IconifyFetcher.SHAPE_MAP.get("dragon", [])
        assert any("game-icons" in icon for icon in dragon)

    def test_all_mappings_have_colons(self):
        for name, icons in IconifyFetcher.SHAPE_MAP.items():
            for icon in icons:
                assert ":" in icon, f"Invalid icon ID: {icon} for {name}"
