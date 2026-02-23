"""
NLP backend implementations for NLP2CMD framework.

This module contains various NLP processing backends including
spaCy, LLM-based, and rule-based implementations.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional, Tuple

from .core_models import Entity, ExecutionPlan

logger = logging.getLogger(__name__)


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
            except OSError:
                raise ImportError(f"spaCy model {self.model_name} not found. Install with: python -m spacy download {self.model_name}")
            except ImportError:
                raise ImportError("spaCy is required. Install with: pip install nlp2cmd[nlp]")
        return self._nlp

    def extract_entities(self, text: str) -> list[Entity]:
        """Extract named entities using spaCy."""
        doc = self.nlp(text)
        entities = []
        
        for ent in doc.ents:
            entity = Entity(
                name=ent.label_,
                value=ent.text,
                type=ent.label_,
                confidence=1.0  # spaCy doesn't provide confidence scores
            )
            entities.append(entity)
        
        return entities


class LLMBackend(NLPBackend):
    """LLM-based NLP backend (Claude, GPT, etc.)."""

    def __init__(
        self,
        model: str = "claude-3-sonnet-20240229",
        api_key: Optional[str] = None,
        config: Optional[dict] = None,
    ):
        super().__init__(config)
        self.model = model
        self.api_key = api_key
        self._client = None

    @property
    def client(self):
        """Lazy-load API client."""
        if self._client is None:
            if "claude" in self.model.lower():
                try:
                    from anthropic import Anthropic
                    self._client = Anthropic(api_key=self.api_key)
                except ImportError:
                    raise ImportError("anthropic is required for Claude. Install with: pip install anthropic")
            elif "gpt" in self.model.lower():
                try:
                    import openai
                    self._client = openai.OpenAI(api_key=self.api_key)
                except ImportError:
                    raise ImportError("openai is required for GPT. Install with: pip install openai")
            else:
                raise ValueError(f"Unsupported model: {self.model}")
        return self._client

    def generate_plan(self, text: str, context: Optional[dict] = None) -> ExecutionPlan:
        """Generate execution plan using LLM."""
        prompt = f"""
Analyze the following command and extract intent and entities:

Command: {text}

Respond with a JSON object containing:
- intent: the main intent (e.g., "list_files", "create_container", "query_database")
- entities: key-value pairs of extracted entities
- confidence: confidence score (0-1)
- domain: the domain (e.g., "shell", "docker", "sql")

Respond ONLY with valid JSON, no additional text."""

        try:
            if "claude" in self.model.lower():
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1000,
                    messages=[{"role": "user", "content": prompt}]
                )
                content = response.content[0].text
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1000
                )
                content = response.choices[0].message.content

            # Parse JSON response
            result = json.loads(content)
            
            return ExecutionPlan(
                intent=result.get("intent", "unknown"),
                entities=result.get("entities", {}),
                confidence=result.get("confidence", 0.5),
                domain=result.get("domain"),
                text=text
            )
            
        except Exception as e:
            logger.error(f"LLM backend error: {e}")
            return ExecutionPlan(intent="unknown", entities={}, confidence=0.0)


class RuleBasedBackend(NLPBackend):
    """Simple rule-based NLP backend for basic pattern matching."""

    def __init__(self, rules: Optional[dict[str, list[str]]] = None, config: Optional[dict] = None):
        super().__init__(config)
        self.rules = rules or {}
        self.last_entity_extraction_meta: dict[str, Any] = {}

    def extract_entities(self, text: str) -> list[Entity]:
        """Extract entities using simple pattern matching."""
        entities = []
        self.last_entity_extraction_meta = {"text": text, "matches": []}
        
        # Extract common patterns
        patterns = {
            "file_path": r'\b[/\\]?[\w\-./\\]+\.[\w]+\b',
            "number": r'\b\d+\b',
            "email": r'\b[\w\.-]+@[\w\.-]+\.\w+\b',
            "url": r'\bhttps?://[^\s]+\b',
            "port": r':(\d{1,5})\b',
            "size": r'\b(\d+[KMGT]?B?)\b',
        }
        
        for entity_type, pattern in patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match[0] else match[1]
                
                entity = Entity(
                    name=entity_type,
                    value=match,
                    type=entity_type,
                    confidence=0.8
                )
                entities.append(entity)
                self.last_entity_extraction_meta["matches"].append({
                    "type": entity_type,
                    "value": match,
                    "pattern": pattern
                })
        
        return entities

    def extract_intent(self, text: str) -> tuple[str, float]:
        """Extract intent using rule-based pattern matching."""
        text_lower = text.lower()
        words = set(text_lower.split())
        
        best_intent = "unknown"
        best_confidence = 0.0
        
        for intent, patterns in self.rules.items():
            for pattern in patterns:
                pattern_lower = pattern.lower()
                
                # Exact substring match
                if pattern_lower in text_lower:
                    confidence = 0.8
                    if confidence > best_confidence:
                        best_intent = intent
                        best_confidence = confidence
                
                # Word-level matching - check if all pattern words are in text
                pattern_words = pattern_lower.split()
                if len(pattern_words) > 1:
                    # Check if all pattern words appear in the text
                    if all(word in text_lower for word in pattern_words):
                        confidence = 0.7
                        if confidence > best_confidence:
                            best_intent = intent
                            best_confidence = confidence
                
                # Single word matching
                if len(pattern_words) == 1 and pattern_words[0] in words:
                    confidence = 0.6
                    if confidence > best_confidence:
                        best_intent = intent
                        best_confidence = confidence

        return best_intent, best_confidence

    def generate_plan(self, text: str, context: Optional[dict] = None) -> ExecutionPlan:
        """Generate execution plan using rule-based approach."""
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
            text=text
        )
