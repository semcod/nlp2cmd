import sys
import logging
from nlp2cmd.pipeline_runner import PipelineRunner
from nlp2cmd.automation.action_planner import ActionPlanner

def run():
    planner = ActionPlanner()
    plan = planner.decompose_sync('wejdź na jspaint.app i narysuj lisa')
    if not plan:
        print("Failed to get plan")
        return
        
    runner = PipelineRunner(headless=False)
    result = runner.execute_action_plan(plan)
    print("Result:", result.success)

if __name__ == "__main__":
    run()
