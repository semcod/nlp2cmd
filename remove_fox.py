import re

file_path = "/home/tom/github/wronai/nlp2cmd/src/nlp2cmd/automation/drawing_blueprints.py"
with open(file_path, "r") as f:
    content = f.read()

# Remove fox from OBJECT_BLUEPRINTS
content = re.sub(r'\s*\{\s*"pattern": r"\\b(?:lis\|lisa\|fox\|liska\|liskiem\|lisek)\\b",[^}]+\},', '', content)

with open(file_path, "w") as f:
    f.write(content)
print("Removed hardcoded fox blueprint")
