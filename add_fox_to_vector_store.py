import sys
from nlp2cmd.automation.vector_store import get_vector_store, DrawingPattern
from nlp2cmd.automation.drawing_blueprints import _fox_steps

store = get_vector_store()
steps = _fox_steps()
steps_dicts = [
    {"action": step.action, "params": step.params, "description": step.description}
    for step in steps
]

fox_pattern = DrawingPattern(
    name="fox",
    description="lis fox lisek zwierzę animal orange head body tail ears paws",
    category="animal",
    steps=steps_dicts,
    tags=["fox", "lis", "animal", "zwierzę", "orange"],
    complexity=5,
    source="manual"
)

store.add_pattern(fox_pattern)
print("Added fox to vector store")
