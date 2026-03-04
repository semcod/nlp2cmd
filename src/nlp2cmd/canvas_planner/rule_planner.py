"""Rule-based canvas planner for simple shapes."""

from __future__ import annotations
from typing import Any

from .base import CanvasPlannerBase, CanvasPlanResult


class RuleBasedCanvasPlanner(CanvasPlannerBase):
    """Generates drawing plans using hardcoded shape rules.
    
    This is a fallback when LLM or blueprints are unavailable.
    Uses keyword matching to determine shape composition.
    """
    
    def plan(self, query: str, text: str, canvas_url: str = "https://jspaint.app") -> CanvasPlanResult | None:
        """Generate rule-based plan for drawing an object."""
        object_name = self._extract_object_name(text)
        obj_lower = object_name.lower()
        
        steps = self._build_base_steps(canvas_url)
        
        # Object category detection and shape rules
        if any(w in obj_lower for w in ["zając", "zajac", "królik", "krolik", "rabbit", "bunny"]):
            steps.extend(self._rabbit_shape())
        elif any(w in obj_lower for w in ["samochód", "samochod", "auto", "car", "pojazd", "vehicle"]):
            steps.extend(self._car_shape())
        elif any(w in obj_lower for w in ["dom", "house", "budynek", "building", "chatka", "cottage"]):
            steps.extend(self._house_shape())
        elif any(w in obj_lower for w in ["słońce", "slonce", "sun", "gwiazda", "star"]):
            steps.extend(self._sun_shape())
        elif any(w in obj_lower for w in ["drzewo", "tree", "las", "forest", "sosna", "pine"]):
            steps.extend(self._tree_shape())
        else:
            steps.extend(self._generic_shape(object_name))
        
        return CanvasPlanResult(
            steps=steps,
            confidence=0.75,
            source="canvas_rule_based",
            estimated_time_ms=len(steps) * 400,
        )
    
    def _build_base_steps(self, canvas_url: str) -> list[dict[str, Any]]:
        """Build common navigation and setup steps."""
        return [
            {"action": "navigate", "params": {"url": canvas_url}, "description": f"Otwórz {canvas_url}"},
            {"action": "wait_for_canvas", "params": {}, "description": "Poczekaj na canvas"},
            {"action": "get_canvas_center", "params": {}, "description": "Pobierz środek canvas"},
        ]
    
    def _rabbit_shape(self) -> list[dict[str, Any]]:
        """Rabbit: tall body, long ears, small head."""
        return [
            {"action": "select_tool", "params": {"tool": "ellipse"}, "description": "Wybierz elipsę"},
            {"action": "set_color", "params": {"color": "#D2B48C"}, "description": "Kolor: beżowy"},
            {"action": "draw_filled_ellipse", "params": {"rx": 50, "ry": 80, "relative_to": "center"}, "description": "Ciało zająca"},
            {"action": "set_color", "params": {"color": "#FFE4B5"}, "description": "Kolor: jasny beż"},
            {"action": "draw_filled_circle", "params": {"radius": 35, "offset": [0, -90]}, "description": "Głowa"},
            {"action": "set_color", "params": {"color": "#D2B48C"}, "description": "Kolor: beżowy"},
            {"action": "draw_polygon", "params": {"points": [[-15, 0], [-35, -50], [0, -15]], "offset": [-20, -120], "fill": True}, "description": "Lewe ucho"},
            {"action": "draw_polygon", "params": {"points": [[15, 0], [35, -50], [0, -15]], "offset": [20, -120], "fill": True}, "description": "Prawe ucho"},
            {"action": "set_color", "params": {"color": "#000000"}, "description": "Kolor: czarny"},
            {"action": "draw_circle", "params": {"radius": 5, "offset": [-12, -95]}, "description": "Lewe oko"},
            {"action": "draw_circle", "params": {"radius": 5, "offset": [12, -95]}, "description": "Prawe oko"},
            {"action": "draw_circle", "params": {"radius": 3, "offset": [0, -85]}, "description": "Nos"},
            {"action": "draw_line", "params": {"from_offset": [-15, -105], "to_offset": [15, -105]}, "description": "Wąsy"},
            {"action": "screenshot", "params": {"suffix": "rabbit"}, "description": "Zrzut ekranu"},
        ]
    
    def _car_shape(self) -> list[dict[str, Any]]:
        """Car: rectangle body, circles for wheels."""
        return [
            {"action": "select_tool", "params": {"tool": "ellipse"}, "description": "Wybierz elipsę"},
            {"action": "set_color", "params": {"color": "#FF0000"}, "description": "Kolor: czerwony"},
            {"action": "draw_filled_ellipse", "params": {"rx": 90, "ry": 40, "relative_to": "center"}, "description": "Karoseria"},
            {"action": "set_color", "params": {"color": "#87CEEB"}, "description": "Kolor: niebieski"},
            {"action": "draw_filled_ellipse", "params": {"rx": 50, "ry": 25, "offset": [20, -30]}, "description": "Szyby"},
            {"action": "set_color", "params": {"color": "#333333"}, "description": "Kolor: czarny"},
            {"action": "draw_filled_circle", "params": {"radius": 25, "offset": [-50, 30]}, "description": "Lewe koło"},
            {"action": "draw_filled_circle", "params": {"radius": 25, "offset": [50, 30]}, "description": "Prawe koło"},
            {"action": "set_color", "params": {"color": "#888888"}, "description": "Kolor: szary"},
            {"action": "draw_circle", "params": {"radius": 12, "offset": [-50, 30]}, "description": "Felga lewa"},
            {"action": "draw_circle", "params": {"radius": 12, "offset": [50, 30]}, "description": "Felga prawa"},
            {"action": "screenshot", "params": {"suffix": "car"}, "description": "Zrzut ekranu"},
        ]
    
    def _house_shape(self) -> list[dict[str, Any]]:
        """House: rectangle body, triangle roof."""
        return [
            {"action": "select_tool", "params": {"tool": "ellipse"}, "description": "Wybierz elipsę"},
            {"action": "set_color", "params": {"color": "#F4A460"}, "description": "Kolor: brązowy"},
            {"action": "draw_filled_ellipse", "params": {"rx": 70, "ry": 60, "relative_to": "center"}, "description": "Ściany domu"},
            {"action": "set_color", "params": {"color": "#8B4513"}, "description": "Kolor: ciemny brąz"},
            {"action": "draw_polygon", "params": {"points": [[-70, -60], [0, -120], [70, -60]], "offset": [0, 0], "fill": True}, "description": "Dach trójkątny"},
            {"action": "set_color", "params": {"color": "#8B4513"}, "description": "Kolor: ciemny brąz"},
            {"action": "draw_filled_ellipse", "params": {"rx": 20, "ry": 30, "offset": [0, 15]}, "description": "Drzwi"},
            {"action": "set_color", "params": {"color": "#87CEEB"}, "description": "Kolor: niebieski"},
            {"action": "draw_filled_circle", "params": {"radius": 15, "offset": [-35, -30]}, "description": "Okno lewe"},
            {"action": "draw_filled_circle", "params": {"radius": 15, "offset": [35, -30]}, "description": "Okno prawe"},
            {"action": "screenshot", "params": {"suffix": "house"}, "description": "Zrzut ekranu"},
        ]
    
    def _sun_shape(self) -> list[dict[str, Any]]:
        """Sun: circle center with radiating lines."""
        return [
            {"action": "select_tool", "params": {"tool": "ellipse"}, "description": "Wybierz elipsę"},
            {"action": "set_color", "params": {"color": "#FFD700"}, "description": "Kolor: złoty"},
            {"action": "draw_filled_circle", "params": {"radius": 60, "offset": [0, 0], "relative_to": "center"}, "description": "Słońce"},
            {"action": "set_color", "params": {"color": "#FFA500"}, "description": "Kolor: pomarańczowy"},
            {"action": "draw_line", "params": {"from_offset": [0, -70], "to_offset": [0, -100]}, "description": "Promień górny"},
            {"action": "draw_line", "params": {"from_offset": [50, -50], "to_offset": [70, -70]}, "description": "Promień górny-prawy"},
            {"action": "draw_line", "params": {"from_offset": [70, 0], "to_offset": [100, 0]}, "description": "Promień prawy"},
            {"action": "draw_line", "params": {"from_offset": [50, 50], "to_offset": [70, 70]}, "description": "Promień dolny-prawy"},
            {"action": "draw_line", "params": {"from_offset": [0, 70], "to_offset": [0, 100]}, "description": "Promień dolny"},
            {"action": "draw_line", "params": {"from_offset": [-50, 50], "to_offset": [-70, 70]}, "description": "Promień dolny-lewy"},
            {"action": "draw_line", "params": {"from_offset": [-70, 0], "to_offset": [-100, 0]}, "description": "Promień lewy"},
            {"action": "draw_line", "params": {"from_offset": [-50, -50], "to_offset": [-70, -70]}, "description": "Promień górny-lewy"},
            {"action": "screenshot", "params": {"suffix": "sun"}, "description": "Zrzut ekranu"},
        ]
    
    def _tree_shape(self) -> list[dict[str, Any]]:
        """Tree: brown rectangle trunk, green triangle/ellipse for foliage."""
        return [
            {"action": "select_tool", "params": {"tool": "ellipse"}, "description": "Wybierz elipsę"},
            {"action": "set_color", "params": {"color": "#8B4513"}, "description": "Kolor: brązowy"},
            {"action": "draw_filled_ellipse", "params": {"rx": 20, "ry": 50, "offset": [0, 40]}, "description": "Pień"},
            {"action": "set_color", "params": {"color": "#228B22"}, "description": "Kolor: zielony"},
            {"action": "draw_filled_ellipse", "params": {"rx": 70, "ry": 60, "offset": [0, -40]}, "description": "Korona dolna"},
            {"action": "draw_filled_ellipse", "params": {"rx": 50, "ry": 50, "offset": [0, -80]}, "description": "Korona górna"},
            {"action": "screenshot", "params": {"suffix": "tree"}, "description": "Zrzut ekranu"},
        ]
    
    def _generic_shape(self, object_name: str) -> list[dict[str, Any]]:
        """Generic object: simple ellipse/circle composition."""
        # Use object name length to determine size
        size_factor = min(40 + len(object_name) * 5, 100)
        return [
            {"action": "select_tool", "params": {"tool": "ellipse"}, "description": "Wybierz elipsę"},
            {"action": "set_color", "params": {"color": "#4169E1"}, "description": "Kolor: niebieski"},
            {"action": "draw_filled_ellipse", "params": {"rx": size_factor, "ry": size_factor * 0.8, "relative_to": "center"}, "description": f"Ciało: {object_name}"},
            {"action": "set_color", "params": {"color": "#FFD700"}, "description": "Kolor: złoty"},
            {"action": "draw_filled_circle", "params": {"radius": size_factor * 0.4, "offset": [0, -size_factor * 0.9]}, "description": "Głowa"},
            {"action": "set_color", "params": {"color": "#000000"}, "description": "Kolor: czarny"},
            {"action": "draw_circle", "params": {"radius": 5, "offset": [-size_factor*0.15, -size_factor*0.9]}, "description": "Oko lewe"},
            {"action": "draw_circle", "params": {"radius": 5, "offset": [size_factor*0.15, -size_factor*0.9]}, "description": "Oko prawe"},
            {"action": "screenshot", "params": {"suffix": object_name.replace(" ", "_")}, "description": "Zrzut ekranu"},
        ]
