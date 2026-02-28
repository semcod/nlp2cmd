#!/usr/bin/env python3
"""
Comprehensive tests for Polish command detection including:
- Single Polish commands
- Mixed Polish-English commands
- Multi-command in one sentence
- Multi-sentence inputs
"""

import sys
import os
import re
from typing import List, Tuple

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import pytest
from nlp2cmd.generation.keywords import KeywordIntentDetector, DetectionResult


class MultiCommandDetector:
    """Utility class to detect multiple commands in one input."""
    
    # Sentence/command separators
    SEPARATORS = [
        r'\.\s+',           # Period followed by space
        r';\s*',            # Semicolon
        r'\s+a\s+potem\s+', # Polish "a potem" (and then)
        r'\s+potem\s+',     # Polish "potem" (then)
        r'\s+nast[eę]pnie\s+',  # Polish "następnie" (next)
        r'\s+oraz\s+',      # Polish "oraz" (and also)
        r'\s+and\s+then\s+', # English "and then"
        r'\s+then\s+',      # English "then"
        r'\s+after\s+that\s+', # English "after that"
        r'\s+i\s+',         # Polish "i" (and)
        r'\s+and\s+',       # English "and"
    ]
    
    def __init__(self):
        self.detector = KeywordIntentDetector()
    
    def split_commands(self, text: str) -> List[str]:
        """Split text into individual commands."""
        # First try to split by common separators
        parts = [text]
        
        for sep in self.SEPARATORS:
            new_parts = []
            for part in parts:
                split_parts = re.split(sep, part, flags=re.IGNORECASE)
                new_parts.extend([p.strip() for p in split_parts if p.strip()])
            parts = new_parts
        
        return parts
    
    def detect_all_commands(self, text: str) -> List[Tuple[str, DetectionResult]]:
        """Detect all commands in the input text."""
        commands = self.split_commands(text)
        results = []
        
        for cmd in commands:
            result = self.detector.detect(cmd)
            if result.domain != 'unknown':
                results.append((cmd, result))
        
        return results


class TestSinglePolishCommands:
    """Test single Polish command detection."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.detector = KeywordIntentDetector()
    
    # Docker commands
    @pytest.mark.parametrize("input_text,expected_domain,expected_intent", [
        ("lista container", "docker", "list"),
        ("lista kontener", "docker", "list"),
        ("lista kontenerów", "docker", "list"),
        ("pokaż kontenery", "docker", "list"),
        ("pokaz kontenery", "docker", "list"),
        ("pokaż container", "docker", "list"),
        ("docker ps", "docker", "list"),
        ("list containers", "docker", "list"),
    ])
    def test_docker_list(self, input_text, expected_domain, expected_intent):
        result = self.detector.detect(input_text)
        assert result.domain == expected_domain, f"Expected domain {expected_domain}, got {result.domain}"
        assert result.intent == expected_intent, f"Expected intent {expected_intent}, got {result.intent}"
    
    @pytest.mark.parametrize("input_text,expected_domain,expected_intent", [
        ("zatrzymaj kontener", "docker", "stop"),
        ("zatrzymaj container", "docker", "stop"),
        ("stop container", "docker", "stop"),
        ("docker stop", "docker", "stop"),
        ("wyłącz kontener", "docker", "stop"),
        ("wylacz kontener", "docker", "stop"),
        ("kill kontener", "docker", "stop"),
    ])
    def test_docker_stop(self, input_text, expected_domain, expected_intent):
        result = self.detector.detect(input_text)
        assert result.domain == expected_domain
        assert result.intent == expected_intent
    
    @pytest.mark.parametrize("input_text,expected_domain,expected_intent", [
        ("uruchom kontener", "docker", "run"),
        ("uruchom container", "docker", "run"),
        ("run container", "docker", "run"),
        ("docker run", "docker", "run"),
        ("odpal kontener", "docker", "run"),
        ("wystartuj kontener", "docker", "run"),
        ("docker run nginx", "docker", "run"),
        ("uruchom kontener nginx", "docker", "run"),
    ])
    def test_docker_run(self, input_text, expected_domain, expected_intent):
        result = self.detector.detect(input_text)
        assert result.domain == expected_domain
        assert result.intent == expected_intent
    
    @pytest.mark.parametrize("input_text,expected_domain,expected_intent", [
        ("pokaż logi", "docker", "logs"),
        ("pokaz logi", "docker", "logs"),
        ("show logs", "docker", "logs"),
        ("docker logs", "docker", "logs"),
        ("logi kontenera", "docker", "logs"),
        ("wyświetl logi", "docker", "logs"),
        ("śledź logi", "docker", "logs"),
    ])
    def test_docker_logs(self, input_text, expected_domain, expected_intent):
        result = self.detector.detect(input_text)
        assert result.domain == expected_domain
        assert result.intent == expected_intent
    
    @pytest.mark.parametrize("input_text,expected_domain,expected_intent", [
        ("docker compose restart", "docker", "restart"),
        ("restartuj kontener nginx", "docker", "restart"),
        ("docker-compose restart", "docker", "restart"),
    ])
    def test_docker_restart(self, input_text, expected_domain, expected_intent):
        result = self.detector.detect(input_text)
        assert result.domain == expected_domain
        assert result.intent == expected_intent
    
    @pytest.mark.parametrize("input_text,expected_domain,expected_intent", [
        ("zbuduj obraz", "docker", "build"),
        ("zbuduj image", "docker", "build"),
        ("build image", "docker", "build"),
        ("docker build", "docker", "build"),
        ("stwórz obraz", "docker", "build"),
        ("stworz obraz", "docker", "build"),
    ])
    def test_docker_build(self, input_text, expected_domain, expected_intent):
        result = self.detector.detect(input_text)
        assert result.domain == expected_domain
        assert result.intent == expected_intent
    
    @pytest.mark.parametrize("input_text,expected_domain,expected_intent", [
        ("wejdź do kontenera", "docker", "exec"),
        ("wejdz do kontenera", "docker", "exec"),
        ("docker exec", "docker", "exec"),
        ("docker exec -it kontener bash", "docker", "exec"),
        ("terminal kontenera", "docker", "exec"),
        ("connect to container", "docker", "exec"),
        ("shell kontenera", "docker", "exec"),
    ])
    def test_docker_exec(self, input_text, expected_domain, expected_intent):
        result = self.detector.detect(input_text)
        assert result.domain == expected_domain
        assert result.intent == expected_intent
    
    @pytest.mark.parametrize("input_text,expected_domain,expected_intent", [
        ("pokaż obrazy", "docker", "images"),
        ("pokaz obrazy", "docker", "images"),
        ("docker images", "docker", "images"),
        ("list images", "docker", "images"),
        ("lista obrazów", "docker", "images"),
    ])
    def test_docker_images(self, input_text, expected_domain, expected_intent):
        result = self.detector.detect(input_text)
        assert result.domain == expected_domain
        assert result.intent == expected_intent
    
    # Shell commands
    @pytest.mark.parametrize("input_text,expected_domain,expected_intent", [
        ("pokaż pliki", "shell", "list"),
        ("pokaz pliki", "shell", "list"),
        ("lista plików", "shell", "list"),
        ("lista plik", "shell", "list"),
        ("show files", "shell", "list"),
        ("list files", "shell", "list"),
        ("ls", "shell", "list"),
    ])
    def test_shell_list(self, input_text, expected_domain, expected_intent):
        result = self.detector.detect(input_text)
        assert result.domain == expected_domain
        assert result.intent == expected_intent
    
    @pytest.mark.parametrize("input_text,expected_domain,expected_intent", [
        ("znajdź plik", "shell", "find"),
        ("znajdz plik", "shell", "find"),
        ("find file", "shell", "find"),
        ("szukaj pliku", "shell", "find"),
    ])
    def test_shell_find(self, input_text, expected_domain, expected_intent):
        result = self.detector.detect(input_text)
        assert result.domain == expected_domain
        assert result.intent == expected_intent
    
    @pytest.mark.parametrize("input_text,expected_domain,expected_intent", [
        ("usuń plik", "shell", "remove"),
        ("usun plik", "shell", "remove"),
        ("delete file", "shell", "remove"),
        ("skasuj plik", "shell", "remove"),
    ])
    def test_shell_delete(self, input_text, expected_domain, expected_intent):
        result = self.detector.detect(input_text)
        assert result.domain == expected_domain
        assert result.intent == expected_intent
    
    @pytest.mark.parametrize("input_text,expected_domain,expected_intent", [
        ("pokaż procesy", "shell", "list_processes"),
        ("pokaz procesy", "shell", "list_processes"),
        ("lista procesów", "shell", "list_processes"),
        ("procesy systemowe", "shell", "list_processes"),
    ])
    def test_shell_processes(self, input_text, expected_domain, expected_intent):
        result = self.detector.detect(input_text)
        assert result.domain == expected_domain
        assert result.intent == expected_intent


class TestMultiCommandDetection:
    """Test detection of multiple commands in one input."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.multi_detector = MultiCommandDetector()
    
    def test_two_docker_commands_with_and(self):
        """Test: 'pokaż kontenery i pokaż logi'"""
        text = "pokaż kontenery i pokaż logi"
        results = self.multi_detector.detect_all_commands(text)
        
        assert len(results) >= 2, f"Expected at least 2 commands, got {len(results)}"
        
        domains = [r[1].domain for r in results]
        intents = [r[1].intent for r in results]
        
        assert "docker" in domains
        assert "list" in intents or "logs" in intents
    
    def test_two_docker_commands_with_then(self):
        """Test: 'zatrzymaj kontener potem uruchom kontener'"""
        text = "zatrzymaj kontener potem uruchom kontener"
        results = self.multi_detector.detect_all_commands(text)
        
        assert len(results) >= 2, f"Expected at least 2 commands, got {len(results)}"
    
    def test_two_docker_commands_with_period(self):
        """Test: 'lista container. pokaż logi.'"""
        text = "lista container. pokaż logi."
        results = self.multi_detector.detect_all_commands(text)
        
        assert len(results) >= 2, f"Expected at least 2 commands, got {len(results)}"
    
    def test_mixed_docker_shell_commands(self):
        """Test: 'pokaż kontenery i pokaż pliki'"""
        text = "pokaż kontenery i pokaż pliki"
        results = self.multi_detector.detect_all_commands(text)
        
        assert len(results) >= 2, f"Expected at least 2 commands, got {len(results)}"
        
        domains = [r[1].domain for r in results]
        assert "docker" in domains
        assert "shell" in domains
    
    def test_three_commands_with_semicolon(self):
        """Test: 'lista container; pokaż logi; docker images'"""
        text = "lista container; pokaż logi; docker images"
        results = self.multi_detector.detect_all_commands(text)
        
        assert len(results) >= 3, f"Expected at least 3 commands, got {len(results)}"
    
    def test_english_multi_command(self):
        """Test: 'list containers and show logs'"""
        text = "list containers and show logs"
        results = self.multi_detector.detect_all_commands(text)
        
        assert len(results) >= 2, f"Expected at least 2 commands, got {len(results)}"
    
    def test_english_then_command(self):
        """Test: 'stop container then start container'"""
        text = "stop container then start container"
        results = self.multi_detector.detect_all_commands(text)
        
        assert len(results) >= 2, f"Expected at least 2 commands, got {len(results)}"

    def test_english_and_then_command(self):
        """Test: 'stop container and then start container'"""
        text = "stop container and then start container"
        results = self.multi_detector.detect_all_commands(text)

        assert len(results) >= 2, f"Expected at least 2 commands, got {len(results)}"
    
    def test_polish_oraz_separator(self):
        """Test: 'pokaż kontenery oraz pokaż obrazy'"""
        text = "pokaż kontenery oraz pokaż obrazy"
        results = self.multi_detector.detect_all_commands(text)
        
        assert len(results) >= 2, f"Expected at least 2 commands, got {len(results)}"
    
    def test_polish_nastepnie_separator(self):
        """Test: 'zatrzymaj kontener następnie uruchom kontener'"""
        text = "zatrzymaj kontener następnie uruchom kontener"
        results = self.multi_detector.detect_all_commands(text)
        
        assert len(results) >= 2, f"Expected at least 2 commands, got {len(results)}"


class TestMultiSentenceDetection:
    """Test detection across multiple sentences."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.multi_detector = MultiCommandDetector()
    
    def test_two_sentences_docker(self):
        """Test: 'Pokaż wszystkie kontenery. Sprawdź logi nginx.'"""
        text = "Pokaż wszystkie kontenery. Sprawdź logi nginx."
        results = self.multi_detector.detect_all_commands(text)
        
        assert len(results) >= 2, f"Expected at least 2 commands, got {len(results)}"
    
    def test_three_sentences_mixed(self):
        """Test: 'Lista kontenerów. Pokaż pliki. Uruchom nginx.'"""
        text = "Lista kontenerów. Pokaż pliki. Uruchom nginx."
        results = self.multi_detector.detect_all_commands(text)
        
        assert len(results) >= 3, f"Expected at least 3 commands, got {len(results)}"
    
    def test_complex_multi_sentence(self):
        """Test: 'Najpierw pokaż kontenery. Potem sprawdź logi. Na końcu zrestartuj nginx.'"""
        text = "Najpierw pokaż kontenery. Potem sprawdź logi. Na końcu zrestartuj nginx."
        results = self.multi_detector.detect_all_commands(text)
        
        assert len(results) >= 3, f"Expected at least 3 commands, got {len(results)}"

    def test_two_sentences_shell(self):
        """Test: 'Pokaż pliki. Usuń plik.'"""
        text = "Pokaż pliki. Usuń plik."
        results = self.multi_detector.detect_all_commands(text)

        assert len(results) >= 2, f"Expected at least 2 commands, got {len(results)}"

        intents = [r[1].intent for r in results]
        assert "list" in intents
        assert "remove" in intents

    def test_two_sentences_mixed_domains(self):
        """Test: 'Pokaż kontenery. Pokaż pliki.'"""
        text = "Pokaż kontenery. Pokaż pliki."
        results = self.multi_detector.detect_all_commands(text)

        assert len(results) >= 2, f"Expected at least 2 commands, got {len(results)}"

        domains = [r[1].domain for r in results]
        assert "docker" in domains
        assert "shell" in domains

    def test_multi_sentence_user_list(self):
        """Test: 'Pokaż userów systemu. Pokaż procesy.'"""
        text = "Pokaż userów systemu. Pokaż procesy."
        results = self.multi_detector.detect_all_commands(text)

        assert len(results) >= 2, f"Expected at least 2 commands, got {len(results)}"

        intents = [r[1].intent for r in results]
        assert "user_list" in intents
        assert "list_processes" in intents


class TestEdgeCases:
    """Test edge cases and special scenarios."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.detector = KeywordIntentDetector()
        self.multi_detector = MultiCommandDetector()
    
    def test_command_with_parameter(self):
        """Test: 'docker run nginx na porcie 8080'"""
        result = self.detector.detect("docker run nginx na porcie 8080")
        assert result.domain == "docker"
        assert result.intent in ["run", "run_detached"]
    
    def test_command_with_container_name(self):
        """Test: 'zatrzymaj kontener web-app'"""
        result = self.detector.detect("zatrzymaj kontener web-app")
        assert result.domain == "docker"
        assert result.intent == "stop"
    
    def test_typo_tolerance(self):
        """Test tolerance for common typos."""
        # Missing diacritics
        result = self.detector.detect("pokaz kontenery")
        assert result.domain == "docker"
        
        result = self.detector.detect("zatrzymaj kontener")
        assert result.domain == "docker"
    
    def test_case_insensitivity(self):
        """Test case insensitivity."""
        result = self.detector.detect("LISTA CONTAINER")
        assert result.domain == "docker"
        
        result = self.detector.detect("Docker PS")
        assert result.domain == "docker"
    
    def test_extra_whitespace(self):
        """Test handling of extra whitespace."""
        result = self.detector.detect("  pokaż   kontenery  ")
        assert result.domain == "docker"
    
    def test_empty_input(self):
        """Test empty input handling."""
        result = self.detector.detect("")
        assert result.domain == "unknown"
    
    def test_unknown_command(self):
        """Test unknown command handling."""
        result = self.detector.detect("xyz abc 123")
        assert result.domain == "unknown"


class TestConfidenceScores:
    """Test confidence scores for different inputs."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.detector = KeywordIntentDetector()
    
    def test_exact_match_high_confidence(self):
        """Exact matches should have high confidence."""
        result = self.detector.detect("docker ps")
        assert result.confidence >= 0.9
    
    def test_partial_match_medium_confidence(self):
        """Partial matches should have medium confidence."""
        result = self.detector.detect("lista container")
        assert result.confidence >= 0.8
    
    def test_fuzzy_match_lower_confidence(self):
        """Fuzzy matches should have lower confidence."""
        result = self.detector.detect("pokaz kontener")
        assert result.confidence >= 0.7


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
