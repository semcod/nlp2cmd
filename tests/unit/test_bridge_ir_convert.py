from pact_ir import PlanStep, TargetKind

from nlp2cmd.bridge.ir_convert import plan_step_to_action_ir


def test_shell_step_to_action_ir():
    step = PlanStep(
        id="s1",
        action="shell_find",
        target_kind=TargetKind.SHELL,
        dsl='find . -name "*.py"',
        params={"path": "."},
    )
    ir = plan_step_to_action_ir(step, query="find py", confidence=0.9)
    assert ir.dsl_kind == "shell"
    assert ir.dsl == 'find . -name "*.py"'
    assert ir.action_id == "shell_find"


def test_browser_step_to_action_ir():
    step = PlanStep(
        id="s1",
        action="navigate",
        target_kind=TargetKind.BROWSER,
        dsl='{"format":"dom_dql.v1","url":"https://example.com"}',
        params={"url": "https://example.com"},
    )
    ir = plan_step_to_action_ir(step)
    assert ir.dsl_kind == "dom"
    assert ir.metadata["dom_action"] == "navigate"
