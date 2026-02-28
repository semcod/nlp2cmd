import re

file_path = "/home/tom/github/wronai/nlp2cmd/src/nlp2cmd/pipeline_runner.py"
with open(file_path, "r") as f:
    content = f.read()

# There are duplicate blocks for wait_for_canvas and others at the end of the file. 
# We should only keep one definition for action in execute_plan_step. Let's see what else is there.
