from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Optional

from nlp2cmd.core.core_backends import NLPBackend
from nlp2cmd.core.core_models import ExecutionPlan


@dataclass
class _ParsedSize:
    value: float
    unit: str


class SemanticShellBackend(NLPBackend):
    def __init__(self, config: Optional[dict[str, Any]] = None):
        super().__init__(config)
        self.model = os.environ.get("NLP2CMD_SPACY_MODEL") or "blank:pl"
        self._nlp = None

    def _maybe_warm_spacy(self) -> None:
        if self._nlp is not None:
            return

        try:
            import spacy

            if self.model.startswith("blank:"):
                lang = self.model.split(":", 1)[1] or "pl"
                nlp = spacy.blank(lang)
            else:
                nlp = spacy.load(self.model)

            if "sentencizer" not in nlp.pipe_names:
                nlp.add_pipe("sentencizer")

            self._nlp = nlp
        except Exception:
            self._nlp = None

    def extract_intent(self, text: str) -> tuple[str, float]:
        text_lower = (text or "").lower()
        
        # Direct command detection (highest priority)
        if text_lower.startswith("cat ") or "cat " in text_lower:
            return "cat", 0.95
        if text_lower.startswith("head ") or "head " in text_lower:
            return "head", 0.95
        if text_lower.startswith("tail ") or "tail " in text_lower:
            return "tail", 0.95
        if text_lower.startswith("wc ") or "wc " in text_lower:
            return "wc", 0.95
        if text_lower.startswith("grep ") or "grep " in text_lower:
            return "search", 0.95
        if text_lower.startswith("ls ") or text_lower == "ls":
            return "list", 0.95
        if text_lower.startswith("ps ") or text_lower == "ps":
            return "process_management", 0.95
        if text_lower.startswith("df ") or text_lower == "df":
            return "disk", 0.95
        
        # Polish/English keyword detection
        if any(x in text_lower for x in ("znajd", "find", "szuk")):
            return "file_search", 0.75
        if any(x in text_lower for x in ("policz lini", "count line", "wc")):
            return "wc", 0.80
        if any(x in text_lower for x in ("pierwsz", "head", "począt")):
            return "head", 0.75
        if any(x in text_lower for x in ("ostatni", "tail", "końc")):
            return "tail", 0.75
        if any(x in text_lower for x in ("grep", "szukaj tekst", "wyszuk")):
            return "search", 0.75
        # Cat detection - "wyświetl zawartość" should be cat, not list
        if any(x in text_lower for x in ("zawartość", "zawartosc", "content")):
            return "cat", 0.80
        if any(x in text_lower for x in ("pokaż", "pokaz", "list", "wyświetl", "wyswietl")):
            return "list", 0.55
        
        return "unknown", 0.0

    def extract_entities(self, text: str) -> list[Any]:
        raise NotImplementedError

    def generate_plan(self, text: str, context: Optional[dict] = None) -> ExecutionPlan:
        # Optional warmup: does not affect logic if spaCy isn't installed.
        self._maybe_warm_spacy()
        text_lower = (text or "").lower()

        # First determine intent
        intent, intent_confidence = self.extract_intent(text)
        
        entities: dict[str, Any] = {}
        entities["_full_text"] = text  # Pass full text for parameter extraction
        entities["scope"] = self._extract_scope(text)
        entities["target"] = self._infer_target(text_lower)
        
        # Extract file path from text
        file_match = re.search(r'([/\w.-]+\.\w+)', text)
        if file_match:
            entities["file"] = file_match.group(1)
            entities["path"] = file_match.group(1)
        
        # Extract pattern for grep
        if intent == "search":
            # Try to extract pattern (word after grep or before "w pliku")
            pattern_match = re.search(r'grep\s+(\S+)', text_lower)
            if pattern_match:
                entities["pattern"] = pattern_match.group(1)
            entities["action"] = "grep"
        
        # Extract username using NLP
        username = self._extract_username_with_nlp(text)
        if username:
            entities["username"] = username
            # Adjust scope for user directories
            if username.lower() == "root":
                entities["scope"] = "/root"
            else:
                entities["scope"] = f"~{username}"

        filters: list[dict[str, Any]] = []

        ext = self._extract_extension(text)
        if ext:
            filters.append({"attribute": "extension", "operator": "=", "value": ext})

        size_filter = self._extract_size_filter(text_lower)
        if size_filter is not None:
            filters.append(size_filter)

        age_filter = self._extract_age_filter(text_lower)
        if age_filter is not None:
            filters.append(age_filter)

        entities["filters"] = filters

        semantic_meta: dict[str, Any] = {}
        try:
            from nlp2cmd.generation.semantic_entities import SemanticEntityExtractor

            semantic_extractor = SemanticEntityExtractor()
            semantic_result = semantic_extractor.extract(text, "shell")
            semantic_mode = semantic_extractor.last_mode
            if semantic_mode == "shadow":
                semantic_meta["shadow_entities"] = semantic_extractor.last_semantic_entities
            elif semantic_mode == "semantic":
                entities.update(semantic_result.entities)
            semantic_meta["entity_extractor_mode"] = semantic_mode
        except Exception:
            semantic_meta = {}

        confidence = intent_confidence
        if size_filter is not None or age_filter is not None:
            confidence = max(confidence, 0.8)
        if ext:
            confidence = max(confidence, 0.7)

        return ExecutionPlan(
            intent=intent if intent != "unknown" else "file_search",
            entities=entities,
            confidence=confidence,
            text=text or "",
            metadata={
                "backend": "semantic_shell_light",
                "spacy_model": self.model,
                **semantic_meta,
            },
        )

    @staticmethod
    def _infer_target(text_lower: str) -> str:
        if any(x in text_lower for x in ("katalog", "folder", "directory", "directories")):
            return "directories"
        return "files"

    @staticmethod
    def _extract_scope(text: str) -> str:
        if not text:
            return "."

        m = re.search(r"\b(?:w|in|from)\s+([/~][\w\./\-]+|\./[\w\./\-]*|\.\./[\w\./\-]*|\.{1,2})\b", text)
        if m:
            return m.group(1)

        return "."

    @staticmethod
    def _extract_extension(text: str) -> Optional[str]:
        if not text:
            return None

        m = re.search(r"\*\.(\w{1,16})\b", text)
        if m:
            return m.group(1).lower()

        m = re.search(r"\.(\w{1,16})\b", text)
        if m:
            return m.group(1).lower()

        text_lower = text.lower()
        if "logi" in text_lower or "logs" in text_lower:
            return "log"

        return None

    @classmethod
    def _extract_size_filter(cls, text_lower: str) -> Optional[dict[str, Any]]:
        parsed = cls._extract_first_size(text_lower)
        if parsed is None:
            return None

        op = cls._infer_size_operator(text_lower)
        value = cls._format_size_for_find(parsed)

        return {"attribute": "size", "operator": op, "value": value}

    @staticmethod
    def _infer_size_operator(text_lower: str) -> str:
        if re.search(r"\bnie\s+mniejsz\w*\b", text_lower):
            return ">="
        if re.search(r"\bnie\s+większ\w*\b", text_lower) or re.search(r"\bnie\s+duż\w*\b", text_lower):
            return "<="
        if any(x in text_lower for x in ("mniejsz", "poniżej", "ponizej")):
            return "<"
        if re.search(r"\bdo\b", text_lower) and re.search(r"\d", text_lower):
            return "<="
        if any(x in text_lower for x in ("większ", "wieksz", "powyżej", "powyzej", "ponad", "duż", "duz")):
            return ">"
        return ">"

    @classmethod
    def _extract_age_filter(cls, text_lower: str) -> Optional[dict[str, Any]]:
        m = re.search(
            r"\b(starsz\w*|nowsz\w*|ostatnio\s+zmienion\w*)\b.*?(\d+)\s*(dni|dnia|dzie[nń]|days?)\b",
            text_lower,
        )
        if not m:
            return None

        kind = m.group(1)
        days = int(m.group(2))

        if kind.startswith("nowsz"):
            op = "<="
        elif kind.startswith("ostatnio"):
            op = "<="
        else:
            op = ">="

        return {"attribute": "mtime", "operator": op, "value": f"{days}_days"}

    @staticmethod
    def _extract_first_size(text_lower: str) -> Optional[_ParsedSize]:
        m = re.search(r"(\d+(?:[\.,]\d+)?)\s*([kmgt]?b)\b", text_lower)
        if not m:
            return None

        val_raw = m.group(1).replace(",", ".")
        try:
            value = float(val_raw)
        except ValueError:
            return None

        unit = m.group(2).upper()
        return _ParsedSize(value=value, unit=unit)

    @staticmethod
    def _format_size_for_find(size: _ParsedSize) -> str:
        # GNU find expects: c (bytes), k (KiB), M/G/T (MiB/GiB/TiB)
        unit_upper = (size.unit or "").upper()
        if unit_upper in {"KB", "K"}:
            unit_letter = "k"
        elif unit_upper in {"MB", "M"}:
            unit_letter = "M"
        elif unit_upper in {"GB", "G"}:
            unit_letter = "G"
        elif unit_upper in {"TB", "T"}:
            unit_letter = "T"
        elif unit_upper in {"B", "BYTE", "BYTES"}:
            unit_letter = "c"
        else:
            unit_letter = "M"

        value_int = int(size.value) if float(size.value).is_integer() else int(round(size.value))
        return f"{value_int}{unit_letter}"

    def _extract_username_with_nlp(self, text: str) -> Optional[str]:
        """Extract username using intelligent patterns (fallback when spaCy not available)."""
        if not text:
            return None
        
        # Try spaCy first if available
        if self._nlp:
            try:
                doc = self._nlp(text)
                
                # Look for patterns like "foldery usera", "pliki usera", "katalogi usera"
                for token in doc:
                    token_lower = token.text.lower()
                    
                    # Check if this token indicates user context
                    if token_lower in ["usera", "użytkownika", "user", "użytkownik"]:
                        # Look for the next token or related tokens
                        for i, other_token in enumerate(doc):
                            if other_token == token:
                                # Check next token
                                if i + 1 < len(doc):
                                    next_token = doc[i + 1]
                                    # If next token is a potential username
                                    if (next_token.is_alpha or next_token.is_digit or 
                                        "_" in next_token.text or "-" in next_token.text):
                                        return next_token.text
                                # Check previous token
                                if i > 0:
                                    prev_token = doc[i - 1]
                                    # If previous token is a potential username
                                    if (prev_token.is_alpha or prev_token.is_digit or 
                                        "_" in prev_token.text or "-" in prev_token.text):
                                        return prev_token.text
                                
                                # If no specific username found, return generic "usera"
                                return "usera"
                
                # Check for user-related patterns in dependencies
                for token in doc:
                    if token.text.lower() in ["foldery", "pliki", "katalogi", "files", "directories"]:
                        # Check if there's a user-related token nearby
                        for child in token.children:
                            if child.text.lower() in ["usera", "użytkownika", "user", "użytkownik"]:
                                return "usera"
                        # Check head dependencies
                        for child in token.head.children:
                            if child.text.lower() in ["usera", "użytkownika", "user", "użytkownik"]:
                                return "usera"
            except Exception:
                pass  # Fallback to regex patterns
        
        # Fallback: Use intelligent regex patterns for username extraction
        patterns = [
            # Pattern: "foldery usera" -> no specific username
            r'(foldery|pliki|katalogi|files?)\s+(użytkownika|usera|user|użytkownik)(?:\s|$)',
            # Pattern: "użytkownika tom" -> specific username
            r'(użytkownika|usera|user|użytkownik)\s+([a-zA-Z0-9_-]+)(?:\s+(foldery|pliki|katalogi|files?)|$)',
            # Pattern: "tom foldery" -> username first
            r'([a-zA-Z0-9_-]+)\s+(?:foldery|pliki|katalogi|files?)\s+(użytkownika|usera|user|użytkownik)',
            # Pattern: "user tom" -> simple user command
            r'(?:użytkownika|usera|user|użytkownik)\s+([a-zA-Z0-9_-]+)',
            # Pattern: "pliki użytkownika" -> generic user context
            r'(?:foldery|pliki|katalogi|files?)\s+(?:użytkownika|usera|user|użytkownik)(?:\s|$)',
            # Pattern: standalone username with context
            r'([a-zA-Z0-9_-]+)\s+(?:foldery|pliki|katalogi|files?)',
        ]
        
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                groups = m.groups()
                if len(groups) >= 2 and groups[1]:  # Specific username found
                    username = groups[1]
                    # Validate username (no spaces, reasonable characters)
                    if re.match(r'^[a-zA-Z0-9_-]+$', username):
                        return username
                else:  # Generic "usera" pattern
                    return "usera"
        
        return None
