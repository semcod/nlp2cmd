# 09 — Online Drawing Tools (No Login Required)

Browser automation examples for drawing on free online tools — no registration needed.

Each example lives in its own folder with:
- `run.py` — main script
- `README.md` — documentation + known issues
- `logs/` — structured logs (human-readable `.log` + machine-readable `.json`)
- `screenshots/` — result screenshots + metadata

## Examples

### 01 — draw.chat: Draw Shapes on Whiteboard

```bash
cd 01_draw_chat
python3 run.py --shape house --color blue
python3 run.py --shape star --color red --headless
```

### 02 — Picsart: Paint Patterns with Brushes

```bash
cd 02_picsart
python3 run.py --pattern spiral --color red
python3 run.py --pattern grid --color green --headless
```

### 03 — Adaptive: LLM-Guided Drawing with Learning

```bash
cd 03_adaptive
python3 run.py --query "narysuj dom z czerwonym dachem"
python3 run.py --query "draw a blue star" --target jspaint
```

## Architecture

```
_run_utils.py          Shared infrastructure (logging, URL discovery, error handling)
├── ExampleRunner      Context manager — browser lifecycle + logging
├── ExampleLogger      Structured file + console logging
├── discover_working_url  Intelligent URL fallback chain
├── check_page_health  DOM health check (canvas, popups, errors)
├── dismiss_popups     Cookie/GDPR/login popup dismissal
└── DRAWING_SITES      Known drawing sites with fallback URLs

DrawingSkill           CQRS + Event Sourcing for drawing operations
├── NLDrawingParser    PL/EN natural language → drawing commands
├── CommandBus         Command dispatch + validation
├── EventStore         Immutable event log
└── ShapeRegistry      Available shape types

PlaywrightRenderer     Browser canvas rendering via mouse movements
├── init_canvas        Navigate + discover canvas element
├── set_color          Color picker / JS injection
├── draw_path          Mouse down → move → up
└── screenshot         Page screenshot
```

## Intelligent Error Handling

| Scenario | Solution |
|----------|----------|
| Site URL changed | Tries multiple URL variations automatically |
| Site returns 404 | Skips, tries next URL in chain |
| Login required | Detects, falls back to alternative site |
| Cookie banner | Dismissed automatically (PL + EN) |
| Canvas not visible | Waits up to 5s, retries with health check |
| Headless detected | Falls back to alternative site |
| LLM credit exhausted | Adaptive learner routes to local model |
| Network error | Exponential backoff retry |

## Drawing Sites Supported

| Site | Canvas | Login | Notes |
|------|--------|-------|-------|
| draw.chat | ✓ | No | Best for shapes, whiteboard |
| jspaint.app | ✓ | No | MS Paint clone, very reliable |
| Picsart Draw | ✓ | Sometimes | May require login |
| Excalidraw | ✓ | No | Hand-drawn style diagrams |
| Kleki | ✓ | No | Online paint tool |

## Requirements

```bash
pip install playwright
playwright install chromium

# Optional (for LLM-guided drawing):
pip install litellm python-dotenv
```

## Platform Support

All examples are platform-independent via Playwright:

| Platform | Headed | Headless | Docker |
|----------|--------|----------|--------|
| Linux    | ✓      | ✓        | ✓ (headless only) |
| macOS    | ✓      | ✓        | ✓ (headless only) |
| Windows  | ✓      | ✓        | ✓ (headless only) |

## How Adaptive Learning Works

1. **First run**: Router tries remote LLM for drawing plan → falls back to local if no credit
2. **Learning**: Records which models work, which fail (credit/timeout/rate limit)
3. **Evolution**: Next run skips known-bad models, routes directly to working ones
4. **Persistence**: Learned patterns saved to `~/.nlp2cmd/adaptive_routing.json`

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

## Author

Created by **Tom Sapletta** - [tom@sapletta.com](mailto:tom@sapletta.com)
