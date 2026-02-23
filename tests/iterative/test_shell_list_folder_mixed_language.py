import pytest

from nlp2cmd.generation.keywords import KeywordIntentDetector


class TestShellListFolderMixedLanguage:
    @pytest.fixture
    def detector(self) -> KeywordIntentDetector:
        return KeywordIntentDetector()

    def test_shell_list_folder_mixed_language(self, detector: KeywordIntentDetector):
        result = detector.detect("Lista folder of systemu")
        assert result.domain == "shell"
        assert result.intent in ("list", "list_dirs")
