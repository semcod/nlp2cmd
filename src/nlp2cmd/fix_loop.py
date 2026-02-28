import re

file_path = "/home/tom/github/wronai/nlp2cmd/src/nlp2cmd/pipeline_runner.py"
with open(file_path, "r") as f:
    lines = f.readlines()

new_lines = []
in_playwright_try = False
skip_lines = 0

for i, line in enumerate(lines):
    if skip_lines > 0:
        skip_lines -= 1
        continue
    
    new_lines.append(line)

with open(file_path, "w") as f:
    f.writelines(new_lines)
