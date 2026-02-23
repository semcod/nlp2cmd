"""
Core module for NLP2CMD framework.

This module contains the main NLP2CMD class and related components
for transforming natural language into domain-specific commands.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Optional
from pathlib import Path

_core_pkg_dir = Path(__file__).resolve().parent / "core"
if _core_pkg_dir.is_dir():
    __path__ = [str(_core_pkg_dir)]
    if __spec__ is not None:
        __spec__.submodule_search_locations = __path__
    __package__ = __name__

try:
    from pydantic import BaseModel, Field
except ImportError:  # pragma: no cover
    import copy
    from dataclasses import dataclass as _dataclass

    @_dataclass
    class _FieldInfo:
        default: Any = ...
        default_factory: Optional[Callable[[], Any]] = None

    def Field(
        default: Any = ...,  # noqa: N803
        default_factory: Optional[Callable[[], Any]] = None,
        description: str | None = None,
        **_: Any,
    ) -> Any:
        return _FieldInfo(default=default, default_factory=default_factory)

    class BaseModel:  # noqa: D101
        def __init__(self, **data: Any):
            annotations = getattr(self.__class__, "__annotations__", {})
            for key in annotations.keys():
                if key in data:
                    value = data[key]
                else:
                    default_value = getattr(self.__class__, key, ...)
                    if isinstance(default_value, _FieldInfo):
                        if default_value.default_factory is not None:
                            value = default_value.default_factory()
                        else:
                            value = default_value.default
                    else:
                        value = default_value

                if value is ...:
                    raise TypeError(f"Missing required field: {key}")

                setattr(self, key, value)

        def __eq__(self, other: object) -> bool:
            if not isinstance(other, self.__class__):
                return False
            return self.model_dump() == other.model_dump()

        def __repr__(self) -> str:
            data = self.model_dump()
            inner = ", ".join(f"{k}={data[k]!r}" for k in data.keys())
            return f"{self.__class__.__name__}({inner})"

        def __str__(self) -> str:
            return self.__repr__()

        def model_dump(self) -> dict[str, Any]:
            out: dict[str, Any] = {}
            annotations = getattr(self.__class__, "__annotations__", {})
            for key in annotations.keys():
                value = getattr(self, key)
                if isinstance(value, BaseModel):
                    out[key] = value.model_dump()
                else:
                    out[key] = value
            return out

        def model_copy(self, update: Optional[dict[str, Any]] = None, deep: bool = False):
            data = self.model_dump()
            if update:
                data.update(update)
            if deep:
                data = copy.deepcopy(data)
            return self.__class__(**data)

from nlp2cmd.ir import ActionIR

if TYPE_CHECKING:
    from nlp2cmd.adapters.base import BaseDSLAdapter
    from nlp2cmd.feedback import FeedbackAnalyzer
    from nlp2cmd.validators.base import BaseValidator

logger = logging.getLogger(__name__)


class TransformStatus(str, Enum):
    """Status of a transformation operation."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    BLOCKED = "blocked"
    NEEDS_CLARIFICATION = "needs_clarification"
    ERROR = "error"


class Intent(BaseModel):
    """Represents a detected intent from natural language input."""

    name: str = Field(..., description="Intent name")
    patterns: list[str] = Field(default_factory=list, description="Matching patterns")
    required_entities: list[str] = Field(
        default_factory=list, description="Required entities for this intent"
    )
    optional_entities: list[str] = Field(
        default_factory=list, description="Optional entities"
    )
    confidence_threshold: float = Field(
        default=0.7, description="Minimum confidence for this intent"
    )


class Entity(BaseModel):
    """Represents an extracted entity from natural language input."""

    name: str = Field(..., description="Entity name")
    value: Any = Field(..., description="Entity value")
    type: str = Field(..., description="Entity type")
    start: int = Field(default=0, description="Start position in text")
    end: int = Field(default=0, description="End position in text")
    confidence: float = Field(default=1.0, description="Extraction confidence")


class ExecutionPlan(BaseModel):
    """Structured plan for command execution."""

    intent: str = Field(..., description="Detected intent")
    entities: dict[str, Any] = Field(default_factory=dict, description="Extracted entities")
    confidence: float = Field(default=0.0, description="Overall confidence")
    requires_confirmation: bool = Field(
        default=False, description="Whether user confirmation is needed"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    text: str = Field(default="", description="Original input text")
    
    def with_confidence(self, confidence: float) -> "ExecutionPlan":
        """Create a copy with updated confidence."""
        return self.model_copy(update={"confidence": confidence})
    
    def with_entities(self, entities: dict[str, Any]) -> "ExecutionPlan":
        """Create a copy with updated entities (merged with existing)."""
        merged_entities = {**self.entities, **entities}
        return self.model_copy(update={"entities": merged_entities})
    
    def with_metadata(self, metadata: dict[str, Any]) -> "ExecutionPlan":
        """Create a copy with updated metadata."""
        return self.model_copy(update={"metadata": metadata})
    
    def with_context(self, context: dict[str, Any]) -> "ExecutionPlan":
        """Create a copy with updated context."""
        return self.model_copy(update={"metadata": {**self.metadata, "context": context}})
    
    def with_errors(self, errors: list[str]) -> "ExecutionPlan":
        """Create a copy with error information in metadata."""
        return self.model_copy(update={"metadata": {**self.metadata, "errors": errors}})
    
    def with_security(self, security_context: dict[str, Any]) -> "ExecutionPlan":
        """Create a copy with security context."""
        return self.model_copy(update={"metadata": {**self.metadata, "security": security_context}})
    
    def with_performance(self, performance_data: dict[str, Any]) -> "ExecutionPlan":
        """Create a copy with performance data."""
        return self.model_copy(update={"metadata": {**self.metadata, "performance": performance_data}})
    
    def is_valid(self) -> bool:
        """Check if execution plan is valid."""
        return (
            len(self.intent.strip()) > 0 and
            0.0 <= self.confidence <= 1.0 and
            isinstance(self.entities, dict)
        )


@dataclass
class TransformResult:
    """Result of a natural language to command transformation."""

    status: TransformStatus
    command: str
    plan: ExecutionPlan
    confidence: float
    dsl_type: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        """Check if transformation was successful."""
        return self.status in [TransformStatus.SUCCESS, TransformStatus.PARTIAL]

    @property
    def is_blocked(self) -> bool:
        """Check if transformation was blocked by security policy."""
        return self.status == TransformStatus.BLOCKED

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "status": self.status.value,
            "command": self.command,
            "plan": self.plan.model_dump(),
            "confidence": self.confidence,
            "dsl_type": self.dsl_type,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "alternatives": self.alternatives,
            "metadata": self.metadata,
        }

    def copy(self) -> "TransformResult":
        """Create a copy of the transform result."""
        return TransformResult(
            status=self.status,
            command=self.command,
            plan=self.plan.model_copy(deep=True),
            confidence=self.confidence,
            dsl_type=self.dsl_type,
            errors=self.errors.copy(),
            warnings=self.warnings.copy(),
            suggestions=self.suggestions.copy(),
            alternatives=self.alternatives.copy(),
            metadata=self.metadata.copy(),
        )

    def is_valid(self) -> bool:
        """Check if result is valid (no errors and successful status)."""
        return (
            self.status == TransformStatus.SUCCESS and 
            len(self.errors) == 0 and
            len(self.command.strip()) > 0 and
            0.0 <= self.confidence <= 1.0
        )


class NLPBackend:
    """Base class for NLP processing backends."""

    def __init__(self, config: Optional[dict[str, Any]] = None):
        self.config = config or {}

    def extract_intent(self, text: str) -> tuple[str, float]:
        """Extract intent from text."""
        raise NotImplementedError

    def extract_entities(self, text: str) -> list[Entity]:
        """Extract entities from text."""
        raise NotImplementedError

    def generate_plan(self, text: str, context: Optional[dict] = None) -> ExecutionPlan:
        """Generate execution plan from text."""
        raise NotImplementedError


class SpaCyBackend(NLPBackend):
    """spaCy-based NLP backend."""

    def __init__(self, model: str = "en_core_web_sm", config: Optional[dict] = None):
        super().__init__(config)
        self.model_name = model
        self._nlp = None

    @property
    def nlp(self):
        """Lazy-load spaCy model."""
        if self._nlp is None:
            try:
                import spacy

                self._nlp = spacy.load(self.model_name)
            except ImportError:
                raise ImportError("spaCy is required. Install with: pip install nlp2cmd[nlp]")
        return self._nlp

    def extract_entities(self, text: str) -> list[Entity]:
        """Extract named entities using spaCy."""
        doc = self.nlp(text)
        entities = []
        for ent in doc.ents:
            entities.append(
                Entity(
                    name=ent.label_,
                    value=ent.text,
                    type=ent.label_,
                    start=ent.start_char,
                    end=ent.end_char,
                )
            )
        return entities


class LLMBackend(NLPBackend):
    """LLM-based NLP backend (Claude, GPT, etc.)."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        api_key: Optional[str] = None,
        system_prompt: Optional[str] = None,
        config: Optional[dict] = None,
    ):
        super().__init__(config)
        self.model = model
        self.api_key = api_key
        self.system_prompt = system_prompt or self._default_system_prompt()
        self._client = None

    def _default_system_prompt(self) -> str:
        return """You are an assistant that converts natural language to structured commands.
        
Analyze the user's request and respond with a JSON object containing:
- intent: the main action (e.g., "query", "create", "update", "delete", "find")
- entities: extracted parameters as key-value pairs
- confidence: your confidence score (0.0-1.0)

Respond ONLY with valid JSON, no additional text."""

    @property
    def client(self):
        """Lazy-load API client."""
        if self._client is None:
            if "claude" in self.model.lower():
                try:
                    from anthropic import Anthropic

                    self._client = Anthropic(api_key=self.api_key)
                except ImportError:
                    raise ImportError(
                        "anthropic is required. Install with: pip install nlp2cmd[llm]"
                    )
            else:
                try:
                    from openai import OpenAI

                    self._client = OpenAI(api_key=self.api_key)
                except ImportError:
                    raise ImportError(
                        "openai is required. Install with: pip install nlp2cmd[llm]"
                    )
        return self._client

    def generate_plan(self, text: str, context: Optional[dict] = None) -> ExecutionPlan:
        """Generate execution plan using LLM."""
        import json

        prompt = text
        if context:
            prompt = f"Context: {json.dumps(context)}\n\nRequest: {text}"

        if "claude" in self.model.lower():
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=self.system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )
            result_text = response.content[0].text
        else:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt},
                ],
            )
            result_text = response.choices[0].message.content

        try:
            data = json.loads(result_text)
            return ExecutionPlan(
                intent=data.get("intent", "unknown"),
                entities=data.get("entities", {}),
                confidence=data.get("confidence", 0.5),
            )
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse LLM response: {result_text}")
            return ExecutionPlan(intent="unknown", entities={}, confidence=0.0)


class RuleBasedBackend(NLPBackend):
    """Simple rule-based NLP backend for basic pattern matching."""

    def __init__(self, rules: Optional[dict[str, list[str]]] = None, config: Optional[dict] = None):
        super().__init__(config)
        self.rules = rules or {}
        self.last_entity_extraction_meta: dict[str, Any] = {}

    def extract_entities(self, text: str) -> list[Entity]:
        """Extract entities using simple pattern matching."""
        dsl = self.config.get("dsl") if isinstance(self.config, dict) else None

        if self._is_regex_dsl(dsl):
            return self._extract_regex_entities(text, str(dsl))

        if dsl == "dql":
            return self._extract_dql_entities(text)

        return []

    def _is_regex_dsl(self, dsl: Optional[str]) -> bool:
        return dsl in {"sql", "shell", "docker", "kubernetes"}

    def _should_use_semantic_extractor(self, dsl: str) -> bool:
        if dsl != "shell":
            return False
        mode = os.environ.get("NLP2CMD_ENTITY_EXTRACTOR_MODE")
        if not isinstance(mode, str):
            return False
        return mode.strip().lower() in {"semantic", "shadow", "ab"}

    def _extract_with_configured_extractor(self, text: str, dsl: str):
        if self._should_use_semantic_extractor(dsl):
            from nlp2cmd.generation.semantic_entities import SemanticEntityExtractor

            extractor = SemanticEntityExtractor()
            result = extractor.extract(text, dsl)
            meta: dict[str, Any] = {"entity_extractor_mode": extractor.last_mode}
            if extractor.last_mode == "shadow":
                meta["shadow_entities"] = extractor.last_semantic_entities
            self.last_entity_extraction_meta = meta
            return result

        from nlp2cmd.generation.regex import RegexEntityExtractor

        extractor = RegexEntityExtractor()
        self.last_entity_extraction_meta = {}
        return extractor.extract(text, dsl)

    def _extract_regex_entities(self, text: str, dsl: str) -> list[Entity]:
        extracted = self._extract_with_configured_extractor(text, dsl)

        entities = [
            Entity(name=name, value=value, type=self._infer_entity_type(value))
            for name, value in extracted.entities.items()
        ]
        self._append_all_entity(text, entities)
        return entities

    def _infer_entity_type(self, value: Any) -> str:
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            return "integer"
        if isinstance(value, float):
            return "number"
        if isinstance(value, (list, dict)):
            return "object"
        return "string"

    def _append_all_entity(self, text: str, entities: list[Entity]) -> None:
        text_lower = text.lower()
        if "all" in text_lower or "wszystkie" in text_lower:
            entities.append(Entity(name="all", value=True, type="boolean"))

    def _extract_dql_entities(self, text: str) -> list[Entity]:
        import re

        entities: list[Entity] = []

        m = re.search(
            r"(?:entity|encj[aeę]|encji|model)\s+([A-Z][A-Za-z0-9_]*)",
            text,
        )
        if not m:
            m = re.search(r"\b([A-Z][A-Za-z0-9_]{2,})\b", text)

        if m:
            entities.append(Entity(name="entity", value=m.group(1), type="string"))

        return entities

    def extract_intent(self, text: str) -> tuple[str, float]:
        """Extract intent using pattern matching."""
        text_lower = text.lower()
        words = text_lower.split()

        for intent, patterns in self.rules.items():
            for pattern in patterns:
                pattern_lower = pattern.lower()
                
                # Exact substring match
                if pattern_lower in text_lower:
                    return intent, 0.8
                
                # Word-level matching - check if all pattern words are in text
                pattern_words = pattern_lower.split()
                if len(pattern_words) > 1:
                    # Check if all pattern words appear in the text
                    if all(word in text_lower for word in pattern_words):
                        return intent, 0.7
                
                # Single word matching
                if len(pattern_words) == 1 and pattern_words[0] in words:
                    return intent, 0.6

        return "unknown", 0.0


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
                        patterns = intent_config.get("patterns", [])
                        rules[intent_name] = patterns
                    self.nlp_backend = RuleBasedBackend(
                        rules=rules,
                        config={"dsl": adapter.DSL_NAME},
                    )
        else:
            self.nlp_backend = nlp_backend
            
        self.validator = validator
        self.feedback_analyzer = feedback_analyzer
        self.validation_mode = validation_mode
        self.auto_fix = auto_fix

        # Context for multi-turn conversations
        self._context: dict[str, Any] = {}
        self._history: list[TransformResult] = []

    @property
    def dsl_name(self) -> str:
        """Get the name of the current DSL adapter."""
        return self.adapter.DSL_NAME

    def _normalize_entities(
        self,
        intent: str,
        entities: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        dsl = self.dsl_name
        normalized = dict(entities)

        handlers: dict[str, Callable[[], None]] = {
            "sql": lambda: self._normalize_sql_entities(normalized, context),
            "shell": lambda: self._normalize_shell_entities(intent, normalized, context),
            "docker": lambda: self._normalize_docker_entities(intent, normalized),
            "kubernetes": lambda: self._normalize_kubernetes_entities(intent, normalized),
            "dql": lambda: self._normalize_dql_entities(normalized, context),
        }
        handler = handlers.get(dsl)
        if handler:
            handler()

        return normalized

    def _normalize_sql_entities(self, normalized: dict[str, Any], context: dict[str, Any]) -> None:
        if "table" not in normalized:
            default_table = context.get("default_table") or context.get("previous_table")
            if default_table:
                normalized["table"] = default_table

        if "filters" not in normalized and "where_field" in normalized and "where_value" in normalized:
            normalized["filters"] = [
                {
                    "field": normalized.get("where_field"),
                    "operator": "=",
                    "value": normalized.get("where_value"),
                }
            ]

        if "ordering" not in normalized and "order_by" in normalized:
            normalized["ordering"] = [
                {
                    "field": normalized.get("order_by"),
                    "direction": normalized.get("order_direction", "ASC"),
                }
            ]

    def _normalize_shell_entities(
        self,
        intent: str,
        normalized: dict[str, Any],
        context: dict[str, Any],
    ) -> None:
        if intent != "file_search":
            return
        scope = normalized.get("scope") or normalized.get("path") or "."
        normalized.setdefault("scope", scope)
        normalized.setdefault("target", "files")

        filters: list[dict[str, Any]] = []

        extension_value = self._extract_shell_extension_value(normalized)
        if extension_value:
            filters.append({"attribute": "extension", "operator": "=", "value": extension_value})

        filename = normalized.get("filename")
        if filename and isinstance(filename, str):
            filters.append({"attribute": "name", "operator": "=", "value": filename})

        full_text = context.get("text", "") or normalized.get("query", "")
        size_filter = self._build_shell_size_filter(normalized, full_text)
        if size_filter:
            filters.append(size_filter)

        age_filter = self._build_shell_age_filter(normalized, full_text)
        if age_filter:
            filters.append(age_filter)

        normalized["filters"] = filters

    def _extract_shell_extension_value(self, normalized: dict[str, Any]) -> Optional[str]:
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
        if intent == "get":
            rt = normalized.get("resource_type")
            if isinstance(rt, str):
                normalized["resource_type"] = rt

        if intent == "scale":
            rc = normalized.get("replica_count")
            if isinstance(rc, str) and rc.isdigit():
                normalized["replica_count"] = int(rc)

    def _normalize_dql_entities(self, normalized: dict[str, Any], context: dict[str, Any]) -> None:
        if "entity" not in normalized:
            default_entity = context.get("default_entity")
            if default_entity:
                normalized["entity"] = default_entity

    def transform(
        self,
        text: str,
        context: Optional[dict[str, Any]] = None,
        dry_run: bool = False,
    ) -> TransformResult:
        """
        Transform natural language text into a DSL command.

        Args:
            text: Natural language input
            context: Additional context for transformation
            dry_run: If True, don't execute, just generate

        Returns:
            TransformResult with generated command and metadata
        """
        # Merge context
        full_context = {**self._context, **(context or {})}
        # Add text to context for operator detection
        full_context["text"] = text

        # Step 1: NLP Processing - Generate execution plan
        try:
            try:
                plan = self.nlp_backend.generate_plan(text, full_context)
                # Always preserve original user input text in the plan.
                plan = plan.model_copy(update={"text": text})
            except NotImplementedError:
                intent, confidence = self.nlp_backend.extract_intent(text)
                entities = self.nlp_backend.extract_entities(text)
                entity_dict = {e.name: e.value for e in entities}
                entity_dict = self._normalize_entities(intent, entity_dict, full_context)
                meta: dict[str, Any] = {}
                backend_meta = getattr(self.nlp_backend, "last_entity_extraction_meta", None)
                if isinstance(backend_meta, dict) and backend_meta:
                    meta.update(backend_meta)
                plan = ExecutionPlan(
                    intent=intent,
                    entities=entity_dict,
                    confidence=confidence,
                    metadata=meta,
                    text=text,
                )
        except Exception as e:
            logger.error(f"NLP processing failed: {e}")
            return TransformResult(
                status=TransformStatus.FAILED,
                command="",
                plan=ExecutionPlan(intent="error", entities={}),
                confidence=0.0,
                dsl_type=self.dsl_name,
                errors=[str(e)],
            )

        # Step 2: Generate command using adapter
        try:
            command = self.adapter.generate(plan.model_dump())
        except Exception as e:
            logger.error(f"Command generation failed: {e}")
            return TransformResult(
                status=TransformStatus.FAILED,
                command="",
                plan=plan,
                confidence=0.0,
                dsl_type=self.dsl_name,
                errors=[f"Generation error: {e}"],
            )

        # If adapter produced a structured ActionIR, expose it in metadata.
        action_ir = getattr(self.adapter, "last_action_ir", None)

        # Step 3: Validate command
        errors = []
        warnings = []
        suggestions = []

        if self.validator:
            validation_result = self.validator.validate(command)
            if not validation_result.is_valid:
                errors.extend(validation_result.errors)
            warnings.extend(validation_result.warnings)
            suggestions.extend(validation_result.suggestions)

        # Step 4: Check safety policy
        safety_result = self.adapter.check_safety(command)
        if not safety_result["allowed"]:
            # Record blocked command in history
            try:
                from nlp2cmd.history.tracker import record_command
                record_command(
                    query=text,
                    dsl=self.dsl_name,
                    command=command,
                    intent=plan.intent,
                    success=False,
                    error=safety_result.get("reason", "Blocked by safety policy"),
                )
            except Exception:
                pass
            
            return TransformResult(
                status=TransformStatus.BLOCKED,
                command=command,
                plan=plan,
                confidence=plan.confidence,
                dsl_type=self.dsl_name,
                errors=[safety_result.get("reason", "Blocked by safety policy")],
                suggestions=safety_result.get("alternatives", []),
            )

        # Determine status
        if errors:
            status = TransformStatus.FAILED
        elif warnings:
            status = TransformStatus.PARTIAL
        else:
            status = TransformStatus.SUCCESS

        result = TransformResult(
            status=status,
            command=command,
            plan=plan,
            confidence=plan.confidence,
            dsl_type=self.dsl_name,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
        )

        if isinstance(action_ir, ActionIR):
            result.metadata["action_ir"] = action_ir.to_dict()

        if plan.metadata.get("entity_extractor_mode") == "shadow":
            result.metadata["entity_extractor_mode"] = plan.metadata.get("entity_extractor_mode")
            result.metadata["shadow_entities"] = plan.metadata.get("shadow_entities")

        # Store in history
        self._history.append(result)
        
        # Record in global command history
        try:
            from nlp2cmd.history.tracker import record_command
            record_command(
                query=text,
                dsl=self.dsl_name,
                command=command,
                intent=plan.intent,
                success=(status == TransformStatus.SUCCESS),
                error=errors[0] if errors else None,
                metadata={
                    "confidence": plan.confidence,
                    "warnings": warnings,
                    "suggestions": suggestions,
                },
            )
        except Exception:
            pass

        return result

    def transform_ir(
        self,
        text: str,
        context: Optional[dict[str, Any]] = None,
        dry_run: bool = False,
    ) -> ActionIR:
        result = self.transform(text, context=context, dry_run=dry_run)
        action_ir = getattr(self.adapter, "last_action_ir", None)
        if isinstance(action_ir, ActionIR):
            return action_ir
        raise ValueError("Adapter did not produce ActionIR")

    def set_context(self, key: str, value: Any) -> None:
        """Set a context value for subsequent transformations."""
        self._context[key] = value

    def clear_context(self) -> None:
        """Clear all context."""
        self._context.clear()

    def get_history(self) -> list[TransformResult]:
        """Get transformation history."""
        return self._history.copy()

    def clear_history(self) -> None:
        """Clear transformation history."""
        self._history.clear()

# Polish Language Support Integration
try:
    from .polish_support import get_polish_support
    polish_support = get_polish_support()
    POLISH_SUPPORT_ENABLED = True
except ImportError:
    polish_support = None
    POLISH_SUPPORT_ENABLED = False

# Enhanced domain detection with Polish support
def enhanced_domain_detection(query, base_domain):
    """Enhanced domain detection with Polish language support"""
    if not POLISH_SUPPORT_ENABLED:
        return base_domain
    
    # Use Polish support to enhance domain detection
    return polish_support.enhance_domain_detection(query, base_domain)

# Enhanced intent detection with Polish support
def enhanced_intent_detection(query, base_intent):
    """Enhanced intent detection with Polish language support"""
    if not POLISH_SUPPORT_ENABLED:
        return base_intent
    
    # Use Polish support to enhance intent detection
    return polish_support.enhance_intent_detection(query, base_intent)
