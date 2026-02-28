with open("src/nlp2cmd/pipeline_runner.py", "r") as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if line.strip() == "def execute_action_plan(":
        skip = True
        new_lines.extend([
            "    def execute_action_plan(\n",
            "        self,\n",
            "        plan,\n",
            "        *,\n",
            "        dry_run: bool = False,\n",
            "        video_fmt: Optional[str] = None,\n",
            "        video_dir: Optional[str] = None,\n",
            "        confirm: bool = False,\n",
            "    ) -> RunnerResult:\n"
        ])
        continue
    
    if skip:
        if line.strip() == ") -> RunnerResult:":
            skip = False
        continue
    
    new_lines.append(line)

with open("src/nlp2cmd/pipeline_runner.py", "w") as f:
    f.writelines(new_lines)
