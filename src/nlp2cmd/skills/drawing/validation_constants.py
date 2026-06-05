TASK_VALIDATION_PROMPT = """Analyze this screenshot of a drawing canvas.

The user's drawing task is: "{description}"

The requested objects are:
{object_list}

For EACH requested object, determine:
1. Is it visible on the canvas? (drawn/missing/wrong/partial)
2. If visible, is the color correct?
3. Any issues with shape, size, or position?

Also provide an overall scene description and match score.

Respond ONLY with JSON:
{{
  "scene_description": "A white canvas with a red star in the center and a blue circle on the left",
  "overall_match": 0.7,
  "objects": [
    {{
      "name": "star",
      "status": "drawn",
      "actual_color": "red",
      "issue": "",
      "suggestion": "",
      "confidence": 0.95
    }},
    {{
      "name": "house",
      "status": "missing",
      "actual_color": "",
      "issue": "Not visible on canvas",
      "suggestion": "Draw a house shape",
      "confidence": 0.9
    }}
  ]
}}"""

PROGRESS_CHECK_PROMPT = """Look at this screenshot of a drawing canvas.

I've been drawing objects from this task: "{description}"

Previously completed: {completed_list}
Still to do: {remaining_list}

What do you see now? Has any progress been made on the remaining items?

Respond ONLY with JSON:
{{
  "scene_description": "what you see",
  "newly_completed": ["list of newly drawn objects"],
  "still_missing": ["list of objects still not drawn"],
  "issues": ["any problems noticed"]
}}"""


# ── DrawValidationSkill ───────────────────────────────────────────────────

