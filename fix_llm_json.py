import re

file_path = "/home/tom/github/wronai/nlp2cmd/src/nlp2cmd/automation/action_planner.py"
with open(file_path, "r") as f:
    content = f.read()

# Fix the regex for stripping markdown fences because multiline regex needs re.MULTILINE or correct flags.
# Also `json.loads` failed with "Expecting property name enclosed in double quotes" which means the LLM returned invalid JSON, maybe trailing commas or single quotes. Let's add simple cleanup.

old_strip = '''            # Strip markdown fences
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

            steps_data = json.loads(raw)'''

new_strip = '''            # Strip markdown fences
            raw = re.sub(r"^```(?:json)?\\s*", "", raw, flags=re.MULTILINE)
            raw = re.sub(r"\\s*```$", "", raw, flags=re.MULTILINE)
            
            # Basic cleanup for common LLM JSON mistakes
            raw = raw.strip()
            # If it didn't strip properly because of newlines
            if raw.startswith("```json"): raw = raw[7:]
            if raw.startswith("```"): raw = raw[3:]
            if raw.endswith("```"): raw = raw[:-3]
            raw = raw.strip()
            
            # Simple heuristic for fixing trailing commas in lists/dicts
            raw = re.sub(r",(\\s*[\\}\\]])", r"\\1", raw)

            steps_data = json.loads(raw)'''

content = content.replace(old_strip, new_strip)

with open(file_path, "w") as f:
    f.write(content)
print("Fixed JSON extraction logic")
