import re

file_path = "/home/tom/github/wronai/nlp2cmd/src/nlp2cmd/pipeline_runner.py"
with open(file_path, "r") as f:
    content = f.read()

# Make sure all drawing commands use the fallback window.__nlp2cmd_foreground if window.colors isn't there
content = content.replace("window.colors && window.colors.foreground", "window.__nlp2cmd_foreground || (window.colors && window.colors.foreground)")
content = content.replace("ctx.fillStyle = window.colors.foreground;", "ctx.fillStyle = window.__nlp2cmd_foreground || window.colors.foreground;")
content = content.replace("ctx.strokeStyle = window.colors.foreground;", "ctx.strokeStyle = window.__nlp2cmd_foreground || window.colors.foreground;")

with open(file_path, "w") as f:
    f.write(content)
print("Updated color fallbacks")
