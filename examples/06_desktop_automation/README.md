# Desktop GUI Automation Examples

Control desktop applications on any OS via noVNC + Playwright.

## Prerequisites

```bash
# Start the desktop environment
docker compose -f docker/novnc/docker-compose.yml up -d

# Wait ~10s, then watch live at:
# http://localhost:6080/vnc.html?autoconnect=true
```

## Examples

| Script | Description |
|--------|-------------|
| `example_terminal.py` | Open terminal, run shell commands |
| `example_calculator.py` | Open calculator, do math |
| `example_text_editor.py` | Open editor, write document, save |
| `example_multi_app.py` | Full workflow: terminal → calc → editor → browser |

## Session Logs

Each example generates a Markdown report with inline base64 thumbnails:

```bash
python3 examples/06_desktop_automation/example_terminal.py
# → examples/06_desktop_automation/terminal_session.md
```

Open the `.md` file in any Markdown viewer to see screenshots inline.

## Stop

```bash
docker compose -f docker/novnc/docker-compose.yml down
```
