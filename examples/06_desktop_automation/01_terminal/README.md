# 01 — Terminal: Run Shell Commands

Open a terminal on the remote desktop and execute system commands.

## What it does

1. Opens XFCE terminal (Ctrl+Alt+T)
2. Runs `uname -a` (kernel info)
3. Runs `whoami` (current user)
4. Runs `df -h /` (disk usage)
5. Runs `free -h` (memory)

## Run

```bash
cd examples/06_desktop_automation/01_terminal
bash run.sh
```

## Output

After running, check `logs/session.md` for the Markdown log with screenshots.
