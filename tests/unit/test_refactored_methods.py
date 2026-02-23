#!/usr/bin/env python3
"""Create unit tests for the refactored methods."""

import pytest
from unittest.mock import Mock, patch

from nlp2cmd.generation.keywords import KeywordIntentDetector, DetectionResult
from nlp2cmd.generation.templates import TemplateGenerator


class TestRefactoredKeywordDetector:
    """Test the refactored KeywordIntentDetector methods."""
    
    @pytest.fixture
    def detector(self):
        """Create a detector instance."""
        return KeywordIntentDetector()
    
    def test_detect_ml_classifier_high_confidence(self, detector):
        """Test ML classifier detection with high confidence."""
        with patch('nlp2cmd.generation.keywords._get_ml_classifier') as mock_get:
            mock_classifier = Mock()
            mock_result = Mock()
            mock_result.domain = 'shell'
            mock_result.intent = 'list_processes'
            mock_result.confidence = 0.95
            mock_result.method = 'test'
            mock_classifier.predict.return_value = mock_result
            mock_get.return_value = mock_classifier
            
            # Call the refactored method
            result = detector._detect_normalized("pokaż procesy")
            
            assert result.domain == 'shell'
            assert result.intent == 'list_processes'
            assert result.confidence == 0.95
            assert result.matched_keyword == 'ml:test'
    
    def test_detect_schema_matcher_high_confidence(self, detector):
        """Test schema matcher with high confidence."""
        with patch('nlp2cmd.generation.keywords._get_ml_classifier', return_value=None), \
             patch('nlp2cmd.generation.keywords._get_fuzzy_schema_matcher') as mock_get:
            
            mock_matcher = Mock()
            mock_result = Mock()
            mock_result.domain = 'shell'
            mock_result.intent = 'list_processes'
            mock_result.confidence = 0.90
            mock_result.matched = True
            mock_result.phrase = 'pokaż procesy'
            mock_matcher.match.return_value = mock_result
            mock_matcher._normalize.return_value = 'pokaż procesy'
            mock_get.return_value = mock_matcher
            
            result = detector._detect_normalized("pokaż procesy")
            
            assert result.domain == 'shell'
            assert result.confidence >= 0.90
    
    def test_detect_explicit_matches(self, detector):
        """Test explicit domain matches."""
        with patch('nlp2cmd.generation.keywords._get_ml_classifier', return_value=None), \
             patch('nlp2cmd.generation.keywords._get_fuzzy_schema_matcher', return_value=None):
            
            # Test SQL DROP detection
            result = detector._detect_normalized("drop table users")
            assert result.domain == 'sql'
            assert result.intent == 'drop_table'
    
    def test_detect_fallback(self, detector):
        """Test fallback to unknown when no matches."""
        with patch('nlp2cmd.generation.keywords._get_ml_classifier', return_value=None), \
             patch('nlp2cmd.generation.keywords._get_fuzzy_schema_matcher', return_value=None), \
             patch('nlp2cmd.generation.keywords._get_semantic_matcher', return_value=None), \
             patch('nlp2cmd.generation.keywords.fuzz', None), \
             patch('nlp2cmd.generation.keywords.process', None):
            
            result = detector._detect_normalized("completely unknown input")
            
            assert result.domain == 'unknown'
            assert result.intent == 'unknown'
            assert result.confidence == 0.0


class TestRefactoredTemplateGenerator:
    """Test the refactored TemplateGenerator methods."""
    
    @pytest.fixture
    def template_gen(self):
        """Create a TemplateGenerator instance."""
        return TemplateGenerator()
    
    def test_apply_shell_backup_defaults(self, template_gen):
        """Test backup defaults application."""
        entities = {"target": "/data"}
        result = {}

        applied = template_gen._apply_shell_backup_defaults("backup_create", entities, result)

        assert applied is True
        assert result["source"] == "/data"
    
    def test_apply_shell_system_defaults(self, template_gen):
        """Test system defaults application."""
        entities = {}
        result = {}

        applied = template_gen._apply_shell_system_defaults("system_logs", entities, result)

        assert applied is True
        assert "file" in result
    
    def test_apply_shell_dev_defaults(self, template_gen):
        """Test development defaults application."""
        entities = {}
        result = {}

        applied = template_gen._apply_shell_dev_defaults("dev_lint", entities, result)

        assert applied is True
        assert result["path"] == "src"
    
    def test_apply_shell_intent_specific_defaults_dispatch(self, template_gen):
        """Test the dispatch logic in _apply_shell_intent_specific_defaults."""
        entities = {"text": "znajdź pliki"}
        result = {}
        
        # Test file operation dispatch
        template_gen._apply_shell_intent_specific_defaults("file_search", entities, result)
        
        assert "extension" in result
        assert result["path"] == "."
    
    def test_apply_shell_network_defaults(self, template_gen):
        """Test network defaults application."""
        entities = {}
        result = {}

        applied = template_gen._apply_shell_network_defaults("network_ping", entities, result)

        assert applied is True
        assert "host" in result
    
    def test_apply_shell_browser_defaults(self, template_gen):
        """Test browser defaults application."""
        entities = {"url": "example.com"}
        result = {}

        applied = template_gen._apply_shell_browser_defaults("open_url", entities, result)

        assert applied is True
        assert result["url"] == "https://example.com"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
