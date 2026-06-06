
"""
Polish Language Support Module for NLP2CMD
Provides Polish language patterns and mappings
"""

import json
import re
from pathlib import Path
from difflib import SequenceMatcher

# Common STT word boundary errors: incorrect -> correct
STT_CORRECTIONS = {
    # "list aplików" -> "lista plików" (boundary shift)
    "list aplik": "lista plik",
    "list a plik": "lista plik",
    "lista plik": "lista plik",  # already correct
    "listy plik": "lista plik",
    "listę plik": "lista plik",
    # "pokaż procesy" variations
    "pokaz procesy": "pokaż procesy",
    "pokaż a procesy": "pokaż procesy",
    "pokaza procesy": "pokaż procesy",
    # "znajdź plik" variations  
    "znajdz plik": "znajdź plik",
    "z najdź plik": "znajdź plik",
    "znaj dplik": "znajdź plik",
    # "usuń plik" variations
    "usun plik": "usuń plik",
    "u suń plik": "usuń plik",
    # "utwórz katalog" variations
    "utworz katalog": "utwórz katalog",
    "u twórz katalog": "utwórz katalog",
    # "kopiuj plik" variations
    "kopi uj plik": "kopiuj plik",
    "kopiu jplik": "kopiuj plik",
}

# Known Polish command phrases for fuzzy matching
KNOWN_PHRASES = [
    "lista plików",
    "lista plikow",
    "pokaż pliki",
    "pokaz pliki",
    "znajdź plik",
    "znajdz plik",
    "usuń plik",
    "usun plik",
    "utwórz katalog",
    "utworz katalog",
    "kopiuj plik",
    "skopiuj plik",
    "przenieś plik",
    "przenies plik",
    "pokaż procesy",
    "pokaz procesy",
    "lista procesów",
    "lista procesow",
    "zabij proces",
    "zatrzymaj proces",
    "sprawdź pamięć",
    "sprawdz pamiec",
    "miejsce dysku",
    "lista kontenerów",
    "lista kontenerow",
    "lista kontener",
    "lista container",
    "pokaż kontenery",
    "pokaz kontenery",
    "pokaż kontener",
    "pokaz kontener",
    "pokaż container",
    "pokaz container",
]


class PolishLanguageSupport:
    """Polish language support for NLP2CMD"""
    
    def __init__(self):
        self.patterns = {}
        self.intent_mappings = {}
        self.table_mappings = {}
        self.domain_weights = {}
        self._load_patterns()
    
    def _load_patterns(self):
        """Load Polish language patterns"""
        try:
            from nlp2cmd.utils.data_files import find_data_file

            # Load Polish shell patterns
            patterns_file = find_data_file(explicit_path=None, default_filename="polish_shell_patterns.json")
            if patterns_file:
                with open(patterns_file, 'r', encoding='utf-8') as f:
                    self.patterns = json.load(f)
            
            # Load Polish intent mappings
            intent_file = find_data_file(explicit_path=None, default_filename="polish_intent_mappings.json")
            if intent_file:
                with open(intent_file, 'r', encoding='utf-8') as f:
                    self.intent_mappings = json.load(f)
            
            # Load Polish table mappings
            table_file = find_data_file(explicit_path=None, default_filename="polish_table_mappings.json")
            if table_file:
                with open(table_file, 'r', encoding='utf-8') as f:
                    self.table_mappings = json.load(f)
            
            # Load domain weights
            weights_file = find_data_file(explicit_path=None, default_filename="domain_weights.json")
            if weights_file:
                with open(weights_file, 'r', encoding='utf-8') as f:
                    self.domain_weights = json.load(f)
                    
        except Exception as e:
            print(f"Error loading Polish patterns: {e}")
    
    def normalize_polish_text(self, text):
        """Normalize Polish text for better matching"""
        # Convert to lowercase
        text = text.lower()
        
        # Handle common Polish diacritics variations
        diacritic_map = {
            'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n',
            'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z',
            'Ą': 'a', 'Ć': 'c', 'Ę': 'e', 'Ł': 'l', 'Ń': 'n',
            'Ó': 'o', 'Ś': 's', 'Ź': 'z', 'Ż': 'z'
        }
        
        for polish, latin in diacritic_map.items():
            text = text.replace(polish, latin)
        
        return text
    
    _ENGLISH_COMMAND_WORDS = {
        'stop', 'start', 'run', 'list', 'show', 'get', 'set', 'delete', 'remove',
        'create', 'update', 'find', 'search', 'copy', 'move', 'kill', 'restart',
        'build', 'push', 'pull', 'exec', 'logs', 'stats', 'inspect', 'container',
        'image', 'volume', 'network', 'service', 'deploy', 'install', 'config'
    }

    _PREPOSITIONS = {
        "na", "w", "we", "do", "z", "ze", "od", "po", "pod", "nad",
        "przed", "za", "o", "u",
    }

    def _apply_direct_corrections(self, text_lower: str) -> str:
        """Apply direct STT corrections from the corrections dictionary."""
        for incorrect, correct in STT_CORRECTIONS.items():
            if incorrect in text_lower:
                return text_lower.replace(incorrect, correct)
        return text_lower

    def _has_english_command_words(self, words: list[str]) -> bool:
        """Check if text contains common English command words."""
        return any(word in self._ENGLISH_COMMAND_WORDS for word in words)

    def _try_adjacent_word_joining(self, words: list[str]) -> str | None:
        """Try joining adjacent words to match known patterns."""
        if len(words) < 2:
            return None

        for i in range(len(words) - 1):
            if words[i] in self._PREPOSITIONS or words[i + 1] in self._PREPOSITIONS:
                continue
            joined = words[i] + words[i + 1]
            for phrase in KNOWN_PHRASES:
                phrase_words = phrase.split()
                for pw in phrase_words:
                    pw_normalized = self.normalize_polish_text(pw)
                    joined_normalized = self.normalize_polish_text(joined)
                    if self._similar(joined_normalized, pw_normalized, threshold=0.8):
                        return ' '.join(words[:i] + [pw] + words[i+2:])
        return None

    def _try_fuzzy_phrase_match(self, text_lower: str) -> str | None:
        """Try fuzzy matching against known phrases."""
        best_match = self._find_best_phrase_match(text_lower)
        if not best_match:
            return None

        input_words = text_lower.split()
        match_words = best_match.split()
        dropped = [w for w in input_words if w in self._PREPOSITIONS and w not in match_words]
        if not dropped:
            return best_match
        return None

    def normalize_stt_errors(self, text):
        """Fix common STT word boundary errors.
        
        STT often shifts word boundaries, e.g.:
        - 'lista plików' -> 'list aplików' (shifted 'a')
        - 'znajdź plik' -> 'z najdź plik' (split first letter)
        """
        text_lower = text.lower()
        words = text_lower.split()

        # Conservative mode for English command words
        if self._has_english_command_words(words):
            return self._apply_direct_corrections(text_lower)

        # Try direct corrections
        corrected = self._apply_direct_corrections(text_lower)
        if corrected != text_lower:
            return corrected

        if len(words) < 3:
            return text_lower

        # Try fuzzy phrase matching
        fuzzy_match = self._try_fuzzy_phrase_match(text_lower)
        if fuzzy_match:
            return fuzzy_match

        # Try adjacent word joining
        joined_match = self._try_adjacent_word_joining(words)
        if joined_match:
            return joined_match

        return text_lower
    
    def _find_best_phrase_match(self, text, threshold=0.85):
        """Find best matching known phrase using fuzzy matching."""
        text_normalized = self.normalize_polish_text(text)
        best_score = 0
        best_phrase = None
        
        for phrase in KNOWN_PHRASES:
            phrase_normalized = self.normalize_polish_text(phrase)
            score = self._similar(text_normalized, phrase_normalized)
            if score > best_score and score >= threshold:
                best_score = score
                best_phrase = phrase
        
        return best_phrase
    
    def _similar(self, a, b, threshold=None):
        """Calculate similarity ratio between two strings."""
        ratio = SequenceMatcher(None, a, b).ratio()
        if threshold is not None:
            return ratio >= threshold
        return ratio
    
    def match_polish_patterns(self, text, domain):
        """Match Polish patterns for given domain"""
        if domain not in self.patterns:
            return []
        
        matches = []
        normalized_text = self.normalize_polish_text(text)
        
        for category, patterns in self.patterns.items():
            for pattern in patterns:
                try:
                    if re.search(pattern, normalized_text, re.IGNORECASE):
                        matches.append({
                            'category': category,
                            'pattern': pattern,
                            'match': True
                        })
                except re.error:
                    continue
        
        return matches
    
    def translate_polish_intent(self, text):
        """Translate Polish intent to English"""
        normalized_text = self.normalize_polish_text(text)
        
        for polish, english in self.intent_mappings.items():
            if polish in normalized_text:
                return english
        
        return None
    
    def translate_polish_table(self, text):
        """Translate Polish table name to English"""
        normalized_text = self.normalize_polish_text(text)
        
        for polish_pattern, english_table in self.table_mappings.items():
            try:
                if re.search(polish_pattern, normalized_text, re.IGNORECASE):
                    return english_table
            except re.error:
                continue
        
        return None
    
    def get_domain_weight(self, domain):
        """Get domain weight for Polish text"""
        return self.domain_weights.get(domain, {}).get("base_weight", 1.0)
    
    def enhance_domain_detection(self, text, base_domain):
        """Enhance domain detection with Polish patterns"""
        # Check if Polish patterns suggest a different domain
        polish_matches = self.match_polish_patterns(text, "shell")
        
        if polish_matches and base_domain == "sql":
            # Polish file operations detected, prefer shell
            return "shell"
        
        return base_domain
    
    def enhance_intent_detection(self, text, base_intent):
        """Enhance intent detection with Polish mappings"""
        # Try to translate Polish intent
        translated_intent = self.translate_polish_intent(text)
        
        if translated_intent:
            return translated_intent
        
        return base_intent

# Global instance
polish_support = PolishLanguageSupport()

def get_polish_support():
    """Get Polish language support instance"""
    return polish_support
