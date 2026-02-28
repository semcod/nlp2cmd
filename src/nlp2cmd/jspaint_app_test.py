import sys
from nlp2cmd.pipeline_runner import PipelineRunner
from nlp2cmd.automation.action_planner import ActionPlan, ActionStep

def run():
    runner = PipelineRunner(headless=False)
    plan = ActionPlan(
        query="test jspaint",
        steps=[
            ActionStep(action="navigate", params={"url": "https://jspaint.app"}),
            ActionStep(action="wait_for_canvas", params={}),
            ActionStep(action="set_color", params={"color": "#ff0000"}),
            ActionStep(action="draw_filled_circle", params={"radius": 50, "offset": [0, 0]}),
            ActionStep(action="draw_filled_circle", params={"radius": 20, "offset": [100, 100]}),
            ActionStep(action="wait", params={"ms": 2000})
        ]
    )
    result = runner.execute_action_plan(plan)
    print("Result:", result.success)

if __name__ == "__main__":
    run()
