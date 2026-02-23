"""Integration module for the enhanced NLP2CMD implementation.

EnhancedNLP2CMD is a convenience wrapper around NLP2CMD that is AppSpec-first:
- input contract: app2schema.appspec
- output format: nlp2cmd.action_ir (via NLP2CMD.transform_ir)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from nlp2cmd.adapters.appspec import AppSpecAdapter
from nlp2cmd.core.core_transform import NLP2CMD
from nlp2cmd.core.core_backends import NLPBackend
from nlp2cmd.core.core_models import TransformResult
from nlp2cmd.ir import ActionIR


class EnhancedNLP2CMD(NLP2CMD):
    """
    Enhanced NLP2CMD with dynamic schema capabilities.
    
    This class extends the base NLP2CMD with:
    - Dynamic schema extraction from OpenAPI, shell help, Python code
    - Shell-gpt integration for intelligent command generation
    - Hybrid NLP processing with multiple backends
    - No hardcoded keywords - everything is extracted dynamically
    """
    
    def __init__(
        self,
        appspec_path: Optional[str] = None,
        nlp_backend: Optional[NLPBackend] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize enhanced NLP2CMD.
        
        Args:
            nlp_backend: Type of NLP backend ("hybrid", "shell_gpt", "rule_based")
            config: Configuration dictionary
        """
        self.config = config or {}

        adapter = AppSpecAdapter(
            appspec_path=appspec_path,
            config=self.config.get("adapter_config"),
            safety_policy=self.config.get("safety_policy"),
        )
        
        # Initialize parent class
        super().__init__(
            adapter=adapter,
            nlp_backend=nlp_backend,
            validator=self.config.get("validator"),
            feedback_analyzer=self.config.get("feedback_analyzer"),
            validation_mode=self.config.get("validation_mode", "normal"),
            auto_fix=self.config.get("auto_fix", False),
        )

    def load_appspec(self, path: str) -> None:
        self.adapter.load_from_file(path)

    def get_available_commands(self, category: Optional[str] = None) -> List[str]:
        spec = getattr(self.adapter, "_spec", None)
        if spec is None:
            return []
        return [a.id for a in spec.actions]

    def get_command_categories(self) -> List[str]:
        return []

    def search_commands(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        spec = getattr(self.adapter, "_spec", None)
        if spec is None:
            return []

        q = (query or "").lower()
        out: list[dict[str, Any]] = []
        for a in spec.actions:
            if q and q not in a.id.lower() and q not in (a.description or "").lower():
                continue
            out.append({"id": a.id, "type": a.type, "dsl_kind": a.dsl_kind, "description": a.description})
            if len(out) >= limit:
                break
        return out

    def get_command_help(self, command_name: str) -> Optional[str]:
        return None
    
    def transform_with_explanation(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
    ) -> TransformResult:
        """
        Transform natural language with detailed explanation.
        
        This method provides additional metadata about how the transformation
        was performed, including which schemas were used.
        """
        result = self.transform(text, context, dry_run)
        if result.is_success and isinstance(result.metadata.get("action_ir"), dict):
            result.metadata.setdefault(
                "explanation",
                str(result.metadata["action_ir"].get("explanation") or ""),
            )
        return result
    
    def export_schemas(self, format: str = "json") -> str:
        raise NotImplementedError("AppSpec is the canonical schema format; export is handled by app2schema")

    def transform_ir(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
    ) -> ActionIR:
        return super().transform_ir(text, context=context, dry_run=dry_run)
    
    def analyze_query(self, text: str) -> Dict[str, Any]:
        """Analyze a natural language query without generating a command."""
        matching_commands = self.search_commands(text, limit=5)
        return {
            "query": text,
            "detected_intent": "",
            "confidence": 0.0,
            "extracted_entities": {},
            "matching_commands": [
                {
                    "id": cmd.get("id"),
                    "description": cmd.get("description"),
                }
                for cmd in matching_commands
            ],
        }


def create_enhanced_nlp2cmd(
    appspec_path: Optional[str] = None,
    nlp_backend: Optional[NLPBackend] = None,
    config: Optional[Dict[str, Any]] = None,
) -> EnhancedNLP2CMD:
    return EnhancedNLP2CMD(appspec_path=appspec_path, nlp_backend=nlp_backend, config=config)


