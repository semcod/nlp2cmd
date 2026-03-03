#!/usr/bin/env python3
"""
04_object_database_drawing — Multi-object drawing with external database + LLM fallback.

This advanced example demonstrates:
- Fetching shape/object definitions from online databases
- Text-to-2DObject generation via LLM for unknown shapes
- Multi-object scene composition
- Autonomous operation with intelligent fallback

Database sources (autonomous fetch):
- HuggingFace datasets (geometric shapes, icons)
- GitHub shape repositories
- Public geometry databases
- Local cache with TTL

LLM Fallback (text-to-2dobject):
- When shape not in database → ask LLM for vertex/coordinates
- LLM generates mathematical representation (points, curves)
- Convert to drawing commands

Usage:
    python3 04_object_database_drawing.py
    python3 04_object_database_drawing.py --scene "forest with trees, birds, sun"
    python3 04_object_database_drawing.py --objects "car, tree, house, cloud" --headless
"""

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
import ssl

# Add project root for imports
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))


@dataclass
class Shape2D:
    """Represents a 2D shape with mathematical definition."""
    name: str
    vertices: List[Tuple[float, float]]
    curves: Optional[List[List[Tuple[float, float]]]] = None
    metadata: Optional[Dict[str, Any]] = None
    source: str = "unknown"  # database, llm, cache, builtin
    
    def to_drawing_commands(self, offset: Tuple[float, float] = (0, 0), 
                           scale: float = 1.0) -> List[Dict]:
        """Convert shape to drawing commands."""
        commands = []
        
        # Scale and offset vertices
        scaled = [(x * scale + offset[0], y * scale + offset[1]) 
                  for x, y in self.vertices]
        
        if scaled:
            commands.append({
                "action": "draw_polygon",
                "params": {"points": scaled, "fill": True}
            })
        
        # Add curves if present
        if self.curves:
            for curve in self.curves:
                scaled_curve = [(x * scale + offset[0], y * scale + offset[1]) 
                               for x, y in curve]
                commands.append({
                    "action": "draw_bezier",
                    "params": {"points": scaled_curve}
                })
        
        return commands


class ShapeDatabase:
    """Autonomous shape database with online fetching and caching."""
    
    # Online database sources
    DATABASES = {
        "shapenet": {
            "url": "https://huggingface.co/api/datasets?search=shapenet",
            "type": "huggingface",
            "shapes": ["car", "airplane", "chair", "table"]
        },
        "geometric": {
            "url": "https://raw.githubusercontent.com/wronai/geometric-shapes-db/main/shapes.json",
            "type": "github_raw",
            "shapes": ["triangle", "square", "pentagon", "hexagon", "octagon"]
        },
        "icons": {
            "url": "https://raw.githubusercontent.com/FortAwesome/Font-Awesome/refs/heads/6.x/metadata/icons.json",
            "type": "fontawesome",
            "shapes": ["star", "heart", "cloud", "sun", "moon"]
        }
    }
    
    def __init__(self, cache_dir: Optional[Path] = None, cache_ttl: int = 3600):
        self.cache_dir = cache_dir or Path.home() / ".nlp2cmd" / "shape_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl = cache_ttl  # seconds
        self._memory_cache: Dict[str, Shape2D] = {}
        self._load_builtin_shapes()
    
    def _load_builtin_shapes(self):
        """Load hardcoded shapes as fallback."""
        builtins = {
            "circle": Shape2D(
                name="circle",
                vertices=[(100, 0), (70, 70), (0, 100), (-70, 70), 
                         (-100, 0), (-70, -70), (0, -100), (70, -70)],
                source="builtin"
            ),
            "star": Shape2D(
                name="star",
                vertices=[(0, -100), (20, -40), (90, -30), (40, 10), 
                         (60, 80), (0, 50), (-60, 80), (-40, 10), 
                         (-90, -30), (-20, -40)],
                source="builtin"
            ),
            "house": Shape2D(
                name="house",
                vertices=[(-80, 0), (-80, -80), (0, -140), (80, -80), 
                         (80, 0), (80, 80), (-80, 80)],
                source="builtin"
            ),
            "tree": Shape2D(
                name="tree",
                vertices=[(-60, -20), (-40, -80), (0, -120), (40, -80), 
                         (60, -20), (30, 0), (-30, 0)],
                curves=[[(-20, -120), (-40, -160), (-20, -180), (0, -200)],
                       [(20, -120), (40, -160), (20, -180), (0, -200)]],
                source="builtin"
            ),
            "car": Shape2D(
                name="car",
                vertices=[(-120, 20), (-120, -20), (-100, -40), (-60, -40),
                         (-40, -60), (40, -60), (60, -40), (100, -40),
                         (120, -20), (120, 20), (100, 40), (60, 40),
                         (40, 20), (-40, 20), (-60, 40), (-100, 40)],
                source="builtin"
            ),
            "cloud": Shape2D(
                name="cloud",
                vertices=[(-80, 0), (-60, -40), (-20, -60), (20, -60), 
                         (60, -40), (80, 0), (60, 40), (20, 60), 
                         (-20, 60), (-60, 40)],
                curves=[[(-60, -40), (-100, -60), (-100, 20), (-80, 0)],
                       [(60, -40), (100, -60), (100, 20), (80, 0)]],
                source="builtin"
            ),
            "sun": Shape2D(
                name="sun",
                vertices=[(0, 0)],  # Center point, rays drawn separately
                curves=[[(0, -80), (20, -100), (0, -120), (-20, -100)],  # Ray 1
                       [(56, -56), (76, -76), (85, -85), (95, -95)],   # Ray 2
                       [(80, 0), (100, 0), (120, 0), (140, 0)],       # Ray 3
                       [(56, 56), (76, 76), (85, 85), (95, 95)],      # Ray 4
                       [(0, 80), (0, 100), (0, 120), (0, 140)],       # Ray 5
                       [(-56, 56), (-76, 76), (-85, 85), (-95, 95)],  # Ray 6
                       [(-80, 0), (-100, 0), (-120, 0), (-140, 0)],   # Ray 7
                       [(-56, -56), (-76, -76), (-85, -85), (-95, -95)]],  # Ray 8
                source="builtin"
            ),
        }
        self._memory_cache.update(builtins)
    
    async def fetch_online_database(self, db_name: str) -> Dict[str, Shape2D]:
        """Fetch shapes from online database with fallback."""
        db = self.DATABASES.get(db_name)
        if not db:
            return {}
        
        # Check cache first
        cache_file = self.cache_dir / f"{db_name}.json"
        if cache_file.exists():
            age = time.time() - cache_file.stat().st_mtime
            if age < self.cache_ttl:
                try:
                    with open(cache_file) as f:
                        data = json.load(f)
                        shapes = {name: Shape2D(**shape_data) 
                                 for name, shape_data in data.items()}
                        print(f"  📦 Loaded {len(shapes)} shapes from cache ({db_name})")
                        return shapes
                except Exception as e:
                    print(f"  ⚠️ Cache load failed: {e}")
        
        # Try to fetch online
        try:
            shapes = await self._fetch_from_url(db_name, db)
            # Save to cache
            cache_data = {name: asdict(shape) for name, shape in shapes.items()}
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            print(f"  🌐 Fetched {len(shapes)} shapes from {db_name}")
            return shapes
        except Exception as e:
            print(f"  ⚠️ Online fetch failed for {db_name}: {e}")
            return {}
    
    async def _fetch_from_url(self, db_name: str, db: Dict) -> Dict[str, Shape2D]:
        """Fetch from specific URL."""
        shapes = {}
        
        try:
            # Create SSL context that doesn't verify certs (for some sites)
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            req = Request(
                db["url"],
                headers={
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
                }
            )
            
            with urlopen(req, timeout=10, context=ssl_context) as response:
                if db["type"] == "huggingface":
                    # Parse HuggingFace API response
                    data = json.loads(response.read().decode('utf-8'))
                    # Extract shape names from datasets
                    for item in data.get("datasets", [])[:10]:
                        name = item.get("id", "").split("/")[-1]
                        if name:
                            shapes[name] = Shape2D(
                                name=name,
                                vertices=[(0, 0)],  # Placeholder
                                source=f"huggingface:{db_name}",
                                metadata={"dataset_info": item}
                            )
                
                elif db["type"] == "github_raw":
                    # Parse GitHub raw JSON
                    data = json.loads(response.read().decode('utf-8'))
                    for name, shape_data in data.items():
                        shapes[name] = Shape2D(
                            name=name,
                            vertices=shape_data.get("vertices", []),
                            curves=shape_data.get("curves"),
                            source=f"github:{db_name}",
                            metadata=shape_data.get("metadata", {})
                        )
                
                elif db["type"] == "fontawesome":
                    # Parse FontAwesome icons
                    data = json.loads(response.read().decode('utf-8'))
                    for name, icon_data in data.items():
                        # Extract SVG path if available
                        if "svg" in str(icon_data):
                            shapes[name] = Shape2D(
                                name=name,
                                vertices=[(0, 0)],  # Parse SVG path to vertices
                                source=f"fontawesome:{db_name}",
                                metadata=icon_data
                            )
        
        except Exception as e:
            print(f"  ⚠️ Fetch error: {e}")
        
        return shapes
    
    async def get_shape(self, name: str, use_llm_fallback: bool = True) -> Optional[Shape2D]:
        """Get shape by name with autonomous database fetch + LLM fallback."""
        name = name.lower().strip()
        
        # Check memory cache
        if name in self._memory_cache:
            return self._memory_cache[name]
        
        # Try to fetch from online databases
        print(f"🔍 Searching for '{name}' in online databases...")
        for db_name in self.DATABASES.keys():
            try:
                online_shapes = await self.fetch_online_database(db_name)
                if name in online_shapes:
                    shape = online_shapes[name]
                    self._memory_cache[name] = shape
                    return shape
            except Exception as e:
                print(f"  ⚠️ Database {db_name}: {e}")
        
        # LLM Fallback: Generate shape from text description
        if use_llm_fallback:
            print(f"🤖 Shape '{name}' not found in databases, using LLM fallback...")
            shape = await self._generate_shape_via_llm(name)
            if shape:
                self._memory_cache[name] = shape
                return shape
        
        return None
    
    async def _generate_shape_via_llm(self, description: str) -> Optional[Shape2D]:
        """Use LLM to generate shape vertices from text description."""
        try:
            # Import LLM router for shape generation
            from nlp2cmd.llm.router import get_router
            
            router = get_router()
            
            prompt = f"""
Generate a 2D shape definition for "{description}".
Return ONLY a JSON object with:
- "vertices": list of [x, y] coordinates forming the shape outline (center at 0,0, size ~200x200)
- "curves": optional list of bezier curve control points
- "description": brief description of the shape

Example for "heart":
{{
  "vertices": [[0,-100],[30,-50],[80,-30],[50,0],[0,60],[-50,0],[-80,-30],[-30,-50]],
  "curves": [[[-30,-50],[0,-80],[30,-50]]],
  "description": "Heart shape with top curves and pointed bottom"
}}
"""
            
            response = await router.route_call(
                prompt=prompt,
                task_category="coding",
                timeout=30
            )
            
            if response and response.text:
                # Extract JSON from response
                text = response.text
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0]
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0]
                
                try:
                    data = json.loads(text.strip())
                    vertices = [(v[0], v[1]) for v in data.get("vertices", [])]
                    curves = None
                    if "curves" in data:
                        curves = [[(p[0], p[1]) for p in curve] 
                                 for curve in data["curves"]]
                    
                    shape = Shape2D(
                        name=description,
                        vertices=vertices,
                        curves=curves,
                        source="llm",
                        metadata={"llm_generated": True, "description": data.get("description", "")}
                    )
                    print(f"  ✨ Generated '{description}' via LLM ({len(vertices)} vertices)")
                    return shape
                    
                except json.JSONDecodeError:
                    print(f"  ⚠️ LLM response parsing failed")
                    return None
        
        except Exception as e:
            print(f"  ⚠️ LLM generation failed: {e}")
        
        return None


class SceneComposer:
    """Composes multiple objects into a scene with automatic layout."""
    
    def __init__(self, canvas_width: int = 1024, canvas_height: int = 768):
        self.width = canvas_width
        self.height = canvas_height
        self.objects: List[Tuple[str, Tuple[float, float], float]] = []  # name, position, scale
    
    def add_object(self, name: str, position: Optional[Tuple[float, float]] = None, 
                   scale: float = 1.0):
        """Add object to scene. Auto-position if not specified."""
        if position is None:
            position = self._find_free_position()
        self.objects.append((name, position, scale))
    
    def _find_free_position(self) -> Tuple[float, float]:
        """Find free position in scene using simple grid layout."""
        cols = 3
        idx = len(self.objects)
        row = idx // cols
        col = idx % cols
        
        x = (col + 1) * (self.width / (cols + 1)) - self.width / 2
        y = (row + 1) * (self.height / 3) - self.height / 2
        
        return (x, y)
    
    def to_nlp_command(self, site: str = "jspaint.app") -> str:
        """Convert scene to natural language command."""
        objects_desc = ", ".join([obj[0] for obj in self.objects])
        return f"Otwórz {site} i narysuj scenę z: {objects_desc}"
    
    async def to_drawing_plan(self, database: ShapeDatabase) -> List[Dict]:
        """Convert scene to detailed drawing plan."""
        plan = []
        
        # Navigate
        plan.append({"action": "navigate", "params": {"url": "https://jspaint.app"}})
        plan.append({"action": "wait_for_canvas", "params": {}})
        
        # Draw each object
        for name, position, scale in self.objects:
            shape = await database.get_shape(name)
            if shape:
                # Set color based on object type
                color = self._get_object_color(name)
                plan.append({"action": "set_color", "params": {"color": color}})
                
                # Add drawing commands
                commands = shape.to_drawing_commands(offset=position, scale=scale)
                plan.extend(commands)
        
        # Screenshot
        plan.append({"action": "screenshot", "params": {}})
        
        return plan
    
    def _get_object_color(self, name: str) -> str:
        """Get appropriate color for object type."""
        colors = {
            "tree": "#228B22",  # Forest green
            "house": "#8B4513",  # Saddle brown
            "car": "#DC143C",    # Crimson
            "cloud": "#87CEEB",  # Sky blue
            "sun": "#FFD700",    # Gold
            "star": "#FFD700",   # Gold
            "heart": "#FF69B4",  # Hot pink
            "bird": "#4169E1",   # Royal blue
            "flower": "#FF1493", # Deep pink
        }
        return colors.get(name.lower(), "#808080")  # Gray default


async def run_nlp2cmd_command(command: str, headless: bool = False, verbose: bool = False):
    """Run nlp2cmd with the given command."""
    args = [
        "--explain" if verbose else "--run",
        command,
    ]
    
    if headless:
        args.append("--headless")
    
    args = [arg for arg in args if arg]
    
    try:
        import subprocess
        env = os.environ.copy()
        env['PYTHONPATH'] = f"{project_root}/src:{env.get('PYTHONPATH', '')}"
        
        cmd = [sys.executable, "-m", "nlp2cmd.cli.main"] + args
        process = subprocess.Popen(cmd, 
                                  stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT,
                                  text=True, 
                                  cwd=project_root, env=env)
        
        stdout, _ = process.communicate(input="Y\n")
        print(stdout, end='')
        
        return process.returncode
    except Exception as e:
        print(f"Error running nlp2cmd: {e}")
        return 1


async def main():
    parser = argparse.ArgumentParser(
        description="Multi-object drawing with database + LLM fallback"
    )
    parser.add_argument("--scene", default="forest with trees, house, sun, clouds",
                       help="Scene description (objects separated by commas)")
    parser.add_argument("--objects", default=None,
                       help="Specific objects to draw (comma-separated)")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--no-llm-fallback", action="store_true",
                       help="Disable LLM fallback for unknown shapes")
    parser.add_argument("--show-database", action="store_true",
                       help="Show available shape databases")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    
    # Show database info
    if args.show_database:
        print("🗄️ Available Shape Databases:")
        db = ShapeDatabase()
        for name, info in db.DATABASES.items():
            print(f"\n📁 {name}")
            print(f"   Type: {info['type']}")
            print(f"   Shapes: {', '.join(info['shapes'][:5])}...")
            print(f"   URL: {info['url'][:60]}...")
        print(f"\n💾 Cache directory: {db.cache_dir}")
        print(f"⏱️  Cache TTL: {db.cache_ttl}s")
        return
    
    # Parse objects
    if args.objects:
        object_names = [o.strip() for o in args.objects.split(",")]
    else:
        # Extract objects from scene description
        object_names = [o.strip() for o in args.scene.replace("with", ",")
                                              .replace("and", ",")
                                              .split(",")
                       if o.strip()]
    
    print(f"🎨 Multi-Object Database Drawing Example")
    print(f"   Scene: {args.scene}")
    print(f"   Objects: {', '.join(object_names)}")
    print()
    
    # Initialize database
    print("🔧 Initializing shape database...")
    db = ShapeDatabase()
    print(f"   Built-in shapes: {len([s for s in db._memory_cache.values() if s.source == 'builtin'])}")
    
    # Compose scene
    print("\n🎬 Composing scene...")
    composer = SceneComposer()
    
    found_objects = []
    generated_objects = []
    
    for name in object_names:
        shape = await db.get_shape(name, use_llm_fallback=not args.no_llm_fallback)
        if shape:
            composer.add_object(name)
            if shape.source == "llm":
                generated_objects.append(name)
            else:
                found_objects.append(f"{name} ({shape.source})")
        else:
            print(f"   ⚠️ Could not find or generate: {name}")
    
    print(f"   ✓ Found: {', '.join(found_objects) if found_objects else 'None'}")
    print(f"   ✨ LLM-generated: {', '.join(generated_objects) if generated_objects else 'None'}")
    
    # Generate command
    command = composer.to_nlp_command()
    print(f"\n📝 Generated command: {command}")
    
    # Show drawing plan
    if args.verbose:
        print("\n📋 Drawing plan:")
        plan = await composer.to_drawing_plan(db)
        for i, step in enumerate(plan[:10], 1):  # Show first 10 steps
            action = step.get("action", "unknown")
            params = step.get("params", {})
            print(f"   {i}. {action}: {params}")
        if len(plan) > 10:
            print(f"   ... and {len(plan) - 10} more steps")
    
    print()
    
    # Execute via nlp2cmd
    exit_code = await run_nlp2cmd_command(command, headless=args.headless, verbose=args.verbose)
    
    print()
    if exit_code == 0:
        print("✅ Scene drawing completed!")
        print(f"   Used {len(found_objects)} database shapes + {len(generated_objects)} LLM-generated shapes")
        print("   Check the browser for the multi-object scene.")
    else:
        print(f"❌ Drawing failed with exit code {exit_code}")


if __name__ == "__main__":
    asyncio.run(main())
