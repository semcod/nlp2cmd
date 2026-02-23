"""
Enhanced NLP backend with shell-gpt integration for dynamic command generation.

This module provides intelligent natural language processing capabilities
that work with dynamically extracted schemas instead of hardcoded patterns.
"""

from __future__ import annotations

import json
import re
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from nlp2cmd.core.core_backends import NLPBackend
from nlp2cmd.core.core_models import Entity, ExecutionPlan
from nlp2cmd.schema_extraction import DynamicSchemaRegistry, CommandSchema


class ShellGPTBackend(NLPBackend):
    """
    NLP backend that uses shell-gpt for intelligent command generation.
    
    This backend leverages shell-gpt (or similar tools) to generate
    shell commands from natural language descriptions, enhanced with
    dynamic schema information.
    """
    
    def __init__(
        self,
        schema_registry: Optional[DynamicSchemaRegistry] = None,
        shell_gpt_path: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize shell-gpt backend."""
        super().__init__(config)
        
        self.registry = schema_registry or DynamicSchemaRegistry(
            use_per_command_storage=True,
            storage_dir="./command_schemas",
        )
        self.shell_gpt_path = shell_gpt_path or self._find_shell_gpt()
        self.fallback_enabled = config.get("fallback_enabled", True) if config else True
    
    def _find_shell_gpt(self) -> Optional[str]:
        """Find shell-gpt executable in PATH."""
        try:
            result = subprocess.run(
                ["which", "shell-gpt"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Try alternative names
        alternatives = ["sgpt", "shell_gpt", "sh-gpt"]
        for alt in alternatives:
            try:
                result = subprocess.run(
                    ["which", alt],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return result.stdout.strip()
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        
        return None
    
    def extract_entities(self, text: str) -> List[Entity]:
        """Extract entities using shell-gpt with schema context."""
        if not self.shell_gpt_path:
            return self._fallback_entity_extraction(text)
        
        try:
            # Get relevant commands for context
            relevant_commands = self.registry.search_commands(text, limit=5)
            
            # Build context for shell-gpt
            context = self._build_shell_gpt_context(relevant_commands)
            
            # Use shell-gpt to extract entities
            prompt = f"""
Extract command parameters from this request: "{text}"

Available commands:
{context}

Please respond with a JSON object containing:
- command: the most relevant command name
- parameters: extracted parameters as key-value pairs
- confidence: your confidence (0.0-1.0)

Only respond with valid JSON.
"""
            
            result = subprocess.run(
                [self.shell_gpt_path, "--model", "gpt-3.5-turbo", prompt],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout.strip())
                    entities = []
                    
                    # Convert command to entity
                    if "command" in data:
                        entities.append(Entity(
                            name="command",
                            value=data["command"],
                            type="string",
                            confidence=0.9
                        ))
                    
                    # Convert parameters to entities
                    parameters = data.get("parameters", {})
                    for key, value in parameters.items():
                        entity_type = self._infer_entity_type(value)
                        entities.append(Entity(
                            name=key,
                            value=value,
                            type=entity_type,
                            confidence=0.8
                        ))
                    
                    return entities
                
                except json.JSONDecodeError:
                    pass
        
        except Exception as e:
            print(f"Shell-gpt extraction failed: {e}")
        
        return self._fallback_entity_extraction(text)
    
    def extract_intent(self, text: str) -> Tuple[str, float]:
        """Extract intent using shell-gpt with schema context."""
        if not self.shell_gpt_path:
            return self._fallback_intent_extraction(text)
        
        try:
            # Get relevant commands for context
            relevant_commands = self.registry.search_commands(text, limit=10)
            
            # Build context
            context = self._build_shell_gpt_context(relevant_commands)
            
            prompt = f"""
Identify the best matching command for this request: "{text}"

Available commands:
{context}

Please respond with a JSON object containing:
- intent: the command name that best matches the request
- confidence: your confidence (0.0-1.0)
- reasoning: brief explanation of why this command matches

Only respond with valid JSON.
"""
            
            result = subprocess.run(
                [self.shell_gpt_path, "--model", "gpt-3.5-turbo", prompt],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout.strip())
                    intent = data.get("intent", "unknown")
                    confidence = float(data.get("confidence", 0.0))
                    return intent, confidence
                except (json.JSONDecodeError, ValueError):
                    pass
        
        except Exception as e:
            print(f"Shell-gpt intent extraction failed: {e}")
        
        return self._fallback_intent_extraction(text)
    
    def generate_plan(self, text: str, context: Optional[Dict] = None) -> ExecutionPlan:
        """Generate execution plan using shell-gpt with dynamic schemas."""
        if not self.shell_gpt_path:
            return self._fallback_plan_generation(text, context)
        
        try:
            # Get relevant commands
            relevant_commands = self.registry.search_commands(text, limit=10)
            
            # Build comprehensive context
            command_context = self._build_shell_gpt_context(relevant_commands)
            user_context = json.dumps(context) if context else "{}"
            
            prompt = f"""
Generate a command execution plan for this request: "{text}"

User context: {user_context}

Available commands:
{command_context}

Please respond with a JSON object containing:
- intent: the command name to execute
- entities: extracted parameters as key-value pairs
- confidence: your confidence in this plan (0.0-1.0)
- reasoning: brief explanation of the plan
- alternatives: list of alternative commands (if any)

Only respond with valid JSON.
"""
            
            result = subprocess.run(
                [self.shell_gpt_path, "--model", "gpt-3.5-turbo", prompt],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout.strip())
                    
                    return ExecutionPlan(
                        intent=data.get("intent", "unknown"),
                        entities=data.get("entities", {}),
                        confidence=float(data.get("confidence", 0.0)),
                        text=text,
                        metadata={
                            "reasoning": data.get("reasoning", ""),
                            "alternatives": data.get("alternatives", []),
                            "backend": "shell_gpt",
                        }
                    )
                
                except (json.JSONDecodeError, ValueError):
                    pass
        
        except Exception as e:
            print(f"Shell-gpt plan generation failed: {e}")
        
        return self._fallback_plan_generation(text, context)
    
    def _build_shell_gpt_context(self, commands: List[CommandSchema]) -> str:
        """Build context string for shell-gpt from command schemas."""
        context_lines = []
        
        for cmd in commands:
            context_lines.append(f"- {cmd.name}: {cmd.description}")
            
            if cmd.parameters:
                param_descs = []
                for param in cmd.parameters:
                    param_str = f"{param.name} ({param.type})"
                    if param.required:
                        param_str += " [required]"
                    if param.description:
                        param_str += f" - {param.description}"
                    param_descs.append(param_str)
                
                context_lines.append(f"  Parameters: {', '.join(param_descs)}")
            
            if cmd.examples:
                context_lines.append(f"  Examples: {'; '.join(cmd.examples[:2])}")
            
            context_lines.append("")  # Empty line between commands
        
        return "\n".join(context_lines)
    
    def _infer_entity_type(self, value: Any) -> str:
        """Infer entity type from value."""
        if isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "number"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, dict):
            return "object"
        elif isinstance(value, str):
            # Check for common patterns
            if value.startswith('/') or value.startswith('./'):
                return "path"
            elif value.endswith(('.txt', '.py', '.json', '.yaml', '.yml')):
                return "file"
            elif re.match(r'^\d+$', value):
                return "integer"
            elif re.match(r'^\d+\.\d+$', value):
                return "number"
            else:
                return "string"
        else:
            return "string"
    
    def _fallback_entity_extraction(self, text: str) -> List[Entity]:
        """Fallback entity extraction using regex patterns."""
        entities = []
        
        # Extract file paths
        path_pattern = r'([/~][\w\.\-/]+)'
        for match in re.finditer(path_pattern, text):
            entities.append(Entity(
                name="path",
                value=match.group(1),
                type="path",
                start=match.start(),
                end=match.end(),
                confidence=0.8
            ))
        
        # Extract file extensions
        ext_pattern = r'\.(\w+)'
        for match in re.finditer(ext_pattern, text):
            entities.append(Entity(
                name="extension",
                value=match.group(1),
                type="string",
                start=match.start(),
                end=match.end(),
                confidence=0.7
            ))
        
        # Extract numbers
        number_pattern = r'\b(\d+)\b'
        for match in re.finditer(number_pattern, text):
            entities.append(Entity(
                name="number",
                value=int(match.group(1)),
                type="integer",
                start=match.start(),
                end=match.end(),
                confidence=0.9
            ))
        
        # Extract quoted strings
        quoted_pattern = r'["\']([^"\']+)["\']'
        for match in re.finditer(quoted_pattern, text):
            entities.append(Entity(
                name="quoted_string",
                value=match.group(1),
                type="string",
                start=match.start(),
                end=match.end(),
                confidence=0.8
            ))
        
        return entities
    
    def _fallback_intent_extraction(self, text: str) -> Tuple[str, float]:
        """Fallback intent extraction using schema registry search."""
        # Search for matching commands in the registry
        matches = self.registry.search_commands(text, limit=10)
        
        import sys
        print(f"[FallbackIntent] Query: {text!r}, matches: {[c.name for c in matches]}", file=sys.stderr)
        
        if matches:
            best_cmd = matches[0]
            # Simple confidence based on search order (could be improved)
            confidence = 0.8 if len(matches) == 1 else max(0.3, 1.0 - (len(matches) - 1) * 0.1)
            return best_cmd.name, confidence
        
        # If no commands match, return unknown
        return "unknown", 0.0
    
    def _fallback_plan_generation(self, text: str, context: Optional[Dict] = None) -> ExecutionPlan:
        """Fallback plan generation using simple heuristics."""
        intent, confidence = self.extract_intent(text)
        entities = self.extract_entities(text)
        
        # Convert entities to dict
        entity_dict = {}
        for entity in entities:
            entity_dict[entity.name] = entity.value
        
        return ExecutionPlan(
            intent=intent,
            entities=entity_dict,
            confidence=confidence,
            text=text,
            metadata={
                "backend": "fallback",
                "context": context or {},
            }
        )


class HybridNLPBackend(NLPBackend):
    """
    Hybrid NLP backend that combines multiple approaches.
    
    This backend tries shell-gpt first, then falls back to rule-based
    extraction, and finally to LLM-based extraction if available.
    """
    
    def __init__(
        self,
        schema_registry: Optional[DynamicSchemaRegistry] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize hybrid backend."""
        super().__init__(config)
        
        self.registry = schema_registry or DynamicSchemaRegistry()
        self.config = config or {}
        
        # Initialize backends in order of preference
        self.shell_gpt = ShellGPTBackend(schema_registry, config=config)
        
        # Try to initialize LLM backend if API keys are available
        self.llm_backend = None
        if self.config.get("openai_api_key") or self.config.get("anthropic_api_key"):
            try:
                from nlp2cmd.core.core_backends import LLMBackend
                model = self.config.get("llm_model", "gpt-3.5-turbo")
                api_key = self.config.get("openai_api_key") or self.config.get("anthropic_api_key")
                self.llm_backend = LLMBackend(model=model, api_key=api_key, config=config)
            except ImportError:
                pass
        
        # Always have rule-based fallback
        from nlp2cmd.core.core_backends import RuleBasedBackend
        self.rule_backend = RuleBasedBackend(config=config)
    
    def extract_entities(self, text: str) -> List[Entity]:
        """Extract entities using hybrid approach."""
        # Try shell-gpt first
        entities = self.shell_gpt.extract_entities(text)
        if entities:
            return entities
        
        # Try LLM backend
        if self.llm_backend:
            try:
                entities = self.llm_backend.extract_entities(text)
                if entities:
                    return entities
            except Exception:
                pass
        
        # Fall back to rule-based
        return self.rule_backend.extract_entities(text)
    
    def extract_intent(self, text: str) -> Tuple[str, float]:
        """Extract intent using hybrid approach."""
        # Try shell-gpt first
        intent, confidence = self.shell_gpt.extract_intent(text)
        if intent != "unknown" and confidence > 0.5:
            return intent, confidence
        
        # Try LLM backend
        if self.llm_backend:
            try:
                intent, confidence = self.llm_backend.extract_intent(text)
                if intent != "unknown" and confidence > 0.5:
                    return intent, confidence
            except Exception:
                pass
        
        # Fall back to rule-based
        return self.rule_backend.extract_intent(text)
    
    def generate_plan(self, text: str, context: Optional[Dict] = None) -> ExecutionPlan:
        """Generate plan using hybrid approach."""
        # Try shell-gpt first
        plan = self.shell_gpt.generate_plan(text, context)
        import sys
        print(f"[HybridPlan] ShellGPT plan: intent={plan.intent!r}, confidence={plan.confidence}", file=sys.stderr)
        if plan.intent != "unknown" and plan.confidence > 0.2:  # Lower threshold from 0.5 to 0.2
            return plan
        
        # Try LLM backend
        if self.llm_backend:
            try:
                plan = self.llm_backend.generate_plan(text, context)
                if plan.intent != "unknown" and plan.confidence > 0.2:
                    return plan
            except Exception:
                pass
        
        # Fall back to rule-based
        intent, confidence = self.rule_backend.extract_intent(text)
        entities = self.rule_backend.extract_entities(text)
        entity_dict = {e.name: e.value for e in entities}
        
        fallback_plan = ExecutionPlan(
            intent=intent,
            entities=entity_dict,
            confidence=confidence,
            text=text,
            metadata={
                "backend": "hybrid_fallback",
                "context": context or {},
            }
        )
        print(f"[HybridPlan] Fallback plan: intent={intent!r}, confidence={confidence}", file=sys.stderr)
        return fallback_plan
