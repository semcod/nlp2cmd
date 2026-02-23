
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
    
    def normalize_stt_errors(self, text):
        """Fix common STT word boundary errors.
        
        STT often shifts word boundaries, e.g.:
        - 'lista plików' -> 'list aplików' (shifted 'a')
        - 'znajdź plik' -> 'z najdź plik' (split first letter)
        """
        text_lower = text.lower()
        
        # Skip correction for common English command words to avoid false positives
        english_command_words = {
            'stop', 'start', 'run', 'list', 'show', 'get', 'set', 'delete', 'remove',
            'create', 'update', 'find', 'search', 'copy', 'move', 'kill', 'restart',
            'build', 'push', 'pull', 'exec', 'logs', 'stats', 'inspect', 'container',
            'image', 'volume', 'network', 'service', 'deploy', 'install', 'config'
        }
        
        words = text_lower.split()
        if any(word in english_command_words for word in words):
            # If we have common English command words, be more conservative
            # Only apply direct corrections, not fuzzy matching
            for incorrect, correct in STT_CORRECTIONS.items():
                if incorrect in text_lower:
                    text_lower = text_lower.replace(incorrect, correct)
                    return text_lower
            return text_lower
        
        # Try direct corrections first
        for incorrect, correct in STT_CORRECTIONS.items():
            if incorrect in text_lower:
                text_lower = text_lower.replace(incorrect, correct)
                return text_lower

        words = text_lower.split()
        if len(words) < 3:
            return text_lower

        prepositions = {
            "na",
            "w",
            "we",
            "do",
            "z",
            "ze",
            "od",
            "po",
            "pod",
            "nad",
            "przed",
            "za",
            "o",
            "u",
        }
        
        # Try fuzzy matching against known phrases
        best_match = self._find_best_phrase_match(text_lower)
        if best_match:
            input_words = text_lower.split()
            match_words = best_match.split()
            dropped = [w for w in input_words if w in prepositions and w not in match_words]
            if not dropped:
                return best_match
        
        # Try joining adjacent words and matching
        if len(words) >= 2:
            # Try joining pairs of words
            for i in range(len(words) - 1):
                if words[i] in prepositions or words[i + 1] in prepositions:
                    continue
                joined = words[i] + words[i + 1]
                # Check if joined word matches any known pattern
                for phrase in KNOWN_PHRASES:
                    phrase_words = phrase.split()
                    for pw in phrase_words:
                        # Remove diacritics for comparison
                        pw_normalized = self.normalize_polish_text(pw)
                        joined_normalized = self.normalize_polish_text(joined)
                        if self._similar(joined_normalized, pw_normalized, threshold=0.8):
                            # Reconstruct with corrected word
                            new_words = words[:i] + [pw] + words[i+2:]
                            return ' '.join(new_words)
        
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
