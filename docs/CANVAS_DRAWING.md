# Canvas Drawing Automation

NLP2CMD supports automated drawing on HTML5 canvas applications like [jspaint.app](https://jspaint.app). This feature allows you to generate complex drawings through natural language commands.

## Quick Start

```bash
# Draw a ladybug on jspaint
nlp2cmd -q "narysuj biedronkę na jspaint.app" --run --video output.webm

# Draw a simple circle
nlp2cmd -q "narysuj czerwone koło" --run

# Draw a cat with screenshot
nlp2cmd -q "narysuj kota" --run --screenshot
```

## Supported Objects

The following objects have built-in drawing blueprints:

| Object | Polish | English | Drawing Primitives |
|--------|--------|---------|-------------------|
| 🐞 Ladybug | biedronka | ladybug | circles, ellipses, dots |
| 🐱 Cat | kot, kicia | cat | bezier curves, ellipses |
| 🐕 Dog | pies | dog | circles, ellipses |
| 🐰 Rabbit | królik, zając | rabbit, bunny | ellipses, circles |
| 🏠 House | dom, domek | house | rectangles, triangles |
| 🚗 Car | auto, samochód | car | rectangles, circles (wheels) |
| 🌳 Tree | drzewo | tree | rectangles, circles |
| 🌻 Flower | kwiat, kwiatek | flower | circles, ellipses |
| ⭐ Star | gwiazda | star | polygon |
| ❤️ Heart | serce | heart | SVG path |
| 🌞 Sun | słońce | sun | circles, arcs |
| 🐟 Fish | ryba | fish | ellipses, curves |
| 🦋 Butterfly | motyl | butterfly | ellipses, lines |
| ⛄ Snowman | bałwan | snowman | circles |

## Drawing Actions

Canvas workflows support the following actions:

### Basic Shapes

```yaml
# Set current color
- action: set_color
  params:
    color: "#FF0000"  # Red

# Set line width
- action: set_line_width
  params:
    width: 3

# Draw filled ellipse
- action: draw_filled_ellipse
  params:
    rx: 50        # X radius
    ry: 30        # Y radius
    offset: [0, 0]  # Offset from canvas center

# Draw filled circle
- action: draw_filled_circle
  params:
    radius: 40
    offset: [20, -10]

# Draw circle (outline)
- action: draw_circle
  params:
    radius: 20
    offset: [0, 0]
```

### Lines and Curves

```yaml
# Draw straight line
- action: draw_line
  params:
    from_offset: [0, 0]
    to_offset: [50, 50]

# Draw bezier curve
- action: draw_bezier
  params:
    curves:
      - type: M    # Move to
        x: 0
        y: 0
      - type: Q    # Quadratic bezier
        cpx: 25    # Control point X
        cpy: -50   # Control point Y
        x: 50      # End X
        y: 0       # End Y
    fill: false
    close: false

# Draw arc
- action: draw_arc
  params:
    start_angle: 0
    end_angle: 180
    radius: 40
```

### Polygons

```yaml
# Draw polygon (triangle, star, etc.)
- action: draw_polygon
  params:
    points:
      - [0, -50]    # Top
      - [-40, 30]   # Bottom left
      - [40, 30]    # Bottom right
    fill: true
    offset: [0, 0]
```

### SVG Paths

```yaml
# Draw complex shapes using SVG path syntax
- action: draw_svg_path
  params:
    path: "M50,50 C20,20 80,20 50,50"  # Heart shape
    fill: true
```

### Interactions

```yaml
# Wait for canvas to load
- action: wait_for_canvas
  params: {}

# Get canvas center coordinates
- action: get_canvas_center
  params: {}

# Click at position
- action: click_canvas
  params:
    offset: [10, 10]

# Fill area at position
- action: fill_at
  params:
    offset: [0, 0]

# Type text
- action: type_text
  params:
    text: "Hello"

# Take screenshot
- action: screenshot
  params:
    suffix: "final"

# Wait
- action: wait
  params:
    ms: 1000
```

## Canvas API JavaScript Helpers

The canvas automation uses JavaScript injected into the page for reliable drawing:

```javascript
// Draw filled circle via Canvas 2D API
function drawFilledCircle(cx, cy, radius, color) {
    const canvas = document.querySelector('canvas');
    const ctx = canvas.getContext('2d');
    ctx.save();
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
}
```

Available JS helpers:

- `_js_set_color(color_hex)` - Select color in jspaint palette
- `_js_select_tool(tool_name)` - Select drawing tool
- `_js_draw_filled_circle(cx, cy, radius, color)` - Draw filled circle
- `_js_draw_filled_ellipse(cx, cy, rx, ry, color)` - Draw filled ellipse
- `_js_draw_line(x1, y1, x2, y2, color, width)` - Draw line
- `_js_draw_polygon(points, color, width, fill)` - Draw polygon
- `_js_draw_bezier(commands, color, width, fill, close)` - Draw bezier curves

## Example Workflows

### Drawing a Ladybug

```bash
nlp2cmd -q "narysuj biedronkę na jspaint.app" --run
```

Generated plan:
```yaml
steps:
  - action: navigate
    params: {url: "https://jspaint.app"}
  - action: wait_for_canvas
  - action: get_canvas_center
  - action: set_color
    params: {color: "#FF0000"}      # Red body
  - action: draw_filled_ellipse
    params: {rx: 60, ry: 80, offset: [0, 10]}
  - action: set_color
    params: {color: "#000000"}      # Black head
  - action: draw_filled_circle
    params: {radius: 35, offset: [0, -60]}
  - action: draw_filled_circle
    params: {radius: 8, offset: [-20, 0]}   # Dot
  - action: draw_filled_circle
    params: {radius: 8, offset: [20, 0]}     # Dot
  - action: draw_filled_circle
    params: {radius: 8, offset: [0, 20]}     # Dot
  - action: screenshot
    params: {suffix: "ladybug"}
```

### Drawing a Cat

```bash
nlp2cmd -q "narysuj kota na jspaint.app" --run --screenshot cat.png
```

### Custom Drawing with Video

```bash
# Record the drawing process
nlp2cmd -q "narysuj serce na jspaint.app" --run --video heart_drawing.webm
```

## CLI Options

| Option | Description |
|--------|-------------|
| `--run` | Execute the drawing in browser |
| `--screenshot [path]` | Save final screenshot |
| `--video [path]` | Record drawing process to video |
| `--duration [seconds]` | Video recording duration |
| `--log-dir [path]` | Save debug logs |

## Testing

Run canvas-specific tests:

```bash
# Unit tests
pytest tests/unit/test_drawing_blueprints.py -v

# Canvas adapter tests
pytest tests/unit/test_automation.py::TestCanvasAdapter -v

# E2E tests (requires playwright)
pytest tests/e2e/test_canvas_e2e.py -v --tb=short

# Headless mode
HEADLESS=1 pytest tests/e2e/test_canvas_e2e.py -v
```

## Architecture

```
nlp2cmd -q "narysuj biedronkę"
    ↓
ActionPlanner.decompose_sync()
    ↓
Canvas blueprint lookup (drawing_blueprints.py)
    ↓
ActionPlan with canvas steps
    ↓
generate.py → Playwright execution
    ↓
JS helpers inject Canvas 2D API calls
    ↓
Screenshot/Video saved
```

## Troubleshooting

### Canvas not found

- Ensure jspaint.app is accessible
- Check network connectivity
- Try increasing wait timeout: `--wait 5000`

### Drawing offset incorrect

- The canvas center is auto-detected
- Fallback to (640, 360) if detection fails
- Check browser zoom level (should be 100%)

### Colors not applied

- Colors are set via `_js_set_color()` helper
- Palette swatch matching may fail on theme changes
- Direct Canvas API fills are used as fallback

### Video recording fails

- Ensure playwright is installed: `playwright install chromium`
- Check disk space for video files
- Video files are saved to temp dir and moved after recording

## Implementation Details

### Blueprint System

Blueprints are defined in `nlp2cmd/automation/drawing_blueprints.py`:

```python
OBJECT_BLUEPRINTS = [
    {
        "name": "ladybug",
        "aliases": ["biedronka", "biedronkę", "ladybug"],
        "steps_fn": lambda: [
            ActionStep("set_color", {"color": "#FF0000"}),
            ActionStep("draw_filled_ellipse", {"rx": 60, "ry": 80, "offset": [0, 10]}),
            # ... more steps
        ],
    },
]
```

### Adding New Objects

1. Create blueprint in `drawing_blueprints.py`
2. Add aliases for Polish and English
3. Define drawing steps using available actions
4. Add test in `test_drawing_blueprints.py`

## References

- [jspaint.app](https://jspaint.app) - Online MS Paint clone
- [Canvas API](https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API) - MDN documentation
- [Drawing Blueprints](../src/nlp2cmd/automation/drawing_blueprints.py) - Source code
