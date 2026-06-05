"""LLM-based canvas planner for arbitrary object generation."""

from __future__ import annotations
import logging
from typing import Any

from .base import CanvasPlannerBase, CanvasPlanResult
from .json_parse import parse_canvas_steps_json
from .llm_client import call_canvas_llm

log = logging.getLogger("nlp2cmd.canvas_planner.llm")


class LLMCanvasPlanner(CanvasPlannerBase):
    """Generates drawing plans using LLM for arbitrary objects."""
    
    CANVAS_PROMPT_TEMPLATE = """\
Wygeneruj SZCZEGÓŁOWY plan rysowania obiektu "{object_name}" na canvas.
Obiekt powinien być rozpoznawalny i realistyczny — użyj wielu warstw.

DOSTĘPNE AKCJE (JSON array):
Kształty wypełnione:
- set_color: {{"color": "#RRGGBB"}}
- draw_filled_ellipse: {{"rx": N, "ry": N, "offset": [x,y], "rotation": rad}}
- draw_filled_circle: {{"radius": N, "offset": [x,y]}}
- draw_filled_rectangle: {{"width": N, "height": N, "offset": [x,y]}}
Kontury:
- draw_line: {{"from_offset": [x,y], "to_offset": [x,y]}}
- draw_circle: {{"radius": N, "offset": [x,y]}}
- draw_arc: {{"radius": N, "start_angle": rad, "end_angle": rad, "offset": [x,y], "fill": bool}}
Zaawansowane:
- draw_polygon: {{"points": [[x,y],...], "offset": [x,y], "fill": bool}}
- draw_bezier: {{"curves": [{{"type":"M","x":N,"y":N}},{{"type":"Q","cpx":N,"cpy":N,"x":N,"y":N}},{{"type":"C","cp1x":N,"cp1y":N,"cp2x":N,"cp2y":N,"x":N,"y":N}}], "fill": bool, "close": bool}}
- draw_svg_path: {{"d": "M0 0 L10 10...", "fill": bool, "scale": N}}
- set_line_width: {{"width": N}}
- screenshot: {{"suffix": "name"}}

ZASADY:
- offset [x,y] relatywny do środka canvas (0,0 = środek)
- Ujemne y = góra, dodatnie y = dół
- Rysuj od tyłu do przodu (tło → ciało → detale → oczy)
- Każda część ciała = osobny kształt z set_color
- Użyj realistycznych kolorów, proporcji i detali
- Minimum 12 kroków dla rozpoznawalnego obiektu
- Odpowiedz TYLKO tablicą JSON, BEZ markdown, BEZ komentarzy

Przykład (kot — 18 kroków):
[
  {{"action":"set_color","params":{{"color":"#808080"}}}},
  {{"action":"draw_filled_ellipse","params":{{"rx":80,"ry":60,"offset":[0,40]}}}},
  {{"action":"draw_filled_circle","params":{{"radius":45,"offset":[0,-35]}}}},
  {{"action":"draw_polygon","params":{{"points":[[-30,-10],[-45,-55],[-10,-30]],"offset":[0,-35],"fill":true}}}},
  {{"action":"draw_polygon","params":{{"points":[[30,-10],[45,-55],[10,-30]],"offset":[0,-35],"fill":true}}}},
  {{"action":"set_color","params":{{"color":"#FFB6C1"}}}},
  {{"action":"draw_polygon","params":{{"points":[[-28,-12],[-40,-48],[-14,-28]],"offset":[0,-35],"fill":true}}}},
  {{"action":"draw_polygon","params":{{"points":[[28,-12],[40,-48],[14,-28]],"offset":[0,-35],"fill":true}}}},
  {{"action":"set_color","params":{{"color":"#32CD32"}}}},
  {{"action":"draw_filled_ellipse","params":{{"rx":10,"ry":8,"offset":[-16,-40]}}}},
  {{"action":"draw_filled_ellipse","params":{{"rx":10,"ry":8,"offset":[16,-40]}}}},
  {{"action":"set_color","params":{{"color":"#000000"}}}},
  {{"action":"draw_filled_ellipse","params":{{"rx":4,"ry":7,"offset":[-16,-40]}}}},
  {{"action":"draw_filled_ellipse","params":{{"rx":4,"ry":7,"offset":[16,-40]}}}},
  {{"action":"set_color","params":{{"color":"#FF69B4"}}}},
  {{"action":"draw_polygon","params":{{"points":[[0,-4],[-5,4],[5,4]],"offset":[0,-25],"fill":true}}}},
  {{"action":"set_color","params":{{"color":"#000000"}}}},
  {{"action":"draw_line","params":{{"from_offset":[-15,-22],"to_offset":[-50,-30]}}}},
  {{"action":"draw_line","params":{{"from_offset":[-15,-20],"to_offset":[-50,-20]}}}},
  {{"action":"draw_line","params":{{"from_offset":[15,-22],"to_offset":[50,-30]}}}},
  {{"action":"draw_line","params":{{"from_offset":[15,-20],"to_offset":[50,-20]}}}},
  {{"action":"set_line_width","params":{{"width":8}}}},
  {{"action":"set_color","params":{{"color":"#808080"}}}},
  {{"action":"draw_bezier","params":{{"curves":[{{"type":"M","x":75,"y":40}},{{"type":"C","cp1x":110,"cp1y":20,"cp2x":120,"cp2y":-30,"x":90,"y":-50}}],"fill":false,"line_width":8}}}},
  {{"action":"screenshot","params":{{"suffix":"cat"}}}}
]
"""
    
    def plan(self, query: str, text: str, canvas_url: str = "https://jspaint.app") -> CanvasPlanResult | None:
        """Generate LLM-based drawing plan."""
        object_name = self._extract_object_name(text)
        
        canvas_prompt = self.CANVAS_PROMPT_TEMPLATE.format(object_name=object_name)
        
        log.info("[LLMCanvasPlanner] Generating plan for object: %s", object_name)
        
        try:
            steps_data = self._call_llm(canvas_prompt)
            if not steps_data:
                return None
            
            # Build full plan
            steps = self._build_full_plan(text, steps_data, object_name)
            
            return CanvasPlanResult(
                steps=steps,
                confidence=0.80,
                source="canvas_llm",
                estimated_time_ms=len(steps) * 600,
            )
            
        except Exception as e:
            log.warning("Canvas LLM call failed: %s", e)
            return None
    
    def _call_llm(self, prompt: str) -> list[dict[str, Any]] | None:
        """Call configured LLM (router or Ollama) with retry logic."""
        raw = None
        for attempt in range(self.config.max_retries + 1):
            try:
                raw = call_canvas_llm(prompt, self.config)
                if raw:
                    break
            except Exception as exc:
                if attempt < self.config.max_retries:
                    log.warning(
                        "Canvas LLM error (attempt %d/%d): %s",
                        attempt + 1,
                        self.config.max_retries + 1,
                        exc,
                    )
                    import time
                    time.sleep(1.0 * (attempt + 1))
                else:
                    raise

        if not raw:
            log.warning("Canvas LLM failed after %d attempts", self.config.max_retries + 1)
            return None

        return self._parse_response(raw)
    
    def _parse_response(self, raw: str) -> list[dict[str, Any]] | None:
        """Parse LLM JSON response with cleanup and truncation salvage."""
        steps_data = parse_canvas_steps_json(raw)
        if steps_data is None:
            log.warning("Canvas LLM returned invalid plan")
        return steps_data
    
    def _build_full_plan(self, text: str, steps_data: list, object_name: str) -> list[dict[str, Any]]:
        """Build complete plan with navigation and setup."""
        url = self._extract_canvas_url(text)
        
        steps: list[dict[str, Any]] = [
            {"action": "navigate", "params": {"url": url}, "description": f"Otwórz {url}"},
            {"action": "wait_for_canvas", "params": {}, "description": "Poczekaj na canvas"},
            {"action": "get_canvas_center", "params": {}, "description": "Pobierz środek canvas"},
        ]
        
        for s in steps_data:
            if not isinstance(s, dict):
                continue
            action = s.get("action", "")
            params = s.get("params", {})
            desc = s.get("description", f"{action}")
            if action and isinstance(params, dict):
                steps.append({
                    "action": action,
                    "params": params,
                    "description": desc,
                })
        
        # Ensure screenshot at end
        if not any(s.get("action") == "screenshot" for s in steps):
            steps.append({
                "action": "screenshot",
                "params": {"suffix": object_name.replace(" ", "_")},
                "description": "Zrób screenshot",
            })
        
        return steps
