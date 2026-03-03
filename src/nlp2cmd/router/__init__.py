"""
Decision Router for NLP2CMD.

Decides whether to use LLM Planner or direct action execution
based on query complexity, intent type, and entity count.
"""

from __future__ import annotations

import logging
import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class RoutingDecision(Enum):
    """Routing decision types."""
    
    DIRECT = "direct"  # Single action, no LLM needed
    LLM_PLANNER = "llm_planner"  # Complex task, needs LLM planning
    DYNAMIC_ORCHESTRATOR = "dynamic_orchestrator"  # LLM-driven orchestration with reflection
    CLARIFICATION = "clarification"  # Ambiguous, needs user input
    REJECT = "reject"  # Cannot process


@dataclass
class RoutingResult:
    """Result of routing decision."""
    
    decision: RoutingDecision
    reason: str
    confidence: float = 1.0
    suggested_actions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RouterConfig:
    """Configuration for Decision Router."""
    
    # Intents that can be handled directly (single action)
    simple_intents: list[str] = field(default_factory=lambda: [
        "select", "get", "list", "show", "count",
        "describe", "status", "version", "help",
    ])
    
    # Intents that always require LLM planning
    complex_intents: list[str] = field(default_factory=lambda: [
        "analyze", "compare", "migrate", "refactor",
        "optimize", "diagnose", "report", "audit",
    ])
    
    # Threshold for entity count - above this, use LLM
    entity_threshold: int = 5
    
    # Threshold for confidence - below this, ask for clarification
    confidence_threshold: float = 0.6
    
    # Keywords suggesting multi-step operations
    multi_step_keywords: list[str] = field(default_factory=lambda: [
        "then", "after", "and then", "followed by",
        "for each", "foreach", "all", "every",
        "first", "second", "finally", "next",
    ])
    
    # Keywords suggesting complex analysis
    complex_keywords: list[str] = field(default_factory=lambda: [
        "analyze", "compare", "correlate", "trend",
        "pattern", "anomaly", "summarize", "aggregate",
        "across", "between", "over time",
    ])


class DecisionRouter:
    """
    Routes incoming requests to appropriate processing path.
    
    Decides between:
    - DIRECT: Simple queries that map to single action
    - LLM_PLANNER: Complex queries requiring multi-step planning
    - CLARIFICATION: Ambiguous queries needing user input
    - REJECT: Queries that cannot be processed
    """
    
    def __init__(self, config: Optional[RouterConfig] = None):
        """
        Initialize Decision Router.
        
        Args:
            config: Router configuration
        """
        config_provided = config is not None
        self.config = config or RouterConfig()
        self._intent_action_map: dict[str, str] = {}
        self._register_default_mappings()
        if not config_provided:
            self._load_config_from_data()
    
    def _register_default_mappings(self) -> None:
        """Register default intent to action mappings."""
        self._intent_action_map = {
            # SQL intents
            "select": "sql_select",
            "insert": "sql_insert",
            "update": "sql_update",
            "delete": "sql_delete",
            "aggregate": "sql_aggregate",
            
            # Shell intents
            "file_search": "shell_find",
            "file_operation": "shell_file_op",
            "process_monitoring": "shell_process",
            "network": "shell_network",
            
            # Docker intents
            "container_run": "docker_run",
            "container_stop": "docker_stop",
            "container_list": "docker_ps",
            "image_build": "docker_build",
            
            # Kubernetes intents
            "get": "k8s_get",
            "describe": "k8s_describe",
            "scale": "k8s_scale",
            "logs": "k8s_logs",
        }

    def _load_config_from_data(self) -> None:
        """Load router configuration from data/router_config.json (optional)."""

        def _candidate_paths() -> list[Path]:
            # 1) CWD-based (common during dev)
            yield Path("data") / "router_config.json"
            yield Path("./data") / "router_config.json"

            # 2) Repo-based (when imported as a module)
            try:
                repo_root = Path(__file__).resolve().parents[4]
                yield repo_root / "data" / "router_config.json"
            except Exception:
                return

        cfg_path: Optional[Path] = None
        for p in _candidate_paths():
            try:
                if p.exists() and p.is_file():
                    cfg_path = p
                    break
            except Exception:
                continue

        if not cfg_path:
            return

        try:
            raw = json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            return

        if not isinstance(raw, dict):
            return

        # Update config lists/thresholds (keep defaults if invalid)
        if isinstance(raw.get("simple_intents"), list):
            self.config.simple_intents = [str(x) for x in raw["simple_intents"] if isinstance(x, str) and x.strip()]

        if isinstance(raw.get("complex_intents"), list):
            self.config.complex_intents = [str(x) for x in raw["complex_intents"] if isinstance(x, str) and x.strip()]

        if isinstance(raw.get("multi_step_keywords"), list):
            self.config.multi_step_keywords = [str(x) for x in raw["multi_step_keywords"] if isinstance(x, str) and x.strip()]

        if isinstance(raw.get("complex_keywords"), list):
            self.config.complex_keywords = [str(x) for x in raw["complex_keywords"] if isinstance(x, str) and x.strip()]

        et = raw.get("entity_threshold")
        if isinstance(et, int) and et > 0:
            self.config.entity_threshold = et

        ct = raw.get("confidence_threshold")
        if isinstance(ct, (int, float)) and 0.0 <= float(ct) <= 1.0:
            self.config.confidence_threshold = float(ct)

        # Intent → action mapping
        intent_map = raw.get("intent_action_map")
        if isinstance(intent_map, dict):
            for k, v in intent_map.items():
                if isinstance(k, str) and k.strip() and isinstance(v, str) and v.strip():
                    self._intent_action_map[k.strip()] = v.strip()
    
    def route(
        self,
        intent: str,
        entities: dict[str, Any],
        text: str,
        confidence: float = 1.0,
        context: Optional[dict[str, Any]] = None,
    ) -> RoutingResult:
        """
        Determine routing for a request.
        
        Args:
            intent: Detected intent
            entities: Extracted entities
            text: Original input text
            confidence: NLP confidence score
            context: Additional context
            
        Returns:
            RoutingResult with decision and metadata
        """
        context = context or {}
        text_lower = text.lower()
        
        # Check for rejection conditions
        if intent == "unknown" and confidence < 0.3:
            return RoutingResult(
                decision=RoutingDecision.REJECT,
                reason="Could not understand the request",
                confidence=confidence,
            )
        
        # Check confidence threshold
        if confidence < self.config.confidence_threshold:
            return RoutingResult(
                decision=RoutingDecision.CLARIFICATION,
                reason=f"Low confidence ({confidence:.0%}), need clarification",
                confidence=confidence,
                metadata={"original_intent": intent},
            )
        
        # Check for multi-step keywords
        if self._has_multi_step_indicators(text_lower):
            return RoutingResult(
                decision=RoutingDecision.LLM_PLANNER,
                reason="Multi-step operation detected",
                confidence=confidence,
                suggested_actions=self._suggest_actions(intent, entities),
                metadata={"multi_step": True},
            )
        
        # Check for complex keywords
        if self._has_complex_indicators(text_lower):
            return RoutingResult(
                decision=RoutingDecision.LLM_PLANNER,
                reason="Complex analysis required",
                confidence=confidence,
                suggested_actions=self._suggest_actions(intent, entities),
                metadata={"complex_analysis": True},
            )
        
        # Check if intent is always complex
        if intent in self.config.complex_intents:
            return RoutingResult(
                decision=RoutingDecision.LLM_PLANNER,
                reason=f"Intent '{intent}' requires planning",
                confidence=confidence,
                suggested_actions=self._suggest_actions(intent, entities),
            )
        
        # Check entity count threshold
        if len(entities) > self.config.entity_threshold:
            return RoutingResult(
                decision=RoutingDecision.LLM_PLANNER,
                reason=f"High entity count ({len(entities)}) suggests complex query",
                confidence=confidence,
                suggested_actions=self._suggest_actions(intent, entities),
            )
        
        # Check for joins or relations (SQL specific)
        if "joins" in entities or "relations" in entities:
            return RoutingResult(
                decision=RoutingDecision.LLM_PLANNER,
                reason="Query involves multiple tables/relations",
                confidence=confidence,
                suggested_actions=self._suggest_actions(intent, entities),
            )
        
        # Simple intent - direct execution
        if intent in self.config.simple_intents:
            action = self._intent_action_map.get(intent, intent)
            return RoutingResult(
                decision=RoutingDecision.DIRECT,
                reason=f"Simple intent '{intent}' maps to single action",
                confidence=confidence,
                suggested_actions=[action],
            )
        
        # Default: use dynamic orchestrator (LLM-driven planning + reflection)
        if self._orchestrator_available():
            return RoutingResult(
                decision=RoutingDecision.DYNAMIC_ORCHESTRATOR,
                reason="Using dynamic LLM orchestrator with reflection",
                confidence=confidence,
                suggested_actions=self._suggest_actions(intent, entities),
                metadata={"orchestrator": True},
            )

        return RoutingResult(
            decision=RoutingDecision.LLM_PLANNER,
            reason="Unknown intent pattern, using LLM planner",
            confidence=confidence,
            suggested_actions=self._suggest_actions(intent, entities),
        )
    
    def _has_multi_step_indicators(self, text: str) -> bool:
        """Check if text contains multi-step operation indicators."""
        return any(kw in text for kw in self.config.multi_step_keywords)
    
    def _has_complex_indicators(self, text: str) -> bool:
        """Check if text contains complex analysis indicators."""
        return any(kw in text for kw in self.config.complex_keywords)
    
    def _suggest_actions(
        self,
        intent: str,
        entities: dict[str, Any],
    ) -> list[str]:
        """Suggest possible actions based on intent and entities."""
        actions = []
        
        # Primary action from intent
        if intent in self._intent_action_map:
            actions.append(self._intent_action_map[intent])
        
        # Additional actions based on entities
        if "aggregations" in entities:
            actions.append("aggregate_results")
        
        if "ordering" in entities or "limit" in entities:
            actions.append("sort_and_limit")
        
        if "joins" in entities:
            actions.append("join_tables")
        
        return actions
    
    def register_intent_mapping(self, intent: str, action: str) -> None:
        """
        Register a new intent to action mapping.
        
        Args:
            intent: Intent name
            action: Action name
        """
        self._intent_action_map[intent] = action
    
    def add_simple_intent(self, intent: str) -> None:
        """Add an intent to the simple intents list."""
        if intent not in self.config.simple_intents:
            self.config.simple_intents.append(intent)
    
    def add_complex_intent(self, intent: str) -> None:
        """Add an intent to the complex intents list."""
        if intent not in self.config.complex_intents:
            self.config.complex_intents.append(intent)

    @staticmethod
    def _orchestrator_available() -> bool:
        """Check if the dynamic orchestration engine is available."""
        try:
            from nlp2cmd.orchestration import Orchestrator  # noqa: F401
            return True
        except ImportError:
            return False


__all__ = [
    "DecisionRouter",
    "RoutingDecision",
    "RoutingResult",
    "RouterConfig",
]
