import sys
from nlp2cmd.pipeline_runner import PipelineRunner
from nlp2cmd.automation.action_planner import ActionPlan, ActionStep

runner = PipelineRunner(headless=False)
plan = ActionPlan(
    query="test",
    steps=[
        ActionStep(action="desktop_wait", params={"ms": 100})
    ]
)
res = runner.execute_action_plan(plan)
print("SUCCESS:", res.success)
