# 07 — Shape Gallery: Preview All 33+ Built-in Shapes

Browse, preview, and draw the full shape library. Generates SVG previews, an HTML gallery page, or draws all shapes in a grid on jspaint.app.

## How It Works

1. **ShapeRegistry** provides all 33+ registered shape generators
2. Each generator produces **PointGroup** data (vertices for strokes)
3. Shapes are organized into 6 categories: basic, geometric, nature, animals, objects, decorative
4. Output: terminal list, SVG files, HTML gallery, or live canvas drawing

## Usage

### New Way (Recommended) — Using run.sh

```bash
# From examples/09_online_drawing/ directory:

# List all shapes with metadata
./run.sh 07_shape_gallery

# Filter by category
./run.sh 07_shape_gallery --category animals
./run.sh 07_shape_gallery --category geometric

# Generate SVG previews
./run.sh 07_shape_gallery --svg

# Generate HTML gallery (open in browser)
./run.sh 07_shape_gallery --html

# Draw all shapes on jspaint.app
./run.sh 07_shape_gallery --draw
./run.sh 07_shape_gallery --draw --headless

# Draw specific shapes
./run.sh 07_shape_gallery --draw --shape car --shape cat --shape rocket
```

### Traditional Way — Direct Python

```bash
cd 07_shape_gallery

# List all shapes with metadata
python3 run.py

# Filter by category
python3 run.py --category animals
python3 run.py --category geometric

# Generate SVG previews
python3 run.py --svg

# Generate HTML gallery (open in browser)
python3 run.py --html

# Draw all shapes on jspaint.app
python3 run.py --draw
python3 run.py --draw --headless

# Draw specific shapes
python3 run.py --draw --shape car --shape cat --shape rocket
```

## Shape Categories

| Category | Shapes | Count |
|----------|--------|-------|
| basic | circle, ellipse, rectangle, square, triangle, line, dot | 7 |
| geometric | pentagon, hexagon, octagon, diamond, cross, crescent | 6 |
| nature | flower, sun, tree, mountain, cloud_detailed, wave | 6 |
| animals | bird, butterfly, cat, fish | 4 |
| objects | house, car, boat, rocket, castle, arrow | 6 |
| decorative | star, heart, spiral, grid | 4 |

## Output Files

```
07_shape_gallery/
├── run.py              # Main script
├── README.md           # This file
├── gallery/            # Generated previews
│   ├── index.html      # HTML gallery page
│   ├── circle.svg      # Individual SVG previews
│   ├── car.svg
│   └── ...
├── logs/               # Execution logs
└── screenshots/        # Canvas screenshots
    └── shape_gallery.png
```

## Requirements

```bash
# For SVG/HTML gallery: no extra deps needed
# For canvas drawing:
pip install playwright
playwright install chromium
```
