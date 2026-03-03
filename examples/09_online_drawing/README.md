# 09 — Online Drawing Tools (No Login Required)

Browser automation examples for drawing on free online tools — no registration needed.

## 🚀 Quick Start (New Simplified Interface)

### Using `run.sh` (Recommended)

```bash
# List all examples
./run.sh list

# Quick draw commands
./run.sh draw "red star"
./run.sh draw "blue house with green roof" --headless

# Autonomous pipeline with validation
./run.sh autonomous "cat and fish"

# Run specific examples
./run.sh 01_draw_chat
./run.sh 03_adaptive --query "draw a castle"
```

### Using `nlp2cmd examples` (Unified CLI)

```bash
# List all available examples
nlp2cmd examples list

# Run specific example with auto-configuration
nlp2cmd examples run 01_draw_chat
nlp2cmd examples run 03_adaptive --query "star" --headless

# Quick draw command
nlp2cmd examples draw "red star" --target jspaint

# Full autonomous pipeline
nlp2cmd examples autonomous "purple butterfly and green tree"
```

### Features of New Interface

- ✅ **Auto-install dependencies** — Playwright, browsers, LLM models
- ✅ **Preconfigured environments** — No manual setup needed
- ✅ **Unified error handling** — Clear messages when something missing
- ✅ **Fallback chains** — Auto-switch to working drawing sites
- ✅ **One command** — No need to `cd` into subdirectories

---

## 🧬 Evolutionary Autonomous Orchestrator — "Never Give Up" Engine

Nowy system autonomicznego uruchamiania który **nigdy się nie poddaje**.

### Core Principles

1. **Nie kończymy się błędem** — każdy problem to okazja do nauki
2. **Konsultacja z LLM** — przy każdym błędu pytamy duży model co robić
3. **Ewolucyjne uczenie** — system sam się doskonali z każdym uruchomieniem
4. **Kontekstowe naprawy** — strategia zależy od typu błędu i historii
5. **Metryki i feedback** — ciągłe monitorowanie i optymalizacja

### How It Works

```
User runs: ./run.sh draw "blue star"
    ↓
[Evolutionary Orchestrator]
    ↓
Pre-flight checks
    ↓
Execute example
    ↓
Error? → Classify error type
    ↓
Consult LLM: "What strategy should I use?"
    ↓
Execute recovery strategy
    ↓
Success? → Learn & continue
Failure? → Try fallback strategies
    ↓
Still failing? → Escalate to cloud LLM
    ↓
Generate creative workaround
    ↓
NEVER GIVE UP → Force continue if needed
```

### Recovery Strategies (Self-Improving)

| Strategy | When Used | Success Rate |
|----------|-----------|--------------|
| `INSTALL_DEPENDENCY` | Missing Playwright/browsers | Tracked |
| `SWITCH_FALLBACK` | HF_TOKEN missing, site down | Tracked |
| `CONFIGURE_ENV` | Missing env vars | Tracked |
| `CONSULT_LLM` | Unknown error | Tracked |
| `RETRY_WITH_DELAY` | Network timeout | Tracked |
| `MODIFY_ARGS` | Arg parsing error | Tracked |
| `ESCALATE_TO_CLOUD` | Multiple failures | Tracked |
| `CREATE_WORKAROUND` | Last resort | Tracked |

### Learning Database

System przechowuje bazę wiedzy w `~/.nlp2cmd/evolutionary_learning.json`:

```json
{
  "error_patterns": {
    "HF_TOKEN_ERROR": {
      "switch_fallback": {"attempts": 5, "successes": 5},
      "configure_env": {"attempts": 2, "successes": 1}
    }
  },
  "llm_insights": [...],
  "version": 1
}
```

### Example: Autonomous Recovery in Action

```bash
$ ./run.sh draw "blue house"
🧬 Using Evolutionary Autonomous Orchestrator...
🚀 Attempt 1/5
   Executing: python3 03_adaptive/run.py --query "blue house" --target jspaint
   ✗ Error: HF_TOKEN_ERROR: HF Hub requests will be unauthenticated
   🤖 Consulting LLM for recovery strategy...
      LLM suggests: switch_fallback
      Reasoning: Continue with local-only mode
   🔧 Executing recovery: switch_fallback
      ⚠ Continuing without HF_TOKEN (rate limits apply)
      💡 Tip: Set HF_TOKEN for better performance
   ✓ Recovery successful, retrying...
🚀 Attempt 2/5
   Executing: python3 03_adaptive/run.py --query "blue house" --target jspaint
   ✓ SUCCESS - Drawing complete!

📊 Execution Summary:
  Attempts: 2
  Recovery operations: 1
  Duration: 12500ms
  Success: ✓

Recovery strategies used:
  ✓ switch_fallback (150ms)
```

### Metryki i Ciągłe Doskonalenie

System automatycznie zbiera metryki:

- **Success rate per strategy** — które naprawy działają najlepiej
- **Avg recovery time** — jak szybko naprawiamy problemy
- **Error patterns** — jakie błędy się powtarzają
- **LLM effectiveness** — jak często rady LLM pomagają

Na podstawie tych danych system ewolucyjnie dostosowuje swoje strategie.

### Commands with Evolutionary Support

All commands now use the evolutionary orchestrator by default:

```bash
./run.sh draw "red star"                    # Auto-recovery enabled
./run.sh autonomous "castle"                # Auto-recovery enabled
./run.sh 03_adaptive --query "house"        # Auto-recovery enabled

# Verbose mode shows learning metrics
./run.sh draw "star" -v

# Check evolutionary learning metrics
nlp2cmd examples metrics

# Manage learning database
nlp2cmd examples learn              # Show learning DB status
nlp2cmd examples learn --reset      # Reset learning database

# Diagnose examples environment
nlp2cmd examples doctor
nlp2cmd examples doctor --fix
```

---

## Traditional Usage (Manual)

Each example lives in its own folder with:
- `run.py` — main script
- `README.md` — documentation + known issues
- `logs/` — structured logs (human-readable `.log` + machine-readable `.json`)
- `screenshots/` — result screenshots + metadata

## Examples

### 01 — draw.chat: Draw Shapes on Whiteboard

**New way (recommended):**
```bash
./run.sh 01_draw_chat
./run.sh 01_draw_chat --shape star --color red
```

**Traditional way:**
```bash
cd 01_draw_chat
python3 run.py --shape house --color blue
python3 run.py --shape star --color red --headless
```

### 02 — Picsart: Paint Patterns with Brushes

**New way (recommended):**
```bash
./run.sh 02_picsart
./run.sh 02_picsart --pattern spiral --color red
```

**Traditional way:**
```bash
cd 02_picsart
python3 run.py --pattern spiral --color red
python3 run.py --pattern grid --color green --headless
```

### 03 — Adaptive: LLM-Guided Drawing with Learning

**New way (recommended):**
```bash
./run.sh draw "narysuj dom z czerwonym dachem"
./run.sh draw "draw a blue star" --target jspaint
./run.sh 03_adaptive --query "purple butterfly"
```

**Traditional way:**
```bash
cd 03_adaptive
python3 run.py --query "narysuj dom z czerwonym dachem"
python3 run.py --query "draw a blue star" --target jspaint
```

### 04 — Object Database: Multi-Object Scenes with DB + LLM

**New way (recommended):**
```bash
./run.sh 04_object_database --objects "car, tree, house, cloud"
./run.sh 04_object_database --scene "forest with trees, birds, sun"
./run.sh 04_object_database --show-database
```

**Traditional way:**
```bash
cd 04_object_database
python3 run.py --objects "car, tree, house, cloud"
python3 run.py --scene "forest with trees, birds, sun"
python3 run.py --show-database
```

### 05 — Autonomous: Full Pipeline (Fetch → Draw → Validate → Correct)

**New way (recommended):**
```bash
./run.sh autonomous "narysuj czerwonego kota i niebieską rybkę"
./run.sh autonomous "draw a castle with a dragon"
./run.sh 05_autonomous --list-shapes          # 33 built-in shapes
./run.sh 05_autonomous --list-fetchable       # 44 database-mapped objects
./run.sh 05_autonomous --fetch-only butterfly
```

**Traditional way:**
```bash
cd 05_autonomous
python3 run.py "narysuj czerwonego kota i niebieską rybkę"
python3 run.py "draw a castle with a dragon"
python3 run.py --list-shapes          # 33 built-in shapes
python3 run.py --list-fetchable       # 44 database-mapped objects
python3 run.py --fetch-only butterfly
```

### 06 — Visual Validator: Vision LLM Drawing Verification

**New way (recommended):**
```bash
./run.sh 06_visual_validator --shape star --color red
./run.sh 06_visual_validator --shape butterfly --description "purple butterfly"
./run.sh 06_visual_validator --demo                 # 5 scenarios
./run.sh 06_visual_validator --shape house --correct  # auto-correct
```

**Traditional way:**
```bash
cd 06_visual_validator
python3 run.py --shape star --color red
python3 run.py --shape butterfly --description "purple butterfly"
python3 run.py --demo                 # 5 scenarios
python3 run.py --shape house --correct  # auto-correct
```

### 07 — Shape Gallery: Preview All 33+ Built-in Shapes

**New way (recommended):**
```bash
./run.sh 07_shape_gallery                        # list all shapes
./run.sh 07_shape_gallery --svg                  # generate SVG previews
./run.sh 07_shape_gallery --html                 # generate HTML gallery
./run.sh 07_shape_gallery --draw                  # draw all on jspaint.app
./run.sh 07_shape_gallery --category animals     # filter by category
```

**Traditional way:**
```bash
cd 07_shape_gallery
python3 run.py                        # list all shapes
python3 run.py --svg                  # generate SVG previews
python3 run.py --html                 # generate HTML gallery
python3 run.py --draw                 # draw all on jspaint.app
python3 run.py --category animals     # filter by category
```

## Folder Structure

```
09_online_drawing/
├── _run_utils.py              Shared infrastructure
├── _old/                      Original flat scripts (preserved)
├── 01_draw_chat/              Draw shapes on draw.chat
│   ├── run.py
│   ├── README.md
│   ├── logs/
│   └── screenshots/
├── 02_picsart/                Paint patterns on Picsart/Kleki
│   ├── run.py
│   ├── README.md
│   ├── logs/
│   └── screenshots/
├── 03_adaptive/               LLM-guided drawing + learning
│   ├── run.py
│   ├── README.md
│   ├── logs/
│   └── screenshots/
├── 04_object_database/        Multi-object DB + LLM scenes
│   ├── run.py
│   ├── README.md
│   ├── logs/
│   └── screenshots/
├── 05_autonomous/             Full pipeline: fetch→draw→validate→correct
│   ├── run.py
│   ├── README.md
│   ├── logs/
│   └── screenshots/
├── 06_visual_validator/       Vision LLM verification
│   ├── run.py
│   ├── README.md
│   ├── logs/
│   └── screenshots/
└── 07_shape_gallery/          Shape library preview
    ├── run.py
    ├── README.md
    ├── gallery/               SVG + HTML output
    ├── logs/
    └── screenshots/
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
├── NLDrawingParser    PL/EN natural language → 33+ shape types
├── CommandBus         Command dispatch + validation
├── EventStore         Immutable event log
└── ShapeRegistry      33 built-in + dynamic shapes

ObjectFetcher          Autonomous shape fetching from online databases
├── IconifyFetcher     200k+ icons (MDI, FontAwesome, GameIcons)
├── SimpleIconsFetcher 3k+ brand SVGs
├── SVGRepoFetcher     General vector graphics
└── parse_svg_path     SVG d-attribute → PointGroup converter

TextToShapeEngine      LLM-driven text → 2D vertex generation
├── generate           Prompt LLM for shape coordinates
├── validate_geometry  NaN/Inf/bounds checking
├── normalize_points   Center and scale coordinates
└── DynamicShapeGenerator  Runtime ShapeGenerator from data

VisualValidator        Vision LLM validates screenshots
├── validate           Screenshot + description → verdict + corrections
├── revalidate         Post-correction re-check
└── heuristic_validate Fallback when no vision model

CorrectionEngine       Iterative drawing repair
├── _build_plan        Corrections → CorrectionStep sequence
├── _execute_plan      Apply steps via DrawingSkill + Renderer
└── correct            Full validate → fix → re-validate loop

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
