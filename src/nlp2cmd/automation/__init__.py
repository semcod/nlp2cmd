"""
Automation package for NLP2CMD.

Provides advanced browser automation, mouse control, CAPTCHA solving,
API key extraction, and complex multi-step command planning.
"""

from nlp2cmd.automation.mouse_controller import MouseController, Point
from nlp2cmd.automation.env_extractor import EnvExtractor
from nlp2cmd.automation.captcha_solver import CaptchaSolver
from nlp2cmd.automation.complex_planner import ComplexCommandPlanner, ActionStep
from nlp2cmd.automation.action_planner import ActionPlanner, ActionPlan
from nlp2cmd.automation.step_validator import StepValidator, ValidationResult, StepMetrics
from nlp2cmd.automation.schema_fallback import SchemaFallback, FallbackContext, FallbackResult
from nlp2cmd.automation.firefox_sessions import FirefoxSessionImporter

__all__ = [
    "MouseController",
    "Point",
    "EnvExtractor",
    "CaptchaSolver",
    "ComplexCommandPlanner",
    "ActionStep",
    "ActionPlanner",
    "ActionPlan",
    "StepValidator",
    "ValidationResult",
    "StepMetrics",
    "SchemaFallback",
    "FallbackContext",
    "FallbackResult",
]
