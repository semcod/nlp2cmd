"""Blueprint planner for rich drawing blueprints with SVG paths."""

from __future__ import annotations
import logging
from typing import Any

from .base import CanvasPlannerBase, CanvasPlanResult

log = logging.getLogger("nlp2cmd.canvas_planner.blueprint")


class BlueprintPlanner(CanvasPlannerBase):
    """Uses rich drawing blueprints (SVG paths, polygons, beziers).
    
    Tries to match query against known blueprints in drawing_blueprints module.
    """
    
    def plan(self, query: str, text: str, canvas_url: str = "https://jspaint.app") -> CanvasPlanResult | None:
        """Find and use blueprint for drawing."""
        try:
            from nlp2cmd.automation.drawing_blueprints import lookup_blueprint
            
            bp = lookup_blueprint(text)
            if not bp:
                return None
            
            log.info("[BlueprintPlanner] Blueprint match: %s", bp["description"])
            
            # Get steps from blueprint
            steps_fn = bp.get("steps_fn")
            if not steps_fn:
                return None
            
            draw_steps = steps_fn()
            
            # Build full plan
            steps = self._build_full_plan(canvas_url, draw_steps)
            
            return CanvasPlanResult(
                steps=steps,
                confidence=0.95,
                source="canvas_blueprint",
                estimated_time_ms=len(steps) * 400,
            )
            
        except ImportError:
            log.debug("drawing_blueprints module not available")
            return None
        except Exception as e:
            log.warning("Blueprint planning failed: %s", e)
            return None
    
    def _build_full_plan(self, canvas_url: str, draw_steps: list) -> list[dict[str, Any]]:
        """Build complete plan with navigation and drawing steps."""
        steps: list[dict[str, Any]] = [
            {"action": "navigate", "params": {"url": canvas_url}, "description": f"Open {canvas_url}"},
            {"action": "wait_for_canvas", "params": {}, "description": "Wait for canvas"},
            {"action": "get_canvas_center", "params": {}, "description": "Get canvas center"},
        ]
        
        for ds in draw_steps:
            steps.append({
                "action": ds.action,
                "params": dict(ds.params) if ds.params else {},
                "description": ds.description,
            })
        
        return steps
