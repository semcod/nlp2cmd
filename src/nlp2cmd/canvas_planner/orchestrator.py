"""Canvas Planning Orchestrator — Coordinates multiple planning strategies.

This orchestrator implements a tiered approach:
1. Blueprint match (highest quality, predefined)
2. Vector DB semantic search (learned patterns)
3. Template matching (hardcoded patterns from complex_planner)
4. LLM generation (arbitrary objects)
5. Rule-based fallback (when LLM unavailable)
"""

from __future__ import annotations
import logging
import re
from typing import Any

from .base import CanvasPlannerBase, CanvasPlanResult
from .rule_planner import RuleBasedCanvasPlanner
from .llm_planner import LLMCanvasPlanner
from .vector_planner import VectorDBPlanner
from .blueprint_planner import BlueprintPlanner

log = logging.getLogger("nlp2cmd.canvas_planner.orchestrator")


class CanvasPlanningOrchestrator:
    """Orchestrates multiple canvas planners in priority order."""
    
    def __init__(self, ollama_url: str | None = None, model: str | None = None):
        self.ollama_url = ollama_url
        self.model = model
        
        # Initialize planners
        self.blueprint = BlueprintPlanner(ollama_url, model)
        self.vector = VectorDBPlanner(ollama_url, model)
        self.llm = LLMCanvasPlanner(ollama_url, model)
        self.rule = RuleBasedCanvasPlanner(ollama_url, model)
    
    def plan(self, query: str, text: str | None = None, canvas_url: str = "https://jspaint.app") -> CanvasPlanResult | None:
        """Generate drawing plan using tiered strategy.
        
        Args:
            query: Original query string
            text: Lowercase text for matching (defaults to query.lower())
            canvas_url: Target canvas URL
            
        Returns:
            CanvasPlanResult or None if all strategies fail
        """
        text = text or query.lower()
        
        # Tier 1: Blueprint match (highest quality)
        result = self._try_blueprint(query, text, canvas_url)
        if result:
            return result
        
        # Tier 2: Vector DB semantic search
        result = self._try_vector_db(query, text, canvas_url)
        if result:
            return result
        
        # Tier 3: Template matching
        result = self._try_template(query, text, canvas_url)
        if result:
            return result
        
        # Tier 4: LLM generation
        result = self._try_llm(query, text, canvas_url)
        if result:
            return result
        
        # Tier 5: Rule-based fallback
        result = self._try_rule(query, text, canvas_url)
        if result:
            return result
        
        log.warning("[Orchestrator] All planning strategies failed for: %s", query[:60])
        return None
    
    def _try_blueprint(self, query: str, text: str, canvas_url: str) -> CanvasPlanResult | None:
        """Try blueprint matching."""
        try:
            result = self.blueprint.plan(query, text, canvas_url)
            if result:
                log.info("[Orchestrator] Using blueprint plan")
                return result
        except Exception as e:
            log.debug("Blueprint planner failed: %s", e)
        return None
    
    def _try_vector_db(self, query: str, text: str, canvas_url: str) -> CanvasPlanResult | None:
        """Try vector DB search."""
        try:
            if not self.vector.is_available():
                return None
            
            result = self.vector.plan(query, text, canvas_url)
            if result:
                # Quality check: must have enough drawing steps
                drawing_steps = [s for s in result.steps if s.get("action", "").startswith("draw_")]
                if len(drawing_steps) >= 8:
                    log.info("[Orchestrator] Using vector DB plan (%d drawing steps)", len(drawing_steps))
                    return result
                else:
                    log.info("[Orchestrator] Vector DB plan too simple (%d steps), trying next", len(drawing_steps))
        except Exception as e:
            log.debug("Vector DB planner failed: %s", e)
        return None
    
    def _try_template(self, query: str, text: str, canvas_url: str) -> CanvasPlanResult | None:
        """Try hardcoded template matching."""
        try:
            from nlp2cmd.automation.complex_planner import DRAWING_PATTERNS
            
            for template in DRAWING_PATTERNS:
                if re.search(template["pattern"], text):
                    log.info("[Orchestrator] Using template: %s", template["description"])
                    steps = []
                    for cstep in template["steps"]:
                        steps.append({
                            "action": cstep.action,
                            "params": dict(cstep.params) if cstep.params else {},
                            "description": cstep.description,
                        })
                    
                    return CanvasPlanResult(
                        steps=steps,
                        confidence=0.92,
                        source="canvas_template",
                        estimated_time_ms=sum(
                            getattr(s, "wait_after_ms", 0) for s in template["steps"]
                        ) + len(steps) * 500,
                    )
        except ImportError:
            log.debug("complex_planner not available for templates")
        except Exception as e:
            log.debug("Template matching failed: %s", e)
        return None
    
    def _try_llm(self, query: str, text: str, canvas_url: str) -> CanvasPlanResult | None:
        """Try LLM-based generation."""
        try:
            result = self.llm.plan(query, text, canvas_url)
            if result:
                log.info("[Orchestrator] Using LLM plan")
                return result
        except Exception as e:
            log.debug("LLM planner failed: %s", e)
        return None
    
    def _try_rule(self, query: str, text: str, canvas_url: str) -> CanvasPlanResult | None:
        """Try rule-based fallback."""
        try:
            result = self.rule.plan(query, text, canvas_url)
            if result:
                log.info("[Orchestrator] Using rule-based plan")
                return result
        except Exception as e:
            log.debug("Rule planner failed: %s", e)
        return None
