"""
Unit tests for the drawing skill module.

Tests cover:
- Event creation and serialization
- EventStore append/replay/persistence
- CommandBus dispatch and validation
- QueryBus projections
- ShapeRegistry and shape generators
- ColorResolver
- NLDrawingParser (PL + EN)
- SVGRenderer
- DrawingSkill facade
"""

import asyncio
import json
import tempfile
from pathlib import Path

import pytest

from nlp2cmd.skills.drawing.colors import ColorResolver
from nlp2cmd.skills.drawing.commands import (
    ClearCanvas,
    CommandBus,
    DrawShape,
    InitCanvas,
    SelectTool,
    SetColor,
)
from nlp2cmd.skills.drawing.event_store import EventStore
from nlp2cmd.skills.drawing.events import (
    CanvasCleared,
    CanvasInitialized,
    ColorChanged,
    DrawingEvent,
    EventType,
    ShapeDrawn,
    ToolSelected,
)
from nlp2cmd.skills.drawing.nl_parser import NLDrawingParser
from nlp2cmd.skills.drawing.queries import (
    GetCanvasState,
    GetDrawingHistory,
    GetShapePoints,
    QueryBus,
)
from nlp2cmd.skills.drawing.shapes import (
    CircleGenerator,
    HouseGenerator,
    ShapeRegistry,
    StarGenerator,
)
from nlp2cmd.skills.drawing.skill import DrawingSkill


# ── Events ────────────────────────────────────────────────────────────────


class TestEvents:
    def test_canvas_initialized(self):
        e = CanvasInitialized(width=800, height=600, url="https://jspaint.app", app="jspaint")
        assert e.event_type == EventType.CANVAS_INITIALIZED
        assert e.payload["width"] == 800
        assert e.payload["url"] == "https://jspaint.app"

    def test_shape_drawn(self):
        pts = [[(0, 0), (100, 0), (100, 100)]]
        e = ShapeDrawn(shape_type="triangle", points=pts, color="#FF0000")
        assert e.event_type == EventType.SHAPE_DRAWN
        assert e.payload["shape_type"] == "triangle"
        assert e.payload["color"] == "#FF0000"

    def test_color_changed(self):
        e = ColorChanged(color="#00FF00", previous_color="#000000")
        assert e.payload["color"] == "#00FF00"
        assert e.payload["previous_color"] == "#000000"

    def test_tool_selected(self):
        e = ToolSelected(tool="pencil", previous_tool="brush")
        assert e.payload["tool"] == "pencil"

    def test_canvas_cleared(self):
        e = CanvasCleared()
        assert e.event_type == EventType.CANVAS_CLEARED

    def test_event_to_dict(self):
        e = ShapeDrawn(shape_type="circle", color="#FF0000")
        d = e.to_dict()
        assert d["event_type"] == "shape_drawn"
        assert "event_id" in d
        assert "timestamp" in d

    def test_event_from_dict(self):
        original = ShapeDrawn(shape_type="star", color="#0000FF", points=[[(1, 2), (3, 4)]])
        d = original.to_dict()
        restored = DrawingEvent.from_dict(d)
        assert isinstance(restored, ShapeDrawn)
        assert restored.event_type == EventType.SHAPE_DRAWN

    def test_event_immutability(self):
        e = ShapeDrawn(shape_type="circle")
        with pytest.raises(AttributeError):
            e.shape_type = "star"


# ── EventStore ────────────────────────────────────────────────────────────


class TestEventStore:
    def test_append_and_count(self):
        store = EventStore()
        assert store.count == 0
        store.append(ShapeDrawn(shape_type="circle"))
        assert store.count == 1

    def test_events_property_returns_copy(self):
        store = EventStore()
        store.append(ShapeDrawn(shape_type="circle"))
        events = store.events
        events.clear()
        assert store.count == 1

    def test_subscribe(self):
        store = EventStore()
        received = []
        store.subscribe(lambda e: received.append(e))
        store.append(ShapeDrawn(shape_type="circle"))
        assert len(received) == 1

    def test_unsubscribe(self):
        store = EventStore()
        received = []
        callback = lambda e: received.append(e)
        store.subscribe(callback)
        store.unsubscribe(callback)
        store.append(ShapeDrawn(shape_type="circle"))
        assert len(received) == 0

    def test_replay(self):
        store = EventStore()
        store.append(ShapeDrawn(shape_type="circle"))
        store.append(ShapeDrawn(shape_type="star"))
        replayed = []
        store.replay(lambda e: replayed.append(e))
        assert len(replayed) == 2

    def test_events_since(self):
        store = EventStore()
        e1 = ShapeDrawn(shape_type="circle")
        store.append(e1)
        e2 = ShapeDrawn(shape_type="star")
        store.append(e2)
        since = store.events_since(e1.timestamp)
        assert len(since) >= 1

    def test_events_of_type(self):
        store = EventStore()
        store.append(ShapeDrawn(shape_type="circle"))
        store.append(ColorChanged(color="#FF0000"))
        store.append(ShapeDrawn(shape_type="star"))
        shapes = store.events_of_type("shape_drawn")
        assert len(shapes) == 2

    def test_save_and_load(self):
        store = EventStore()
        store.append(CanvasInitialized(width=800, height=600))
        store.append(ShapeDrawn(shape_type="circle", color="#FF0000"))

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        store.save(path)
        loaded = EventStore.load(path)
        assert loaded.count == 2
        Path(path).unlink()

    def test_to_dict(self):
        store = EventStore()
        store.append(ShapeDrawn(shape_type="circle"))
        data = store.to_dict()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["event_type"] == "shape_drawn"

    def test_clear(self):
        store = EventStore()
        store.append(ShapeDrawn(shape_type="circle"))
        store.clear()
        assert store.count == 0


# ── CommandBus ────────────────────────────────────────────────────────────


class TestCommandBus:
    def test_init_canvas(self):
        store = EventStore()
        bus = CommandBus(store)
        event = bus.dispatch(InitCanvas(width=1024, height=768))
        assert isinstance(event, CanvasInitialized)
        assert bus.state["canvas_width"] == 1024

    def test_draw_shape(self):
        store = EventStore()
        bus = CommandBus(store)
        bus.dispatch(InitCanvas(width=800, height=600))
        event = bus.dispatch(DrawShape(shape_type="circle", color="#FF0000"))
        assert isinstance(event, ShapeDrawn)
        assert event.shape_type == "circle"
        assert len(event.points) > 0

    def test_set_color(self):
        store = EventStore()
        bus = CommandBus(store)
        event = bus.dispatch(SetColor(color="#FF0000"))
        assert isinstance(event, ColorChanged)
        assert bus.state["current_color"] == "#FF0000"

    def test_select_tool(self):
        store = EventStore()
        bus = CommandBus(store)
        event = bus.dispatch(SelectTool(tool="pencil"))
        assert isinstance(event, ToolSelected)
        assert bus.state["current_tool"] == "pencil"

    def test_clear_canvas(self):
        store = EventStore()
        bus = CommandBus(store)
        bus.dispatch(InitCanvas(width=800, height=600))
        bus.dispatch(DrawShape(shape_type="circle"))
        event = bus.dispatch(ClearCanvas())
        assert isinstance(event, CanvasCleared)

    def test_validation_error(self):
        store = EventStore()
        bus = CommandBus(store)
        with pytest.raises(ValueError, match="width must be positive"):
            bus.dispatch(InitCanvas(width=-1, height=600))

    def test_unknown_command(self):
        store = EventStore()
        bus = CommandBus(store)

        class FakeCommand:
            def validate(self):
                return []
        with pytest.raises(TypeError, match="No handler"):
            bus.dispatch(FakeCommand())

    def test_pre_hook(self):
        store = EventStore()
        bus = CommandBus(store)
        hooked = []
        bus.add_pre_hook(lambda cmd: hooked.append(cmd))
        bus.dispatch(SetColor(color="#FF0000"))
        assert len(hooked) == 1

    def test_post_hook(self):
        store = EventStore()
        bus = CommandBus(store)
        hooked = []
        bus.add_post_hook(lambda cmd, evt: hooked.append((cmd, evt)))
        bus.dispatch(SetColor(color="#FF0000"))
        assert len(hooked) == 1
        assert isinstance(hooked[0][1], ColorChanged)

    def test_rebuild_state(self):
        store = EventStore()
        bus = CommandBus(store)
        bus.dispatch(InitCanvas(width=800, height=600))
        bus.dispatch(SetColor(color="#FF0000"))
        bus.dispatch(SelectTool(tool="pencil"))

        bus2 = CommandBus(store)
        bus2.rebuild_state()
        assert bus2.state["canvas_width"] == 800
        assert bus2.state["current_color"] == "#FF0000"
        assert bus2.state["current_tool"] == "pencil"


# ── QueryBus ──────────────────────────────────────────────────────────────


class TestQueryBus:
    def test_get_canvas_state(self):
        store = EventStore()
        bus = CommandBus(store)
        bus.dispatch(InitCanvas(width=800, height=600))
        bus.dispatch(SetColor(color="#FF0000"))

        qbus = QueryBus(store)
        state = qbus.execute(GetCanvasState())
        assert state["width"] == 800
        assert state["current_color"] == "#FF0000"
        assert state["is_blank"]

    def test_get_canvas_state_after_draw(self):
        store = EventStore()
        bus = CommandBus(store)
        bus.dispatch(InitCanvas(width=800, height=600))
        bus.dispatch(DrawShape(shape_type="circle"))

        qbus = QueryBus(store)
        state = qbus.execute(GetCanvasState())
        assert state["shapes_count"] == 1
        assert not state["is_blank"]

    def test_get_drawing_history(self):
        store = EventStore()
        bus = CommandBus(store)
        bus.dispatch(InitCanvas(width=800, height=600))
        bus.dispatch(DrawShape(shape_type="circle"))
        bus.dispatch(DrawShape(shape_type="star"))

        qbus = QueryBus(store)
        history = qbus.execute(GetDrawingHistory())
        assert len(history) == 3

    def test_get_drawing_history_filtered(self):
        store = EventStore()
        bus = CommandBus(store)
        bus.dispatch(InitCanvas(width=800, height=600))
        bus.dispatch(DrawShape(shape_type="circle"))
        bus.dispatch(SetColor(color="#FF0000"))

        qbus = QueryBus(store)
        shapes = qbus.execute(GetDrawingHistory(event_type_filter="shape_drawn"))
        assert len(shapes) == 1

    def test_get_shape_points(self):
        store = EventStore()
        bus = CommandBus(store)
        bus.dispatch(InitCanvas(width=800, height=600))
        bus.dispatch(DrawShape(shape_type="circle", color="#FF0000"))

        qbus = QueryBus(store)
        shapes = qbus.execute(GetShapePoints())
        assert len(shapes) == 1
        assert shapes[0]["shape_type"] == "circle"
        assert shapes[0]["color"] == "#FF0000"
        assert len(shapes[0]["points"]) > 0

    def test_shapes_cleared_on_clear(self):
        store = EventStore()
        bus = CommandBus(store)
        bus.dispatch(InitCanvas(width=800, height=600))
        bus.dispatch(DrawShape(shape_type="circle"))
        bus.dispatch(ClearCanvas())

        qbus = QueryBus(store)
        shapes = qbus.execute(GetShapePoints())
        assert len(shapes) == 0


# ── ShapeRegistry ─────────────────────────────────────────────────────────


class TestShapeRegistry:
    def test_available_shapes(self):
        shapes = ShapeRegistry.available()
        assert "circle" in shapes
        assert "star" in shapes
        assert "house" in shapes
        assert "heart" in shapes
        assert "spiral" in shapes
        assert len(shapes) >= 16

    def test_get_circle(self):
        gen = ShapeRegistry.get("circle")
        assert isinstance(gen, CircleGenerator)
        points = gen.generate(400, 300, 100)
        assert len(points) == 1
        assert len(points[0]) == 37  # 36 steps + close

    def test_get_star(self):
        gen = ShapeRegistry.get("star")
        points = gen.generate(400, 300, 100)
        assert len(points) == 1
        assert len(points[0]) == 11  # 5 outer + 5 inner + close

    def test_get_house(self):
        gen = ShapeRegistry.get("house")
        points = gen.generate(400, 300, 100)
        assert len(points) == 3  # body, roof, door

    def test_unknown_falls_back_to_circle(self):
        gen = ShapeRegistry.get("nonexistent")
        assert isinstance(gen, CircleGenerator)

    def test_custom_registration(self):
        from nlp2cmd.skills.drawing.shapes import ShapeGenerator

        class DiamondGenerator(ShapeGenerator):
            name = "diamond"
            def generate(self, cx, cy, size, **params):
                return [[(cx, cy - size), (cx + size, cy),
                         (cx, cy + size), (cx - size, cy), (cx, cy - size)]]

        ShapeRegistry.register(DiamondGenerator())
        gen = ShapeRegistry.get("diamond")
        assert isinstance(gen, DiamondGenerator)
        points = gen.generate(400, 300, 100)
        assert len(points) == 1
        assert len(points[0]) == 5

    def test_circle_points_form_circle(self):
        import math
        gen = ShapeRegistry.get("circle")
        pts = gen.generate(0, 0, 100)[0]
        for x, y in pts:
            dist = math.sqrt(x ** 2 + y ** 2)
            assert abs(dist - 100) < 0.01

    def test_grid_generator(self):
        gen = ShapeRegistry.get("grid")
        groups = gen.generate(400, 300, 200, cols=3, rows=3)
        assert len(groups) == 8  # 4 vertical + 4 horizontal

    def test_wave_generator(self):
        gen = ShapeRegistry.get("wave")
        groups = gen.generate(400, 300, 200)
        assert len(groups) == 1
        assert len(groups[0]) == 60


# ── ColorResolver ─────────────────────────────────────────────────────────


class TestColorResolver:
    def test_resolve_polish(self):
        r = ColorResolver()
        assert r.resolve("czerwony") == "#FF0000"
        assert r.resolve("niebieski") == "#0000FF"
        assert r.resolve("zielony") == "#00FF00"

    def test_resolve_english(self):
        r = ColorResolver()
        assert r.resolve("red") == "#FF0000"
        assert r.resolve("blue") == "#0000FF"

    def test_resolve_polish_cases(self):
        r = ColorResolver()
        assert r.resolve("czerwonym") == "#FF0000"
        assert r.resolve("niebieskim") == "#0000FF"

    def test_resolve_hex_passthrough(self):
        r = ColorResolver()
        assert r.resolve("#AABBCC") == "#AABBCC"

    def test_resolve_default(self):
        r = ColorResolver()
        assert r.resolve("nonexistent") == "#000000"
        assert r.resolve("nonexistent", "#FFFFFF") == "#FFFFFF"

    def test_extract_colors(self):
        r = ColorResolver()
        colors = r.extract_colors("narysuj czerwone koło i niebieski trójkąt")
        assert "#FF0000" in colors
        assert "#0000FF" in colors

    def test_extract_hex_from_text(self):
        r = ColorResolver()
        colors = r.extract_colors("użyj koloru #AABBCC")
        assert "#AABBCC" in colors

    def test_custom_color_registration(self):
        r = ColorResolver()
        r.register("magenta", "#FF00FF")
        assert r.resolve("magenta") == "#FF00FF"


# ── NLDrawingParser ───────────────────────────────────────────────────────


class TestNLDrawingParser:
    def test_parse_polish_circle(self):
        p = NLDrawingParser()
        cmds = p.parse("narysuj czerwone koło")
        assert len(cmds) == 2
        assert isinstance(cmds[0], SetColor)
        assert cmds[0].color == "#FF0000"
        assert isinstance(cmds[1], DrawShape)
        assert cmds[1].shape_type == "circle"

    def test_parse_english_star(self):
        p = NLDrawingParser()
        cmds = p.parse("draw a blue star")
        assert len(cmds) == 2
        assert isinstance(cmds[1], DrawShape)
        assert cmds[1].shape_type == "star"

    def test_parse_multiple_shapes(self):
        p = NLDrawingParser()
        cmds = p.parse("narysuj koło i trójkąt")
        shapes = [c for c in cmds if isinstance(c, DrawShape)]
        assert len(shapes) == 2
        shape_types = {s.shape_type for s in shapes}
        assert "circle" in shape_types
        assert "triangle" in shape_types

    def test_parse_clear(self):
        p = NLDrawingParser()
        cmds = p.parse("wyczyść wszystko")
        assert len(cmds) == 1
        assert isinstance(cmds[0], ClearCanvas)

    def test_parse_house(self):
        p = NLDrawingParser()
        cmds = p.parse("narysuj dom z czerwonym dachem")
        shapes = [c for c in cmds if isinstance(c, DrawShape)]
        assert any(s.shape_type == "house" for s in shapes)

    def test_detect_shape(self):
        p = NLDrawingParser()
        assert p.detect_shape("narysuj gwiazdkę") == "star"
        assert p.detect_shape("draw a circle") == "circle"
        assert p.detect_shape("unknown shape") == "circle"

    def test_detect_color(self):
        p = NLDrawingParser()
        assert p.detect_color("czerwone koło") == "#FF0000"
        assert p.detect_color("blue star") == "#0000FF"
        assert p.detect_color("no color") == "#000000"

    def test_size_params(self):
        p = NLDrawingParser()
        cmds = p.parse("narysuj duże koło")
        shapes = [c for c in cmds if isinstance(c, DrawShape)]
        assert shapes[0].params.get("size_multiplier") == 1.5

    def test_star_points_param(self):
        p = NLDrawingParser()
        cmds = p.parse("narysuj gwiazdę z 8 ramion")
        shapes = [c for c in cmds if isinstance(c, DrawShape)]
        assert shapes[0].params.get("points_count") == 8

    def test_flower_petals_param(self):
        p = NLDrawingParser()
        cmds = p.parse("narysuj kwiat z 8 płatków")
        shapes = [c for c in cmds if isinstance(c, DrawShape)]
        assert shapes[0].params.get("petals") == 8


# ── SVGRenderer ───────────────────────────────────────────────────────────


class TestSVGRenderer:
    def test_render_circle(self):
        from nlp2cmd.skills.drawing.renderers.svg import SVGRenderer

        async def _test():
            r = SVGRenderer()
            await r.init_canvas(800, 600)
            await r.set_color("#FF0000")
            pts = CircleGenerator().generate(400, 300, 100)[0]
            await r.draw_path(pts, color="#FF0000")
            svg = r.to_svg()
            assert "<svg" in svg
            assert "FF0000" in svg
            assert "<path" in svg

        asyncio.get_event_loop().run_until_complete(_test())

    def test_render_shape_event(self):
        from nlp2cmd.skills.drawing.renderers.svg import SVGRenderer

        async def _test():
            r = SVGRenderer()
            await r.init_canvas(800, 600)
            event = ShapeDrawn(
                shape_type="circle",
                points=CircleGenerator().generate(400, 300, 100),
                color="#0000FF",
            )
            await r.draw_shape(event)
            svg = r.to_svg()
            assert "0000FF" in svg

        asyncio.get_event_loop().run_until_complete(_test())

    def test_screenshot_saves_file(self):
        from nlp2cmd.skills.drawing.renderers.svg import SVGRenderer

        async def _test():
            r = SVGRenderer()
            await r.init_canvas(800, 600)
            pts = [(100, 100), (200, 200), (100, 200), (100, 100)]
            await r.draw_path(pts, color="#FF0000")
            with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
                path = f.name
            result = await r.screenshot(path)
            assert result is not None
            content = Path(result).read_text()
            assert "<svg" in content
            Path(result).unlink()

        asyncio.get_event_loop().run_until_complete(_test())

    def test_clear_removes_elements(self):
        from nlp2cmd.skills.drawing.renderers.svg import SVGRenderer

        async def _test():
            r = SVGRenderer()
            await r.init_canvas(800, 600)
            await r.draw_path([(0, 0), (100, 100)], color="#FF0000")
            assert "<path" in r.to_svg()
            await r.clear()
            assert "<path" not in r.to_svg()

        asyncio.get_event_loop().run_until_complete(_test())


# ── DrawingSkill Facade ───────────────────────────────────────────────────


class TestDrawingSkill:
    def test_init_and_draw(self):
        skill = DrawingSkill()
        skill.init_canvas(800, 600)
        skill.draw("circle", color="#FF0000")
        assert skill.event_count == 2
        shapes = skill.get_shapes()
        assert len(shapes) == 1
        assert shapes[0]["shape_type"] == "circle"

    def test_execute_nl_polish(self):
        skill = DrawingSkill()
        skill.init_canvas(800, 600)
        events = skill.execute_nl("narysuj czerwone koło")
        assert len(events) == 2  # SetColor + DrawShape

    def test_execute_nl_english(self):
        skill = DrawingSkill()
        skill.init_canvas(800, 600)
        events = skill.execute_nl("draw a blue star")
        assert len(events) == 2

    def test_multiple_shapes(self):
        skill = DrawingSkill()
        skill.init_canvas(800, 600)
        skill.draw("circle", color="red")
        skill.draw("star", color="blue")
        skill.draw("house", color="green")
        assert skill.get_state()["shapes_count"] == 3

    def test_clear(self):
        skill = DrawingSkill()
        skill.init_canvas(800, 600)
        skill.draw("circle")
        skill.clear()
        state = skill.get_state()
        assert state["shapes_count"] == 0
        assert state["is_blank"]

    def test_get_history(self):
        skill = DrawingSkill()
        skill.init_canvas(800, 600)
        skill.draw("circle")
        history = skill.get_history()
        assert len(history) == 2

    def test_available_shapes(self):
        shapes = DrawingSkill.available_shapes()
        assert "circle" in shapes
        assert "star" in shapes
        assert len(shapes) >= 16

    def test_save_and_load_session(self):
        skill = DrawingSkill()
        skill.init_canvas(800, 600)
        skill.draw("circle", color="#FF0000")
        skill.draw("star", color="#0000FF")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        skill.save_session(path)
        loaded = DrawingSkill.load_session(path)
        assert loaded.event_count == 3
        assert loaded.get_state()["shapes_count"] == 2
        Path(path).unlink()

    def test_render_svg(self):
        from nlp2cmd.skills.drawing.renderers.svg import SVGRenderer

        async def _test():
            skill = DrawingSkill()
            skill.init_canvas(800, 600)
            skill.draw("circle", color="#FF0000")
            skill.draw("star", color="#0000FF")

            renderer = SVGRenderer()
            await skill.render(renderer)
            svg = renderer.to_svg()
            assert "<svg" in svg
            assert "FF0000" in svg
            assert "0000FF" in svg

        asyncio.get_event_loop().run_until_complete(_test())

    def test_detect_shape(self):
        skill = DrawingSkill()
        assert skill.detect_shape("narysuj dom") == "house"
        assert skill.detect_shape("draw circle") == "circle"

    def test_detect_color(self):
        skill = DrawingSkill()
        assert skill.detect_color("czerwony") == "#FF0000"
        assert skill.detect_color("blue") == "#0000FF"

    def test_set_color_with_name(self):
        skill = DrawingSkill()
        event = skill.set_color("czerwony")
        assert isinstance(event, ColorChanged)

    def test_repr(self):
        skill = DrawingSkill()
        skill.init_canvas(800, 600)
        r = repr(skill)
        assert "DrawingSkill" in r
        assert "800x600" in r
