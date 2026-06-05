"""
Drawing blueprints for NLP2CMD canvas automation.

Rich, multi-part drawing templates for common objects using SVG paths,
polygons, bezier curves, and basic shapes. Each blueprint produces a
realistic drawing on a canvas application like jspaint.app.

Blueprints use offset-from-center coordinates:
  - (0, 0) = canvas center
  - negative y = up, positive y = down
  - negative x = left, positive x = right

Supported drawing actions:
  - set_color, set_line_width
  - draw_filled_ellipse, draw_filled_circle, draw_filled_rectangle
  - draw_line, draw_circle, draw_ellipse
  - draw_polygon, draw_bezier, draw_svg_path, draw_arc
  - screenshot
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class DrawStep:
    """Single drawing step in a blueprint."""
    action: str
    params: dict[str, Any] = field(default_factory=dict)
    description: str = ""


def _step(action: str, params: dict[str, Any], desc: str = "") -> DrawStep:
    return DrawStep(action=action, params=params, description=desc)


# ── Rabbit / Zając ────────────────────────────────────────────────────

def _rabbit_steps() -> list[DrawStep]:
    """Detailed rabbit drawing with body, head, ears, eyes, nose, whiskers, tail, paws."""
    return [
        # Body — brown filled ellipse
        _step("set_color", {"color": "#8B6914"}, "Brown for body"),
        _step("draw_filled_ellipse", {"rx": 90, "ry": 70, "offset": [0, 40]}, "Body"),
        # Head — lighter brown circle
        _step("set_color", {"color": "#A07828"}, "Lighter brown for head"),
        _step("draw_filled_circle", {"radius": 45, "offset": [0, -45]}, "Head"),
        # Left ear
        _step("set_color", {"color": "#8B6914"}, "Brown for ears"),
        _step("draw_filled_ellipse", {"rx": 14, "ry": 50, "offset": [-20, -120]}, "Left ear"),
        # Left ear inner (pink)
        _step("set_color", {"color": "#FFB6C1"}, "Pink inner ear"),
        _step("draw_filled_ellipse", {"rx": 8, "ry": 35, "offset": [-20, -120]}, "Left ear inner"),
        # Right ear
        _step("set_color", {"color": "#8B6914"}, "Brown for ears"),
        _step("draw_filled_ellipse", {"rx": 14, "ry": 50, "offset": [20, -120]}, "Right ear"),
        # Right ear inner (pink)
        _step("set_color", {"color": "#FFB6C1"}, "Pink inner ear"),
        _step("draw_filled_ellipse", {"rx": 8, "ry": 35, "offset": [20, -120]}, "Right ear inner"),
        # Eyes — white with black pupils
        _step("set_color", {"color": "#FFFFFF"}, "White for eyes"),
        _step("draw_filled_circle", {"radius": 10, "offset": [-16, -52]}, "Left eye white"),
        _step("draw_filled_circle", {"radius": 10, "offset": [16, -52]}, "Right eye white"),
        _step("set_color", {"color": "#000000"}, "Black for pupils"),
        _step("draw_filled_circle", {"radius": 5, "offset": [-14, -52]}, "Left pupil"),
        _step("draw_filled_circle", {"radius": 5, "offset": [14, -52]}, "Right pupil"),
        # Nose — pink triangle
        _step("set_color", {"color": "#FF69B4"}, "Pink for nose"),
        _step("draw_polygon", {"points": [[0, -6], [-6, 4], [6, 4]], "offset": [0, -35], "fill": True}, "Nose"),
        # Mouth lines
        _step("set_color", {"color": "#000000"}, "Black for mouth"),
        _step("draw_line", {"from_offset": [0, -31], "to_offset": [0, -24]}, "Mouth center"),
        _step("draw_bezier", {"curves": [
            {"type": "M", "x": 0, "y": -24},
            {"type": "Q", "cpx": -10, "cpy": -18, "x": -18, "y": -22},
        ], "fill": False, "line_width": 2}, "Left mouth"),
        _step("draw_bezier", {"curves": [
            {"type": "M", "x": 0, "y": -24},
            {"type": "Q", "cpx": 10, "cpy": -18, "x": 18, "y": -22},
        ], "fill": False, "line_width": 2}, "Right mouth"),
        # Whiskers
        _step("set_line_width", {"width": 1}),
        _step("draw_line", {"from_offset": [-18, -34], "to_offset": [-50, -42]}, "Left whisker top"),
        _step("draw_line", {"from_offset": [-18, -30], "to_offset": [-50, -30]}, "Left whisker mid"),
        _step("draw_line", {"from_offset": [-18, -26], "to_offset": [-50, -20]}, "Left whisker bottom"),
        _step("draw_line", {"from_offset": [18, -34], "to_offset": [50, -42]}, "Right whisker top"),
        _step("draw_line", {"from_offset": [18, -30], "to_offset": [50, -30]}, "Right whisker mid"),
        _step("draw_line", {"from_offset": [18, -26], "to_offset": [50, -20]}, "Right whisker bottom"),
        # Front paws
        _step("set_color", {"color": "#A07828"}, "Paw color"),
        _step("draw_filled_ellipse", {"rx": 15, "ry": 10, "offset": [-35, 105]}, "Left paw"),
        _step("draw_filled_ellipse", {"rx": 15, "ry": 10, "offset": [35, 105]}, "Right paw"),
        # Tail — white fluffy circle
        _step("set_color", {"color": "#FFFFFF"}, "White for tail"),
        _step("draw_filled_circle", {"radius": 18, "offset": [-80, 50]}, "Tail"),
        _step("screenshot", {"suffix": "rabbit"}, "Screenshot"),
    ]


# ── Cat / Kot ─────────────────────────────────────────────────────────

def _cat_steps() -> list[DrawStep]:
    """Detailed cat with body, head, pointed ears, eyes, whiskers, tail."""
    return [
        # Body
        _step("set_color", {"color": "#808080"}, "Gray body"),
        _step("draw_filled_ellipse", {"rx": 80, "ry": 60, "offset": [0, 40]}, "Body"),
        # Head
        _step("draw_filled_circle", {"radius": 45, "offset": [0, -35]}, "Head"),
        # Left ear (triangle)
        _step("draw_polygon", {"points": [[-30, -10], [-45, -55], [-10, -30]], "offset": [0, -35], "fill": True}, "Left ear"),
        # Right ear (triangle)
        _step("draw_polygon", {"points": [[30, -10], [45, -55], [10, -30]], "offset": [0, -35], "fill": True}, "Right ear"),
        # Inner ears (pink)
        _step("set_color", {"color": "#FFB6C1"}, "Pink inner ears"),
        _step("draw_polygon", {"points": [[-28, -12], [-40, -48], [-14, -28]], "offset": [0, -35], "fill": True}, "Left inner ear"),
        _step("draw_polygon", {"points": [[28, -12], [40, -48], [14, -28]], "offset": [0, -35], "fill": True}, "Right inner ear"),
        # Eyes — green with black pupils
        _step("set_color", {"color": "#32CD32"}, "Green eyes"),
        _step("draw_filled_ellipse", {"rx": 10, "ry": 8, "offset": [-16, -40]}, "Left eye"),
        _step("draw_filled_ellipse", {"rx": 10, "ry": 8, "offset": [16, -40]}, "Right eye"),
        _step("set_color", {"color": "#000000"}, "Black pupils"),
        _step("draw_filled_ellipse", {"rx": 4, "ry": 7, "offset": [-16, -40]}, "Left pupil"),
        _step("draw_filled_ellipse", {"rx": 4, "ry": 7, "offset": [16, -40]}, "Right pupil"),
        # Nose
        _step("set_color", {"color": "#FF69B4"}, "Pink nose"),
        _step("draw_polygon", {"points": [[0, -4], [-5, 4], [5, 4]], "offset": [0, -25], "fill": True}, "Nose"),
        # Mouth
        _step("set_color", {"color": "#000000"}, "Black mouth"),
        _step("draw_line", {"from_offset": [0, -21], "to_offset": [0, -16]}, "Mouth"),
        # Whiskers
        _step("draw_line", {"from_offset": [-15, -22], "to_offset": [-50, -30]}, "L whisker 1"),
        _step("draw_line", {"from_offset": [-15, -20], "to_offset": [-50, -20]}, "L whisker 2"),
        _step("draw_line", {"from_offset": [-15, -18], "to_offset": [-50, -10]}, "L whisker 3"),
        _step("draw_line", {"from_offset": [15, -22], "to_offset": [50, -30]}, "R whisker 1"),
        _step("draw_line", {"from_offset": [15, -20], "to_offset": [50, -20]}, "R whisker 2"),
        _step("draw_line", {"from_offset": [15, -18], "to_offset": [50, -10]}, "R whisker 3"),
        # Tail — curved bezier
        _step("set_color", {"color": "#808080"}, "Gray tail"),
        _step("set_line_width", {"width": 8}),
        _step("draw_bezier", {"curves": [
            {"type": "M", "x": 75, "y": 40},
            {"type": "C", "cp1x": 110, "cp1y": 20, "cp2x": 120, "cp2y": -30, "x": 90, "y": -50},
        ], "fill": False, "line_width": 8}, "Tail"),
        # Paws
        _step("set_color", {"color": "#696969"}, "Dark gray paws"),
        _step("draw_filled_ellipse", {"rx": 14, "ry": 8, "offset": [-30, 95]}, "Left paw"),
        _step("draw_filled_ellipse", {"rx": 14, "ry": 8, "offset": [30, 95]}, "Right paw"),
        _step("screenshot", {"suffix": "cat"}, "Screenshot"),
    ]


# ── Dog / Pies ────────────────────────────────────────────────────────

def _dog_steps() -> list[DrawStep]:
    """Friendly dog with floppy ears, tongue out."""
    return [
        # Body
        _step("set_color", {"color": "#D2691E"}, "Brown body"),
        _step("draw_filled_ellipse", {"rx": 90, "ry": 65, "offset": [0, 40]}, "Body"),
        # Head
        _step("draw_filled_circle", {"radius": 50, "offset": [0, -35]}, "Head"),
        # Left floppy ear
        _step("set_color", {"color": "#8B4513"}, "Dark brown ears"),
        _step("draw_filled_ellipse", {"rx": 20, "ry": 40, "offset": [-45, -25], "rotation": 0.3}, "Left ear"),
        # Right floppy ear
        _step("draw_filled_ellipse", {"rx": 20, "ry": 40, "offset": [45, -25], "rotation": -0.3}, "Right ear"),
        # Muzzle — lighter area
        _step("set_color", {"color": "#DEB887"}, "Lighter muzzle"),
        _step("draw_filled_ellipse", {"rx": 25, "ry": 18, "offset": [0, -18]}, "Muzzle"),
        # Eyes
        _step("set_color", {"color": "#FFFFFF"}, "White eyes"),
        _step("draw_filled_circle", {"radius": 10, "offset": [-18, -48]}, "Left eye"),
        _step("draw_filled_circle", {"radius": 10, "offset": [18, -48]}, "Right eye"),
        _step("set_color", {"color": "#000000"}, "Black pupils"),
        _step("draw_filled_circle", {"radius": 5, "offset": [-16, -48]}, "Left pupil"),
        _step("draw_filled_circle", {"radius": 5, "offset": [16, -48]}, "Right pupil"),
        # Nose
        _step("set_color", {"color": "#000000"}, "Black nose"),
        _step("draw_filled_ellipse", {"rx": 10, "ry": 7, "offset": [0, -22]}, "Nose"),
        # Tongue
        _step("set_color", {"color": "#FF6B6B"}, "Red tongue"),
        _step("draw_filled_ellipse", {"rx": 8, "ry": 14, "offset": [0, -4]}, "Tongue"),
        # Tail
        _step("set_color", {"color": "#D2691E"}, "Brown tail"),
        _step("set_line_width", {"width": 8}),
        _step("draw_bezier", {"curves": [
            {"type": "M", "x": 85, "y": 30},
            {"type": "Q", "cpx": 115, "cpy": -10, "x": 100, "y": -40},
        ], "fill": False, "line_width": 8}, "Tail wagging"),
        # Legs
        _step("set_color", {"color": "#D2691E"}, "Brown legs"),
        _step("draw_filled_rectangle", {"width": 18, "height": 35, "offset": [-40, 95]}, "Left front leg"),
        _step("draw_filled_rectangle", {"width": 18, "height": 35, "offset": [40, 95]}, "Right front leg"),
        # Paws
        _step("set_color", {"color": "#8B4513"}, "Dark paws"),
        _step("draw_filled_ellipse", {"rx": 12, "ry": 6, "offset": [-40, 115]}, "Left paw"),
        _step("draw_filled_ellipse", {"rx": 12, "ry": 6, "offset": [40, 115]}, "Right paw"),
        _step("screenshot", {"suffix": "dog"}, "Screenshot"),
    ]


# ── Car / Samochód ────────────────────────────────────────────────────

def _car_steps() -> list[DrawStep]:
    """Side-view car with body, roof, windows, wheels, headlights."""
    return [
        # Car body — main rectangle
        _step("set_color", {"color": "#DC143C"}, "Red car body"),
        _step("draw_filled_rectangle", {"width": 240, "height": 60, "offset": [0, 20]}, "Car body"),
        # Roof / cabin
        _step("draw_polygon", {"points": [
            [-60, 0], [-40, -45], [50, -45], [70, 0],
        ], "offset": [0, -10], "fill": True}, "Car roof"),
        # Front windshield (light blue)
        _step("set_color", {"color": "#87CEEB"}, "Light blue windshield"),
        _step("draw_polygon", {"points": [
            [25, -2], [45, -40], [65, -40], [65, -2],
        ], "offset": [0, -10], "fill": True}, "Front windshield"),
        # Rear window
        _step("draw_polygon", {"points": [
            [-55, -2], [-35, -40], [15, -40], [15, -2],
        ], "offset": [0, -10], "fill": True}, "Rear window"),
        # Wheels — dark gray with hubcaps
        _step("set_color", {"color": "#1C1C1C"}, "Dark tire color"),
        _step("draw_filled_circle", {"radius": 22, "offset": [-70, 50]}, "Left wheel"),
        _step("draw_filled_circle", {"radius": 22, "offset": [70, 50]}, "Right wheel"),
        _step("set_color", {"color": "#C0C0C0"}, "Silver hubcaps"),
        _step("draw_filled_circle", {"radius": 10, "offset": [-70, 50]}, "Left hubcap"),
        _step("draw_filled_circle", {"radius": 10, "offset": [70, 50]}, "Right hubcap"),
        # Headlight
        _step("set_color", {"color": "#FFD700"}, "Yellow headlight"),
        _step("draw_filled_rectangle", {"width": 12, "height": 16, "offset": [118, 15]}, "Headlight"),
        # Taillight
        _step("set_color", {"color": "#FF4500"}, "Orange taillight"),
        _step("draw_filled_rectangle", {"width": 8, "height": 14, "offset": [-118, 15]}, "Taillight"),
        # Door handle
        _step("set_color", {"color": "#A9A9A9"}, "Handle"),
        _step("draw_filled_rectangle", {"width": 14, "height": 4, "offset": [0, 15]}, "Door handle"),
        # Ground line
        _step("set_color", {"color": "#808080"}, "Ground"),
        _step("set_line_width", {"width": 2}),
        _step("draw_line", {"from_offset": [-140, 72], "to_offset": [140, 72]}, "Ground line"),
        _step("screenshot", {"suffix": "car"}, "Screenshot"),
    ]


# ── House / Dom ───────────────────────────────────────────────────────

def _house_steps() -> list[DrawStep]:
    """House with walls, roof, door, windows, chimney."""
    return [
        # Walls
        _step("set_color", {"color": "#F5DEB3"}, "Wheat walls"),
        _step("draw_filled_rectangle", {"width": 180, "height": 140, "offset": [0, 30]}, "Walls"),
        # Roof — red triangle
        _step("set_color", {"color": "#B22222"}, "Dark red roof"),
        _step("draw_polygon", {"points": [
            [0, -60], [-110, 0], [110, 0],
        ], "offset": [0, -40], "fill": True}, "Roof"),
        # Door — brown
        _step("set_color", {"color": "#8B4513"}, "Brown door"),
        _step("draw_filled_rectangle", {"width": 35, "height": 65, "offset": [0, 67]}, "Door"),
        # Door knob
        _step("set_color", {"color": "#FFD700"}, "Gold knob"),
        _step("draw_filled_circle", {"radius": 4, "offset": [10, 67]}, "Door knob"),
        # Left window
        _step("set_color", {"color": "#87CEEB"}, "Blue windows"),
        _step("draw_filled_rectangle", {"width": 35, "height": 30, "offset": [-55, 15]}, "Left window"),
        # Right window
        _step("draw_filled_rectangle", {"width": 35, "height": 30, "offset": [55, 15]}, "Right window"),
        # Window cross frames
        _step("set_color", {"color": "#FFFFFF"}, "White frames"),
        _step("set_line_width", {"width": 2}),
        _step("draw_line", {"from_offset": [-55, 0], "to_offset": [-55, 30]}, "Left window V"),
        _step("draw_line", {"from_offset": [-73, 15], "to_offset": [-37, 15]}, "Left window H"),
        _step("draw_line", {"from_offset": [55, 0], "to_offset": [55, 30]}, "Right window V"),
        _step("draw_line", {"from_offset": [37, 15], "to_offset": [73, 15]}, "Right window H"),
        # Chimney
        _step("set_color", {"color": "#A0522D"}, "Brick chimney"),
        _step("draw_filled_rectangle", {"width": 20, "height": 40, "offset": [60, -65]}, "Chimney"),
        # Chimney smoke (curvy line)
        _step("set_color", {"color": "#C0C0C0"}, "Smoke"),
        _step("set_line_width", {"width": 3}),
        _step("draw_bezier", {"curves": [
            {"type": "M", "x": 60, "y": -85},
            {"type": "Q", "cpx": 55, "cpy": -100, "x": 65, "y": -110},
            {"type": "Q", "cpx": 75, "cpy": -120, "x": 60, "y": -130},
        ], "fill": False, "line_width": 3}, "Smoke"),
        # Ground
        _step("set_color", {"color": "#228B22"}, "Green ground"),
        _step("draw_filled_rectangle", {"width": 300, "height": 15, "offset": [0, 107]}, "Grass"),
        _step("screenshot", {"suffix": "house"}, "Screenshot"),
    ]


# ── Tree / Drzewo ─────────────────────────────────────────────────────

def _tree_steps() -> list[DrawStep]:
    """Tree with brown trunk and green foliage."""
    return [
        # Trunk
        _step("set_color", {"color": "#8B4513"}, "Brown trunk"),
        _step("draw_filled_rectangle", {"width": 30, "height": 100, "offset": [0, 50]}, "Trunk"),
        # Main foliage (overlapping circles for natural look)
        _step("set_color", {"color": "#228B22"}, "Forest green foliage"),
        _step("draw_filled_circle", {"radius": 55, "offset": [0, -25]}, "Center foliage"),
        _step("set_color", {"color": "#32CD32"}, "Lime green highlights"),
        _step("draw_filled_circle", {"radius": 40, "offset": [-35, -10]}, "Left foliage"),
        _step("draw_filled_circle", {"radius": 40, "offset": [35, -10]}, "Right foliage"),
        _step("set_color", {"color": "#006400"}, "Dark green shadow"),
        _step("draw_filled_circle", {"radius": 35, "offset": [0, -55]}, "Top foliage"),
        # Ground
        _step("set_color", {"color": "#228B22"}, "Green ground"),
        _step("draw_filled_ellipse", {"rx": 50, "ry": 10, "offset": [0, 100]}, "Ground grass"),
        _step("screenshot", {"suffix": "tree"}, "Screenshot"),
    ]


# ── Sun / Słońce ──────────────────────────────────────────────────────

def _sun_steps() -> list[DrawStep]:
    """Sun with rays."""
    rays = []
    for i in range(12):
        angle = 2 * math.pi * i / 12
        inner_r = 55
        outer_r = 90
        fx = round(inner_r * math.cos(angle))
        fy = round(inner_r * math.sin(angle))
        tx = round(outer_r * math.cos(angle))
        ty = round(outer_r * math.sin(angle))
        rays.append(_step("draw_line", {
            "from_offset": [fx, fy], "to_offset": [tx, ty],
        }, f"Ray {i+1}"))

    return [
        # Rays first (behind the circle)
        _step("set_color", {"color": "#FFD700"}, "Gold rays"),
        _step("set_line_width", {"width": 4}),
        *rays,
        # Sun body
        _step("set_color", {"color": "#FFD700"}, "Gold sun"),
        _step("draw_filled_circle", {"radius": 50, "offset": [0, 0]}, "Sun body"),
        # Face — eyes and smile
        _step("set_color", {"color": "#000000"}, "Face features"),
        _step("draw_filled_circle", {"radius": 5, "offset": [-15, -10]}, "Left eye"),
        _step("draw_filled_circle", {"radius": 5, "offset": [15, -10]}, "Right eye"),
        _step("draw_arc", {"radius": 20, "start_angle": 0.3, "end_angle": 2.84, "offset": [0, 5], "fill": False, "line_width": 3}, "Smile"),
        _step("screenshot", {"suffix": "sun"}, "Screenshot"),
    ]


# ── Flower / Kwiat ────────────────────────────────────────────────────

def _flower_steps() -> list[DrawStep]:
    """Flower with petals around a center, stem, and leaves."""
    petals = []
    for i in range(8):
        angle = 2 * math.pi * i / 8
        ox = round(35 * math.cos(angle))
        oy = round(35 * math.sin(angle))
        petals.append(_step("draw_filled_ellipse", {
            "rx": 20, "ry": 12, "offset": [ox, oy - 30], "rotation": round(angle, 2),
        }, f"Petal {i+1}"))

    return [
        # Stem
        _step("set_color", {"color": "#228B22"}, "Green stem"),
        _step("set_line_width", {"width": 5}),
        _step("draw_line", {"from_offset": [0, 0], "to_offset": [0, 100]}, "Stem"),
        # Leaves
        _step("set_color", {"color": "#32CD32"}, "Light green leaves"),
        _step("draw_filled_ellipse", {"rx": 25, "ry": 10, "offset": [-25, 50], "rotation": 0.5}, "Left leaf"),
        _step("draw_filled_ellipse", {"rx": 25, "ry": 10, "offset": [25, 70], "rotation": -0.5}, "Right leaf"),
        # Petals
        _step("set_color", {"color": "#FF6347"}, "Red petals"),
        *petals,
        # Center
        _step("set_color", {"color": "#FFD700"}, "Gold center"),
        _step("draw_filled_circle", {"radius": 15, "offset": [0, -30]}, "Flower center"),
        _step("screenshot", {"suffix": "flower"}, "Screenshot"),
    ]


# ── Star / Gwiazda ───────────────────────────────────────────────────

def _star_steps() -> list[DrawStep]:
    """Five-pointed star."""
    # Generate 5-pointed star vertices
    outer_r = 80
    inner_r = 35
    points = []
    for i in range(10):
        angle = math.pi / 2 + 2 * math.pi * i / 10
        r = outer_r if i % 2 == 0 else inner_r
        points.append([round(r * math.cos(angle)), round(-r * math.sin(angle))])
    return [
        _step("set_color", {"color": "#FFD700"}, "Gold star"),
        _step("draw_polygon", {"points": points, "offset": [0, 0], "fill": True}, "Star"),
        _step("set_color", {"color": "#DAA520"}, "Darker gold outline"),
        _step("draw_polygon", {"points": points, "offset": [0, 0], "fill": False, "line_width": 2}, "Star outline"),
        _step("screenshot", {"suffix": "star"}, "Screenshot"),
    ]


# ── Heart / Serce ────────────────────────────────────────────────────

def _heart_steps() -> list[DrawStep]:
    """Heart shape using SVG path."""
    heart_path = (
        "M 0 -30 "
        "C -10 -50, -40 -55, -50 -30 "
        "C -60 -5, -40 25, 0 55 "
        "C 40 25, 60 -5, 50 -30 "
        "C 40 -55, 10 -50, 0 -30 Z"
    )
    return [
        _step("set_color", {"color": "#FF1744"}, "Red heart"),
        _step("draw_svg_path", {"d": heart_path, "fill": True, "scale": 1.5}, "Heart shape"),
        # Highlight
        _step("set_color", {"color": "#FF6B6B"}, "Light highlight"),
        _step("draw_filled_circle", {"radius": 12, "offset": [-25, -25]}, "Heart highlight"),
        _step("screenshot", {"suffix": "heart"}, "Screenshot"),
    ]


# ── Fish / Ryba ──────────────────────────────────────────────────────

def _fish_steps() -> list[DrawStep]:
    """Colorful fish with body, tail, fins, eye."""
    return [
        # Body
        _step("set_color", {"color": "#FF8C00"}, "Orange fish body"),
        _step("draw_filled_ellipse", {"rx": 80, "ry": 45, "offset": [0, 0]}, "Fish body"),
        # Tail fin (triangle)
        _step("draw_polygon", {"points": [
            [0, 0], [45, -35], [45, 35],
        ], "offset": [-80, 0], "fill": True}, "Tail fin"),
        # Top fin
        _step("set_color", {"color": "#FF6347"}, "Darker orange fin"),
        _step("draw_polygon", {"points": [
            [-20, 0], [0, -35], [30, 0],
        ], "offset": [0, -45], "fill": True}, "Top fin"),
        # Belly — lighter
        _step("set_color", {"color": "#FFD700"}, "Golden belly"),
        _step("draw_filled_ellipse", {"rx": 60, "ry": 20, "offset": [0, 15]}, "Belly"),
        # Eye
        _step("set_color", {"color": "#FFFFFF"}, "White eye"),
        _step("draw_filled_circle", {"radius": 12, "offset": [35, -8]}, "Eye white"),
        _step("set_color", {"color": "#000000"}, "Black pupil"),
        _step("draw_filled_circle", {"radius": 6, "offset": [38, -8]}, "Pupil"),
        # Mouth
        _step("draw_line", {"from_offset": [75, 5], "to_offset": [65, 5]}, "Mouth"),
        # Scales pattern — small arcs
        _step("set_color", {"color": "#E07000"}, "Scale color"),
        _step("set_line_width", {"width": 1}),
        _step("draw_arc", {"radius": 10, "start_angle": 0.5, "end_angle": 2.6, "offset": [10, -5], "fill": False, "line_width": 1}, "Scale 1"),
        _step("draw_arc", {"radius": 10, "start_angle": 0.5, "end_angle": 2.6, "offset": [-10, 0], "fill": False, "line_width": 1}, "Scale 2"),
        _step("draw_arc", {"radius": 10, "start_angle": 0.5, "end_angle": 2.6, "offset": [0, 10], "fill": False, "line_width": 1}, "Scale 3"),
        _step("draw_arc", {"radius": 10, "start_angle": 0.5, "end_angle": 2.6, "offset": [-20, 10], "fill": False, "line_width": 1}, "Scale 4"),
        _step("screenshot", {"suffix": "fish"}, "Screenshot"),
    ]


# ── Butterfly / Motyl ────────────────────────────────────────────────

def _butterfly_steps() -> list[DrawStep]:
    """Butterfly with symmetric wings, body, antennae."""
    return [
        # Upper wings
        _step("set_color", {"color": "#9B59B6"}, "Purple wings"),
        _step("draw_filled_ellipse", {"rx": 55, "ry": 40, "offset": [-45, -25], "rotation": -0.4}, "Left upper wing"),
        _step("draw_filled_ellipse", {"rx": 55, "ry": 40, "offset": [45, -25], "rotation": 0.4}, "Right upper wing"),
        # Lower wings
        _step("set_color", {"color": "#8E44AD"}, "Darker purple"),
        _step("draw_filled_ellipse", {"rx": 40, "ry": 30, "offset": [-40, 25], "rotation": 0.3}, "Left lower wing"),
        _step("draw_filled_ellipse", {"rx": 40, "ry": 30, "offset": [40, 25], "rotation": -0.3}, "Right lower wing"),
        # Wing spots
        _step("set_color", {"color": "#F39C12"}, "Orange spots"),
        _step("draw_filled_circle", {"radius": 12, "offset": [-50, -25]}, "Left wing spot"),
        _step("draw_filled_circle", {"radius": 12, "offset": [50, -25]}, "Right wing spot"),
        _step("set_color", {"color": "#E74C3C"}, "Red spots"),
        _step("draw_filled_circle", {"radius": 8, "offset": [-40, 20]}, "Left lower spot"),
        _step("draw_filled_circle", {"radius": 8, "offset": [40, 20]}, "Right lower spot"),
        # Body
        _step("set_color", {"color": "#2C3E50"}, "Dark body"),
        _step("draw_filled_ellipse", {"rx": 6, "ry": 45, "offset": [0, 0]}, "Body"),
        # Head
        _step("draw_filled_circle", {"radius": 8, "offset": [0, -48]}, "Head"),
        # Antennae
        _step("set_line_width", {"width": 2}),
        _step("draw_bezier", {"curves": [
            {"type": "M", "x": -3, "y": -55},
            {"type": "Q", "cpx": -25, "cpy": -80, "x": -30, "y": -85},
        ], "fill": False, "line_width": 2}, "Left antenna"),
        _step("draw_filled_circle", {"radius": 3, "offset": [-30, -85]}, "Left antenna tip"),
        _step("draw_bezier", {"curves": [
            {"type": "M", "x": 3, "y": -55},
            {"type": "Q", "cpx": 25, "cpy": -80, "x": 30, "y": -85},
        ], "fill": False, "line_width": 2}, "Right antenna"),
        _step("draw_filled_circle", {"radius": 3, "offset": [30, -85]}, "Right antenna tip"),
        _step("screenshot", {"suffix": "butterfly"}, "Screenshot"),
    ]


# ── Snowman / Bałwan ────────────────────────────────────────────────

def _snowman_steps() -> list[DrawStep]:
    """Snowman with three snowballs, hat, scarf, face, arms."""
    return [
        # Bottom snowball
        _step("set_color", {"color": "#F0F8FF"}, "White snow"),
        _step("draw_filled_circle", {"radius": 60, "offset": [0, 60]}, "Bottom ball"),
        # Middle snowball
        _step("draw_filled_circle", {"radius": 45, "offset": [0, -15]}, "Middle ball"),
        # Head
        _step("draw_filled_circle", {"radius": 32, "offset": [0, -72]}, "Head"),
        # Hat
        _step("set_color", {"color": "#000000"}, "Black hat"),
        _step("draw_filled_rectangle", {"width": 50, "height": 35, "offset": [0, -112]}, "Hat top"),
        _step("draw_filled_rectangle", {"width": 70, "height": 8, "offset": [0, -92]}, "Hat brim"),
        # Eyes (coal)
        _step("draw_filled_circle", {"radius": 4, "offset": [-12, -78]}, "Left eye"),
        _step("draw_filled_circle", {"radius": 4, "offset": [12, -78]}, "Right eye"),
        # Carrot nose
        _step("set_color", {"color": "#FF8C00"}, "Orange nose"),
        _step("draw_polygon", {"points": [[0, 0], [25, 4], [0, 8]], "offset": [0, -68], "fill": True}, "Carrot nose"),
        # Mouth (dots)
        _step("set_color", {"color": "#000000"}, "Coal mouth"),
        _step("draw_filled_circle", {"radius": 3, "offset": [-12, -58]}, "Mouth 1"),
        _step("draw_filled_circle", {"radius": 3, "offset": [-6, -55]}, "Mouth 2"),
        _step("draw_filled_circle", {"radius": 3, "offset": [0, -54]}, "Mouth 3"),
        _step("draw_filled_circle", {"radius": 3, "offset": [6, -55]}, "Mouth 4"),
        _step("draw_filled_circle", {"radius": 3, "offset": [12, -58]}, "Mouth 5"),
        # Buttons
        _step("draw_filled_circle", {"radius": 5, "offset": [0, -25]}, "Button 1"),
        _step("draw_filled_circle", {"radius": 5, "offset": [0, -5]}, "Button 2"),
        _step("draw_filled_circle", {"radius": 5, "offset": [0, 15]}, "Button 3"),
        # Scarf
        _step("set_color", {"color": "#FF0000"}, "Red scarf"),
        _step("draw_filled_rectangle", {"width": 70, "height": 10, "offset": [0, -42]}, "Scarf wrap"),
        _step("draw_filled_rectangle", {"width": 12, "height": 30, "offset": [25, -25]}, "Scarf tail"),
        # Arms (sticks)
        _step("set_color", {"color": "#8B4513"}, "Brown arms"),
        _step("set_line_width", {"width": 4}),
        _step("draw_line", {"from_offset": [-45, -15], "to_offset": [-100, -50]}, "Left arm"),
        _step("draw_line", {"from_offset": [-100, -50], "to_offset": [-90, -65]}, "Left hand"),
        _step("draw_line", {"from_offset": [-100, -50], "to_offset": [-110, -60]}, "Left hand 2"),
        _step("draw_line", {"from_offset": [45, -15], "to_offset": [100, -50]}, "Right arm"),
        _step("draw_line", {"from_offset": [100, -50], "to_offset": [90, -65]}, "Right hand"),
        _step("draw_line", {"from_offset": [100, -50], "to_offset": [110, -60]}, "Right hand 2"),
        # Ground
        _step("set_color", {"color": "#E8E8E8"}, "Snow ground"),
        _step("draw_filled_ellipse", {"rx": 100, "ry": 12, "offset": [0, 118]}, "Snow ground"),
        _step("screenshot", {"suffix": "snowman"}, "Screenshot"),
    ]


# ── Ladybug / Biedronka (enhanced) ──────────────────────────────────

def _ladybug_steps() -> list[DrawStep]:
    """Enhanced ladybug with body, head, dots, antennae, legs."""
    return [
        # Body — red
        _step("set_color", {"color": "#FF0000"}, "Red body"),
        _step("draw_filled_circle", {"radius": 80, "offset": [0, 10]}, "Body"),
        # Center dividing line
        _step("set_color", {"color": "#000000"}, "Black"),
        _step("set_line_width", {"width": 3}),
        _step("draw_line", {"from_offset": [0, -70], "to_offset": [0, 90]}, "Center line"),
        # Head
        _step("draw_filled_circle", {"radius": 28, "offset": [0, -85]}, "Head"),
        # Antennae
        _step("set_line_width", {"width": 2}),
        _step("draw_bezier", {"curves": [
            {"type": "M", "x": -10, "y": -110},
            {"type": "Q", "cpx": -30, "cpy": -140, "x": -35, "y": -145},
        ], "fill": False, "line_width": 2}, "Left antenna"),
        _step("draw_filled_circle", {"radius": 4, "offset": [-35, -145]}, "Left antenna tip"),
        _step("draw_bezier", {"curves": [
            {"type": "M", "x": 10, "y": -110},
            {"type": "Q", "cpx": 30, "cpy": -140, "x": 35, "y": -145},
        ], "fill": False, "line_width": 2}, "Right antenna"),
        _step("draw_filled_circle", {"radius": 4, "offset": [35, -145]}, "Right antenna tip"),
        # Dots
        _step("draw_filled_circle", {"radius": 12, "offset": [-28, -25]}, "Dot 1 left-top"),
        _step("draw_filled_circle", {"radius": 12, "offset": [28, -25]}, "Dot 2 right-top"),
        _step("draw_filled_circle", {"radius": 12, "offset": [-35, 20]}, "Dot 3 left-mid"),
        _step("draw_filled_circle", {"radius": 12, "offset": [35, 20]}, "Dot 4 right-mid"),
        _step("draw_filled_circle", {"radius": 10, "offset": [-25, 60]}, "Dot 5 left-bot"),
        _step("draw_filled_circle", {"radius": 10, "offset": [25, 60]}, "Dot 6 right-bot"),
        # Eyes
        _step("set_color", {"color": "#FFFFFF"}, "White eyes"),
        _step("draw_filled_circle", {"radius": 6, "offset": [-10, -90]}, "Left eye"),
        _step("draw_filled_circle", {"radius": 6, "offset": [10, -90]}, "Right eye"),
        _step("set_color", {"color": "#000000"}, "Black pupils"),
        _step("draw_filled_circle", {"radius": 3, "offset": [-9, -90]}, "Left pupil"),
        _step("draw_filled_circle", {"radius": 3, "offset": [9, -90]}, "Right pupil"),
        # Legs
        _step("set_line_width", {"width": 3}),
        _step("draw_line", {"from_offset": [-70, -20], "to_offset": [-95, -35]}, "Leg L1"),
        _step("draw_line", {"from_offset": [-75, 10], "to_offset": [-100, 10]}, "Leg L2"),
        _step("draw_line", {"from_offset": [-70, 40], "to_offset": [-95, 55]}, "Leg L3"),
        _step("draw_line", {"from_offset": [70, -20], "to_offset": [95, -35]}, "Leg R1"),
        _step("draw_line", {"from_offset": [75, 10], "to_offset": [100, 10]}, "Leg R2"),
        _step("draw_line", {"from_offset": [70, 40], "to_offset": [95, 55]}, "Leg R3"),
        _step("screenshot", {"suffix": "ladybug"}, "Screenshot"),
    ]


# ── Child / Dziecko ─────────────────────────────────────────────────

def _child_steps() -> list[DrawStep]:
    """Cartoon child with head, hair, shirt, arms, legs, shoes, and face."""
    return [
        _step("set_color", {"color": "#1E3A8A"}, "Blue pants"),
        _step("draw_filled_ellipse", {"rx": 12, "ry": 40, "offset": [-18, 55]}, "Left leg"),
        _step("draw_filled_ellipse", {"rx": 12, "ry": 40, "offset": [18, 55]}, "Right leg"),
        _step("set_color", {"color": "#8B4513"}, "Brown shoes"),
        _step("draw_filled_ellipse", {"rx": 18, "ry": 8, "offset": [-18, 92]}, "Left shoe"),
        _step("draw_filled_ellipse", {"rx": 18, "ry": 8, "offset": [18, 92]}, "Right shoe"),
        _step("set_color", {"color": "#FF6B6B"}, "Red shirt"),
        _step("draw_filled_ellipse", {"rx": 35, "ry": 45, "offset": [0, 5]}, "Torso"),
        _step("set_line_width", {"width": 10}),
        _step("set_color", {"color": "#FF6B6B"}, "Shirt sleeves"),
        _step("draw_line", {"from_offset": [-35, 0], "to_offset": [-60, 25]}, "Left arm"),
        _step("draw_line", {"from_offset": [35, 0], "to_offset": [60, 25]}, "Right arm"),
        _step("set_color", {"color": "#FDBCB4"}, "Skin hands"),
        _step("draw_filled_circle", {"radius": 8, "offset": [-62, 30]}, "Left hand"),
        _step("draw_filled_circle", {"radius": 8, "offset": [62, 30]}, "Right hand"),
        _step("set_color", {"color": "#FDBCB4"}, "Skin"),
        _step("draw_filled_circle", {"radius": 32, "offset": [0, -55]}, "Head"),
        _step("set_color", {"color": "#4A3728"}, "Brown hair"),
        _step("draw_filled_ellipse", {"rx": 34, "ry": 20, "offset": [0, -72]}, "Hair top"),
        _step("draw_filled_ellipse", {"rx": 8, "ry": 25, "offset": [-32, -58]}, "Hair left"),
        _step("draw_filled_ellipse", {"rx": 8, "ry": 25, "offset": [32, -58]}, "Hair right"),
        _step("set_color", {"color": "#FFFFFF"}, "White eyes"),
        _step("draw_filled_circle", {"radius": 7, "offset": [-12, -58]}, "Left eye white"),
        _step("draw_filled_circle", {"radius": 7, "offset": [12, -58]}, "Right eye white"),
        _step("set_color", {"color": "#4169E1"}, "Blue pupils"),
        _step("draw_filled_circle", {"radius": 4, "offset": [-11, -57]}, "Left pupil"),
        _step("draw_filled_circle", {"radius": 4, "offset": [11, -57]}, "Right pupil"),
        _step("set_color", {"color": "#C0392B"}, "Mouth"),
        _step("draw_arc", {"radius": 12, "start_angle": 0.2, "end_angle": 2.9, "offset": [0, -48], "fill": False}, "Smile"),
        _step("set_color", {"color": "#FFB6C1"}, "Rosy cheeks"),
        _step("draw_filled_ellipse", {"rx": 8, "ry": 5, "offset": [-22, -52]}, "Left cheek"),
        _step("draw_filled_ellipse", {"rx": 8, "ry": 5, "offset": [22, -52]}, "Right cheek"),
        _step("screenshot", {"suffix": "child"}, "Screenshot"),
    ]


# ── Spider / Pająk ──────────────────────────────────────────────────

def _spider_steps() -> list[DrawStep]:
    """Spider with abdomen, head, eight legs, and eyes."""
    return [
        _step("set_color", {"color": "#000000"}, "Black legs"),
        _step("set_line_width", {"width": 3}),
        _step("draw_line", {"from_offset": [-12, 0], "to_offset": [-65, -55]}, "Leg L1"),
        _step("draw_line", {"from_offset": [-18, 8], "to_offset": [-75, 15]}, "Leg L2"),
        _step("draw_line", {"from_offset": [-18, 18], "to_offset": [-75, 55]}, "Leg L3"),
        _step("draw_line", {"from_offset": [-12, 25], "to_offset": [-65, 75]}, "Leg L4"),
        _step("draw_line", {"from_offset": [12, 0], "to_offset": [65, -55]}, "Leg R1"),
        _step("draw_line", {"from_offset": [18, 8], "to_offset": [75, 15]}, "Leg R2"),
        _step("draw_line", {"from_offset": [18, 18], "to_offset": [75, 55]}, "Leg R3"),
        _step("draw_line", {"from_offset": [12, 25], "to_offset": [65, 75]}, "Leg R4"),
        _step("set_color", {"color": "#1A1A1A"}, "Black body"),
        _step("draw_filled_ellipse", {"rx": 50, "ry": 35, "offset": [0, 15]}, "Abdomen"),
        _step("draw_filled_circle", {"radius": 28, "offset": [0, -35]}, "Head"),
        _step("set_color", {"color": "#CC0000"}, "Red marking"),
        _step("draw_filled_ellipse", {"rx": 8, "ry": 12, "offset": [0, 5]}, "Back marking"),
        _step("set_color", {"color": "#FFFFFF"}, "White eyes"),
        _step("draw_filled_circle", {"radius": 8, "offset": [-12, -40]}, "Left eye"),
        _step("draw_filled_circle", {"radius": 8, "offset": [12, -40]}, "Right eye"),
        _step("set_color", {"color": "#000000"}, "Black pupils"),
        _step("draw_filled_circle", {"radius": 4, "offset": [-10, -40]}, "Left pupil"),
        _step("draw_filled_circle", {"radius": 4, "offset": [10, -40]}, "Right pupil"),
        _step("set_color", {"color": "#000000"}, "Fangs"),
        _step("draw_line", {"from_offset": [-6, -22], "to_offset": [-10, -8]}, "Left fang"),
        _step("draw_line", {"from_offset": [6, -22], "to_offset": [10, -8]}, "Right fang"),
        _step("screenshot", {"suffix": "spider"}, "Screenshot"),
    ]


# ── Registry ─────────────────────────────────────────────────────────

# Maps (Polish regex pattern, English regex pattern) → (description, steps_fn)
OBJECT_BLUEPRINTS: list[dict[str, Any]] = [
    {
        "pattern": r"(?:zaj[aąę]c(?:a|em)?|kr[oó]lik(?:a|iem)?|rabbit|bunny)",
        "name": "rabbit",
        "description": "Draw a rabbit (body, head, ears, eyes, whiskers, tail)",
        "steps_fn": _rabbit_steps,
    },
    {
        "pattern": r"(?:kot(?:a|em|ka)?|cat|kitten|kitty|kotek)",
        "name": "cat",
        "description": "Draw a cat (body, head, ears, eyes, whiskers, tail)",
        "steps_fn": _cat_steps,
    },
    {
        "pattern": r"(?:pies|psa|psem|piesek|pieska|dog|puppy)",
        "name": "dog",
        "description": "Draw a dog (body, head, floppy ears, tongue, tail)",
        "steps_fn": _dog_steps,
    },
    {
        "pattern": r"(?:samoch[oó]d(?:em)?|auto(?:m)?|car|vehicle)",
        "name": "car",
        "description": "Draw a car (body, roof, windows, wheels, headlights)",
        "steps_fn": _car_steps,
    },
    {
        "pattern": r"(?:dom(?:ek|em|u)?|house|home|domek)",
        "name": "house",
        "description": "Draw a house (walls, roof, door, windows, chimney)",
        "steps_fn": _house_steps,
    },
    {
        "pattern": r"(?:drzew(?:o|a|em|ko)|tree)",
        "name": "tree",
        "description": "Draw a tree (trunk, foliage)",
        "steps_fn": _tree_steps,
    },
    {
        "pattern": r"(?:s[lł]o[nń]c(?:e|em)|sun)",
        "name": "sun",
        "description": "Draw a sun with rays and face",
        "steps_fn": _sun_steps,
    },
    {
        "pattern": r"(?:kwiat(?:ek|em|a)?|flower)",
        "name": "flower",
        "description": "Draw a flower (petals, stem, leaves)",
        "steps_fn": _flower_steps,
    },
    {
        "pattern": r"(?:gwiazd[aęeą]|gwiazdka|gwiazdkę|star)",
        "name": "star",
        "description": "Draw a five-pointed star",
        "steps_fn": _star_steps,
    },
    {
        "pattern": r"(?:serc(?:e|em|a)|serduszko|heart)",
        "name": "heart",
        "description": "Draw a heart shape",
        "steps_fn": _heart_steps,
    },
    {
        "pattern": r"(?:ryb[aęeką]|rybk[aęeą]|fish)",
        "name": "fish",
        "description": "Draw a fish (body, tail, fins, eye)",
        "steps_fn": _fish_steps,
    },
    {
        "pattern": r"(?:motyl(?:a|em|ek|ka)?|butterfly)",
        "name": "butterfly",
        "description": "Draw a butterfly (wings, body, antennae)",
        "steps_fn": _butterfly_steps,
    },
    {
        "pattern": r"(?:ba[lł]wan(?:a|em|ek|ka)?|snowman)",
        "name": "snowman",
        "description": "Draw a snowman (three balls, hat, scarf, arms)",
        "steps_fn": _snowman_steps,
    },
    {
        "pattern": r"(?:biedronk[aęeą]|ladybug)",
        "name": "ladybug",
        "description": "Draw a ladybug (body, dots, head, antennae, legs)",
        "steps_fn": _ladybug_steps,
    },
    {
        "pattern": r"(?:dziecko|dziecka|dzieckiem|child|boy|girl|ch[lł]op(?:iec|ca)|dziewczynk[aęeą]|dziewczyn[aęeą])",
        "name": "child",
        "description": "Draw a child (head, hair, shirt, arms, legs, face)",
        "steps_fn": _child_steps,
    },
    {
        "pattern": r"(?:paj[aąę]k(?:a|iem|iem)?|spider)",
        "name": "spider",
        "description": "Draw a spider (body, head, eight legs, eyes)",
        "steps_fn": _spider_steps,
    },
]


def lookup_blueprint(query: str) -> Optional[dict[str, Any]]:
    """Find a matching drawing blueprint for the given query.

    Args:
        query: Natural language query (Polish or English)

    Returns:
        Blueprint dict with 'name', 'description', 'steps_fn' or None
    """
    text = query.lower()
    for bp in OBJECT_BLUEPRINTS:
        if re.search(bp["pattern"], text):
            return bp
    return None


def get_blueprint_steps(query: str) -> Optional[list[DrawStep]]:
    """Get drawing steps for a matched blueprint.

    Args:
        query: Natural language query

    Returns:
        List of DrawStep objects or None if no blueprint matches
    """
    bp = lookup_blueprint(query)
    if bp:
        return bp["steps_fn"]()
    return None


def list_available_blueprints() -> list[str]:
    """Return list of available blueprint names."""
    return [bp["name"] for bp in OBJECT_BLUEPRINTS]
