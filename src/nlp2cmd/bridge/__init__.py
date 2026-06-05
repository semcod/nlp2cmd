"""Bridge nlp2cmd to nlp2dsl integration packages (pact-ir, propact)."""

from nlp2cmd.bridge.intent_ir import detection_to_intent_ir, has_integration_packages
from nlp2cmd.bridge.integration import integration_enabled, plan_query_via_integration
from nlp2cmd.bridge.query_input import (
    QueryInputAnalysis,
    analyze_query_input,
    attach_query_input,
    display_query_analysis,
)

__all__ = [
    "QueryInputAnalysis",
    "analyze_query_input",
    "attach_query_input",
    "detection_to_intent_ir",
    "display_query_analysis",
    "has_integration_packages",
    "integration_enabled",
    "plan_query_via_integration",
]
