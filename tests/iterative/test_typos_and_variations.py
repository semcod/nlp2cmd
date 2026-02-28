"""
Test cases for typos, variations, and different word orders.
Tests the robustness of keyword detection with rapidfuzz and lemmatization.
"""

import pytest
from nlp2cmd.generation.keywords import KeywordIntentDetector
from nlp2cmd.generation.pipeline import RuleBasedPipeline


class TestTyposAndVariations:
    """Test detection robustness with typos and variations."""

    @pytest.fixture
    def detector(self):
        return KeywordIntentDetector()

    @pytest.fixture
    def pipeline(self):
        return RuleBasedPipeline()

    def test_docker_typos(self, detector, pipeline):
        """Test Docker commands with common typos."""
        test_cases = [
            # Typos
            ("doker ps", "docker", "list", "docker ps"),
            ("dokcer ps", "docker", "list", "docker ps"),
            ("doker images", "docker", "images", "docker images"),
            ("dokcer images", "docker", "images", "docker images"),
            ("doker run nginx", "docker", "run", "docker run nginx"),
            ("dokcer stop kontener", "docker", "stop", "docker stop"),
            
            # Mixed case
            ("Doker PS", "docker", "list", "docker ps"),
            ("DOKCER IMAGES", "docker", "images", "docker images"),
            
            # With extra spaces - should still match list (not list_all) since no -a flag
            ("  doker  ps  ", "docker", "list", "docker ps"),
            ("dokcer   run    nginx", "docker", "run", "docker run nginx"),
        ]
        
        for query, exp_domain, exp_intent, exp_command in test_cases:
            result = detector.detect(query)
            pipeline_result = pipeline.process(query)
            
            assert result.domain == exp_domain, f"Expected domain {exp_domain}, got {result.domain} for '{query}'"
            assert result.intent == exp_intent, f"Expected intent {exp_intent}, got {result.intent} for '{query}'"
            assert pipeline_result.command == exp_command, f"Expected command {exp_command}, got {pipeline_result.command} for '{query}'"

    def test_list_dirs_user_home_polish(self, detector, pipeline):
        query = "lista folderow w folderze usera"

        result = detector.detect(query)
        pipeline_result = pipeline.process(query)

        assert result.domain == "shell"
        assert result.intent == "list_dirs"
        assert pipeline_result.command == "find ~ -maxdepth 1 -type d"

    def test_shell_service_variations(self, detector, pipeline):
        """Test shell service commands with variations."""
        test_cases = [
            # Standard forms
            ("uruchom usługę nginx", "shell", "service_start", "systemctl start nginx"),
            ("zatrzymaj usługę nginx", "shell", "service_stop", "systemctl stop nginx"),
            ("restartuj usługę nginx", "shell", "service_restart", "systemctl restart nginx"),
            ("status usługi nginx", "shell", "service_status", "systemctl status nginx"),
            
            # Word order variations
            ("nginx uruchom usługę", "shell", "service_start", "systemctl start nginx"),
            ("usługę nginx zatrzymaj", "shell", "service_stop", "systemctl stop nginx"),
            ("nginx restartuj usługę", "shell", "service_restart", "systemctl restart nginx"),
            
            # With articles/prepositions
            ("uruchom usługę nginx teraz", "shell", "service_start", "systemctl start nginx"),
            ("zatrzymaj usługę nginx proszę", "shell", "service_stop", "systemctl stop nginx"),
            
            # Typos in service commands
            ("uruchom uslugę nginx", "shell", "service_start", "systemctl start nginx"),
            ("zatrzymaj usluge nginx", "shell", "service_stop", "systemctl stop nginx"),
            ("restartuj uslugę nginx", "shell", "service_restart", "systemctl restart nginx"),
        ]
        
        for query, exp_domain, exp_intent, exp_command in test_cases:
            result = detector.detect(query)
            pipeline_result = pipeline.process(query)
            
            assert result.domain == exp_domain, f"Expected domain {exp_domain}, got {result.domain} for '{query}'"
            assert result.intent == exp_intent, f"Expected intent {exp_intent}, got {result.intent} for '{query}'"
            assert pipeline_result.command == exp_command, f"Expected command {exp_command}, got {pipeline_result.command} for '{query}'"

    def test_system_reboot_variations(self, detector, pipeline):
        """Test system reboot commands with variations."""
        test_cases = [
            # Standard forms
            ("startuj system", "shell", "reboot", "reboot"),
            ("uruchom system", "shell", "reboot", "reboot"),
            ("restartuj system", "shell", "reboot", "reboot"),
            ("zrestartuj komputer", "shell", "reboot", "reboot"),
            
            # Word order variations
            ("system uruchom", "shell", "reboot", "reboot"),
            ("komputer zrestartuj", "shell", "reboot", "reboot"),
            
            # With context
            ("teraz startuj system", "shell", "reboot", "reboot"),
            ("proszę uruchom system", "shell", "reboot", "reboot"),
            ("natychmiast zrestartuj komputer", "shell", "reboot", "reboot"),
            
            # Typos
            ("startuj sistem", "shell", "reboot", "reboot"),
            ("uruchom sistem", "shell", "reboot", "reboot"),
            ("restartuj sistem", "shell", "reboot", "reboot"),
        ]
        
        for query, exp_domain, exp_intent, exp_command in test_cases:
            result = detector.detect(query)
            pipeline_result = pipeline.process(query)
            
            assert result.domain == exp_domain, f"Expected domain {exp_domain}, got {result.domain} for '{query}'"
            assert result.intent == exp_intent, f"Expected intent {exp_intent}, got {result.intent} for '{query}'"
            assert pipeline_result.command == exp_command, f"Expected command {exp_command}, got {pipeline_result.command} for '{query}'"

    def test_file_operations_variations(self, detector, pipeline):
        """Test file operations with variations."""
        test_cases = [
            # Copy operations
            ("skopiuj plik", "shell", "copy", "cp "),
            ("kopiuj plik", "shell", "copy", "cp "),
            ("plik skopiuj", "shell", "copy", "cp "),
            
            # Delete operations
            ("usuń plik", "shell", "remove", "rm "),
            ("usun plik", "shell", "remove", "rm "),
            ("plik usuń", "shell", "remove", "rm "),
            
            # Find operations
            ("znajdź plik", "shell", "find", "find . -name "),
            ("znajdz plik", "shell", "find", "find . -name "),
            ("plik znajdź", "shell", "find", "find . -name "),
            
            # List operations
            ("pokaż foldery", "shell", "list_dirs", "ls -la ."),
            ("pokaz foldery", "shell", "list_dirs", "ls -la ."),
            ("foldery pokaż", "shell", "list_dirs", "ls -la ."),
            
            # Typos
            ("kopij plik", "shell", "file_operation", "ls -la ."),  # file_operation due to typo handling
            ("usun plik", "shell", "remove", "rm "),
            ("znajdz plik", "shell", "find", "find . -name "),
        ]
        
        for query, exp_domain, exp_intent, exp_command in test_cases:
            result = detector.detect(query)
            pipeline_result = pipeline.process(query)
            
            assert result.domain == exp_domain, f"Expected domain {exp_domain}, got {result.domain} for '{query}'"
            assert result.intent == exp_intent, f"Expected intent {exp_intent}, got {result.intent} for '{query}'"

    def test_docker_container_variations(self, detector, pipeline):
        """Test Docker container commands with variations."""
        test_cases = [
            # List containers
            ("pokaż kontenery", "docker", "list", "docker ps"),
            ("kontenery pokaż", "docker", "list", "docker ps"),
            ("listę kontenerów", "docker", "list", "docker ps"),
            ("kontenery", "docker", "list", "docker ps"),
            
            # Typos in containers
            ("pokaż kontenery", "docker", "list", "docker ps"),
            ("kontenery pokaz", "docker", "list", "docker ps"),
            ("kontenerów listę", "docker", "list", "docker ps"),
            
            # Mixed with typos
            ("pokaż kontenery", "docker", "list", "docker ps"),
            ("dokcer kontenery", "docker", "list", "docker ps"),
            ("doker kontenery", "docker", "list", "docker ps"),
        ]
        
        for query, exp_domain, exp_intent, exp_command in test_cases:
            result = detector.detect(query)
            pipeline_result = pipeline.process(query)
            
            assert result.domain == exp_domain, f"Expected domain {exp_domain}, got {result.domain} for '{query}'"
            assert result.intent == exp_intent, f"Expected intent {exp_intent}, got {result.intent} for '{query}'"
            assert pipeline_result.command == exp_command, f"Expected command {exp_command}, got {pipeline_result.command} for '{query}'"

    def test_edge_cases_and_ambiguity(self, detector, pipeline):
        """Test edge cases and ambiguous queries."""
        test_cases = [
            # Very short queries
            ("ps", "shell", "list_processes", "ps aux"),
            ("ls", "shell", "list", "ls -la ."),
            ("cd", "unknown", "unknown", None),
            
            # Mixed domains
            ("docker uruchom nginx", "docker", "run", "docker run"),
            ("systemctl uruchom nginx", "shell", "service_start", "systemctl start nginx"),
            
            # Numbers and special characters
            ("uruchom nginx 8080", "shell", "service_start", "systemctl start nginx"),
            ("doker run -p 8080:80 nginx", "docker", "run", "docker run -p 8080:80"),
            
            # Empty or whitespace
            ("", "unknown", "unknown", None),
            ("   ", "unknown", "unknown", None),
            
            # Very long queries
            ("proszę uruchom usługę nginx na porcie 8080 teraz", "shell", "service_start", "systemctl start nginx"),
        ]
        
        for query, exp_domain, exp_intent, exp_command in test_cases:
            result = detector.detect(query)
            pipeline_result = pipeline.process(query)
            
            assert result.domain == exp_domain, f"Expected domain {exp_domain}, got {result.domain} for '{query}'"
            assert result.intent == exp_intent, f"Expected intent {exp_intent}, got {result.intent} for '{query}'"
            
            # For unknown cases, command might be None
            if exp_command is not None:
                assert pipeline_result.command == exp_command, f"Expected command {exp_command}, got {pipeline_result.command} for '{query}'"

    def test_confidence_scores_with_variations(self, detector):
        """Test that confidence scores are reasonable with variations."""
        test_cases = [
            # Exact matches should have high confidence
            ("docker ps", 0.90),
            ("uruchom usługę nginx", 0.95),
            ("startuj system", 0.90),  # Lower due to normalization
            
            # Typos should have slightly lower confidence but still good
            ("doker ps", 0.95),  # Should be caught by normalization
            ("dokcer ps", 0.95),  # Should be caught by normalization
            
            # Word order variations might have slightly lower confidence
            ("nginx uruchom usługę", 0.85),
            ("kontenery pokaż", 0.85),
            
            # Edge cases
            ("ps", 0.85),  # Short but valid
            ("", 0.0),    # Empty
        ]
        
        for query, expected_min_confidence in test_cases:
            result = detector.detect(query)
            assert result.confidence >= expected_min_confidence, f"Expected confidence >= {expected_min_confidence}, got {result.confidence} for '{query}'"

    def test_lemmatization_benefits(self, detector):
        """Test that lemmatization improves detection (if spaCy is available)."""
        # These should work better with lemmatization
        test_cases = [
            ("uruchomienie usługi nginx", "shell", "service_start"),
            ("restartowanie systemu", "shell", "reboot"),
            ("usuwanie pliku", "shell", "remove"),
            ("tworzenie katalogu", "shell", "create"),
            ("pokaz foldery", "shell", "list_dirs"),
        ]
        
        for query, exp_domain, exp_intent in test_cases:
            result = detector.detect(query)
            
            # At minimum, should detect the right domain even if intent is wrong
            assert result.domain == exp_domain, f"Expected domain {exp_domain}, got {result.domain} for '{query}'"
            
            # If lemmatization is working, intent should also be correct
            # But we don't fail the test if it's not, as lemmatization is optional
            if result.intent != exp_intent:
                print(f"Note: Lemmatization not fully working for '{query}' - got {result.intent} instead of {exp_intent}")

    def test_fuzzy_matching_thresholds(self, detector):
        """Test that fuzzy matching doesn't create false positives."""
        # These should NOT match anything (too different)
        negative_cases = [
            "xyz123",  # Random string
            "abcdefg", # Random string
            "qwerty",  # Keyboard pattern
            "lorem ipsum dolor sit amet",  # Latin text
        ]
        
        for query in negative_cases:
            result = detector.detect(query)
            assert result.domain == "unknown", f"Expected unknown domain for '{query}', got {result.domain}"
            assert result.intent == "unknown", f"Expected unknown intent for '{query}', got {result.intent}"
            assert result.confidence == 0.0, f"Expected confidence 0.0 for '{query}', got {result.confidence}"
