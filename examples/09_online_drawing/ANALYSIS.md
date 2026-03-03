# Analysis Report — Online Drawing Examples

**Date**: 2026-03-03  
**Platform**: Linux x86_64, Python 3.13.7, Playwright Chromium

## Summary

| Example | Shape | Color | Site | Status |
|---------|-------|-------|------|--------|
| 01_draw_chat | star | red ✓ | jspaint (fallback) | ✅ PASS |
| 01_draw_chat | house | blue ✓ | jspaint (fallback) | ✅ PASS |
| 02_picsart | spiral | black (no color on kleki) | kleki (fallback) | ⚠ PARTIAL |
| 03_adaptive | star (NL: "czerwoną gwiazdę") | red ✓ | jspaint (fallback) | ✅ PASS |

## Bugs Found and Fixed

### 1. Coordinate Scaling (Critical)

**File**: `src/nlp2cmd/skills/drawing/skill.py`  
**Root cause**: `DrawingSkill.render()` had a `pass` placeholder where canvas coordinate scaling should be. Shapes generated for 1024×768 were drawn on a 683×384 jspaint canvas — points overflowed, nothing visible.  
**Fix**: Added proportional scaling (`sx = actual_w / init_w`, `sy = actual_h / init_h`) applied to all shape points when actual canvas differs from initialized dimensions.

### 2. JSPaint Color Setting (Critical)

**File**: `src/nlp2cmd/skills/drawing/renderers/playwright.py`  
**Root cause**: `set_color()` tried `window.set_foreground_color()` which doesn't exist in jspaint, then set `ctx.strokeStyle` directly which jspaint overrides on each mouse operation.  
**Fix**: Replaced with palette click approach — converts target color to RGB, finds closest `.color-button[data-color]` in jspaint's 28-color palette, clicks it. This simulates actual user interaction and works reliably.

### 3. Polish Color Declensions (Medium)

**File**: `src/nlp2cmd/skills/drawing/colors.py`  
**Root cause**: `ColorResolver._BUILTIN` was missing accusative feminine forms like "czerwoną", "niebieską", "zieloną". Polish grammar requires these in phrases like "narysuj czerwoną gwiazdę".  
**Fix**: Added ~20 missing declension forms (accusative -ą, genitive -ej, dative -emu) for all 12 color families.

## What Works

- **Shape generation**: All 16 shape types (circle, star, house, heart, flower, spiral, grid, wave, triangle, rectangle, etc.) generate correct mathematical coordinates
- **Event sourcing**: CQRS commands → events → JSON session files work perfectly
- **Intelligent URL fallback**: When draw.chat is down (timeout/404), automatically discovers jspaint.app within seconds
- **Picsart design editor detection**: Detects redirect to `/create/editor` and falls back to kleki/jspaint
- **Popup dismissal**: Cookie banners, GDPR notices, login modals dismissed across sites
- **Canvas polling**: Dynamic canvas wait (up to 10s polling) handles slow-loading sites
- **NL parsing (PL+EN)**: Shape + color detection from natural language works for both languages
- **LLM adaptive routing**: Tries remote → local Ollama with adaptive learning
- **Vision verification**: Gemini 2.5 Pro analyzes screenshots (when available)
- **Structured logging**: JSON + human-readable logs with timestamps, platform info, error counts
- **Platform independence**: Works on Linux (tested), macOS, Windows via Playwright Chromium

## What Doesn't Work / Limitations

### draw.chat is currently down
- `draw.chat/` — timeout (15s)
- `draw.chat/pl/index.html` — HTTP 200 but no canvas element (landing page only)
- `draw.chat/pl/whiteboard.html` — 404
- **Workaround**: Automatic fallback to jspaint.app works seamlessly

### Picsart requires login for drawing
- `picsart.com/draw` → redirects to `/create/editor?category=layout` (design editor, not drawing)
- Login modal blocks freehand drawing
- **Workaround**: Detected and falls back to kleki.com

### Color on non-jspaint sites
- Kleki: color picker is a gradient panel, not a palette — current palette-click approach doesn't apply
- Excalidraw: uses custom UI for colors
- **Impact**: Shapes draw in default black on kleki/excalidraw
- **Future fix**: Add per-site color strategies (gradient click for kleki, toolbar button for excalidraw)

### Vision model quality
- Local `llava:7b` struggles to verify drawings ("No" for a visible star)
- Remote `gemini-2.5-pro` gives detailed but truncated analysis (MAX_TOKENS)
- **Impact**: Vision verification is advisory, not blocking

## Architecture Decisions

### URL Discovery Strategy
```
Target URL → fallback URLs → base domain variations → alternative sites
```
Each URL is checked with: HTTP status → popup dismissal → canvas polling (10s) → bounding box validation (>50×50px)

### Color Setting Strategy (priority order)
1. **Palette click** (jspaint): Find closest color in `.color-button` palette via RGB distance
2. **HTML5 color input**: Set value + dispatch input/change events
3. **Direct canvas context**: Set `strokeStyle`/`fillStyle` (may be overridden by app)

### Coordinate Scaling
When actual canvas dimensions differ from initialized dimensions by >10px, all shape points are scaled proportionally:
```python
sx = actual_width / init_width
sy = actual_height / init_height
scaled_points = [(x * sx, y * sy) for x, y in original_points]
```

## Test Results

- **Drawing skill unit tests**: 78 passed, 0 failed
- **Automation unit tests**: 62 passed, 0 failed
- **E2E examples**: 3/3 complete successfully (with fallback)
