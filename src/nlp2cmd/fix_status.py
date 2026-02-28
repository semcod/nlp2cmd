import re

file_path = "/home/tom/github/wronai/nlp2cmd/src/nlp2cmd/pipeline_runner.py"
with open(file_path, "r") as f:
    content = f.read()

# Fix desktop success evaluation
content = content.replace(
    'success=(not plan_aborted and all(r["status"] != "failed" for r in results_log)),',
    'success=(not plan_aborted and all(r["status"] not in ("failed", "error") for r in results_log)),'
)

# Fix Playwright success evaluation
content = content.replace(
    'success=all(r["status"] != "failed" for r in results_log),',
    'success=all(r["status"] not in ("failed", "error") for r in results_log),'
)

with open(file_path, "w") as f:
    f.write(content)
