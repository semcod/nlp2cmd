import sys

file_path = "/home/tom/github/wronai/nlp2cmd/src/nlp2cmd/pipeline_runner.py"
with open(file_path, "r") as f:
    lines = f.readlines()

start_dup = -1
end_dup = -1

for i, line in enumerate(lines):
    if line.strip() == 'elif action == "wait_for_canvas":':
        if i > 3000:
            start_dup = i
            break

for i in range(start_dup, len(lines)):
    if line.strip() == 'elif action == "login":':
        end_dup = i
        # Since "wait" is also duplicated in one run or missing, wait until login
        break
            
if start_dup != -1 and end_dup != -1:
    print(f"Deleting from {start_dup} to {end_dup}")
    new_lines = lines[:start_dup] + lines[end_dup:]
    with open(file_path, "w") as f:
        f.writelines(new_lines)
else:
    print(f"Could not find duplicate block bounds: {start_dup} to {end_dup}")
