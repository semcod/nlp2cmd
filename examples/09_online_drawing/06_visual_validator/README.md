# 06 — Visual Validator: Vision LLM Drawing Verification

Validate drawings using vision LLM models. Draw a shape, take a screenshot, and ask a vision model whether it matches the requested description — with specific correction suggestions.

## How It Works

1. **DrawingSkill** generates the shape on jspaint.app
2. **Screenshot** captures the result
3. **VisualValidator** sends the image to a vision model (Gemini 2.5 Pro / Qwen2.5-VL / llava)
4. Model returns: what it sees, match verdict, confidence, and per-issue corrections
5. Optionally: **CorrectionEngine** applies fixes and re-validates

## Usage

### New Way (Recommended) — Using run.sh

```bash
# From examples/09_online_drawing/ directory:

# Draw and validate a red star
./run.sh 06_visual_validator --shape star --color red

# Validate with custom description
./run.sh 06_visual_validator --shape butterfly --description "purple butterfly with wings"

# Validate an existing screenshot
./run.sh 06_visual_validator --screenshot path/to/image.png --description "red star"

# Draw, validate, and auto-correct
./run.sh 06_visual_validator --shape house --color brown --correct

# Run demo with 5 scenarios
./run.sh 06_visual_validator --demo

# Headless mode
./run.sh 06_visual_validator --shape rocket --color blue --headless
```

### Traditional Way — Direct Python

```bash
cd 06_visual_validator

# Draw and validate a red star
python3 run.py --shape star --color red

# Validate with custom description
python3 run.py --shape butterfly --description "purple butterfly with wings"

# Validate an existing screenshot
python3 run.py --screenshot path/to/image.png --description "red star"

# Draw, validate, and auto-correct
python3 run.py --shape house --color brown --correct

# Run demo with 5 scenarios
python3 run.py --demo

# Headless mode
python3 run.py --shape rocket --color blue --headless
```

## Validation Output

```
📊 Validation Report
============================================================
   Shape:       star
   Color:       red
   Description: red star
   Verdict:     correct
   Confidence:  92%
   Model:       gemini-2.5-pro

   👁️ What the model sees:
      A five-pointed star drawn in red on a white canvas

   🔧 Corrections needed (0):
============================================================
```

## Verdicts

| Verdict | Icon | Meaning |
|---------|------|---------|
| correct | ✅ | Drawing matches description |
| partial | ⚠️ | Some elements match, some don't |
| wrong | ❌ | Drawing doesn't match at all |
| empty | 🔲 | Canvas is blank |
| error | 💥 | Validation model failed |

## Output Files

```
06_visual_validator/
├── run.py              # Main script
├── README.md           # This file
├── logs/               # JSON validation reports
│   └── validation_star_red.json
└── screenshots/        # Validated screenshots
    └── validate_star_red.png
```

## Requirements

```bash
pip install playwright
playwright install chromium
# Vision models (at least one):
#   ollama pull qwen2.5vl:7b   (local, free)
#   ollama pull llava:7b        (local, free)
#   OPENROUTER_API_KEY for Gemini 2.5 Pro (remote, paid)
```
