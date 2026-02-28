import os
import sys
from nlp2cmd.pipeline_runner import PipelineRunner
from nlp2cmd.automation.action_planner import ActionPlan, ActionStep

def test_runner():
    runner = PipelineRunner(headless=False, enable_history=False, video_fmt="webm")
    plan = ActionPlan(
        query="test",
        steps=[
            ActionStep(action="open_firefox_tab", params={"url": "https://example.com"}),
            ActionStep(action="desktop_wait", params={"ms": 100}),
            ActionStep(action="echo", params={"message": "done"}),
        ]
    )
    res = runner.execute_action_plan(plan, dry_run=False, confirm=False)
    print(res.success)

if __name__ == '__main__':
    test_runner()
