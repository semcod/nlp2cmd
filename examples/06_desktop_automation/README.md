# Desktop GUI Automation Examples

Control desktop applications via `nlp2cmd --source novnc://` bash commands.  
Each example is a **bash script** with `nlp2cmd` CLI calls — no Python needed.  
Every run generates a **Markdown log with inline screenshots** in `logs/`.

## Prerequisites

```bash
# Start the desktop environment
docker compose -f docker/novnc/docker-compose.yml up -d
# Wait ~10s for XFCE to start
# Watch live: http://localhost:6080/vnc.html?autoconnect=true
```

## Examples

| Folder | What it does | Command |
|--------|-------------|---------|
| `01_terminal/` | Open terminal, run shell commands | `bash 01_terminal/run.sh` |
| `02_calculator/` | Open calculator, do math | `bash 02_calculator/run.sh` |
| `03_text_editor/` | Write a document, save it | `bash 03_text_editor/run.sh` |
| `04_multi_app/` | Full workflow: 5 apps in sequence | `bash 04_multi_app/run.sh` |

## How it works

Each `run.sh` calls `nlp2cmd --source novnc://localhost:6080 --run --log-dir ./logs`:

```bash
nlp2cmd --source novnc://localhost:6080 --run --log-dir ./logs \
    -q "open terminal"
nlp2cmd --source novnc://localhost:6080 --run --log-dir ./logs \
    -q "type uname -a"
nlp2cmd --source novnc://localhost:6080 --run --log-dir ./logs \
    -q "press Enter"
```

After running, check `logs/session.md` for the Markdown report with screenshots.

## Stop

```bash
docker compose -f docker/novnc/docker-compose.yml down
```
