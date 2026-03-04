"""LLM-based canvas planner for arbitrary object generation."""

from __future__ import annotations
import json
import logging
import os
import re
from typing import Any

from .base import CanvasPlannerBase, CanvasPlanResult

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
        """Call Ollama LLM with retry logic."""
        try:
            import requests
        except ImportError:
            log.debug("requests not available")
            return None
        
        timeout = float(os.getenv("CANVAS_LLM_TIMEOUT", "60"))
        max_retries = int(os.getenv("CANVAS_LLM_RETRIES", "2"))
        
        resp = None
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                resp = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.3, "num_predict": 3000},
                    },
                    timeout=timeout,
                )
                if resp.status_code == 200:
                    break
                if attempt < max_retries:
                    log.warning("Canvas LLM returned %d, retrying...", resp.status_code)
                    import time
                    time.sleep(1.0 * (attempt + 1))
                    
            except requests.exceptions.Timeout as e:
                last_error = e
                if attempt < max_retries:
                    log.warning("Canvas LLM timeout (attempt %d/%d), retrying...", attempt + 1, max_retries + 1)
                    import time
                    time.sleep(1.0 * (attempt + 1))
                else:
                    raise
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    log.warning("Canvas LLM error (attempt %d/%d): %s", attempt + 1, max_retries + 1, e)
                    import time
                    time.sleep(1.0 * (attempt + 1))
                else:
                    raise
        
        if resp is None or resp.status_code != 200:
            log.warning("Canvas LLM failed after %d attempts", max_retries + 1)
            return None
        
        raw = resp.json().get("response", "").strip()
        return self._parse_response(raw)
    
    def _parse_response(self, raw: str) -> list[dict[str, Any]] | None:
        """Parse LLM JSON response with cleanup."""
        # Strip markdown fences
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
        raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)
        
        # Basic cleanup for common LLM JSON mistakes
        raw = raw.strip()
        if raw.startswith("```json"): raw = raw[7:]
        if raw.startswith("```"): raw = raw[3:]
        if raw.endswith("```"): raw = raw[:-3]
        raw = raw.strip()
        
        # Fix trailing commas
        raw = re.sub(r",(\s*[\}\]])", r"\1", raw)
        
        try:
            steps_data = json.loads(raw)
            if not isinstance(steps_data, list) or len(steps_data) < 2:
                log.warning("Canvas LLM returned invalid plan")
                return None
            return steps_data
        except json.JSONDecodeError as e:
            log.warning("Failed to parse LLM response: %s", e)
            return None
    
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
