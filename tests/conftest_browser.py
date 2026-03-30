"""
Browser test fixtures and mocks for faster test execution.
"""

import pytest
from unittest.mock import Mock, MagicMock
from nlp2cmd.adapters.browser import BrowserAdapter
from nlp2cmd.ir import ActionIR
import json


@pytest.fixture
def mock_site_explorer():
    """Mock SiteExplorer to avoid browser startup in tests."""
    mock = Mock()
    return mock


@pytest.fixture
def mock_browser_adapter(mock_site_explorer):
    """Provide a BrowserAdapter with mocked SiteExplorer."""
    adapter = BrowserAdapter()
    adapter.site_explorer = mock_site_explorer
    return adapter


@pytest.fixture
def sample_browser_irs():
    """Sample ActionIR objects for browser tests."""
    return {
        "open_google": ActionIR(
            dsl=json.dumps({
                "actions": [
                    {"action": "goto", "url": "https://google.com"}
                ]
            }),
            confidence=0.9,
            intent="browse"
        ),
        "fill_form": ActionIR(
            dsl=json.dumps({
                "actions": [
                    {"action": "goto", "url": "https://example.com/form"},
                    {"action": "fill", "selector": "#name", "text": "John Doe"},
                    {"action": "submit"}
                ]
            }),
            confidence=0.85,
            intent="browse"
        ),
        "navigate_and_extract": ActionIR(
            dsl=json.dumps({
                "actions": [
                    {"action": "goto", "url": "https://example.com"},
                    {"action": "extract", "type": "article"}
                ]
            }),
            confidence=0.8,
            intent="browse"
        )
    }


# Mark all browser tests as slow by default
pytest_plugins = []

def pytest_collection_modifyitems(config, items):
    """Automatically mark browser tests as slow."""
    for item in items:
        if "browser" in item.nodeid.lower():
            item.add_marker(pytest.mark.slow)
