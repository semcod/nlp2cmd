"""Tests for ActionPlan → VQLProgram adapter."""

from nlp2cmd.automation.action_planner import ActionPlan, ActionStep
from nlp2cmd.vql.adapters.canvas_to_vql import action_plan_to_vql_program


def test_action_plan_to_vql_program_maps_draw_steps():
    plan = ActionPlan(
        query="narysuj kolo",
        source="canvas_blueprint",
        steps=[
            ActionStep("navigate", {"url": "https://jspaint.app"}),
            ActionStep("set_color", {"color": "#ff0000"}),
            ActionStep("draw_filled_circle", {"radius": 20, "offset": [100, 50]}),
            ActionStep("draw_line", {"from_offset": [0, 0], "to_offset": [10, 10]}),
        ],
    )
    program = action_plan_to_vql_program(plan)
    assert program.scene.app == "jspaint"
    assert program.scene.url == "https://jspaint.app"
    assert len(program.scene.layers) == 1
    objects = program.scene.layers[0].objects
    assert len(objects) == 2
    assert objects[0].primitives[0].shape_type == "circle"
    assert objects[0].style.color == "#ff0000"
    assert objects[0].transform.translate_x == 100
    assert program.metadata["draw_object_count"] == 2


def test_action_plan_to_vql_program_skips_non_draw():
    plan = ActionPlan(
        query="q",
        source="canvas_llm",
        steps=[
            ActionStep("screenshot", {"path": "out.png"}),
            ActionStep("set_line_width", {"width": 3}),
        ],
    )
    program = action_plan_to_vql_program(plan)
    assert program.metadata["draw_object_count"] == 0
