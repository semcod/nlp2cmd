"""
Core transformation logic for NLP2CMD framework.

This module contains the main NLP2CMD class and transformation
logic for converting natural language to domain-specific commands.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from nlp2cmd.adapters.base import BaseDSLAdapter
    from nlp2cmd.feedback import FeedbackAnalyzer
    from nlp2cmd.validators.base import BaseValidator

from .core_backends import NLPBackend, RuleBasedBackend
from .core_models import ExecutionPlan, TransformResult, TransformStatus

logger = logging.getLogger(__name__)


class NLP2CMD:
    """
    Main class for Natural Language to Command transformation.

    This class orchestrates the transformation of natural language input
    into domain-specific commands using adapters, validators, and NLP backends.
    """

    def __init__(
        self,
        adapter: BaseDSLAdapter,
        nlp_backend: Optional[NLPBackend] = None,
        validator: Optional[BaseValidator] = None,
        feedback_analyzer: Optional[FeedbackAnalyzer] = None,
        validation_mode: str = "normal",
        auto_fix: bool = False,
    ):
        """
        Initialize NLP2CMD instance.

        Args:
            adapter: DSL adapter for command generation
            nlp_backend: NLP processing backend (spaCy, LLM, or rule-based)
            validator: Command validator
            feedback_analyzer: Analyzer for feedback loop
            validation_mode: Validation strictness ("strict", "normal", "permissive")
            auto_fix: Whether to automatically fix detected issues
        """
        self.adapter = adapter
        self.validator = validator
        self.feedback_analyzer = feedback_analyzer
        self.validation_mode = validation_mode
        self.auto_fix = auto_fix
        
        # Initialize backend if not provided
        if nlp_backend is None:
            def _truthy_env(name: str) -> bool:
                v = os.environ.get(name)
                if not isinstance(v, str):
                    return False
                return v.strip().lower() in {"1", "true", "yes", "y", "on"}

            dynamic_registry = getattr(adapter, "registry", None)
            if adapter.DSL_NAME == "dynamic" and dynamic_registry is not None:
                try:
                    from nlp2cmd.nlp_enhanced import HybridNLPBackend

                    self.nlp_backend = HybridNLPBackend(schema_registry=dynamic_registry, config={})
                    import sys
                    print(f"[NLP2CMD] Using HybridNLPBackend with {len(dynamic_registry.get_all_commands())} commands", file=sys.stderr)
                except Exception as e:
                    # Fallback to rule-based with dynamic-generated rules
                    import sys
                    print(f"[NLP2CMD] Failed to import HybridNLPBackend: {e}", file=sys.stderr)
                    self.nlp_backend = RuleBasedBackend(rules={}, config={"dsl": adapter.DSL_NAME})
            else:
                if adapter.DSL_NAME == "shell":
                    # Try SemanticShellBackend first (intelligent NLP)
                    try:
                        from nlp2cmd.nlp_light import SemanticShellBackend
                        self.nlp_backend = SemanticShellBackend(config={"dsl": adapter.DSL_NAME})
                        import sys
                        print("[NLP2CMD] Using SemanticShellBackend for intelligent NLP processing", file=sys.stderr)
                    except Exception as e:
                        import sys
                        print(f"[NLP2CMD] Failed to import SemanticShellBackend: {e}, falling back to RuleBasedBackend", file=sys.stderr)
                        self.nlp_backend = RuleBasedBackend(
                            rules={k: list(v.get("patterns", [])) for k, v in adapter.INTENTS.items()},
                            config={"dsl": adapter.DSL_NAME},
                        )
                elif adapter.DSL_NAME == "shell" and _truthy_env("NLP2CMD_SEMANTIC_NLP"):
                    try:
                        from nlp2cmd.nlp_light import SemanticShellBackend

                        self.nlp_backend = SemanticShellBackend(config={"dsl": adapter.DSL_NAME})
                    except Exception:
                        self.nlp_backend = RuleBasedBackend(
                            rules={k: list(v.get("patterns", [])) for k, v in adapter.INTENTS.items()},
                            config={"dsl": adapter.DSL_NAME},
                        )
                else:
                    # Convert adapter INTENTS to rule format
                    rules = {}
                    for intent_name, intent_config in adapter.INTENTS.items():
                        if isinstance(intent_config, dict) and "patterns" in intent_config:
                            rules[intent_name] = intent_config["patterns"]
                        else:
                            rules[intent_name] = []
                    
                    self.nlp_backend = RuleBasedBackend(rules=rules, config={"dsl": adapter.DSL_NAME})
        else:
            self.nlp_backend = nlp_backend

    def transform(self, text: str, context: Optional[dict] = None) -> TransformResult:
        """
        Transform natural language text into a domain-specific command.

        Args:
            text: Natural language input text
            context: Additional context for transformation

        Returns:
            TransformResult with the generated command and metadata
        """
        try:
            # Generate execution plan
            plan = self.nlp_backend.generate_plan(text, context)
            
            # Normalize entities based on domain
            self._normalize_entities(plan)
            
            # Generate command using adapter
            command = self.adapter.generate_command(plan.intent, plan.entities)
            
            # Validate command if validator is available
            validation_errors = []
            validation_warnings = []
            
            if self.validator:
                try:
                    validation_result = self.validator.validate(command, plan)
                    validation_errors = validation_result.errors or []
                    validation_warnings = validation_result.warnings or []
                    
                    # Auto-fix if enabled and there are errors
                    if self.auto_fix and validation_errors:
                        fixed_command = self.validator.fix(command, plan)
                        if fixed_command != command:
                            command = fixed_command
                            validation_errors = []  # Clear errors after successful fix
                            
                except Exception as e:
                    validation_errors.append(f"Validation error: {e}")
            
            # Determine transformation status
            if validation_errors and self.validation_mode == "strict":
                status = TransformStatus.FAILED
            elif validation_errors:
                status = TransformStatus.PARTIAL
            else:
                status = TransformStatus.SUCCESS
            
            return TransformResult(
                status=status,
                command=command,
                intent=plan.intent,
                entities=plan.entities,
                confidence=plan.confidence,
                execution_plan=plan,
                errors=validation_errors,
                warnings=validation_warnings,
                metadata={
                    "domain": plan.domain,
                    "validation_mode": self.validation_mode,
                    "auto_fix_applied": self.auto_fix and bool(validation_errors),
                }
            )
            
        except Exception as e:
            logger.error(f"Transformation failed: {e}")
            return TransformResult(
                status=TransformStatus.ERROR,
                command=None,
                intent=None,
                confidence=0.0,
                errors=[f"Transformation error: {e}"],
            )

    def _normalize_entities(self, plan: ExecutionPlan) -> None:
        """Normalize entities based on domain and intent."""
        domain = plan.domain or self.adapter.DSL_NAME
        intent = plan.intent
        
        # Domain-specific normalization
        if domain == "shell":
            self._normalize_shell_entities(intent, plan.entities, plan.text)
        elif domain == "docker":
            self._normalize_docker_entities(intent, plan.entities)
        elif domain == "kubernetes":
            self._normalize_kubernetes_entities(intent, plan.entities)
        elif domain == "sql":
            self._normalize_sql_entities(intent, plan.entities)

    def _normalize_shell_entities(self, intent: str, normalized: dict[str, Any], full_text: str) -> None:
        """Normalize shell command entities."""
        # Handle path normalization
        if "path" in normalized:
            path = normalized["path"]
            if isinstance(path, str) and not path.startswith(('/', '~', '.', '-')):
                # Relative path, ensure it's properly formatted
                normalized["path"] = f"./{path}"
        
        # Build filters for find commands
        if intent in ["find", "search"]:
            filters = []
            
            # Extension filter
            ext_value = self._extract_shell_extension_value(normalized)
            if ext_value:
                filters.append({
                    "attribute": "name",
                    "operator": "like",
                    "value": f"*.{ext_value}"
                })
            
            # Size filter
            size_filter = self._build_shell_size_filter(normalized, full_text)
            if size_filter:
                filters.append(size_filter)
            
            # Age filter
            age_filter = self._build_shell_age_filter(normalized, full_text)
            if age_filter:
                filters.append(age_filter)
            
            if filters:
                normalized["filters"] = filters

    def _extract_shell_extension_value(self, normalized: dict[str, Any]) -> Optional[str]:
        """Extract file extension from entities."""
        ext = normalized.get("file_pattern")
        pattern = normalized.get("pattern")

        extension_value = None
        if ext and isinstance(ext, str):
            extension_value = ext

        if pattern and isinstance(pattern, str) and pattern.startswith("*."):
            pattern_ext = pattern[2:]
            if extension_value is None:
                extension_value = pattern_ext

        return extension_value

    def _build_shell_size_filter(
        self,
        normalized: dict[str, Any],
        full_text: str,
    ) -> Optional[dict[str, Any]]:
        """Build size filter for shell commands."""
        size = normalized.get("size")
        size_parsed = normalized.get("size_parsed")

        operator = ">"
        if "mniejsz" in full_text.lower() or "smaller" in full_text.lower():
            operator = "<"
        elif "większ" in full_text.lower() or "larger" in full_text.lower() or "bigger" in full_text.lower():
            operator = ">"

        if isinstance(size_parsed, dict) and "value" in size_parsed:
            return {
                "attribute": "size",
                "operator": operator,
                "value": f"{size_parsed.get('value')}{size_parsed.get('unit', '')}",
            }
        if isinstance(size, str) and size.strip():
            import re

            m = re.match(r"^(\d+)\s*([a-zA-Z]+)$", size.strip())
            if m:
                return {
                    "attribute": "size",
                    "operator": operator,
                    "value": f"{m.group(1)}{m.group(2)}",
                }
        return None

    def _build_shell_age_filter(
        self,
        normalized: dict[str, Any],
        full_text: str,
    ) -> Optional[dict[str, Any]]:
        """Build age filter for shell commands."""
        age = normalized.get("age")
        if not isinstance(age, dict) or "value" not in age:
            return None

        age_operator = ">"
        if "ostatnich" in full_text.lower() or "last" in full_text.lower() or "recent" in full_text.lower():
            age_operator = "<"
        elif "starsze" in full_text.lower() or "older" in full_text.lower():
            age_operator = ">"

        return {
            "attribute": "mtime",
            "operator": age_operator,
            "value": f"{age.get('value')}_days",
        }

    def _normalize_docker_entities(self, intent: str, normalized: dict[str, Any]) -> None:
        """Normalize Docker command entities."""
        if "port" in normalized and "ports" not in normalized:
            port = normalized.get("port")
            if isinstance(port, dict):
                normalized["ports"] = [port]
            elif port is not None:
                normalized["ports"] = [port]

        if "tail_lines" in normalized and "tail" not in normalized:
            try:
                normalized["tail"] = int(str(normalized.get("tail_lines")))
            except (TypeError, ValueError):
                pass

        env_var = normalized.get("env_var")
        if env_var and "environment" not in normalized:
            if isinstance(env_var, dict) and "name" in env_var and "value" in env_var:
                normalized["environment"] = {env_var["name"]: env_var["value"]}

        if intent == "container_run":
            normalized.setdefault("detach", True)

    def _normalize_kubernetes_entities(self, intent: str, normalized: dict[str, Any]) -> None:
        """Normalize Kubernetes command entities."""
        if intent == "get":
            rt = normalized.get("resource_type")
            if isinstance(rt, str):
                normalized["resource_type"] = rt

        if intent == "scale":
            replicas = normalized.get("replicas")
            if isinstance(replicas, str) and replicas.isdigit():
                normalized["replicas"] = int(replicas)

    def _normalize_sql_entities(self, intent: str, normalized: dict[str, Any]) -> None:
        """Normalize SQL command entities."""
        # Handle table name normalization
        if "table" in normalized:
            table = normalized["table"]
            if isinstance(table, str):
                # Remove quotes if present and add proper quoting
                table = table.strip('"\'')
                normalized["table"] = f'"{table}"'
        
        # Handle columns normalization
        if "columns" in normalized:
            columns = normalized["columns"]
            if isinstance(columns, list):
                # Quote column names
                normalized["columns"] = [f'"{col.strip('"\'')}"' for col in columns]
            elif isinstance(columns, str):
                normalized["columns"] = f'"{columns.strip('"\'')}"'

    def get_supported_intents(self) -> list[str]:
        """Get list of supported intents from the adapter."""
        return list(self.adapter.INTENTS.keys())

    def get_adapter_info(self) -> dict[str, Any]:
        """Get information about the current adapter."""
        return {
            "dsl_name": self.adapter.DSL_NAME,
            "description": getattr(self.adapter, "DESCRIPTION", ""),
            "supported_intents": self.get_supported_intents(),
            "backend_type": type(self.nlp_backend).__name__,
        }
