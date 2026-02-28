import asyncio
from nlp2cmd.automation.complex_planner import ComplexCommandPlanner

async def test():
    planner = ComplexCommandPlanner()
    plan = await planner.plan("narysuj zająca")
    print(plan.source)
    for step in plan.steps:
        print(step.action)

if __name__ == "__main__":
    asyncio.run(test())
