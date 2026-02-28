import re

file_path = "/home/tom/github/wronai/nlp2cmd/src/nlp2cmd/automation/drawing_blueprints.py"
with open(file_path, "r") as f:
    content = f.read()

fox_code = """
# ── Fox / Lis ─────────────────────────────────────────────────────────

def _fox_steps() -> list[DrawStep]:
    \"\"\"Detailed fox drawing with head, ears, body, bushy tail, paws, and face.\"\"\"
    return [
        # Body - orange filled ellipse
        _step("set_color", {"color": "#D95E00"}, "Orange for fox body"),
        _step("draw_filled_ellipse", {"rx": 80, "ry": 50, "offset": [0, 30]}, "Body"),
        
        # Tail - large bushy ellipse on the right
        _step("draw_filled_ellipse", {"rx": 60, "ry": 25, "rotation": -0.3, "offset": [80, 20]}, "Bushy tail main"),
        # Tail tip - white
        _step("set_color", {"color": "#FFFFFF"}, "White for tail tip"),
        _step("draw_filled_ellipse", {"rx": 20, "ry": 15, "rotation": -0.3, "offset": [130, 10]}, "Tail tip"),
        
        # Head - orange circle/ellipse
        _step("set_color", {"color": "#D95E00"}, "Orange for head"),
        _step("draw_filled_circle", {"radius": 40, "offset": [-60, -20]}, "Head base"),
        
        # Snout/chin - white lower part of face
        _step("set_color", {"color": "#FFFFFF"}, "White for snout"),
        _step("draw_filled_ellipse", {"rx": 45, "ry": 25, "offset": [-65, -5]}, "Snout white part"),
        
        # Nose - small black tip
        _step("set_color", {"color": "#000000"}, "Black for nose"),
        _step("draw_filled_circle", {"radius": 5, "offset": [-110, -5]}, "Nose tip"),
        
        # Ears - orange triangles/polygons
        _step("set_color", {"color": "#D95E00"}, "Orange for ears"),
        _step("draw_polygon", {"points": [[-40, -50], [-30, -90], [-20, -50]]}, "Right ear"),
        _step("draw_polygon", {"points": [[-80, -50], [-70, -90], [-60, -50]]}, "Left ear"),
        
        # Inner ears - white/pink
        _step("set_color", {"color": "#FFC0CB"}, "Pink for inner ear"),
        _step("draw_polygon", {"points": [[-37, -55], [-30, -80], [-23, -55]]}, "Right inner ear"),
        _step("draw_polygon", {"points": [[-77, -55], [-70, -80], [-63, -55]]}, "Left inner ear"),
        
        # Eyes - black dots
        _step("set_color", {"color": "#000000"}, "Black for eyes"),
        _step("draw_filled_circle", {"radius": 4, "offset": [-75, -25]}, "Left eye"),
        _step("draw_filled_circle", {"radius": 4, "offset": [-45, -25]}, "Right eye"),
        
        # Legs - dark brown or black
        _step("set_color", {"color": "#331100"}, "Dark brown for legs"),
        _step("set_line_width", {"width": 10}, "Thick lines for legs"),
        _step("draw_line", {"from_offset": [-30, 70], "to_offset": [-30, 110]}, "Front leg 1"),
        _step("draw_line", {"from_offset": [-10, 70], "to_offset": [-10, 110]}, "Front leg 2"),
        _step("draw_line", {"from_offset": [30, 70], "to_offset": [30, 110]}, "Back leg 1"),
        _step("draw_line", {"from_offset": [50, 70], "to_offset": [50, 110]}, "Back leg 2"),
        
        # Paws - black ellipses
        _step("set_color", {"color": "#000000"}, "Black for paws"),
        _step("draw_filled_ellipse", {"rx": 12, "ry": 6, "offset": [-35, 110]}, "Front paw 1"),
        _step("draw_filled_ellipse", {"rx": 12, "ry": 6, "offset": [-15, 110]}, "Front paw 2"),
        _step("draw_filled_ellipse", {"rx": 12, "ry": 6, "offset": [25, 110]}, "Back paw 1"),
        _step("draw_filled_ellipse", {"rx": 12, "ry": 6, "offset": [45, 110]}, "Back paw 2"),
    ]
"""

# Insert fox before the list of OBJECT_BLUEPRINTS
if "def _fox_steps" not in content:
    content = content.replace("OBJECT_BLUEPRINTS = [", fox_code + "\nOBJECT_BLUEPRINTS = [")

# Add fox to OBJECT_BLUEPRINTS
fox_entry = """
    {
        "pattern": r"\\b(?:lis|fox|liska|liskiem|lisek)\\b",
        "name": "fox",
        "description": "Draw a fox (head, body, tail, ears, paws)",
        "steps_fn": _fox_steps,
    },"""

if '"name": "fox"' not in content:
    content = content.replace("OBJECT_BLUEPRINTS = [", "OBJECT_BLUEPRINTS = [" + fox_entry)

with open(file_path, "w") as f:
    f.write(content)
print("Added fox blueprint properly")
