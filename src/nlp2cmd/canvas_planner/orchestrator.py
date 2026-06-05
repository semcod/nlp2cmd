"""Canvas Planning Orchestrator — Coordinates multiple planning strategies.

LLM-first dynamic planning (default):
1. LLM generation (arbitrary objects via LLM_MODEL / router)
2. Vector DB semantic search (learned patterns cache)
3. Blueprint match (opt-in via CANVAS_USE_BLUEPRINTS=1)
4. Template matching (opt-in via CANVAS_USE_TEMPLATES=1)
5. Rule-based fallback (opt-out via CANVAS_USE_RULE_FALLBACK=0)
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
from .config import CanvasLLMConfig

log = logging.getLogger("nlp2cmd.canvas_planner.orchestrator")


class CanvasPlanningOrchestrator:
    """Orchestrates multiple canvas planners in priority order."""
    
    def __init__(self, ollama_url: str | None = None, model: str | None = None):
        self.config = CanvasLLMConfig.from_env(ollama_url=ollama_url, model=model)
        self.ollama_url = self.config.ollama_url
        self.model = self.config.model
        
        # Initialize planners
        self.blueprint = BlueprintPlanner(self.ollama_url, self.model)
        self.vector = VectorDBPlanner(self.ollama_url, self.model)
        self.llm = LLMCanvasPlanner(self.ollama_url, self.model)
        self.rule = RuleBasedCanvasPlanner(self.ollama_url, self.model)
    
    def plan(self, query: str, text: str | None = None, canvas_url: str = "https://jspaint.app") -> CanvasPlanResult | None:
        """Generate drawing plan using tiered strategy."""
        text = text or query.lower()

        # Opt-in handcrafted blueprints (CANVAS_USE_BLUEPRINTS=1)
        if self.config.use_blueprints:
            result = self._try_blueprint(query, text, canvas_url)
            if result:
                return result

        # Tier 1: LLM generation (primary dynamic path)
        result = self._try_llm(query, text, canvas_url)
        if result:
            return result
        
        # Tier 2: Vector DB semantic search (cached learned plans)
        result = self._try_vector_db(query, text, canvas_url)
        if result:
            return result
        
        if self.config.use_templates:
            result = self._try_template(query, text, canvas_url)
            if result:
                return result
        
        if self.config.use_rule_fallback:
            result = self._try_rule(query, text, canvas_url)
            if result:
                return result
        
        log.warning("[Orchestrator] All planning strategies failed for: %s", query[:60])
        return None
    
    def _try_blueprint(self, query: str, text: str, canvas_url: str) -> CanvasPlanResult | None:
        """Try blueprint matching (opt-in hardcoded fast path)."""
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
        """Try hardcoded template matching (opt-in)."""
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
                log.info("[Orchestrator] Using LLM plan (%s)", self.model)
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
