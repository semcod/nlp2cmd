import re

file_path = "/home/tom/github/wronai/nlp2cmd/src/nlp2cmd/pipeline_runner.py"
with open(file_path, "r") as f:
    content = f.read()

# Replace all occurrences of document.querySelector('canvas') 
# with (document.querySelector('.main-canvas') || document.querySelector('canvas'))
content = content.replace("document.querySelector('canvas')", "(document.querySelector('.main-canvas') || document.querySelector('canvas'))")

# Wait, there's another problem. We should raise exceptions in Python when JS fails
# Instead of `_debug(f"Draw... error: {e}")` we should raise an exception so it is logged as error!
content = re.sub(r'_debug\(f"([a-zA-Z\s]+) error: \{e\}"\)', r'raise RuntimeError(f"\1 error: {e}")', content)
content = re.sub(r'_debug\(f"Tool selection error: \{e\}"\)', r'raise RuntimeError(f"Tool selection error: {e}")', content)
content = re.sub(r'_debug\(f"Color set error: \{e\}"\)', r'raise RuntimeError(f"Color set error: {e}")', content)

with open(file_path, "w") as f:
    f.write(content)
print("Updated canvas selectors and error handling")
