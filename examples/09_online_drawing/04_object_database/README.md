# 04 — Object Database: Multi-Object Drawing with DB + LLM Fallback

Draw complex scenes composed of multiple objects, fetched autonomously from online databases with LLM fallback for unknown shapes.

## How It Works

1. **ShapeDatabase** searches online sources (HuggingFace, GitHub, FontAwesome) for object definitions
2. **LLM Fallback** generates vertex coordinates for shapes not found in any database
3. **SceneComposer** arranges multiple objects on a canvas with automatic grid layout
4. **nlp2cmd** executes the composed scene on jspaint.app via Playwright

## Usage

### New Way (Recommended) — Using run.sh

```bash
# From examples/09_online_drawing/ directory:

# Default scene: forest with trees, house, sun, clouds
./run.sh 04_object_database

# Custom scene
./run.sh 04_object_database --scene "city with car, house, tree, cloud"

# Specific objects
./run.sh 04_object_database --objects "car, tree, house, cloud"

# Headless mode
./run.sh 04_object_database --objects "star, heart, sun" --headless

# Show available databases
./run.sh 04_object_database --show-database

# Verbose mode (show drawing plan)
./run.sh 04_object_database -v
```

### Traditional Way — Direct Python

```bash
cd 04_object_database

# Default scene: forest with trees, house, sun, clouds
python3 run.py

# Custom scene
python3 run.py --scene "city with car, house, tree, cloud"

# Specific objects
python3 run.py --objects "car, tree, house, cloud"

# Headless mode
python3 run.py --objects "star, heart, sun" --headless

# Show available databases
python3 run.py --show-database

# Verbose mode (show drawing plan)
python3 run.py -v
```

## Database Sources

| Source | Type | Example Shapes |
|--------|------|---------------|
| HuggingFace | ShapeNet datasets | car, airplane, chair, table |
| GitHub | Raw JSON repos | triangle, square, pentagon, hexagon |
| FontAwesome | Icon SVGs | star, heart, cloud, sun, moon |

## Output Files

```
04_object_database/
├── run.py              # Main script
├── README.md           # This file
├── logs/               # Execution logs
└── screenshots/        # Result screenshots
```

## Known Issues

- **HuggingFace rate limits**: API may throttle after many requests. Cached shapes avoid this.
- **LLM vertex quality**: Generated shapes are approximate; complex objects may look simplified.
- **Cache TTL**: Default 3600s. Pass `--no-llm-fallback` to use only database shapes.

## Requirements

```bash
pip install playwright
playwright install chromium
```
