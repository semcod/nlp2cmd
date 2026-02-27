# 07 — Canvas Drawing: JSPaint Automation

Draw shapes and patterns on jspaint.app using NLP2CMD mouse control.

## What it does

1. Opens jspaint.app in Playwright browser
2. Selects drawing tools (ellipse, brush, fill, line)
3. Sets colors (red, black)
4. Draws a ladybug: red circle body + black dots + antennae
5. Takes screenshot of the finished drawing

## Complex command example

```bash
nlp2cmd -r "wejdź na jspaint.app i narysuj biedronkę z czerwonym tłem i czarnymi kropkami"
```

## Run

```bash
cd examples/06_desktop_automation/07_canvas_drawing
python3 run.py
# Or specific shape:
python3 run.py --shape ladybug
python3 run.py --shape circle --color red
python3 run.py --shape rectangle --color blue
```

## Capabilities

- **Shapes**: circle, ellipse, rectangle, line, dots
- **Patterns**: ladybug (red body + black dots + antennae)
- **Tools**: pencil, brush, fill, eraser, ellipse, rectangle, line, text
- **Colors**: Polish and English names + hex codes
- **Bézier curves**: smooth freehand drawing via mouse controller
