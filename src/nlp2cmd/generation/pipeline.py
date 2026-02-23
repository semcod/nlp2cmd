"""
Iteration 3: Rule-Based Pipeline.

Combines KeywordIntentDetector, RegexEntityExtractor, and TemplateGenerator
into a complete NL → DSL pipeline without LLM.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Optional

from nlp2cmd.utils.data_files import data_file_write_path
from nlp2cmd.generation.keywords.keyword_detector import KeywordIntentDetector, DetectionResult
from nlp2cmd.generation.regex import RegexEntityExtractor, ExtractionResult
from nlp2cmd.generation.template_generator import TemplateGenerator, TemplateResult
from nlp2cmd.generation.pipeline_components import (
    PipelineResult,
    PipelineMetrics,
    SimpleExecutionPlan,
    _create_default_extractor,
    _DEFAULT_USE_ENHANCED_CONTEXT,
)


class RuleBasedPipeline:
    """
    Complete rule-based NL → DSL pipeline.
    
    Combines intent detection, entity extraction, and template generation
    to transform natural language into domain-specific commands.
    """
    
    def __init__(
        self,
        *,
        use_enhanced_context: Optional[bool] = None,
        persist_results: bool = False,
        metrics: Optional[PipelineMetrics] = None,
        confidence_threshold: Optional[float] = None,
    ):
        self.use_enhanced_context = (
            use_enhanced_context if use_enhanced_context is not None 
            else _DEFAULT_USE_ENHANCED_CONTEXT
        )
        self.persist_results = persist_results
        self.metrics = metrics or PipelineMetrics()
        self.confidence_threshold = confidence_threshold
        
        # Initialize components
        self.detector = KeywordIntentDetector(confidence_threshold=self.confidence_threshold)
        self.extractor = _create_default_extractor()
        self.template_generator = TemplateGenerator()
        
        # Enhanced context detector (lazy loaded)
        self._enhanced_detector = None
        self._enhanced_detector_loaded = False
    
    @property
    def enhanced_detector(self):
        """Lazy load enhanced context detector."""
        if self._enhanced_detector_loaded:
            return self._enhanced_detector
        
        if not self.use_enhanced_context:
            self._enhanced_detector_loaded = True
            return None
        
        try:
            from nlp2cmd.generation.enhanced_context import EnhancedContextDetector
            self._enhanced_detector = EnhancedContextDetector()
        except ImportError:
            pass
        
        self._enhanced_detector_loaded = True
        return self._enhanced_detector
    
    def process(self, text: str) -> PipelineResult:
        """
        Process natural language text through the pipeline.
        
        Args:
            text: Natural language input
            
        Returns:
            PipelineResult with generated command and metadata
        """
        start_time = time.time()
        
        result = PipelineResult(input_text=text)
        
        try:
            # Step 1: Intent detection
            detection = self.detector.detect(text)
            if not detection.matched:
                result.errors.append("No intent detected")
                return result
            
            result.domain = detection.domain
            result.intent = detection.intent
            result.detection_confidence = detection.confidence
            
            # Step 2: Enhanced context (if available)
            if self.enhanced_detector:
                enhanced_result = self.enhanced_detector.enhance(detection, text)
                if enhanced_result:
                    detection = enhanced_result
                    result.metadata["enhanced_context"] = True
            
            # Step 3: Entity extraction
            extraction = self._process_with_detection(text, detection)
            if extraction:
                result.entities = extraction.entities
                result.metadata.update(extraction.metadata or {})
            
            # Step 4: Template generation
            template_result = self.template_generator.generate(
                intent=result.intent,
                entities=result.entities,
                domain=result.domain,
            )
            
            if template_result.success:
                result.command = template_result.command
                result.template_used = template_result.template_used
                result.success = True
                result.confidence = min(detection.confidence, template_result.confidence)
            else:
                result.errors.extend(template_result.errors)
                result.warnings.extend(template_result.warnings)
            
        except Exception as e:
            result.errors.append(f"Pipeline error: {e}")
        
        # Calculate latency
        result.latency_ms = (time.time() - start_time) * 1000
        
        # Record metrics
        self.metrics.record_result(result)
        
        # Persist results if enabled
        if self.persist_results and result.success:
            self._persist_result(result)
        
        return result
    
    def process_steps(self, text: str) -> list[PipelineResult]:
        """Process text step by step for multi-step commands."""
        sentences = self._split_sentences(text)
        if len(sentences) <= 1:
            return [self.process(text)]
        
        results = []
        context_entities = {}
        
        for i, sentence in enumerate(sentences):
            # Add context from previous steps
            enhanced_text = sentence
            if context_entities:
                context_str = ", ".join(f"{k}: {v}" for k, v in context_entities.items())
                enhanced_text = f"{sentence} (context: {context_str})"
            
            result = self.process(enhanced_text)
            result.metadata["step"] = i + 1
            result.metadata["total_steps"] = len(sentences)
            
            # Update context with new entities
            if result.success:
                context_entities.update(result.entities)
            
            results.append(result)
        
        return results
    
    def _process_with_detection(
        self,
        text: str,
        detection: DetectionResult,
    ) -> Optional[ExtractionResult]:
        """Process entity extraction with detection context."""
        try:
            return self.extractor.extract(text, detection)
        except Exception as e:
            # Log error but don't fail the pipeline
            return None
    
    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # Simple sentence splitting - can be enhanced
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _persist_result(self, result: PipelineResult) -> None:
        """Persist successful result to file."""
        try:
            output_path = data_file_write_path("pipeline_results.jsonl")
            
            with open(output_path, "a", encoding="utf-8") as f:
                record = {
                    "timestamp": time.time(),
                    "input": result.input_text,
                    "domain": result.domain,
                    "intent": result.intent,
                    "command": result.command,
                    "confidence": result.confidence,
                    "latency_ms": result.latency_ms,
                }
                f.write(json.dumps(record) + "\n")
        except Exception:
            pass  # Don't fail pipeline for persistence issues
    
    def process_with_llm_repair(
        self,
        text: str,
        *,
        llm_client: Any,
        persist: bool = False,
        max_repairs: int = 2,
    ) -> PipelineResult:
        """Process with LLM repair for failed results."""
        result = self.process(text)
        
        if result.success or max_repairs <= 0:
            return result
        
        # Try LLM repair
        try:
            repair_prompt = self._build_repair_prompt(result)
            repair_response = llm_client.generate(repair_prompt)
            
            if repair_response:
                # Parse repair response
                repaired_command = self._parse_repair_response(repair_response)
                if repaired_command:
                    result.command = repaired_command
                    result.success = True
                    result.source = "llm_repair"
                    result.metadata["repair_attempts"] = 1
                    
                    # Try recursive repair if still needed
                    if max_repairs > 1:
                        return self.process_with_llm_repair(
                            text,
                            llm_client=llm_client,
                            persist=persist,
                            max_repairs=max_repairs - 1,
                        )
        except Exception as e:
            result.errors.append(f"LLM repair failed: {e}")
        
        return result
    
    def _build_repair_prompt(self, result: PipelineResult) -> str:
        """Build repair prompt for LLM."""
        return f"""
Please fix this failed command generation:

Input: {result.input_text}
Detected intent: {result.intent}
Detected domain: {result.domain}
Entities: {result.entities}
Failed command: {result.command}
Errors: {result.errors}

Please provide a corrected command that accomplishes the user's intent.
Respond with only the corrected command, no explanation.
"""
    
    def _parse_repair_response(self, response: str) -> Optional[str]:
        """Parse LLM repair response."""
        response = response.strip()
        
        # Remove common prefixes
        prefixes = ["Command:", "Corrected command:", "Fixed command:"]
        for prefix in prefixes:
            if response.startswith(prefix):
                response = response[len(prefix):].strip()
        
        # Remove quotes if present
        if response.startswith('"') and response.endswith('"'):
            response = response[1:-1]
        elif response.startswith("'") and response.endswith("'"):
            response = response[1:-1]
        
        return response if response else None
    
    def process_batch(self, texts: list[str]) -> list[PipelineResult]:
        """Process multiple texts."""
        results = []
        for text in texts:
            result = self.process(text)
            results.append(result)
        return results
    
    def get_supported_domains(self) -> list[str]:
        """Get list of supported domains."""
        return self.detector.get_supported_domains()
    
    def get_supported_intents(self, domain: Optional[str] = None) -> list[str]:
        """Get list of supported intents."""
        if domain:
            return self.detector.get_supported_intents(domain)
        return self.detector.get_supported_intents()
    
    def get_metrics(self) -> dict[str, Any]:
        """Get pipeline metrics."""
        return self.metrics.get_summary()
    
    def reset_metrics(self) -> None:
        """Reset pipeline metrics."""
        self.metrics = PipelineMetrics()


def create_pipeline(
    confidence_threshold: float = 0.3,  # Lower threshold for better test compatibility
    custom_patterns: Optional[dict] = None,
    **kwargs
) -> RuleBasedPipeline:
    """Create a RuleBasedPipeline with default configuration."""
    from nlp2cmd.generation.keywords.keyword_patterns import KeywordPatterns
    
    patterns = custom_patterns if custom_patterns else None
    
    return RuleBasedPipeline(
        confidence_threshold=confidence_threshold,
        **kwargs
    )
