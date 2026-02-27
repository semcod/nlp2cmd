# Desktop GUI Automation via noVNC

**Status:** Experimental (v1.0.89) · **Date:** 2026-02-27

---

## Overview

NLP2CMD can now control **desktop GUI applications** on any OS — not just web pages.
Using VNC/noVNC protocol, Playwright connects to a full Linux desktop running inside
Docker and controls it via natural language commands.

```
User: "otwórz kalkulator i policz 42 * 137"
  → NLP2CMD detects intent: open_app + type_text
  → Generates desktop_dql.v1 actions: Alt+F2 → type "galculator" → Enter → type "42*137" → Enter
  → Playwright executes via noVNC websocket
  → Screenshot + optional video recording
```

## Architecture

```
User (NL query)
    ↓
NLP2CMD CLI (--run --dsl desktop)
    ↓
DesktopAdapter
    ↓ generates desktop_dql.v1 JSON
PipelineRunner
    ↓ executes via Playwright
noVNC (websocket) ←→ VNC Server (tigervnc)
    ↓
Linux Desktop (XFCE in Docker)
    ↓
GUI Applications (terminal, calculator, editor, browser, ...)
```

## Quick Start

### 1. Start the Desktop Environment

```bash
docker compose -f docker/novnc/docker-compose.yml up -d
# Wait ~15s for desktop to initialize
```

### 2. Watch Live (optional)

Open in browser: **http://localhost:6080/vnc.html?autoconnect=true&password=nlp2cmd**

### 3. Run Demo

```bash
# Basic demo — opens apps, types text, takes screenshots
python3 docker/novnc/demos/demo_desktop_gui.py

# With video recording
python3 docker/novnc/demos/demo_desktop_gui.py --record

# Headless (no visible browser)
python3 docker/novnc/demos/demo_desktop_gui.py --headless
```

### 4. Use with NLP2CMD CLI (future)

```bash
# Open calculator
nlp2cmd --run --dsl desktop "otwórz kalkulator i policz 2+2"

# Open terminal and run command
nlp2cmd --run --dsl desktop "otwórz terminal i sprawdź dyski"

# Write a document
nlp2cmd --run --dsl desktop "otwórz edytor tekstu i napisz raport o systemie"
```

## Supported Intents

| Intent | Keywords (PL/EN) | Example |
|--------|-------------------|---------|
| `open_app` | otwórz, uruchom, open, launch | "otwórz kalkulator" |
| `type_text` | wpisz, napisz, type, write | "wpisz Hello World" |
| `click` | kliknij, naciśnij, click, press | "kliknij OK" |
| `keyboard_shortcut` | skrót, ctrl+, alt+ | "naciśnij Ctrl+S" |
| `screenshot` | zrzut ekranu, screenshot | "zrób zrzut ekranu" |
| `close_app` | zamknij, close, quit | "zamknij aplikację" |
| `navigate_menu` | menu, przejdź | "przejdź do menu Plik" |

## Supported Applications

| App | Launch Command | Keywords |
|-----|---------------|----------|
| Terminal | `xfce4-terminal` | terminal, konsola |
| Calculator | `galculator` | calculator, kalkulator |
| Text Editor | `mousepad` | editor, edytor, notatnik |
| File Manager | `thunar` | file manager, menedżer plików |
| Browser | `firefox` | browser, przeglądarka, firefox |
| Settings | `xfce4-settings-manager` | settings, ustawienia |

## Cross-OS Support

| Protocol | OS | Status |
|----------|-----|--------|
| **noVNC** (Docker) | Linux | ✅ Working |
| **noVNC** (remote) | Any with VNC server | 🔜 Planned |
| **RDP** via xfreerdp | Windows | 🔜 Planned |
| **VNC** direct | macOS (Screen Sharing) | 🔜 Planned |

## Video Recording

```bash
# Record 30s of demo inside Docker
docker exec nlp2cmd-desktop bash -c \
  "ffmpeg -f x11grab -video_size 1280x800 -framerate 10 \
   -i :1 -t 30 -c:v libx264 -preset ultrafast \
   /home/nlp2cmd/recordings/demo.mp4"

# Copy recording to host
docker cp nlp2cmd-desktop:/home/nlp2cmd/recordings/demo.mp4 ./demo.mp4
```

## Docker Environment

- **Base:** Ubuntu 22.04
- **Desktop:** XFCE4 (lightweight)
- **VNC:** TigerVNC
- **noVNC:** websockify + novnc
- **Resolution:** 1280x800 (configurable)
- **Password:** nlp2cmd (configurable)

## Files

```
docker/novnc/
├── Dockerfile              # Desktop environment image
├── docker-compose.yml      # Docker Compose setup
├── start-vnc.sh            # VNC + noVNC startup script
├── demos/
│   └── demo_desktop_gui.py # Demo: open apps, type, screenshot, record
└── recordings/             # Screenshots and videos (gitignored)

src/nlp2cmd/adapters/
└── desktop.py              # DesktopAdapter (desktop_dql.v1 DSL)
```
