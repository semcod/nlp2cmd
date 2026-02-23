"""
Multi-command detection module for NLP2CMD.

Supports detection of multiple commands in one input including:
- Multiple sentences (separated by periods)
- Commands joined with Polish/English connectors (i, oraz, then, and)
- Semicolon-separated commands
"""

import re
from typing import List, Tuple, Optional
from dataclasses import dataclass

from nlp2cmd.generation.keywords.keyword_detector import KeywordIntentDetector, DetectionResult


@dataclass
class MultiCommandResult:
    """Result of multi-command detection."""
    original_text: str
    commands: List[Tuple[str, DetectionResult]]
    is_multi_command: bool
    
    @property
    def count(self) -> int:
        return len(self.commands)
    
    def get_domains(self) -> List[str]:
        """Get list of detected domains."""
        return [r[1].domain for r in self.commands]
    
    def get_intents(self) -> List[str]:
        """Get list of detected intents."""
        return [r[1].intent for r in self.commands]


class MultiCommandDetector:
    """
    Utility class to detect multiple commands in one input.
    
    Supports various separators:
    - Period followed by space
    - Semicolon
    - Polish connectors: "i", "oraz", "a potem", "potem", "następnie"
    - English connectors: "then", "and then", "after that", "and"
    
    Example usage:
        detector = MultiCommandDetector()
        result = detector.detect("pokaż kontenery i pokaż logi")
        print(f"Found {result.count} commands")
        for cmd, detection in result.commands:
            print(f"  {cmd}: {detection.domain}/{detection.intent}")
    """
    
    # Sentence/command separators (order matters - more specific first)
    SEPARATORS = [
        r'\.\s+',                # Period followed by space
        r';\s*',                 # Semicolon
        r'\s+a\s+potem\s+',      # Polish "a potem" (and then)
        r'\s+potem\s+',          # Polish "potem" (then)
        r'\s+nast[eę]pnie\s+',   # Polish "następnie" (next)
        r'\s+oraz\s+',           # Polish "oraz" (and also)
        r'\s+and\s+then\s+',     # English "and then"
        r'\s+then\s+',           # English "then"
        r'\s+after\s+that\s+',   # English "after that"
        r'\s+i\s+',              # Polish "i" (and) - last because it's short
        r'\s+and\s+',            # English "and" - last because it's short
    ]
    
    def __init__(self, detector: Optional[KeywordIntentDetector] = None):
        """
        Initialize multi-command detector.
        
        Args:
            detector: Optional KeywordIntentDetector instance (creates new if not provided)
        """
        self.detector = detector or KeywordIntentDetector()
    
    def split_commands(self, text: str) -> List[str]:
        """
        Split text into individual commands.
        
        Args:
            text: Input text potentially containing multiple commands
            
        Returns:
            List of individual command strings
        """
        # First try to split by common separators
        parts = [text]
        
        for sep in self.SEPARATORS:
            new_parts = []
            for part in parts:
                split_parts = re.split(sep, part, flags=re.IGNORECASE)
                new_parts.extend([p.strip() for p in split_parts if p.strip()])
            parts = new_parts
        
        return parts
    
    def detect(self, text: str) -> MultiCommandResult:
        """
        Detect all commands in the input text.
        
        Args:
            text: Input text potentially containing multiple commands
            
        Returns:
            MultiCommandResult with all detected commands
        """
        commands = self.split_commands(text)
        results = []
        
        for cmd in commands:
            result = self.detector.detect(cmd)
            if result.domain != 'unknown':
                results.append((cmd, result))
        
        return MultiCommandResult(
            original_text=text,
            commands=results,
            is_multi_command=len(results) > 1
        )
    
    def detect_with_fallback(self, text: str) -> MultiCommandResult:
        """
        Detect commands with fallback to single command if splitting fails.
        
        If splitting produces no valid commands but the original text
        produces a valid command, return that single command.
        
        Args:
            text: Input text
            
        Returns:
            MultiCommandResult
        """
        result = self.detect(text)
        
        if not result.commands:
            # Try detecting the original text as a single command
            single_result = self.detector.detect(text)
            if single_result.domain != 'unknown':
                return MultiCommandResult(
                    original_text=text,
                    commands=[(text, single_result)],
                    is_multi_command=False
                )
        
        return result


# Global instance for convenience
_multi_detector: Optional[MultiCommandDetector] = None


def get_multi_command_detector() -> MultiCommandDetector:
    """Get or create the global multi-command detector instance."""
    global _multi_detector
    if _multi_detector is None:
        _multi_detector = MultiCommandDetector()
    return _multi_detector


def detect_multi_commands(text: str) -> MultiCommandResult:
    """
    Convenience function to detect multiple commands.
    
    Args:
        text: Input text
        
    Returns:
        MultiCommandResult
    """
    return get_multi_command_detector().detect_with_fallback(text)
