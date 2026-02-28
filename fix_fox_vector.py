import sys
from nlp2cmd.automation.vector_store import get_vector_store, DrawingPattern

store = get_vector_store()
# The previous search found something with 66% confidence, probably a generic animal like cat or spider.
# We want to insert the actual "fox" pattern we created in drawing_blueprints into the vector DB 
# so that the semantic search returns the fox steps with high confidence.

# Since we removed _fox_steps from drawing_blueprints, let's redefine it here and push to vector store

steps_dicts = [
    {"action": "set_color", "params": {"color": "#D95E00"}, "description": "Orange for fox body"},
    {"action": "draw_filled_ellipse", "params": {"rx": 80, "ry": 50, "offset": [0, 30]}, "description": "Body"},
    
    {"action": "draw_filled_ellipse", "params": {"rx": 60, "ry": 25, "rotation": -0.3, "offset": [80, 20]}, "description": "Bushy tail main"},
    {"action": "set_color", "params": {"color": "#FFFFFF"}, "description": "White for tail tip"},
    {"action": "draw_filled_ellipse", "params": {"rx": 20, "ry": 15, "rotation": -0.3, "offset": [130, 10]}, "description": "Tail tip"},
    
    {"action": "set_color", "params": {"color": "#D95E00"}, "description": "Orange for head"},
    {"action": "draw_filled_circle", "params": {"radius": 40, "offset": [-60, -20]}, "description": "Head base"},
    
    {"action": "set_color", "params": {"color": "#FFFFFF"}, "description": "White for snout"},
    {"action": "draw_filled_ellipse", "params": {"rx": 45, "ry": 25, "offset": [-65, -5]}, "description": "Snout white part"},
    
    {"action": "set_color", "params": {"color": "#000000"}, "description": "Black for nose"},
    {"action": "draw_filled_circle", "params": {"radius": 5, "offset": [-110, -5]}, "description": "Nose tip"},
    
    {"action": "set_color", "params": {"color": "#D95E00"}, "description": "Orange for ears"},
    {"action": "draw_polygon", "params": {"points": [[-40, -50], [-30, -90], [-20, -50]]}, "description": "Right ear"},
    {"action": "draw_polygon", "params": {"points": [[-80, -50], [-70, -90], [-60, -50]]}, "description": "Left ear"},
    
    {"action": "set_color", "params": {"color": "#FFC0CB"}, "description": "Pink for inner ear"},
    {"action": "draw_polygon", "params": {"points": [[-37, -55], [-30, -80], [-23, -55]]}, "description": "Right inner ear"},
    {"action": "draw_polygon", "params": {"points": [[-77, -55], [-70, -80], [-63, -55]]}, "description": "Left inner ear"},
    
    {"action": "set_color", "params": {"color": "#000000"}, "description": "Black for eyes"},
    {"action": "draw_filled_circle", "params": {"radius": 4, "offset": [-75, -25]}, "description": "Left eye"},
    {"action": "draw_filled_circle", "params": {"radius": 4, "offset": [-45, -25]}, "description": "Right eye"},
    
    {"action": "set_color", "params": {"color": "#331100"}, "description": "Dark brown for legs"},
    {"action": "set_line_width", "params": {"width": 10}, "description": "Thick lines for legs"},
    {"action": "draw_line", "params": {"from_offset": [-30, 70], "to_offset": [-30, 110]}, "description": "Front leg 1"},
    {"action": "draw_line", "params": {"from_offset": [-10, 70], "to_offset": [-10, 110]}, "description": "Front leg 2"},
    {"action": "draw_line", "params": {"from_offset": [30, 70], "to_offset": [30, 110]}, "description": "Back leg 1"},
    {"action": "draw_line", "params": {"from_offset": [50, 70], "to_offset": [50, 110]}, "description": "Back leg 2"},
    
    {"action": "set_color", "params": {"color": "#000000"}, "description": "Black for paws"},
    {"action": "draw_filled_ellipse", "params": {"rx": 12, "ry": 6, "offset": [-35, 110]}, "description": "Front paw 1"},
    {"action": "draw_filled_ellipse", "params": {"rx": 12, "ry": 6, "offset": [-15, 110]}, "description": "Front paw 2"},
    {"action": "draw_filled_ellipse", "params": {"rx": 12, "ry": 6, "offset": [25, 110]}, "description": "Back paw 1"},
    {"action": "draw_filled_ellipse", "params": {"rx": 12, "ry": 6, "offset": [45, 110]}, "description": "Back paw 2"},
]

fox_pattern = DrawingPattern(
    name="fox",
    description="lis fox lisek zwierzę animal orange head body tail ears paws",
    category="animal",
    steps=steps_dicts,
    tags=["fox", "lis", "animal", "zwierzę", "orange"],
    complexity=5,
    source="manual"
)

# First delete if exists to update
store.delete_pattern("fox")
store.add_pattern(fox_pattern)
print("Added fox to vector DB.")
