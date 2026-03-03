# 09 — Online Drawing Tools (No Login Required)

Browser automation examples for drawing on free online tools — no registration needed.

## Tools Supported

- **draw.chat** — Whiteboard with shapes, text, and image annotation
- **Picsart Draw** — Advanced drawing with brushes, layers, colors
- **Tutkit** — Simple painting with brushes and erasers

## Examples

### 01 — draw.chat: Draw shapes on whiteboard

```bash
python3 01_draw_chat_shapes.py
python3 01_draw_chat_shapes.py --shape star --color blue
```

### 02 — Picsart: Paint with brushes

```bash
python3 02_picsart_painting.py
python3 02_picsart_painting.py --brush round --color red --pattern spiral
```

### 03 — Multi-tool drawing with LLM-guided adaptation

```bash
python3 03_adaptive_drawing.py --query "narysuj dom z czerwonym dachem"
python3 03_adaptive_drawing.py --query "draw a blue circle and green triangle"
```

## Requirements

```bash
pip install playwright
playwright install chromium
```

## How Adaptive Learning Works

Each example uses the `LLMRouter` with `AdaptiveLearner`:

1. **First run**: Router tries remote LLM for drawing plan → falls back to local if no credit
2. **Learning**: Records which models work, which fail (credit/timeout/rate limit)
3. **Evolution**: Next run skips known-bad models, routes directly to working ones
4. **Persistence**: Learned patterns saved to `~/.nlp2cmd/adaptive_routing.json`
