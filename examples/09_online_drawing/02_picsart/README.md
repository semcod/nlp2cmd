# 02 — Picsart: Paint Patterns with Brushes

Paint patterns on [Picsart Draw](https://picsart.com/draw) — a feature-rich online drawing tool.

## How It Works

1. **DrawingSkill** generates mathematical patterns (spiral, grid, waves, flower)
2. **PlaywrightRenderer** draws them via mouse movements on the browser canvas
3. **Intelligent fallback**: If Picsart is unavailable (login required, blocked), automatically falls back to Kleki → Excalidraw → draw.chat
4. **Aggressive popup handling**: Picsart shows multiple popup chains (cookies, login prompts, feature tours)

## Usage

### New Way (Recommended) — Using run.sh

```bash
# From examples/09_online_drawing/ directory:

# Default: draw a spiral in blue
./run.sh 02_picsart

# Custom patterns
./run.sh 02_picsart --pattern spiral --color red
./run.sh 02_picsart --pattern grid --color green
./run.sh 02_picsart --pattern waves --color purple
./run.sh 02_picsart --pattern flower --color "#ff6600"

# Headless + verbose
./run.sh 02_picsart --pattern spiral --headless -v
```

### Traditional Way — Direct Python

```bash
cd 02_picsart

# Default: draw a spiral in blue
python3 run.py

# Custom patterns
python3 run.py --pattern spiral --color red
python3 run.py --pattern grid --color green
python3 run.py --pattern waves --color purple
python3 run.py --pattern flower --color "#ff6600"

# Headless + verbose
python3 run.py --pattern spiral --headless -v
```

## Available Patterns

| Pattern  | Description |
|----------|-------------|
| spiral   | Archimedean spiral from center outward |
| grid     | Rectangular grid of lines |
| waves    | Sinusoidal wave pattern |
| flower   | Petal-based flower shape |

## Output Files

```
02_picsart/
├── run.py              # Main script
├── README.md           # This file
├── logs/               # Structured logs
│   ├── 02_picsart_YYYYMMDD_HHMMSS.log
│   └── 02_picsart_YYYYMMDD_HHMMSS.json
└── screenshots/        # Result screenshots + metadata
    ├── picsart_spiral_blue.png
    └── picsart_spiral_blue.meta.json
```

## Known Issues

- **Login required**: Picsart sometimes requires login for the draw tool. The script automatically falls back to alternative drawing sites.
- **Heavy JavaScript**: Picsart loads ~10MB of JS, so canvas may take 5-10s to appear.
- **Headless detection**: Picsart may detect headless browsers. Fallback to other sites handles this.

## Fallback Chain

```
picsart.com/draw → picsart.com/pl/draw → picsart.com/en/draw
    ↓ (if all fail)
kleki.com → excalidraw.com → draw.chat
```

## Platform Support

| Platform | Status | Notes |
|----------|--------|-------|
| Linux    | ✓      | May need fallback if Picsart blocks |
| macOS    | ✓      | Full support |
| Windows  | ✓      | Full support |
| Docker   | ✓      | Likely uses fallback site |
