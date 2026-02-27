# Desktop GUI Automation Examples

Control desktop applications via `nlp2cmd --source novnc://` bash commands.  
Each example is a **bash script** or **Python script** with `nlp2cmd` CLI calls.  
Every run generates a **Markdown log with inline screenshots** in `logs/`.

## Prerequisites

```bash
# Start the desktop environment
docker compose -f docker/novnc/docker-compose.yml up -d
# Wait ~10s for XFCE to start
# Watch live: http://localhost:6080/vnc.html?autoconnect=true

# For examples 06-09 (Python scripts):
pip install playwright httpx
playwright install chromium
export OPENROUTER_API_KEY="sk-or-v1-..."  # for CAPTCHA/LLM features
```

## Examples

| Folder | What it does | Type | Command |
|--------|-------------|------|---------|
| `01_terminal/` | Open terminal, run shell commands | bash | `bash 01_terminal/run.sh` |
| `02_calculator/` | Open calculator, do math | bash | `bash 02_calculator/run.sh` |
| `03_text_editor/` | Write a document, save it | bash | `bash 03_text_editor/run.sh` |
| `04_browser_tabs/` | Multi-tab browser management | bash | `bash 04_browser_tabs/run.sh` |
| `05_email_client/` | Thunderbird: check/compose email | bash | `bash 05_email_client/run.sh` |
| `06_env_extract/` | Extract API keys → .env | python | `python3 06_env_extract/run.py` |
| `07_canvas_drawing/` | Draw shapes on jspaint.app | python | `python3 07_canvas_drawing/run.py` |
| `08_captcha_solver/` | Solve CAPTCHAs via LLM vision | python | `python3 08_captcha_solver/run.py --url ...` |
| `09_complex_commands/` | Multi-step NL command planning | python | `python3 09_complex_commands/run.py --query ...` |

## How it works

### Bash examples (01-05): noVNC protocol

```bash
nlp2cmd --source novnc://localhost:6080 --run --log-dir ./logs \
    -q "open terminal"
nlp2cmd --source novnc://localhost:6080 --run --log-dir ./logs \
    -q "type uname -a"
nlp2cmd --source novnc://localhost:6080 --run --log-dir ./logs \
    -q "press Enter"
```

### Python examples (06-09): Playwright + LLM

```bash
# Extract API key from browser → .env
python3 06_env_extract/run.py --service openrouter --env-path .env

# Draw a ladybug on jspaint.app
python3 07_canvas_drawing/run.py --shape ladybug

# Solve CAPTCHA on a page
python3 08_captcha_solver/run.py --url "https://example.com/login"

# Plan & execute complex NL command
python3 09_complex_commands/run.py --query "wejdź na jspaint.app i narysuj biedronkę"
```

### Complex NL command examples

```bash
nlp2cmd -r "wejdź na jspaint.app i narysuj okrąg z czerwonym tłem jak biedronka"
nlp2cmd -r "otwórz Chrome, wejdź na openrouter.ai, skopiuj API key i zapisz do .env"
nlp2cmd -r "otwórz 3 taby: GitHub issues, Stack Overflow i ChatGPT"
nlp2cmd -r "w Thunderbird odpowiedz na ostatniego maila słowami 'Dziękuję'"
nlp2cmd -r "zrób screenshot ekranu i wyślij mailem do szef@firma.pl"
```

After running, check `logs/session.md` for the Markdown report with screenshots.

## Architecture

```
NL Query → Intent Router → [browser | desktop | canvas | captcha | env]
                                    ↓
              ┌─────────────────────────────────────────┐
              │       PlaywrightController              │
              │  • Mouse: click, drag, Bézier curves    │
              │  • Keyboard: type, shortcuts, combos    │
              │  • Canvas: shapes, fill, text            │
              │  • Multi-tab: create, switch, close      │
              │  • Desktop: xdotool, wmctrl             │
              └─────────────────────────────────────────┘
```

## Stop

```bash
docker compose -f docker/novnc/docker-compose.yml down
```
