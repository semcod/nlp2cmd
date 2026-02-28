"""
Test shell keyword intent detection.

This module tests keyword-based intent detection for shell domain
including file operations, process management, and system commands.
"""

import pytest

from nlp2cmd.generation.keywords import KeywordIntentDetector, DetectionResult


class TestShellKeywords:
    """Test shell keyword intent detection."""
    
    @pytest.fixture
    def detector(self) -> KeywordIntentDetector:
        return KeywordIntentDetector()
    
    def test_shell_find_polish(self, detector):
        """Test shell find detection in Polish."""
        result = detector.detect("Znajdź pliki konfiguracyjne")
        assert result.domain == 'shell'
        assert result.intent == 'find'
    
    def test_shell_find_english(self, detector):
        """Test shell find detection in English."""
        result = detector.detect("Find configuration files")
        assert result.domain == 'shell'
        assert result.intent == 'find'
    
    def test_shell_list(self, detector):
        """Test shell list detection."""
        result = detector.detect("Pokaż zawartość katalogu")
        assert result.domain == 'shell'
        assert result.intent == 'list'
    
    def test_shell_process(self, detector):
        """Test shell process detection."""
        result = detector.detect("Pokaż uruchomione procesy")
        assert result.domain == 'shell'
        assert result.intent == 'list_processes'
    
    def test_shell_disk(self, detector):
        """Test shell disk detection."""
        result = detector.detect("Sprawdź miejsce na dysku")
        assert result.domain == 'shell'
        assert result.intent == 'disk_usage'
    
    def test_shell_grep(self, detector):
        """Test shell grep detection."""
        result = detector.detect("Znajdź słowo error w logach")
        assert result.domain == 'shell'
        assert result.intent == 'search'
    
    def test_shell_copy(self, detector):
        """Test shell copy detection."""
        result = detector.detect("Skopiuj plik do backup")
        assert result.domain == 'shell'
        assert result.intent == 'copy'
    
    def test_shell_move(self, detector):
        """Test shell move detection."""
        result = detector.detect("Przenieś plik do nowego folderu")
        assert result.domain == 'shell'
        assert result.intent == 'move'
    
    def test_shell_delete(self, detector):
        """Test shell delete detection."""
        result = detector.detect("Usuń stary plik")
        assert result.domain == 'shell'
        assert result.intent == 'remove'
    
    def test_shell_permissions(self, detector):
        """Test shell permissions detection."""
        result = detector.detect("Zmień uprawnienia pliku")
        assert result.domain == 'shell'
        assert result.intent == 'permissions_chmod'
    
    def test_shell_compress(self, detector):
        """Test shell compress detection."""
        result = detector.detect("Spakuj folder do archiwum")
        assert result.domain == 'shell'
        assert result.intent == 'compress_tar'
