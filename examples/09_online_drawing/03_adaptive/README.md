# 03 — Adaptive Drawing: LLM-Guided with Learning

Full NLP2CMD adaptive learning pipeline — takes a natural language drawing command
(Polish or English), routes to LLM for plan generation, learns from failures,
executes via Playwright, and verifies with vision model.

## How It Works

```
Natural Language → NL Parser (shape/color detection)
       ↓
   LLM Router → Generate drawing plan (JSON)
       ↓          ↓ failure → adaptive learner remembers
   DrawingSkill → Event Sourcing (CQRS commands/events)
       ↓
   PlaywrightRenderer → Mouse movements on browser canvas
       ↓
   Vision Model → Verify result (optional)
       ↓
   Adaptive Learner → Save what worked for next run
```

## Usage

### New Way (Recommended) — Using run.sh

```bash
# From examples/09_online_drawing/ directory:

# Quick draw with natural language
./run.sh draw "narysuj dom z czerwonym dachem"
./run.sh draw "draw a blue star"
./run.sh draw "purple butterfly" --target jspaint

# Run with specific example ID
./run.sh 03_adaptive --query "narysuj dom z czerwonym dachem"
./run.sh 03_adaptive --query "namaluj niebieskie koło"
./run.sh 03_adaptive --query "draw a green triangle" --target jspaint

# Headless + verbose
./run.sh 03_adaptive --query "draw a star" --headless -v
```

### Traditional Way — Direct Python

```bash
cd 03_adaptive

# Polish commands
python3 run.py --query "narysuj dom z czerwonym dachem"
python3 run.py --query "namaluj niebieskie koło"
python3 run.py --query "namaluj kwiat z 6 płatkami"

# English commands
python3 run.py --query "draw a blue star"
python3 run.py --query "draw a green triangle"

# Different targets (available: jspaint, excalidraw, kleki, draw.chat)
python3 run.py --query "draw a circle" --target jspaint
python3 run.py --query "draw a house" --target excalidraw
python3 run.py --query "draw a spiral" --target kleki

# Headless + no vision validation
python3 run.py --query "draw a star" --headless --no-vision -v
```

## Adaptive Learning

| Run | Behavior |
|-----|----------|
| 1st | Tries remote LLM → if credit exhausted, falls back to local Ollama |
| 2nd | Skips known-bad remote models, goes directly to working ones |
| 3rd+ | Stabilized routing — uses fastest working model |

Learned patterns persist to `~/.nlp2cmd/adaptive_routing.json`.

## Fallback Chain

If the target site is unavailable:
```
target → all other known sites (draw.chat, jspaint, excalidraw, kleki, picsart)
```

## Output Files

```
03_adaptive/
├── run.py              # Main script
├── README.md           # This file
├── logs/               # Structured logs (human-readable + JSON)
│   ├── 03_adaptive_YYYYMMDD_HHMMSS.log
│   └── 03_adaptive_YYYYMMDD_HHMMSS.json
└── screenshots/        # Result screenshots + session + metadata
    ├── adaptive_house_FF0000_draw_chat.png
    ├── adaptive_house_FF0000_draw_chat.meta.json
    └── adaptive_house_session.json
```

## Known Issues

- **LLM not installed**: Works fine without LLM — falls back to DrawingSkill NL parser
- **Vision model unavailable**: Verification is optional, skipped gracefully
- **Remote models exhausted**: Adaptive learner routes to local Ollama automatically
- **Target site down**: Falls back through all known drawing sites

## Platform Support

All platforms supported via Playwright. LLM features require either:
- Internet access (OpenRouter API) or
- Local Ollama with qwen2.5-coder models
