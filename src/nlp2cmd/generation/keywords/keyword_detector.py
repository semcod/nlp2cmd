"""
Keyword-based intent detection logic.

This module contains the core detection algorithms and logic
for matching keywords to intents and domains.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Optional

from .keyword_patterns import KeywordPatterns

logger = logging.getLogger(__name__)

# Lazy imports for heavy dependencies
_polish_support = None
_fuzzy_schema_matcher = None
_ml_classifier = None
_semantic_matcher = None
_spacy = None
_nlp_model = None
_nlp_model_loaded = False


def _get_polish_support():
    """Lazy load Polish support to avoid circular imports."""
    global _polish_support
    if _polish_support is None:
        try:
            from nlp2cmd.polish_support import polish_support
            _polish_support = polish_support
        except ImportError:
            _polish_support = False
    return _polish_support if _polish_support else None


def _get_fuzzy_schema_matcher():
    """Lazy load FuzzySchemaMatcher with multilingual phrases."""
    global _fuzzy_schema_matcher
    if _fuzzy_schema_matcher is None:
        try:
            from nlp2cmd.generation.fuzzy_schema_matcher import FuzzySchemaMatcher
            from pathlib import Path
            
            schema_paths = [
                Path(__file__).parent.parent.parent.parent / "data" / "multilingual_phrases.json",
                Path("data/multilingual_phrases.json"),
                Path("multilingual_phrases.json"),
            ]
            
            matcher = FuzzySchemaMatcher()
            for path in schema_paths:
                if path.exists():
                    matcher.load_schema(path)
                    break
            
            if not matcher.phrases:
                from nlp2cmd.generation.fuzzy_schema_matcher import create_multilingual_matcher
                matcher = create_multilingual_matcher()
            
            _fuzzy_schema_matcher = matcher
        except ImportError:
            _fuzzy_schema_matcher = False
    return _fuzzy_schema_matcher if _fuzzy_schema_matcher else None


def _get_ml_classifier():
    """Lazy load ML intent classifier for high-accuracy predictions."""
    global _ml_classifier
    enable_ml = str(
        os.environ.get("NLP2CMD_ENABLE_ML_CLASSIFIER")
        or os.environ.get("NLP2CMD_ENABLE_HEAVY_NLP")
        or ""
    ).strip().lower() in {"1", "true", "yes", "y", "on"}
    
    if not enable_ml:
        return None
    
    if _ml_classifier is None:
        try:
            from nlp2cmd.generation.ml_intent_classifier import get_ml_classifier
            _ml_classifier = get_ml_classifier()
            if _ml_classifier is None:
                _ml_classifier = False
        except ImportError:
            _ml_classifier = False
    return _ml_classifier if _ml_classifier else None


def _get_semantic_matcher():
    """Lazy load semantic matcher for high-accuracy predictions."""
    global _semantic_matcher
    enable_semantic = str(
        os.environ.get("NLP2CMD_ENABLE_SEMANTIC_MATCHING")
        or os.environ.get("NLP2CMD_ENABLE_HEAVY_NLP")
        or ""
    ).strip().lower() in {"1", "true", "yes", "y", "on"}
    
    if not enable_semantic:
        return None
    
    if _semantic_matcher is None:
        try:
            from nlp2cmd.generation.semantic_matcher_optimized import OptimizedSemanticMatcher
            _semantic_matcher = OptimizedSemanticMatcher()
        except ImportError:
            _semantic_matcher = False
    return _semantic_matcher if _semantic_matcher else None


def _get_spacy_model():
    """Lazy load spaCy model for lemmatization."""
    global _spacy, _nlp_model, _nlp_model_loaded
    enable_spacy = str(
        os.environ.get("NLP2CMD_ENABLE_SPACY_LEMMATIZATION")
        or os.environ.get("NLP2CMD_ENABLE_HEAVY_NLP")
        or ""
    ).strip().lower() in {"1", "true", "yes", "y", "on"}
    
    if not enable_spacy:
        return None
    
    if _nlp_model_loaded:
        return _nlp_model
    
    try:
        import spacy
        _spacy = spacy
        
        # Try to load Polish model first, fall back to English
        try:
            _nlp_model = spacy.load("pl_core_news_sm")
        except OSError:
            try:
                _nlp_model = spacy.load("en_core_web_sm")
            except OSError:
                logger.warning("No spaCy model available, falling back to basic tokenization")
                _nlp_model = None
        
        _nlp_model_loaded = True
        return _nlp_model
        
    except ImportError:
        logger.debug("spaCy not available")
        _nlp_model_loaded = True
        return None


@dataclass
class DetectionResult:
    """Result of intent detection."""
    
    domain: str
    intent: str
    confidence: float
    entities: dict[str, str] = None
    metadata: dict[str, any] = None
    matched: bool = True  # Whether detection was successful
    matched_keyword: str = ""  # The keyword that triggered this detection
    
    def __post_init__(self):
        if self.entities is None:
            self.entities = {}
        if self.metadata is None:
            self.metadata = {}


class KeywordIntentDetector:
    """
    Rule-based intent detection using keyword matching.
    
    No LLM needed - uses predefined keyword patterns to detect
    domain (sql, shell, docker, kubernetes) and intent.
    
    Example:
        detector = KeywordIntentDetector()
        result = detector.detect("Pokaż wszystkich użytkowników z tabeli users")
        # result.domain == 'sql', result.intent == 'select'
    """
    
    def __init__(
        self,
        patterns: Optional[KeywordPatterns] = None,
        confidence_threshold: float = 0.5,
        custom_patterns: Optional[dict] = None,
    ):
        """
        Initialize keyword detector.
        
        Args:
            patterns: KeywordPatterns instance or None to create default
            confidence_threshold: Minimum confidence to return a match
            custom_patterns: Optional dict of {domain: {intent: [patterns]}} to add
        """
        self.patterns = patterns or KeywordPatterns()
        self.confidence_threshold = confidence_threshold
        if custom_patterns:
            for domain, intents in custom_patterns.items():
                for intent, pats in intents.items():
                    self.patterns.add_pattern(domain, intent, pats)

    def add_pattern(self, domain: str, intent: str, patterns: list) -> None:
        """Add custom patterns for a domain/intent pair."""
        self.patterns.add_pattern(domain, intent, patterns)
    
    def detect(self, text: str) -> DetectionResult:
        """
        Detect domain and intent from text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            DetectionResult with detected domain, intent, and confidence
        """
        if not text or not text.strip():
            return DetectionResult(domain="", intent="", confidence=0.0, matched=False)
        
        text_lower = text.lower()

        # ML-based detection if available (highest quality, checked first)
        ml_result = self._ml_detection(text)
        if ml_result and ml_result.confidence >= self.confidence_threshold:
            return ml_result

        # Enhanced detection with fuzzy matching
        fuzzy_result = self._fuzzy_detection(text)
        if fuzzy_result and fuzzy_result.confidence >= self.confidence_threshold:
            return fuzzy_result

        # Fast path checks for explicit patterns (browser, SQL syntax, docker, k8s, shell)
        # Only run domain-specific fast-path when patterns are loaded
        has_patterns = bool(self.patterns.patterns)
        fast_result = self._fast_path_detection(text_lower, domain_rules=has_patterns)
        if fast_result:
            return fast_result

        # Semantic matching if available
        semantic_result = self._semantic_detection(text)
        if semantic_result and semantic_result.confidence >= self.confidence_threshold:
            return semantic_result

        # Traditional keyword matching
        result = self._keyword_detection(text, text_lower)

        # Set matched based on confidence threshold
        result.matched = result.confidence >= self.confidence_threshold

        return result
    
    def detect_all(self, text: str) -> list[DetectionResult]:
        """
        Detect all matching domains and intents.
        
        Args:
            text: Natural language input
            
        Returns:
            List of DetectionResult, sorted by confidence descending
        """
        if not text or not text.strip():
            return []
        
        text_lower = text.lower()
        results: list[DetectionResult] = []
        seen: set[tuple[str, str]] = set()
        
        # Get all possible matches from patterns
        for domain, intents in self.patterns.patterns.items():
            for intent, keywords in intents.items():
                for kw in keywords:
                    if self._match_keyword(text_lower, kw):
                        key = (domain, intent)
                        if key not in seen:
                            seen.add(key)
                            confidence = 0.7  # Base confidence for keyword matches
                            results.append(DetectionResult(
                                domain=domain,
                                intent=intent,
                                confidence=confidence
                            ))
        
        # Sort by confidence descending
        results.sort(key=lambda x: x.confidence, reverse=True)
        return results
    
    def _match_keyword(self, text_lower: str, keyword: str) -> bool:
        """Simple keyword matching."""
        return keyword.lower() in text_lower
    
    def _fast_path_detection(self, text_lower: str, domain_rules: bool = True) -> Optional[DetectionResult]:
        """Fast path detection for common patterns."""
        # Explicit overrides — highest priority, very specific patterns
        _EXPLICIT_OVERRIDES = [
            # IP address / network
            ("adres ip", "shell", "network", "adres ip"),
            ("ip address", "shell", "network", "ip address"),
            ("show my ip", "shell", "network", "show my ip"),
            ("pokaż ip", "shell", "network", "pokaż ip"),
            # JSON / jq
            ("parsuj json", "shell", "json_jq", "parsuj json"),
            ("parse json", "shell", "json_jq", "parse json"),
            ("json z pliku", "shell", "json_jq", "json z pliku"),
            ("użyj jq", "utility", "jq", "użyj jq"),
            ("jq do", "utility", "jq", "jq do"),
            # Directory/folder listing — must come before generic file content
            ("zawartość katalogu", "shell", "list", "directory contents"),
            ("zawartość folderu", "shell", "list", "directory contents"),
            ("lista folder", "shell", "list", "directory contents"),
            ("list folder", "shell", "list", "directory contents"),
            # Shell user management
            ("użytkowników systemu", "shell", "user_list", "user_list"),
            ("system users", "shell", "user_list", "user_list"),
            # File content (cat) — after directory listing
            ("zawartość pliku", "shell", "text_cat", "file content"),
            ("zawartosc pliku", "shell", "text_cat", "file content"),
            ("pokaż plik ", "shell", "text_cat", "file content"),
            ("show file content", "shell", "text_cat", "file content"),
            # Logs — docker context (application logs)
            ("logi aplikacji", "docker", "logs", "logi aplikacji"),
            ("application logs", "docker", "logs", "application logs"),
            ("app logs", "docker", "logs", "app logs"),
        ]
        for kw, domain, intent, matched_kw in _EXPLICIT_OVERRIDES:
            if kw in text_lower:
                return DetectionResult(domain=domain, intent=intent, confidence=0.95, matched_keyword=matched_kw)

        # Domain-specific fast-path rules — only when patterns data is loaded
        if not domain_rules:
            return None

        # SQL keyword fast-path (highest priority — explicit SQL syntax)
        _SQL_EXACT = {
            "select ": "select", "insert into": "insert", "update ": "update",
            "delete from": "delete", "delete from ": "delete",  # More specific
            "create table": "create_table", "drop table": "drop_table",
            "alter table": "alter_table", "truncate ": "truncate",
            "create index": "create_index", "create view": "create_view",
            "create database": "create_database",
        }
        for kw, intent in _SQL_EXACT.items():
            if kw in text_lower:
                return DetectionResult(domain="sql", intent=intent, confidence=0.95)

        # Docker fast-path — explicit docker/container terms (ordered: specific first)
        _DOCKER_TERMS = [
            ("docker compose", "compose_up"), ("docker-compose", "compose_up"),
            ("compose up", "compose_up"), ("uruchom docker compose", "compose_up"),
            ("docker ps", "list"), ("docker run", "run"), ("docker stop", "stop"),
            ("docker start", "start"), ("docker rm", "remove"), ("docker rmi", "remove_image"),
            ("docker pull", "pull"), ("docker push", "push"), ("docker build", "build"),
            ("docker exec", "exec"), ("docker logs", "logs"), ("docker image", "images"),
            ("docker volume", "volume"), ("docker network", "network"),
            ("docker ", "list"),
        ]
        for kw, intent in _DOCKER_TERMS:
            if kw in text_lower:
                return DetectionResult(domain="docker", intent=intent, confidence=0.9)

        # Docker container-specific terms (with action context)
        _DOCKER_CONTAINER_ACTIONS = [
            ("uruchom kontener", "run"), ("run container", "run"), ("start container", "start"),
            ("uruchom container", "run"), ("run kontener", "run"), ("start kontener", "start"),
            ("zatrzymaj kontener", "stop"), ("stop container", "stop"),
            ("zatrzymaj container", "stop"), ("stop kontener", "stop"),
            ("uruchom zatrzymany kontener", "start"),
            ("usuń kontener", "remove"), ("remove container", "remove"), ("delete container", "remove"),
            ("usun kontener", "remove"), ("remove kontener", "remove"), ("delete kontener", "remove"),
            ("wykonaj komendę w kontenerze", "exec"), ("wykonaj polecenie w kontenerze", "exec"),
            ("exec in container", "exec"), ("wejdź do kontenera", "exec"), ("shell kontenera", "exec"),
            ("wejdź do container", "exec"), ("shell container", "exec"),
            ("pokaż logi kontenera", "logs"), ("container logs", "logs"),
            ("pokaż logi container", "logs"), ("logi kontenera", "logs"), ("container logs", "logs"),
            ("pobierz obraz", "pull"), ("pull image", "pull"), ("ściągnij obraz", "pull"),
            ("pobierz image", "pull"), ("sciagnij image", "pull"), ("pull obraz", "pull"),
            ("wypchnij obraz", "push"), ("wyślij obraz", "push"), ("push image", "push"),
            ("wypchnij image", "push"), ("push obraz", "push"),
            ("opublikuj obraz", "push"), ("wypchnij", "push"),
            ("zbuduj obraz", "build"), ("build image", "build"),
            ("zbuduj image", "build"), ("build obraz", "build"), ("stwórz obraz", "build"),
            ("list containers", "list"), ("pokaż kontenery", "list"),
            ("kontenery docker", "list"), ("docker containers", "list"),
            ("kontener", "list"), ("container", "list"),
        ]
        for kw, intent in _DOCKER_CONTAINER_ACTIONS:
            if kw in text_lower:
                return DetectionResult(domain="docker", intent=intent, confidence=0.88)

        # Kubernetes fast-path — explicit k8s terms (ordered: specific first)
        _K8S_TERMS = [
            ("kubectl ", "get"), ("kubernetes", "get"), ("k8s", "get"),
            ("opisz deployment", "describe"), ("opisz pod", "describe"),
            ("describe deployment", "describe"), ("describe pod", "describe"),
            ("skaluj deployment", "scale"), ("scale deployment", "scale"),
            ("stwórz serwis", "create_service"), ("create service", "create_service"),
            ("utwórz serwis", "create_service"),
            ("stwórz configmap", "create_configmap"), ("create configmap", "create_configmap"),
            ("utwórz configmap", "create_configmap"),
            ("stwórz secret", "create_secret"), ("create secret", "create_secret"),
            ("utwórz secret", "create_secret"),
            ("stwórz ingress", "create_ingress"), ("create ingress", "create_ingress"),
            ("utwórz ingress", "create_ingress"),
            ("stwórz deployment", "create"), ("create deployment", "create"),
            ("utwórz deployment", "create"), ("stwórz zasób", "create"),
            ("utwórz namespace", "create"), ("create namespace", "create"),
            ("pokaż logi poda", "logs"), ("pod logs", "logs"),
            ("pody w klastrze", "get"), ("pods in cluster", "get"),
            ("pokaż pody", "get"), ("show pods", "get"), ("get pods", "get"),
            (" pods", "get"), ("pod ", "get"), (" pod ", "get"),
            ("deployment", "get"), ("namespace", "get"),
            ("klaster", "get"), ("cluster", "get"),
            ("ingress", "get"), ("configmap", "get"), ("secret", "get"),
            ("service mesh", "get"), ("helm ", "get"),
        ]
        for kw, intent in _K8S_TERMS:
            if kw in text_lower:
                # For namespace detection, extract namespace value into entities
                if intent == "get" and "namespace" in text_lower:
                    import re as _re
                    ns_match = _re.search(r'namespace\s+(\S+)', text_lower)
                    entities = {"namespace": ns_match.group(1)} if ns_match else {}
                    return DetectionResult(domain="kubernetes", intent=intent, confidence=0.9, entities=entities)
                return DetectionResult(domain="kubernetes", intent=intent, confidence=0.9)

        # Shell fast-path — file/process/system terms (only when no docker/k8s context)
        _SHELL_TERMS = {
            "configuration files": "find", "config files": "find",
            "find files": "find", "find file": "find",
            "search files": "find", "search for files": "find",
            "pliki konfiguracyjne": "find",
            "znajdź pliki": "find", "znajdź plik": "find",
            "zawartość katalogu": "list", "zawartość folderu": "list",
            "directory contents": "list", "folder contents": "list",
            "list files": "list", "list directory": "list",
            "pokaż pliki": "list", "pokaz pliki": "list",
            "lista plików": "list", "lista plikow": "list",
            "show files": "list", "show file": "list",
            "uruchomione procesy": "list_processes", "running processes": "list_processes",
            "pokaż procesy": "list_processes", "show processes": "list_processes",
            "miejsce na dysku": "disk_usage", "disk space": "disk_usage",
            "disk usage": "disk_usage", "wolne miejsce": "disk_usage",
            "sprawdź dysk": "disk_usage",
            "grep ": "search", "szukaj w pliku": "search", "search in file": "search",
            "znajdź słowo": "search", "szukaj w logach": "search",
            "skopiuj plik": "copy", "copy file": "copy", "skopiuj ": "copy",
            "przenieś plik": "move", "move file": "move", "przenieś ": "move",
            "usuń plik": "delete", "delete file": "delete", "usuń stary": "delete",
            "usun plik": "delete", "skasuj plik": "delete", "skasuj": "delete",
            "zmień uprawnienia": "chmod", "uprawnienia pliku": "chmod",
            "change permissions": "chmod",
            "spakuj folder": "compress", "spakuj ": "compress",
            "compress folder": "compress", "skompresuj": "compress",
        }
        for kw, intent in _SHELL_TERMS.items():
            if kw in text_lower:
                entities = {}
                # Extract file patterns for find operations
                if intent == "find" and ("*" in text_lower or ".py" in text_lower or ".txt" in text_lower or ".json" in text_lower):
                    import re as _re
                    # Look for file patterns like *.py, *.txt, etc.
                    file_pattern_match = _re.search(r'(\*\\\?[a-zA-Z0-9]+|\*[a-zA-Z0-9]+)', text_lower)
                    if file_pattern_match:
                        entities["pattern"] = file_pattern_match.group(1)
                    elif ".py" in text_lower:
                        entities["pattern"] = "*.py"
                    elif ".txt" in text_lower:
                        entities["pattern"] = "*.txt"
                    elif ".json" in text_lower:
                        entities["pattern"] = "*.json"
                
                return DetectionResult(domain="shell", intent=intent, confidence=0.88, entities=entities)

        # SQL natural language fast-path (after docker/k8s/shell)
        # Ordered list — more specific first to avoid false matches
        _SQL_NL = [
            # DDL — table creation/deletion (highest priority)
            ("stwórz tabelę", "create_table"), ("utwórz tabelę", "create_table"),
            ("create table", "create_table"), ("nowa tabela", "create_table"),
            ("usuń tabelę", "drop_table"), ("skasuj tabelę", "drop_table"),
            ("drop table", "drop_table"), ("zniszcz tabelę", "drop_table"),
            # DML — insert/update/delete
            ("dodaj nowy rekord", "insert"), ("dodaj rekord", "insert"),
            ("add new record", "insert"), ("add record", "insert"),
            ("wstaw rekord", "insert"), ("insert record", "insert"),
            ("zaktualizuj status", "update"), ("zaktualizuj rekord", "update"),
            ("update record", "update"), ("zmień wartość", "update"),
            ("usuń rekord", "delete"), ("delete record", "delete"),
            ("skasuj rekord", "delete"),
            ("usuń stare dane", "delete"), ("usuń dane", "delete"),
            ("delete old data", "delete"), ("remove old data", "delete"),
            # Aggregates
            ("policz liczbę", "aggregate"), ("policz rekordy", "aggregate"),
            ("count(", "aggregate"), ("sum(", "aggregate"), ("avg(", "aggregate"),
            ("zsumuj", "aggregate"), ("count records", "aggregate"),
            # Joins
            ("inner join", "join"), ("left join", "join"), ("right join", "join"),
            ("join tables", "join"), ("połącz tabele", "join"), ("złącz tabele", "join"),
            # Select
            ("from the table", "select"), ("from table", "select"),
            ("z tabeli", "select"), ("wyświetl dane", "select"),
            ("pokaż rekordy", "select"), ("show records", "select"),
            ("all users", "select"), ("all records", "select"),
            ("wszystkich użytkowników", "select"), ("wszystkie rekordy", "select"),
            ("pokaż użytkowników", "select"), ("show users", "select"),
            ("lista użytkowników", "select"), ("list users", "select"),
            ("pokaż dane", "select"), ("show data", "select"),
            ("wyświetl dane", "select"), ("display data", "select"),
            (" tabeli ", "select"), (" table ", "select"),
        ]
        for kw, intent in _SQL_NL:
            if kw in text_lower:
                entities = {}
                # Extract table name for common patterns
                if kw in ["z tabeli", "from table", "from the table"]:
                    import re as _re
                    # Look for table name after the pattern
                    table_match = _re.search(rf'{re.escape(kw)}\s+(\w+)', text_lower)
                    if table_match:
                        entities["table"] = table_match.group(1)
                elif " tabeli " in text_lower or " table " in text_lower:
                    import re as _re
                    # Look for table name around "tabeli" or "table"
                    table_match = _re.search(r'(\w+)\s+tabeli|tabeli\s+(\w+)|(\w+)\s+table|table\s+(\w+)', text_lower)
                    if table_match:
                        # Find the non-None group
                        table_name = next((group for group in table_match.groups() if group), None)
                        if table_name:
                            entities["table"] = table_name
                elif kw in ["pokaż użytkowników", "show users", "lista użytkowników", "list users"]:
                    import re as _re
                    # Extract table name from user-related patterns
                    entities["table"] = "users"
                
                # Extract WHERE conditions for patterns containing "gdzie", "where"
                if "gdzie" in text_lower or "where" in text_lower:
                    import re as _re
                    # Look for WHERE condition
                    where_match = _re.search(r'(?:gdzie|where)\s+([^,.!?]+)', text_lower)
                    if where_match:
                        entities["where"] = where_match.group(1).strip()
                
                return DetectionResult(domain="sql", intent=intent, confidence=0.85, entities=entities)

        # URL detection
        # IMPORTANT:
        # - Prefer explicit URLs (https?://...) over bare domain matches.
        # - Preserve the full path/query when present.
        # - If the user provides a bare domain (e.g. prototypowanie.pl),
        #   default to https:// so xdg-open doesn't treat it like a local file.

        def _normalize_url(raw: str) -> str:
            u = (raw or "").strip().strip("'\"")
            if not u:
                return u
            if u.startswith("http://") or u.startswith("https://") or u.startswith("file://"):
                return u
            if u.startswith("www."):
                return f"https://{u}"
            # If it looks like a domain[/path], default to https
            if re.match(r"^[a-zA-Z0-9][\w\-]*\.[a-zA-Z]{2,}(?:/[^\s'\"]*)?$", u):
                return f"https://{u}"
            return u

        # 1) Full explicit URLs
        url_match = re.search(r"\b(https?://[^\s'\"]+)", text_lower)
        if url_match:
            return DetectionResult(
                domain="browser",
                intent="navigate",
                confidence=0.95,
                entities={"url": _normalize_url(url_match.group(1))},
            )

        # 2) www.* URLs
        www_match = re.search(r"\b(www\.[^\s'\"]+)", text_lower)
        if www_match:
            return DetectionResult(
                domain="browser",
                intent="navigate",
                confidence=0.92,
                entities={"url": _normalize_url(www_match.group(1))},
            )

        # 3) Bare domains (optionally with a path)
        domain_match = re.search(
            r"\b([a-zA-Z0-9][\w\-]*\.(?:com|org|net|io|dev|pl|de|uk|eu|gov|edu|tv|co)(?:/[^\s'\"]*)?)\b",
            text_lower,
        )
        if domain_match:
            return DetectionResult(
                domain="browser",
                intent="navigate",
                confidence=0.9,
                entities={"url": _normalize_url(domain_match.group(1))},
            )
        
        # Browser keywords
        browser_keywords = self.patterns.fast_path_browser_keywords
        if any(kw in text_lower for kw in browser_keywords):
            return DetectionResult(
                domain="browser",
                intent="web_action",
                confidence=0.8,
            )
        
        # Search keywords
        search_keywords = self.patterns.fast_path_search_keywords
        if any(kw in text_lower for kw in search_keywords):
            return DetectionResult(
                domain="shell",
                intent="search_web",
                confidence=0.8,
            )
        
        return None
    
    def _fuzzy_detection(self, text: str) -> Optional[DetectionResult]:
        """Detection using fuzzy schema matching."""
        matcher = _get_fuzzy_schema_matcher()
        if not matcher:
            return None
        
        try:
            result = matcher.match(text)
            if result and result.confidence >= self.confidence_threshold:
                return DetectionResult(
                    domain=result.domain,
                    intent=result.intent,
                    confidence=result.confidence,
                    entities=result.entities or {},
                )
        except Exception as e:
            logger.debug(f"Fuzzy matching failed: {e}")
        
        return None
    
    def _ml_detection(self, text: str) -> Optional[DetectionResult]:
        """ML-based detection using trained classifier."""
        classifier = _get_ml_classifier()
        if not classifier:
            return None
        
        try:
            result = classifier.predict(text)
            if result and result.confidence >= self.confidence_threshold:
                return DetectionResult(
                    domain=result.domain,
                    intent=result.intent,
                    confidence=result.confidence,
                    entities=result.entities or {},
                )
        except Exception as e:
            logger.debug(f"ML detection failed: {e}")
        
        return None
    
    def _semantic_detection(self, text: str) -> Optional[DetectionResult]:
        """Semantic detection using sentence embeddings."""
        matcher = _get_semantic_matcher()
        if not matcher:
            return None
        
        try:
            result = matcher.match(text)
            if result and result.confidence >= self.confidence_threshold:
                return DetectionResult(
                    domain=result.domain,
                    intent=result.intent,
                    confidence=result.confidence,
                    entities=result.entities or {},
                )
        except Exception as e:
            logger.debug(f"Semantic matching failed: {e}")
        
        return None
    
    def _keyword_detection(self, text: str, text_lower: str) -> DetectionResult:
        """Traditional keyword-based detection."""
        best_match = DetectionResult(domain="unknown", intent="", confidence=0.0, matched=False)
        
        # Check priority intents first
        for domain in self.patterns.list_domains():
            priority_intents = self.patterns.get_priority_intents(domain)
            for intent in priority_intents:
                patterns = self.patterns.get_intent_patterns(domain, intent)
                confidence = self._calculate_keyword_confidence(text_lower, patterns)
                
                if confidence > best_match.confidence:
                    best_match = DetectionResult(
                        domain=domain,
                        intent=intent,
                        confidence=confidence,
                    )
        
        # Check all intents if no priority match found
        if best_match.confidence < self.confidence_threshold:
            for domain in self.patterns.list_domains():
                for intent in self.patterns.list_intents(domain):
                    # Skip if already checked as priority
                    if intent in self.patterns.get_priority_intents(domain):
                        continue
                    
                    patterns = self.patterns.get_intent_patterns(domain, intent)
                    confidence = self._calculate_keyword_confidence(text_lower, patterns)
                    
                    if confidence > best_match.confidence:
                        best_match = DetectionResult(
                            domain=domain,
                            intent=intent,
                            confidence=confidence,
                        )
        
        # Apply domain boosters
        if best_match.domain:
            boosters = self.patterns.get_domain_boosters(best_match.domain)
            booster_confidence = self._calculate_keyword_confidence(text_lower, boosters)
            if booster_confidence > 0:
                best_match.confidence = min(1.0, best_match.confidence + 0.1)
        
        return best_match
    
    def _calculate_keyword_confidence(self, text: str, keywords: list[str]) -> float:
        """Calculate confidence based on keyword matches."""
        if not keywords:
            return 0.0
        
        matches = 0
        total_keywords = len(keywords)
        
        # Use enhanced tokenization if available
        tokens = self._tokenize_text(text)
        token_set = set(tokens)
        
        for keyword in keywords:
            if self._keyword_matches(keyword, text, token_set):
                matches += 1
        
        if matches == 0:
            return 0.0
        
        # Base confidence from keyword matches
        base_confidence = matches / total_keywords
        
        # Boost for multiple matches
        if matches >= 2:
            base_confidence = min(1.0, base_confidence + 0.2)
        
        return base_confidence
    
    def _tokenize_text(self, text: str) -> list[str]:
        """Tokenize text using available tools."""
        # Try spaCy first
        nlp = _get_spacy_model()
        if nlp:
            try:
                doc = nlp(text)
                tokens = []
                polish_support = _get_polish_support()
                
                for token in doc:
                    if polish_support and hasattr(polish_support, '_is_important_token'):
                        if polish_support._is_important_token(token):
                            original_text = token.text.lower()
                            lemma = (token.lemma_ or "").lower()
                            important_keywords = {
                                'restartuj', 'uruchom', 'zrestartuj', 'startuj', 'wystartuj',
                                'zatrzymaj', 'stopuj', 'usuń', 'skopiuj', 'przenieś', 'znajdź',
                                'pokaż', 'sprawdź', 'utwórz', 'zmień', 'restart', 'docker', 'ps',
                                'kill', 'run', 'stop', 'start', 'create', 'delete', 'remove',
                                'katalog', 'katalogi', 'usługa', 'usługi', 'usługę', 'serwis',
                                'komputer', 'system', 'proces', 'procesy'
                            }
                            if original_text in important_keywords or not lemma or len(lemma) <= 1:
                                tokens.append(original_text)
                            else:
                                tokens.append(lemma)
                    else:
                        tokens.append(token.text.lower())
                return tokens
            except Exception as e:
                logger.debug(f"spaCy tokenization failed: {e}")
        
        # Fallback to basic tokenization
        return re.findall(r'\b\w+\b', text.lower())
    
    def _keyword_matches(self, keyword: str, text: str, tokens: set[str]) -> bool:
        """Check if a keyword matches the text."""
        # Direct token match
        if keyword in tokens:
            return True
        
        # Multi-word keyword matching
        if ' ' in keyword:
            pattern = r'\s+'.join(map(re.escape, keyword.split()))
            return re.search(pattern, text) is not None
        
        # Special patterns for single keywords
        if len(keyword) <= 3 and re.fullmatch(r"[a-z0-9]+", keyword):
            return re.search(rf"(?<![a-z0-9_]){re.escape(keyword)}(?![a-z0-9_])", text) is not None
        
        # General substring search
        return keyword in text
