# 05 — Autonomous Drawing: Full Pipeline with Fetch + Draw + Validate + Correct

The most advanced drawing example — a fully autonomous pipeline that resolves shapes from databases, generates missing ones via LLM, draws on a canvas, validates with a vision model, and self-corrects.

## How It Works

1. **NL Parser** detects shapes and colors from Polish/English description (33 built-in shapes)
2. **ObjectFetcher** searches Iconify (200k+ icons), Simple Icons, SVG Repo for unknown shapes
3. **TextToShapeEngine** generates 2D vertex data via LLM when databases fail
4. **DrawingSkill** + **PlaywrightRenderer** draws on jspaint.app
5. **VisualValidator** screenshots and validates via vision LLM (Gemini/Qwen2.5-VL/llava)
6. **CorrectionEngine** iteratively fixes issues and re-validates

## Usage

### New Way (Recommended) — Using run.sh

```bash
# From examples/09_online_drawing/ directory:

# Draw with validation using natural language
./run.sh autonomous "narysuj czerwonego kota i niebieską rybkę"
./run.sh autonomous "draw a castle with a dragon"
./run.sh autonomous "draw a star and a moon"

# Run with specific example ID
./run.sh 05_autonomous --fetch-only butterfly
./run.sh 05_autonomous --list-shapes       # 33 built-in shapes
./run.sh 05_autonomous --list-fetchable    # 44 database-mapped objects

# Skip validation
./run.sh 05_autonomous "draw a star" --no-validate

# Headless + max corrections
./run.sh 05_autonomous "narysuj zamek" --headless --max-corrections 5
```

### Traditional Way — Direct Python

```bash
cd 05_autonomous

# Draw with validation
python3 run.py "narysuj czerwonego kota i niebieską rybkę"
python3 run.py "draw a castle with a dragon"

# Fetch shape info only
python3 run.py --fetch-only butterfly
python3 run.py --fetch-only dragon

# List available shapes
python3 run.py --list-shapes       # 33 built-in shapes
python3 run.py --list-fetchable    # 44 database-mapped objects

# Skip validation
python3 run.py "draw a star" --no-validate

# Headless + max corrections
python3 run.py "narysuj zamek" --headless --max-corrections 5
```

## Shape Sources

| Priority | Source | Count | Examples |
|----------|--------|-------|----------|
| 1 | Built-in generators | 33 | car, butterfly, castle, rocket, cat, fish |
| 2 | Iconify API | 200k+ | dragon, robot, skull, crown, guitar |
| 3 | Simple Icons | 3k+ | Brand SVGs |
| 4 | SVG Repo | 500k+ | General vectors |
| 5 | LLM generation | ∞ | Any shape via text description |

## Output Files

```
05_autonomous/
├── run.py              # Main script
├── README.md           # This file
├── logs/               # Execution logs
└── screenshots/        # Initial + corrected screenshots
    ├── autonomous_initial.png
    ├── autonomous_final.png
    └── correction_N.png
```

## Validation Verdicts

| Verdict | Meaning | Action |
|---------|---------|--------|
| ✅ correct | Drawing matches description | Done |
| ⚠️ partial | Some elements correct | Correction engine fixes issues |
| ❌ wrong | Doesn't match at all | Full redraw |
| 🔲 empty | Canvas is blank | Redraw everything |
| 💥 error | Validation failed | Heuristic fallback |

## Requirements

```bash
pip install playwright
playwright install chromium
# For vision validation (optional):
# Ollama with qwen2.5vl:7b or llava:7b
# Or OpenRouter API key for Gemini 2.5 Pro
```
