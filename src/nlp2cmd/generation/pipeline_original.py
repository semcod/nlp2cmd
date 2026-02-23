"""
Iteration 3: Rule-Based Pipeline.

Combines KeywordIntentDetector, RegexEntityExtractor, and TemplateGenerator
into a complete NL → DSL pipeline without LLM.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
import json
import os
from pathlib import Path
import re
import time

from nlp2cmd.utils.data_files import data_file_write_path

# Simple execution plan to avoid circular import
@dataclass
class SimpleExecutionPlan:
    """Simple execution plan for adapters."""
    intent: str
    entities: dict[str, Any]
    confidence: float
    text: str

from nlp2cmd.generation.keywords.keyword_detector import KeywordIntentDetector, DetectionResult
from nlp2cmd.generation.regex import RegexEntityExtractor, ExtractionResult
from nlp2cmd.generation.template_generator import TemplateGenerator, TemplateResult

# Enhanced context detector is imported lazily (it can pull heavy deps like torch).
ENHANCED_CONTEXT_AVAILABLE: bool | None = None

_DEFAULT_USE_ENHANCED_CONTEXT = str(os.environ.get("NLP2CMD_USE_ENHANCED_CONTEXT") or "").strip().lower() in {
    "1",
    "true",
    "yes",
    "y",
    "on",
}

_SEMANTIC_ENTITY_MODES = {"semantic", "shadow", "ab"}


def _should_use_semantic_extractor() -> bool:
    mode = os.environ.get("NLP2CMD_ENTITY_EXTRACTOR_MODE")
    if not isinstance(mode, str):
        return False
    return mode.strip().lower() in _SEMANTIC_ENTITY_MODES


def _create_default_extractor() -> Any:
    if _should_use_semantic_extractor():
        from nlp2cmd.generation.semantic_entities import SemanticEntityExtractor

        return SemanticEntityExtractor()
    return RegexEntityExtractor()


@dataclass
class PipelineResult:
    """Result of the complete pipeline."""
    
    # Input
    input_text: str = ""
    
    # Detection
    domain: str = "unknown"
    intent: str = "unknown"
    confidence: float = 0.0
    detection_confidence: float = 0.0
    
    # Extraction
    entities: dict[str, Any] = field(default_factory=dict)
    
    # Generation
    command: str = ""
    template_used: str = ""
    
    # Metadata
    success: bool = False
    source: str = "rules"  # "rules" or "llm"
    latency_ms: float = 0.0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.confidence == 0.0 and self.detection_confidence != 0.0:
            self.confidence = self.detection_confidence
        if self.detection_confidence == 0.0 and self.confidence != 0.0:
            self.detection_confidence = self.confidence
    
    def to_plan(self) -> 'SimpleExecutionPlan':
        """Convert to execution plan format for adapters."""
        conf = self.confidence if self.confidence != 0.0 else self.detection_confidence
        return SimpleExecutionPlan(intent=self.intent, entities=self.entities, confidence=conf, text=self.input_text)


class RuleBasedPipeline:
    """
    Complete rule-based NL → DSL pipeline.
    
    Combines:
    - KeywordIntentDetector for domain/intent detection
    - RegexEntityExtractor for entity extraction  
    - TemplateGenerator for DSL generation
    
    No LLM required - fast, free, deterministic.
    
    Example:
        pipeline = RuleBasedPipeline()
        result = pipeline.process("Pokaż wszystkich użytkowników z tabeli users")
        print(result.command)  # SELECT * FROM users;
    """
    
    def __init__(
        self,
        detector: Optional[KeywordIntentDetector] = None,
        extractor: Optional[Any] = None,
        generator: Optional[TemplateGenerator] = None,
        confidence_threshold: float = 0.5,
        use_enhanced_context: bool = _DEFAULT_USE_ENHANCED_CONTEXT,
    ):
        """
        Initialize pipeline.
        
        Args:
            detector: Intent detector (default: KeywordIntentDetector)
            extractor: Entity extractor (default: RegexEntityExtractor or SemanticEntityExtractor)
            generator: Template generator (default: TemplateGenerator)
            confidence_threshold: Minimum confidence to proceed
            use_enhanced_context: Use enhanced NLP context detection
        """
        self.detector = detector or KeywordIntentDetector()
        self.extractor = extractor or _create_default_extractor()
        self.generator = generator or TemplateGenerator()
        self.confidence_threshold = confidence_threshold
        self.use_enhanced_context = use_enhanced_context
        
        # Initialize enhanced detector lazily (only when needed)
        self._enhanced_detector = None
        self._enhanced_detector_loaded = False

    @property
    def enhanced_detector(self):
        """Lazy load enhanced detector only when needed."""
        global ENHANCED_CONTEXT_AVAILABLE

        if not self.use_enhanced_context:
            return None

        if ENHANCED_CONTEXT_AVAILABLE is None:
            try:
                from nlp2cmd.generation.enhanced_context import get_enhanced_detector  # noqa: WPS433
                ENHANCED_CONTEXT_AVAILABLE = True
            except Exception:
                ENHANCED_CONTEXT_AVAILABLE = False

        if not ENHANCED_CONTEXT_AVAILABLE:
            self.use_enhanced_context = False
            return None

        if not self._enhanced_detector_loaded:
            from nlp2cmd.generation.enhanced_context import get_enhanced_detector  # noqa: WPS433
            self._enhanced_detector = get_enhanced_detector()
            self._enhanced_detector_loaded = True
        return self._enhanced_detector
    
    def process(self, text: str) -> PipelineResult:
        """
        Process natural language text through the pipeline.
        
        Args:
            text: Natural language input
            
        Returns:
            PipelineResult with generated command
        """
        start_time = time.time()
        errors: list[str] = []
        warnings: list[str] = []
        
        # Step 1: Detect domain and intent
        detection = self.detector.detect(text)
        
        # Step 1.5: Try enhanced context detection if available and basic detection failed
        if (self.use_enhanced_context and 
            not self._enhanced_detector_loaded and 
            (detection.domain == 'unknown' or 
             detection.confidence < 0.7)):  # Only trigger for low confidence or unknown domain
            
            try:
                enhanced_match = self.enhanced_detector.get_best_match(text)
                if enhanced_match and enhanced_match.combined_score > 0.25:  # Even lower threshold
                    # Convert enhanced match to DetectionResult
                    detection = DetectionResult(
                        domain=enhanced_match.domain,
                        intent=enhanced_match.intent,
                        confidence=enhanced_match.combined_score,
                        matched_keyword=enhanced_match.pattern,
                        entities=enhanced_match.entities
                    )
            except Exception as e:
                # Enhanced detection failed, continue with basic detection
                pass

        sentences = self._split_sentences(text)
        if len(sentences) >= 2:
            agg = self._aggregate_detection(sentences)
            if agg is not None:
                dominant = agg.get("detection")
                if isinstance(dominant, DetectionResult):
                    # Enhanced multi-sentence decision logic
                    consistency = agg.get("consistency", {})
                    domain_consistency = consistency.get("domain", 0.0)
                    intent_consistency = consistency.get("intent", 0.0)
                    
                    # Use aggregated result if:
                    # 1. Original detection is unknown, OR
                    # 2. Aggregated has higher confidence, OR  
                    # 3. High consistency (>0.7) even with slightly lower confidence
                    should_use_agg = (
                        detection.domain == "unknown" or
                        dominant.confidence >= detection.confidence or
                        (domain_consistency > 0.7 and dominant.confidence > 0.6)
                    )
                    
                    if should_use_agg:
                        detection = dominant
                        consistency_info = f" (domain: {domain_consistency:.2f}, intent: {intent_consistency:.2f})"
                        warnings.append(
                            f"Multi-sentence aggregation: using {dominant.domain}/{dominant.intent} "
                            f"(confidence {dominant.confidence:.2f}){consistency_info}"
                        )
        
        if detection.domain == 'unknown':
            latency = (time.time() - start_time) * 1000
            return PipelineResult(
                input_text=text,
                domain='unknown',
                intent='unknown',
                confidence=0.0,
                detection_confidence=0.0,
                entities={},
                command=f"# Unknown: could not detect domain for: {text}",
                template_used="",
                success=False,
                latency_ms=latency,
                errors=["Could not detect domain from input text"],
            )
        
        if detection.confidence < self.confidence_threshold:
            warnings.append(f"Low confidence detection: {detection.confidence:.2f}")
        
        # Step 2: Extract entities
        extraction = self.extractor.extract(text, detection.domain)

        extractor_meta: dict[str, Any] = {}
        last_mode = getattr(self.extractor, "last_mode", None)
        if isinstance(last_mode, str) and last_mode:
            extractor_meta["entity_extractor_mode"] = last_mode
            if last_mode == "shadow":
                extractor_meta["shadow_entities"] = getattr(self.extractor, "last_semantic_entities", None)
        
        if not extraction.entities:
            warnings.append("No entities extracted from text")
        
        # Step 3: Generate command from template
        # Add original text to entities for context-aware template selection
        # Use enhanced context entities if available, otherwise use extraction entities
        if hasattr(detection, 'entities') and detection.entities:
            merged_entities = detection.entities.copy()
        else:
            merged_entities = extraction.entities.copy()
        
        entities_with_text = merged_entities.copy()
        entities_with_text['text'] = text

        template_result = self.generator.generate(
            domain=detection.domain,
            intent=detection.intent,
            entities=entities_with_text,
        )

        if not template_result.success:
            fallback_results: list[tuple[DetectionResult, ExtractionResult, TemplateResult]] = []
            for cand in self.detector.detect_all(text)[:8]:
                if cand.domain == detection.domain and cand.intent == detection.intent:
                    continue

                cand_extraction = self.extractor.extract(text, cand.domain)
                cand_entities = cand_extraction.entities.copy()
                cand_entities["text"] = text
                cand_template = self.generator.generate(
                    domain=cand.domain,
                    intent=cand.intent,
                    entities=cand_entities,
                )
                if cand_template.success:
                    fallback_results.append((cand, cand_extraction, cand_template))
                    break

            if fallback_results:
                chosen_detection, chosen_extraction, chosen_template = fallback_results[0]
                detection = chosen_detection
                extraction = chosen_extraction
                template_result = chosen_template
        
        if not template_result.success:
            errors.append(f"Template generation failed: {template_result.command}")
        
        if template_result.missing_entities:
            warnings.append(f"Missing entities: {template_result.missing_entities}")
        
        # Determine success based on template success, no errors, and confidence threshold
        is_successful = (
            template_result.success and 
            len(errors) == 0 and 
            detection.confidence >= self.confidence_threshold
        )
        
        # If confidence is too low, return unknown command
        if detection.confidence < self.confidence_threshold:
            command = "# Unknown: could not detect domain for input"
            template_used = ""
        else:
            command = template_result.command
            template_used = template_result.template_used
        
        latency = (time.time() - start_time) * 1000
        
        return PipelineResult(
            input_text=text,
            domain=detection.domain,
            intent=detection.intent,
            confidence=detection.confidence,
            detection_confidence=detection.confidence,
            entities=merged_entities,
            command=command,
            template_used=template_used,
            success=is_successful,
            source="rules",
            latency_ms=latency,
            errors=errors,
            warnings=warnings,
            metadata=extractor_meta,
        )

    def _infer_domain_from_markers(self, text_lower: str) -> Optional[str]:
        if not text_lower:
            return None

        if any(x in text_lower for x in ("kubectl", "kubernetes", "k8s")) or re.search(r"\bpod(y)?\b", text_lower):
            return "kubernetes"

        if any(x in text_lower for x in ("docker", "kontener", "container", "docker-compose", "compose")):
            return "docker"

        if re.search(r"\b(select|update|delete|insert|from|where|join|sql|tabela|table)\b", text_lower):
            return "sql"

        if any(x in text_lower for x in ("entity", "graph", "dql")):
            return "dql"

        return None

    def process_steps(self, text: str) -> list[PipelineResult]:
        sentences = self._split_sentences(text)
        if len(sentences) <= 1:
            return [self.process(text)]

        results: list[PipelineResult] = []
        prev_domain: Optional[str] = None
        prev_intent: Optional[str] = None
        prev_conf: float = 0.0
        prev_entities: dict[str, Any] = {}

        for sent in sentences:
            sent_lower = sent.strip().lower()
            forced_domain = self._infer_domain_from_markers(sent_lower)

            d = self.detector.detect(sent)
            if forced_domain is not None and d.domain != forced_domain:
                for c in self.detector.detect_all(sent)[:12]:
                    if c.domain == forced_domain:
                        d = c
                        break

            begins_with_connector = bool(
                re.match(r"^(nast[eę]pnie|potem|dalej|oraz|a potem|je[sś]li|je[sś]eli|gdy|wtedy|na koniec)\b", sent_lower)
            )

            is_conditional = bool(re.match(r"^(je[sś]li|je[sś]eli|gdy|wtedy)\b", sent_lower))

            if prev_domain and begins_with_connector and forced_domain is None and d.domain != prev_domain:
                # Avoid domain drift on continuation/conditional sentences unless explicit markers appear.
                d = DetectionResult(
                    domain=prev_domain,
                    intent=d.intent if d.intent != "unknown" else (prev_intent or "unknown"),
                    confidence=max(0.35, min(0.7, prev_conf * 0.6)),
                    matched_keyword=None,
                )

            if prev_domain == "shell" and prev_intent and prev_intent.startswith("git_") and begins_with_connector and forced_domain is None:
                if "status" in sent_lower:
                    d = DetectionResult(
                        domain="shell",
                        intent="git_status",
                        confidence=max(0.6, min(0.85, prev_conf * 0.8)),
                        matched_keyword="git_status_followup",
                    )

            if (d.domain == "unknown" or d.intent == "unknown") and prev_domain and begins_with_connector:
                chosen = None
                for c in self.detector.detect_all(sent)[:8]:
                    if c.domain == prev_domain:
                        chosen = c
                        break
                if chosen is not None:
                    d = chosen
                else:
                    d = DetectionResult(
                        domain=prev_domain,
                        intent=prev_intent or "unknown",
                        confidence=max(0.35, min(0.7, prev_conf * 0.6)),
                        matched_keyword=None,
                    )

            context_entities: dict[str, Any] = {}
            if prev_domain and d.domain == prev_domain and (begins_with_connector or is_conditional):
                context_entities = dict(prev_entities)

            step = self._process_with_detection(sent, d, context_entities=context_entities)
            results.append(step)

            if step.domain != "unknown":
                prev_domain = step.domain
                prev_intent = step.intent
                prev_conf = float(step.detection_confidence)
                prev_entities = step.entities or {}

        return results

    def _process_with_detection(
        self,
        text: str,
        detection: DetectionResult,
        *,
        context_entities: Optional[dict[str, Any]] = None,
    ) -> PipelineResult:
        start_time = time.time()
        errors: list[str] = []
        warnings: list[str] = []

        if detection.domain == 'unknown':
            latency = (time.time() - start_time) * 1000
            return PipelineResult(
                input_text=text,
                domain='unknown',
                intent='unknown',
                detection_confidence=0.0,
                entities={},
                command=f"# Could not detect domain for: {text}",
                template_used="",
                success=False,
                latency_ms=latency,
                errors=["Could not detect domain from input text"],
            )

        if detection.confidence < self.confidence_threshold:
            warnings.append(f"Low confidence detection: {detection.confidence:.2f}")

        extraction = self.extractor.extract(text, detection.domain)
        if not extraction.entities:
            warnings.append("No entities extracted from text")

        merged_entities: dict[str, Any] = {}
        # Use enhanced context entities if available
        if hasattr(detection, 'entities') and detection.entities:
            merged_entities.update(detection.entities)
        elif isinstance(context_entities, dict) and context_entities:
            merged_entities.update(context_entities)
        merged_entities.update(extraction.entities or {})

        entities_with_text = merged_entities.copy()
        entities_with_text['text'] = text

        template_result = self.generator.generate(
            domain=detection.domain,
            intent=detection.intent,
            entities=entities_with_text,
        )

        if not template_result.success:
            fallback_results: list[tuple[DetectionResult, ExtractionResult, TemplateResult]] = []
            for cand in self.detector.detect_all(text)[:8]:
                if cand.domain == detection.domain and cand.intent == detection.intent:
                    continue

                cand_extraction = self.extractor.extract(text, cand.domain)
                cand_entities = cand_extraction.entities.copy()
                cand_entities["text"] = text
                cand_template = self.generator.generate(
                    domain=cand.domain,
                    intent=cand.intent,
                    entities=cand_entities,
                )
                if cand_template.success:
                    fallback_results.append((cand, cand_extraction, cand_template))
                    break

            if fallback_results:
                chosen_detection, chosen_extraction, chosen_template = fallback_results[0]
                detection = chosen_detection
                extraction = chosen_extraction
                template_result = chosen_template

        if not template_result.success:
            errors.append(f"Template generation failed: {template_result.command}")

        if template_result.missing_entities:
            warnings.append(f"Missing entities: {template_result.missing_entities}")

        # Determine success based on template success, no errors, and confidence threshold
        is_successful = (
            template_result.success and 
            len(errors) == 0 and 
            detection.confidence >= self.confidence_threshold
        )
        
        # If confidence is too low, return unknown command
        if detection.confidence < self.confidence_threshold:
            command = "# Unknown: could not detect domain for input"
            template_used = ""
        else:
            command = template_result.command
            template_used = template_result.template_used

        latency = (time.time() - start_time) * 1000
        return PipelineResult(
            input_text=text,
            domain=detection.domain,
            intent=detection.intent,
            detection_confidence=detection.confidence,
            entities=extraction.entities,
            command=command,
            template_used=template_used,
            success=is_successful,
            source="rules",
            latency_ms=latency,
            errors=errors,
            warnings=warnings,
        )

    def _split_sentences(self, text: str) -> list[str]:
        if not isinstance(text, str) or not text.strip():
            return []

        if "\n" in text:
            lines = [ln for ln in text.splitlines() if ln.strip()]
            if len(lines) >= 3:
                score = 0
                for ln in lines[:40]:
                    ll = ln.lower()
                    if "traceback (most recent call last)" in ll:
                        score += 4
                    if re.search(r"file \".+\", line \d+", ln):
                        score += 3
                    if re.search(r"\b(exception|error|fatal|stack trace)\b", ll):
                        score += 1
                    if re.search(r"^\d{4}-\d{2}-\d{2}[ t]\d{2}:\d{2}:\d{2}", ln):
                        score += 1
                    if re.search(r"^\[(info|warn|warning|error|debug|trace)\]", ll):
                        score += 1
                    if "command not found" in ll:
                        score += 2

                # Treat log-like input as a single "sentence" to avoid expensive NLP.
                if score >= 4:
                    return [text]

        # Fast regex-based splitting (default). This keeps cold-start fast.
        parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text) if p.strip()]
        return parts

    def _aggregate_detection(self, sentences: list[str]) -> Optional[dict[str, Any]]:
        """Enhanced aggregation of multi-sentence detection using semantic analysis."""
        if not sentences or len(sentences) < 2:
            return None

        domain_scores: dict[str, float] = {}
        intent_scores: dict[str, float] = {}
        sentence_results: list[DetectionResult] = []
        
        # Enhanced Polish connectors and semantic markers
        polish_connectors = {
            'sequence': ['następnie', 'potem', 'dalej', 'wtedy', 'na koniec', 'potem', 'po czym', 'zanim'],
            'conditional': ['jeśli', 'jeżeli', 'gdy', 'gdyby', 'w razie', 'przy'],
            'causal': ['ponieważ', 'dlatego', 'zatem', 'w związku z tym', 'wskutek'],
            'additive': ['oraz', 'i', 'także', 'również', 'ponadto', 'wszakże'],
            'contrastive': ['ale', 'jednakże', 'lecz', 'aczkolwiek', 'natomiast', 'mimo wszystko']
        }
        
        # Analyze each sentence
        for i, sent in enumerate(sentences):
            d = self.detector.detect(sent)
            sentence_results.append(d)
            
            sent_lower = sent.strip().lower()
            
            # Detect sentence type and connectors
            connector_type = None
            for conn_type, connectors in polish_connectors.items():
                if any(re.match(rf"^{re.escape(conn)}\b", sent_lower) for conn in connectors):
                    connector_type = conn_type
                    break
            
            # Weight confidence based on position and connector type
            weight = 1.0
            if i == 0:
                weight = 1.2  # First sentence gets higher weight
            elif i == len(sentences) - 1:
                weight = 1.1  # Last sentence gets slightly higher weight
            
            if connector_type == 'sequence':
                weight *= 1.15
            elif connector_type == 'conditional':
                weight *= 0.9  # Conditional sentences are less central
            elif connector_type == 'causal':
                weight *= 1.25  # Causal sentences are important
            
            # Apply weighted scoring
            if isinstance(d.domain, str) and d.domain and d.domain != "unknown":
                domain_scores[d.domain] = domain_scores.get(d.domain, 0.0) + (float(d.confidence) * weight)
            
            if isinstance(d.intent, str) and d.intent and d.intent != "unknown":
                intent_scores[d.intent] = intent_scores.get(d.intent, 0.0) + (float(d.confidence) * weight)
        
        # Enhanced domain consistency analysis
        if not domain_scores:
            return None
        
        # Find dominant domain with consistency bonus
        sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
        dominant_domain, dominant_score = sorted_domains[0]
        
        # Apply consistency bonus if most sentences agree on domain
        domain_consistency = sum(1 for r in sentence_results if r.domain == dominant_domain) / len(sentence_results)
        if domain_consistency >= 0.6:
            dominant_score *= 1.2
        
        # Enhanced intent detection with context awareness
        if not intent_scores:
            dominant_intent = "unknown"
        else:
            sorted_intents = sorted(intent_scores.items(), key=lambda x: x[1], reverse=True)
            dominant_intent, intent_score = sorted_intents[0]
            
            # Apply intent consistency bonus
            intent_consistency = sum(1 for r in sentence_results if r.intent == dominant_intent) / len(sentence_results)
            if intent_consistency >= 0.5:
                intent_score *= 1.1
        
        # Find best individual detection as fallback
        best = max(sentence_results, key=lambda x: x.confidence)
        
        # Calculate final confidence with multiple factors
        base_confidence = float(best.confidence)
        consistency_bonus = (domain_consistency + intent_consistency) / 2 * 0.2
        sentence_count_bonus = min(len(sentences) * 0.05, 0.15)
        
        final_confidence = min(0.95, base_confidence + consistency_bonus + sentence_count_bonus)
        
        return {
            "domain_scores": domain_scores,
            "intent_scores": intent_scores,
            "detection": DetectionResult(
                domain=dominant_domain,
                intent=dominant_intent,
                confidence=final_confidence,
                matched_keyword=None,
            ),
            "consistency": {
                "domain": domain_consistency,
                "intent": intent_consistency if intent_scores else 0.0
            },
            "sentence_count": len(sentences)
        }

    def process_with_llm_repair(
        self,
        text: str,
        *,
        llm_client: "LLMClient",
        persist: bool = False,
        max_repairs: int = 1,
    ) -> PipelineResult:
        from nlp2cmd.generation.llm_simple import LLMClient

        _ = llm_client
        start = time.time()
        last = self.process(text)
        if last.success:
            return last

        for _attempt in range(max_repairs):
            patch = self._suggest_schema_patch(text, last, llm_client=llm_client)
            if not patch:
                break

            self._apply_schema_patch(patch)
            if persist:
                self._persist_schema_patch(patch)

            last = self.process(text)
            if last.success:
                last.source = "llm"
                last.latency_ms = (time.time() - start) * 1000
                return last

        last.latency_ms = (time.time() - start) * 1000
        return last

    def _suggest_schema_patch(
        self,
        text: str,
        last_result: PipelineResult,
        *,
        llm_client: "LLMClient",
    ) -> Optional[dict[str, Any]]:
        import asyncio
        from nlp2cmd.generation.llm_simple import LLMClient

        _ = llm_client

        system = (
            "You are a code assistant that fixes a rule-based NL->command router. "
            "Respond ONLY with valid JSON. No markdown.\n\n"
            "Goal: propose minimal additions to keyword patterns and/or templates so the rule-based pipeline can handle the query.\n"
            "Constraints:\n"
            "- Only propose SAFE, read-only shell commands when domain is shell (no rm, mv, cp, sudo).\n"
            "- Prefer using find/ls/grep/wc.\n"
            "- Output JSON with keys: patterns, templates.\n"
            "- patterns format: {domain: {intent: [keywords...]}}\n"
            "- templates format: {domain: {intent: template_string}}\n"
        )

        user = {
            "query": text,
            "last_error": last_result.command,
            "last_domain": last_result.domain,
            "last_intent": last_result.intent,
            "known_domains": self.detector.get_supported_domains(),
            "shell_intents": self.detector.get_supported_intents("shell") if "shell" in self.detector.get_supported_domains() else [],
        }
        prompt = json.dumps(user, ensure_ascii=False)

        async def _run() -> str:
            return await llm_client.complete(user=prompt, system=system, max_tokens=700, temperature=0.0)

        try:
            raw = asyncio.run(_run())
        except Exception:
            return None

        try:
            payload = json.loads(raw)
        except Exception:
            return None

        if not isinstance(payload, dict):
            return None

        patterns = payload.get("patterns")
        templates = payload.get("templates")
        if patterns is None and templates is None:
            return None

        out: dict[str, Any] = {}
        if isinstance(patterns, dict):
            out["patterns"] = patterns
        if isinstance(templates, dict):
            out["templates"] = templates
        return out or None

    def _apply_schema_patch(self, patch: dict[str, Any]) -> None:
        patterns = patch.get("patterns")
        if isinstance(patterns, dict):
            for domain, intents in patterns.items():
                if not isinstance(domain, str) or not isinstance(intents, dict):
                    continue
                for intent, keywords in intents.items():
                    if not isinstance(intent, str) or not isinstance(keywords, list):
                        continue
                    clean = [kw.strip() for kw in keywords if isinstance(kw, str) and kw.strip()]
                    if clean:
                        self.detector.add_pattern(domain, intent, clean)

        templates = patch.get("templates")
        if isinstance(templates, dict):
            for domain, intents in templates.items():
                if not isinstance(domain, str) or not isinstance(intents, dict):
                    continue
                for intent, template in intents.items():
                    if isinstance(intent, str) and intent and isinstance(template, str) and template:
                        self.generator.add_template(domain, intent, template)

    def _persist_schema_patch(self, patch: dict[str, Any]) -> None:
        patterns_path = data_file_write_path(
            explicit_path=os.environ.get("NLP2CMD_PATTERNS_FILE"),
            default_filename="patterns.json",
        )
        templates_path = data_file_write_path(
            explicit_path=os.environ.get("NLP2CMD_TEMPLATES_FILE"),
            default_filename="templates.json",
        )

        patterns = patch.get("patterns")
        if isinstance(patterns, dict):
            self._merge_json_file(patterns_path, patterns)

        templates = patch.get("templates")
        if isinstance(templates, dict):
            self._merge_json_file(templates_path, templates)

    def _merge_json_file(self, path: Path, patch: dict[str, Any]) -> None:
        try:
            existing: dict[str, Any] = {}
            if path.exists():
                loaded = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    existing = loaded

            for domain, intents in patch.items():
                if not isinstance(domain, str) or not isinstance(intents, dict):
                    continue
                bucket = existing.setdefault(domain, {})
                if not isinstance(bucket, dict):
                    continue
                for intent, value in intents.items():
                    if not isinstance(intent, str) or not intent:
                        continue
                    if isinstance(value, list):
                        prev = bucket.get(intent)
                        prev_list = prev if isinstance(prev, list) else []
                        merged = prev_list + [v for v in value if isinstance(v, str) and v.strip()]
                        deduped: list[str] = []
                        seen: set[str] = set()
                        for s in merged:
                            key = s.strip().lower()
                            if not key or key in seen:
                                continue
                            seen.add(key)
                            deduped.append(s.strip())
                        bucket[intent] = deduped
                    elif isinstance(value, str) and value:
                        bucket[intent] = value

            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except Exception:
            return
    
    def process_batch(self, texts: list[str]) -> list[PipelineResult]:
        """
        Process multiple texts.
        
        Args:
            texts: List of natural language inputs
            
        Returns:
            List of PipelineResult
        """
        return [self.process(text) for text in texts]
    
    def detect_only(self, text: str) -> DetectionResult:
        """
        Only detect domain and intent (skip extraction and generation).
        
        Args:
            text: Natural language input
            
        Returns:
            DetectionResult
        """
        return self.detector.detect(text)
    
    def extract_only(self, text: str, domain: str) -> ExtractionResult:
        """
        Only extract entities (skip detection and generation).
        
        Args:
            text: Natural language input
            domain: Target domain
            
        Returns:
            ExtractionResult
        """
        return self.extractor.extract(text, domain)
    
    def generate_only(
        self,
        domain: str,
        intent: str,
        entities: dict[str, Any],
    ) -> TemplateResult:
        """
        Only generate command (skip detection and extraction).
        
        Args:
            domain: Target domain
            intent: Intent
            entities: Entities dict
            
        Returns:
            TemplateResult
        """
        return self.generator.generate(domain, intent, entities)
    
    def get_supported_domains(self) -> list[str]:
        """Get list of supported domains."""
        return self.detector.get_supported_domains()
    
    def get_supported_intents(self, domain: str) -> list[str]:
        """Get list of supported intents for a domain."""
        return self.detector.get_supported_intents(domain)


class PipelineMetrics:
    """Track pipeline metrics for evaluation."""
    
    def __init__(self):
        self.latencies: list[float] = []
        self.total_requests = 0
        self.successful_requests = 0
        self.domain_counts: dict[str, int] = {}
        self.intent_counts: dict[str, int] = {}
        self.total_latency_ms = 0.0
        self.confidence_sum = 0.0
        self.errors: list[str] = []
    
    def record(self, result: PipelineResult) -> None:
        """Record a pipeline result."""
        self.total_requests += 1
        
        if result.success:
            self.successful_requests += 1
        
        self.domain_counts[result.domain] = self.domain_counts.get(result.domain, 0) + 1
        
        intent_key = f"{result.domain}.{result.intent}"
        self.intent_counts[intent_key] = self.intent_counts.get(intent_key, 0) + 1
        
        self.total_latency_ms += result.latency_ms
        self.confidence_sum += result.detection_confidence
        
        if result.errors:
            self.errors.extend(result.errors)

    def record_result(self, success: bool, latency: float) -> None:
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        try:
            latency_f = float(latency)
        except Exception:
            latency_f = 0.0
        self.latencies.append(latency_f)
        self.total_latency_ms += latency_f * 1000.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency."""
        if self.total_requests == 0:
            return 0.0
        return self.total_latency_ms / self.total_requests
    
    @property
    def avg_confidence(self) -> float:
        """Calculate average confidence."""
        if self.total_requests == 0:
            return 0.0
        return self.confidence_sum / self.total_requests
    
    def report(self) -> dict[str, Any]:
        """Generate metrics report."""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "success_rate": f"{self.success_rate:.2%}",
            "avg_latency_ms": f"{self.avg_latency_ms:.2f}",
            "avg_confidence": f"{self.avg_confidence:.2f}",
            "domain_distribution": self.domain_counts,
            "intent_distribution": self.intent_counts,
            "error_count": len(self.errors),
        }

    def generate_report(self) -> dict[str, Any]:
        total = self.total_requests
        success_rate = (self.successful_requests / total) if total else 0.0
        avg_latency = (sum(self.latencies) / len(self.latencies)) if self.latencies else 0.0
        min_latency = min(self.latencies) if self.latencies else 0.0
        max_latency = max(self.latencies) if self.latencies else 0.0
        return {
            "total_processed": total,
            "successful": self.successful_requests,
            "success_rate": success_rate,
            "avg_latency": avg_latency,
            "min_latency": min_latency,
            "max_latency": max_latency,
        }


def create_pipeline(
    confidence_threshold: float = 0.5,
    custom_patterns: Optional[dict[str, dict[str, list[str]]]] = None,
    custom_templates: Optional[dict[str, dict[str, str]]] = None,
) -> RuleBasedPipeline:
    """
    Factory function to create a configured pipeline.
    
    Args:
        confidence_threshold: Minimum confidence threshold
        custom_patterns: Additional keyword patterns
        custom_templates: Additional templates
        
    Returns:
        Configured RuleBasedPipeline
    """
    detector = KeywordIntentDetector(confidence_threshold=confidence_threshold)
    extractor = _create_default_extractor()
    generator = TemplateGenerator(custom_templates=custom_templates)
    
    # Add custom patterns if provided
    if custom_patterns:
        for domain, intents in custom_patterns.items():
            for intent, keywords in intents.items():
                detector.add_pattern(domain, intent, keywords)
    
    return RuleBasedPipeline(
        detector=detector,
        extractor=extractor,
        generator=generator,
        confidence_threshold=confidence_threshold,
    )
