import json
import logging
import os
import re
from pathlib import Path
from typing import Optional, List, Dict, Any

from nlp2cmd.automation.action_planner import ActionStep

log = logging.getLogger(__name__)

class ShapePlanner:
    """Manages a knowledge base of shapes and generates new ones via LLM."""

    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = "llama3"):
        self.ollama_url = ollama_url
        self.model = model
        self.db_path = Path.home() / ".nlp2cmd" / "shapes_db.json"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.shapes_db = self._load_db()

    def _load_db(self) -> Dict[str, List[Dict[str, Any]]]:
        if self.db_path.exists():
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                log.warning(f"Failed to load shapes db: {e}")
        return {}

    def _save_db(self):
        try:
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(self.shapes_db, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log.warning(f"Failed to save shapes db: {e}")

    def get_or_generate_shape_steps(self, shape_name: str) -> Optional[List[ActionStep]]:
        shape_name = shape_name.lower().strip()
        
        # Check local knowledge base
        if shape_name in self.shapes_db:
            log.info(f"[ShapePlanner] Found shape '{shape_name}' in local knowledge base.")
            return [ActionStep(**step) for step in self.shapes_db[shape_name]]

        # Query LLM for the shape
        log.info(f"[ShapePlanner] Shape '{shape_name}' not found. Querying LLM...")
        steps_data = self._query_llm_for_shape(shape_name)
        
        if steps_data:
            # Save to knowledge base
            self.shapes_db[shape_name] = steps_data
            self._save_db()
            log.info(f"[ShapePlanner] Saved new shape '{shape_name}' to local knowledge base.")
            return [ActionStep(**step) for step in steps_data]
            
        return None

    def _query_llm_for_shape(self, shape_name: str) -> Optional[List[Dict[str, Any]]]:
        try:
            import requests
        except ImportError:
            log.warning("requests not available for ShapePlanner LLM call")
            return None

        prompt = f"""\
Jesteś ekspertem od rysowania na canvasie (jspaint). Twoim zadaniem jest narysowanie: "{shape_name}".
Rozłóż ten rysunek na podstawowe figury geometryczne i zwróć listę akcji w formacie JSON.
Nie używaj markdowna, odpowiedz SAMYM listem JSON.

Dostępne akcje:
- {{"action": "select_tool", "params": {{"tool": "ellipse/rectangle/line/brush/fill"}}}}
- {{"action": "set_color", "params": {{"color": "#RRGGBB"}}}}
- {{"action": "draw_ellipse", "params": {{"rx": 50, "ry": 30, "offset": [0, 0]}}}}
- {{"action": "draw_filled_ellipse", "params": {{"rx": 50, "ry": 30, "offset": [0, 0]}}}}
- {{"action": "draw_circle", "params": {{"radius": 20, "offset": [0, 0]}}}}
- {{"action": "draw_rectangle", "params": {{"width": 60, "height": 40, "offset": [0, 0]}}}}
- {{"action": "draw_line", "params": {{"from_offset": [0, 0], "to_offset": [10, 10]}}}}

Uwagi:
1. `offset` to przesunięcie [x, y] od środka płótna (0, 0 to środek). Zając może składać się z dużej elipsy (tułów), mniejszej (głowa przesunięta do góry), długich uszu itp.
2. Odpowiedź musi być poprawnym JSONem, będącym tablicą obiektów. Zwróć tylko JSON!
"""
        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 800},
                },
                timeout=45,
            )
            if resp.status_code != 200:
                return None
                
            raw = resp.json().get("response", "")
            # Strip markdown code fences if present
            raw = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
            raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)
            
            # Find the first '[' and last ']'
            start = raw.find('[')
            end = raw.rfind(']')
            if start != -1 and end != -1:
                raw = raw[start:end+1]
                
            steps_data = json.loads(raw)
            if isinstance(steps_data, list) and len(steps_data) > 0:
                return steps_data
        except Exception as e:
            log.warning(f"ShapePlanner LLM call failed: {e}")
            
        return None
