import sys

file_path = "/home/tom/github/wronai/nlp2cmd/src/nlp2cmd/pipeline_runner.py"
with open(file_path, "r") as f:
    lines = f.readlines()

start_dup = -1
end_dup = -1

# Find the second instance of wait_for_canvas
count = 0
for i, line in enumerate(lines):
    if line.strip() == 'elif action == "wait_for_canvas":':
        count += 1
        if count == 2:
            start_dup = i
            break

if start_dup != -1:
    for i in range(start_dup, len(lines)):
        # Stop at wait
        if line.strip() == 'elif action == "wait":':
            end_dup = i
            break

if start_dup != -1 and end_dup != -1:
    print(f"Deleting from {start_dup} to {end_dup}")
    new_lines = lines[:start_dup] + lines[end_dup:]
    with open(file_path, "w") as f:
        f.writelines(new_lines)
else:
    print(f"Could not find duplicate block bounds: {start_dup} to {end_dup}")
