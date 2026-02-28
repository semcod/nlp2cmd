import sys

file_path = "/home/tom/github/wronai/nlp2cmd/src/nlp2cmd/pipeline_runner.py"
with open(file_path, "r") as f:
    content = f.read()

# Let's add wait action back before login
new_wait = """
        elif action == "wait":
            ms = int(params.get("ms", 1000))
            page.wait_for_timeout(ms)
"""

if 'elif action == "login":' in content:
    content = content.replace('elif action == "login":', new_wait + '\n        elif action == "login":')
    with open(file_path, "w") as f:
        f.write(content)
    print("Added wait back")
else:
    print("Login not found")
