# 01 — draw.chat: Draw Shapes on Whiteboard

Draw geometric shapes on [draw.chat](https://draw.chat) — a free online whiteboard requiring no login.

## How It Works

1. **DrawingSkill** (CQRS + Event Sourcing) generates a mathematical drawing plan
2. **PlaywrightRenderer** executes it on the browser canvas via mouse movements
3. **Intelligent URL discovery** tries multiple draw.chat paths if the primary URL fails
4. **Popup dismissal** handles cookie banners, GDPR notices automatically

## Usage

### New Way (Recommended) — Using run.sh

```bash
# From examples/09_online_drawing/ directory:

# Default: draw a house in blue
./run.sh 01_draw_chat

# Custom shape and color
./run.sh 01_draw_chat --shape star --color red
./run.sh 01_draw_chat --shape circle --color "#00ff00"
./run.sh 01_draw_chat --shape flower --color purple

# Headless mode (no visible browser)
./run.sh 01_draw_chat --shape house --color blue --headless

# Verbose mode (DOM inspection, selector matching)
./run.sh 01_draw_chat -v
```

### Traditional Way — Direct Python

```bash
cd 01_draw_chat

# Default: draw a house in blue
python3 run.py

# Custom shape and color
python3 run.py --shape star --color red
python3 run.py --shape circle --color "#00ff00"
python3 run.py --shape flower --color purple

# Headless mode (no visible browser)
python3 run.py --shape house --color blue --headless

# Verbose mode (DOM inspection, selector matching)
python3 run.py -v
```

## Available Shapes

circle, star, house, heart, flower, spiral, grid, wave, triangle, rectangle, line, dots, ellipse

## Output Files

```
01_draw_chat/
├── run.py              # Main script
├── README.md           # This file
├── logs/               # Structured logs (human-readable + JSON)
│   ├── 01_draw_chat_YYYYMMDD_HHMMSS.log
│   └── 01_draw_chat_YYYYMMDD_HHMMSS.json
└── screenshots/        # Result screenshots + metadata
    ├── draw_chat_house_blue.png
    └── draw_chat_house_blue.meta.json
```

## Known Issues

- **draw.chat URL changes**: The site sometimes moves pages between `/pl/index.html` and `/pl/whiteboard.html`. The URL discovery handles this automatically.
- **Canvas not visible**: Some draw.chat pages load canvas lazily. The health check waits up to 5s for canvas visibility.
- **Cookie banners**: draw.chat shows GDPR banners for EU users. These are dismissed automatically.

## Platform Support

| Platform | Status | Notes |
|----------|--------|-------|
| Linux    | ✓      | Full support via Playwright Chromium |
| macOS    | ✓      | Full support |
| Windows  | ✓      | Full support |
| Docker   | ✓      | Requires `--headless` flag |

## Requirements

```bash
pip install playwright
playwright install chromium
```
