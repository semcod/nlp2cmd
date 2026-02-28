import re

file_path = "/home/tom/github/wronai/nlp2cmd/src/nlp2cmd/automation/drawing_blueprints.py"
with open(file_path, "r") as f:
    content = f.read()

content = content.replace(r"\b(?:lis|fox|liska|liskiem|lisek)\b", r"\b(?:lis|lisa|fox|liska|liskiem|lisek)\b")

with open(file_path, "w") as f:
    f.write(content)
print("Fixed fox regex")
