"""Shared constants for canvas adapter and execution."""

TOOLS_JSPAINT = {
    "pencil": {"selector": '.tool[title*="Pencil"]', "fallback_idx": 4},
    "brush": {"selector": '.tool[title*="Brush"]', "fallback_idx": 5},
    "fill": {"selector": '.tool[title*="Fill"]', "fallback_idx": 9},
    "eraser": {"selector": '.tool[title*="Eraser"]', "fallback_idx": 3},
    "pick_color": {"selector": '.tool[title*="Pick Color"]', "fallback_idx": 6},
    "magnifier": {"selector": '.tool[title*="Magnifier"]', "fallback_idx": 7},
    "select": {"selector": '.tool[title*="Select"]', "fallback_idx": 0},
    "free_select": {"selector": '.tool[title*="Free-Form Select"]', "fallback_idx": 1},
    "text": {"selector": '.tool[title*="Text"]', "fallback_idx": 10},
    "line": {"selector": '.tool[title*="Line"]', "fallback_idx": 11},
    "curve": {"selector": '.tool[title*="Curve"]', "fallback_idx": 12},
    "rectangle": {"selector": '.tool[title*="Rectangle"]', "fallback_idx": 13},
    "polygon": {"selector": '.tool[title*="Polygon"]', "fallback_idx": 14},
    "ellipse": {"selector": '.tool[title*="Ellipse"]', "fallback_idx": 15},
    "rounded_rectangle": {"selector": '.tool[title*="Rounded Rectangle"]', "fallback_idx": 16},
}
