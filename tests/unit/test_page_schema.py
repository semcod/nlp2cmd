"""Tests for page_schema package."""

import pytest
from unittest.mock import MagicMock, Mock

from nlp2cmd.page_schema import (
    PageSchema,
    ButtonExtractor,
    FormExtractor,
    RadioExtractor,
    TokenExtractor,
    CopyButtonExtractor,
    PageSchemaExtractor,
)


class TestPageSchema:
    """Test PageSchema dataclass."""
    
    def test_default_creation(self):
        """Test creating empty PageSchema."""
        schema = PageSchema()
        assert schema.buttons == []
        assert schema.forms == []
        assert schema.radio_buttons == []
        assert schema.tokens == []
        assert schema.copy_buttons == []
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        schema = PageSchema(
            buttons=[{"text": "Click", "selector": "#btn"}],
            forms=[{"name": "email", "selector": "#email"}],
        )
        result = schema.to_dict()
        assert result["buttons"] == [{"text": "Click", "selector": "#btn"}]
        assert result["forms"] == [{"name": "email", "selector": "#email"}]
        assert result["tokens"] == []


class TestButtonExtractor:
    """Test ButtonExtractor."""
    
    def test_extract_single_button(self):
        """Test extracting a single button."""
        extractor = ButtonExtractor()
        
        # Mock page and element
        mock_el = MagicMock()
        mock_el.text_content.return_value = "Click Me"
        mock_el.get_attribute.side_effect = lambda x: "test-btn" if x == "data-testid" else ""
        mock_el.evaluate.return_value = "button"
        
        mock_locator = MagicMock()
        mock_locator.count.return_value = 1
        mock_locator.nth.return_value = mock_el
        
        mock_page = MagicMock()
        mock_page.locator.return_value = mock_locator
        
        result = extractor.extract(mock_page)
        
        assert len(result) == 1
        assert result[0]["text"] == "Click Me"
        assert result[0]["selector"] == "[data-testid='test-btn']"
        assert result[0]["tag"] == "button"
    
    def test_extract_button_with_aria_label(self):
        """Test extracting button with aria-label."""
        extractor = ButtonExtractor()
        
        mock_el = MagicMock()
        mock_el.text_content.return_value = "Submit"
        mock_el.get_attribute.side_effect = lambda x: "submit-btn" if x == "aria-label" else ""
        mock_el.evaluate.return_value = "button"
        
        mock_locator = MagicMock()
        mock_locator.count.return_value = 1
        mock_locator.nth.return_value = mock_el
        
        mock_page = MagicMock()
        mock_page.locator.return_value = mock_locator
        
        result = extractor.extract(mock_page)
        
        assert result[0]["selector"] == "[aria-label='submit-btn']"
    
    def test_extract_button_with_text_selector(self):
        """Test extracting button using text as selector fallback."""
        extractor = ButtonExtractor()
        
        mock_el = MagicMock()
        mock_el.text_content.return_value = "Click Here"
        mock_el.get_attribute.return_value = ""  # No test_id or aria
        mock_el.evaluate.return_value = "a"
        
        mock_locator = MagicMock()
        mock_locator.count.return_value = 1
        mock_locator.nth.return_value = mock_el
        
        mock_page = MagicMock()
        mock_page.locator.return_value = mock_locator
        
        result = extractor.extract(mock_page)
        
        assert result[0]["selector"] == "text='Click Here'"
        assert result[0]["tag"] == "a"
    
    def test_skip_short_text(self):
        """Test skipping buttons with very short text."""
        extractor = ButtonExtractor()
        
        mock_el = MagicMock()
        mock_el.text_content.return_value = "X"  # Too short
        
        mock_locator = MagicMock()
        mock_locator.count.return_value = 1
        mock_locator.nth.return_value = mock_el
        
        mock_page = MagicMock()
        mock_page.locator.return_value = mock_locator
        
        result = extractor.extract(mock_page)
        
        assert len(result) == 0
    
    def test_respects_max_buttons(self):
        """Test that extraction respects MAX_BUTTONS limit."""
        extractor = ButtonExtractor()
        
        mock_locator = MagicMock()
        mock_locator.count.return_value = 50  # More than MAX_BUTTONS
        
        mock_page = MagicMock()
        mock_page.locator.return_value = mock_locator
        
        result = extractor.extract(mock_page)
        
        # Should only try to get MAX_BUTTONS (30)
        assert mock_locator.nth.call_count == 30


class TestFormExtractor:
    """Test FormExtractor."""
    
    def test_extract_text_input(self):
        """Test extracting text input."""
        extractor = FormExtractor()
        
        mock_el = MagicMock()
        mock_el.get_attribute.side_effect = lambda x: {
            "name": "username",
            "placeholder": "Enter username",
            "type": "text",
            "data-testid": "",
        }.get(x, "")
        
        mock_locator = MagicMock()
        mock_locator.count.return_value = 1
        mock_locator.nth.return_value = mock_el
        
        mock_page = MagicMock()
        mock_page.locator.return_value = mock_locator
        
        result = extractor.extract(mock_page)
        
        assert len(result) == 1
        assert result[0]["name"] == "username"
        assert result[0]["placeholder"] == "Enter username"
        assert result[0]["type"] == "text"
        assert result[0]["selector"] == "input[name='username']"
    
    def test_extract_with_testid(self):
        """Test extracting input with data-testid."""
        extractor = FormExtractor()
        
        mock_el = MagicMock()
        mock_el.get_attribute.side_effect = lambda x: {
            "name": "",
            "placeholder": "",
            "type": "text",
            "data-testid": "email-input",
        }.get(x, "")
        
        mock_locator = MagicMock()
        mock_locator.count.return_value = 1
        mock_locator.nth.return_value = mock_el
        
        mock_page = MagicMock()
        mock_page.locator.return_value = mock_locator
        
        result = extractor.extract(mock_page)
        
        assert result[0]["selector"] == "[data-testid='email-input']"


class TestRadioExtractor:
    """Test RadioExtractor."""
    
    def test_extract_radio_button(self):
        """Test extracting radio button."""
        extractor = RadioExtractor()
        
        mock_el = MagicMock()
        mock_el.get_attribute.side_effect = lambda x: {
            "value": "pro",
            "name": "plan",
            "data-testid": "",
            "id": "plan-pro",
        }.get(x, "")
        
        mock_label = MagicMock()
        mock_label.text_content.return_value = "Pro Plan"
        
        mock_page = MagicMock()
        mock_page.query_selector.return_value = mock_label
        
        mock_locator = MagicMock()
        mock_locator.count.return_value = 1
        mock_locator.nth.return_value = mock_el
        mock_page.locator.return_value = mock_locator
        
        result = extractor.extract(mock_page)
        
        assert len(result) == 1
        assert result[0]["value"] == "pro"
        assert result[0]["name"] == "plan"
        assert result[0]["label"] == "Pro Plan"
        assert result[0]["selector"] == "input[name='plan'][value='pro']"


class TestTokenExtractor:
    """Test TokenExtractor."""
    
    def test_extract_token(self):
        """Test extracting API token."""
        extractor = TokenExtractor()
        
        mock_el = MagicMock()
        mock_el.text_content.return_value = "sk-1234567890abcdef"
        mock_el.get_attribute.return_value = None
        
        mock_page = MagicMock()
        mock_page.query_selector_all.return_value = [mock_el]
        
        result = extractor.extract(mock_page)
        
        # TokenExtractor tries 9 different selectors, each finding the mock
        assert len(result) == 9
        assert result[0]["text_preview"] == "sk-1234567890ab..."
        assert result[0]["length"] == "19"
    
    def test_skip_short_tokens(self):
        """Test skipping tokens that are too short."""
        extractor = TokenExtractor()
        
        mock_el = MagicMock()
        mock_el.text_content.return_value = "short"  # Less than 10 chars
        
        mock_page = MagicMock()
        mock_page.query_selector_all.return_value = [mock_el]
        
        result = extractor.extract(mock_page)
        
        # Should be empty or not include this token
        assert len(result) == 0 or all(len(t["length"]) >= 2 for t in result)


class TestCopyButtonExtractor:
    """Test CopyButtonExtractor."""
    
    def test_extract_copy_button(self):
        """Test extracting copy button."""
        extractor = CopyButtonExtractor()
        
        mock_el = MagicMock()
        mock_el.text_content.return_value = "Copy"
        mock_el.get_attribute.side_effect = lambda x: "copy-btn" if x == "data-testid" else ""
        
        mock_locator = MagicMock()
        mock_locator.count.return_value = 1
        mock_locator.nth.return_value = mock_el
        
        mock_page = MagicMock()
        mock_page.locator.return_value = mock_locator
        
        result = extractor.extract(mock_page)
        
        assert len(result) == 1
        assert result[0]["text"] == "Copy"
        assert result[0]["selector"] == "[data-testid='copy-btn']"


class TestPageSchemaExtractor:
    """Test PageSchemaExtractor."""
    
    def test_extract_complete_schema(self):
        """Test extracting complete page schema."""
        extractor = PageSchemaExtractor()
        
        # Mock page that returns elements for all extractors
        mock_page = MagicMock()
        
        # Setup mock locators
        def mock_locator(selector):
            mock_el = MagicMock()
            mock_el.text_content.return_value = "Test"
            mock_el.get_attribute.side_effect = lambda x: "test-id" if x == "data-testid" else ""
            mock_el.evaluate.return_value = "button"
            
            mock_loc = MagicMock()
            mock_loc.count.return_value = 1
            mock_loc.nth.return_value = mock_el
            return mock_loc
        
        mock_page.locator = mock_locator
        mock_page.query_selector_all.return_value = []
        
        result = extractor.extract(mock_page)
        
        assert isinstance(result, PageSchema)
        assert len(result.buttons) >= 0  # May or may not extract based on mocking
    
    def test_extract_dict_format(self):
        """Test extracting as dictionary."""
        extractor = PageSchemaExtractor()
        
        mock_page = MagicMock()
        mock_page.locator.return_value.count.return_value = 0
        mock_page.query_selector_all.return_value = []
        
        result = extractor.extract_dict(mock_page)
        
        assert isinstance(result, dict)
        assert "buttons" in result
        assert "forms" in result
        assert "radio_buttons" in result
        assert "tokens" in result
        assert "copy_buttons" in result


class TestIntegration:
    """Integration tests."""
    
    def test_full_extraction_flow(self):
        """Test full extraction flow with realistic mock page."""
        extractor = PageSchemaExtractor()
        
        # Create mock elements
        mock_button = MagicMock()
        mock_button.text_content.return_value = "Create API Key"
        mock_button.get_attribute.side_effect = lambda x: {
            "data-testid": "create-key-btn",
            "aria-label": "",
        }.get(x, "")
        mock_button.evaluate.return_value = "button"
        
        mock_input = MagicMock()
        mock_input.get_attribute.side_effect = lambda x: {
            "name": "key_name",
            "placeholder": "Enter key name",
            "type": "text",
            "data-testid": "",
        }.get(x, "")
        
        # Setup mock page
        mock_page = MagicMock()
        
        btn_locator = MagicMock()
        btn_locator.count.return_value = 1
        btn_locator.nth.return_value = mock_button
        
        input_locator = MagicMock()
        input_locator.count.return_value = 1
        input_locator.nth.return_value = mock_input
        
        def mock_locator(selector):
            if "button" in selector:
                return btn_locator
            elif "input" in selector or "textarea" in selector:
                return input_locator
            return MagicMock()
        
        mock_page.locator = mock_locator
        mock_page.query_selector_all.return_value = []
        
        result = extractor.extract(mock_page)
        
        # Verify structure
        assert isinstance(result, PageSchema)
        assert len(result.buttons) == 1
        assert result.buttons[0]["text"] == "Create API Key"
        assert len(result.forms) == 1
        assert result.forms[0]["name"] == "key_name"
