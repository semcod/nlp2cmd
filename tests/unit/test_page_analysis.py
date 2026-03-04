"""Tests for page_analysis package."""

import pytest
from unittest.mock import MagicMock

from nlp2cmd.page_analysis import (
    PageAnalysisResult,
    FieldInfo,
    FormAnalyzer,
    FieldClassifier,
    IframeAnalyzer,
    LinkExtractor,
    PageAnalyzer,
)


class TestPageAnalysisResult:
    """Test PageAnalysisResult dataclass."""
    
    def test_default_creation(self):
        """Test creating empty result."""
        result = PageAnalysisResult()
        assert result.url == ""
        assert result.title == ""
        assert result.has_form is False
        assert result.form_count == 0
        assert result.links == []
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = PageAnalysisResult(
            url="https://example.com",
            title="Test Page",
            has_form=True,
            form_count=2,
            fields=[FieldInfo(name="email", is_contact=True)],
        )
        d = result.to_dict()
        assert d["url"] == "https://example.com"
        assert d["has_form"] is True
        assert len(d["fields"]) == 1


class TestFieldInfo:
    """Test FieldInfo dataclass."""
    
    def test_default_creation(self):
        """Test creating field info."""
        field = FieldInfo()
        assert field.tag == ""
        assert field.field_type == "text"
        assert field.is_contact is False
        assert field.is_junk is False


class TestFormAnalyzer:
    """Test FormAnalyzer."""
    
    def test_analyze_with_forms(self):
        """Test analyzing page with forms."""
        analyzer = FormAnalyzer()
        
        mock_page = MagicMock()
        mock_page.query_selector_all.side_effect = [
            [MagicMock(), MagicMock()],  # inputs
            [MagicMock()],  # textareas
            [],  # selects
        ]
        
        form_count, visible_count, inputs, textareas, selects = analyzer.analyze(mock_page)
        
        assert form_count == 3
        assert visible_count == 3
        assert len(inputs) == 2
        assert len(textareas) == 1
    
    def test_analyze_no_forms(self):
        """Test analyzing page without forms."""
        analyzer = FormAnalyzer()
        
        mock_page = MagicMock()
        mock_page.query_selector_all.side_effect = [[], [], []]
        
        form_count, visible_count, inputs, textareas, selects = analyzer.analyze(mock_page)
        
        assert form_count == 0
        assert visible_count == 0
        assert len(inputs) == 0
    
    def test_extract_field_info(self):
        """Test extracting field information."""
        analyzer = FormAnalyzer()
        
        mock_node = MagicMock()
        mock_node.evaluate.return_value = "INPUT"
        mock_node.get_attribute.side_effect = lambda x: {
            "type": "email",
            "name": "user_email",
            "id": "email-field",
            "placeholder": "Your email",
            "aria-label": "Email address",
        }.get(x, "")
        
        field_info = analyzer.extract_field_info(mock_node)
        
        assert field_info is not None
        assert field_info.tag == "input"
        assert field_info.field_type == "email"
        assert field_info.name == "user_email"
    
    def test_get_field_nodes(self):
        """Test getting combined field nodes."""
        analyzer = FormAnalyzer(max_inputs=2, max_textareas=1)
        
        inputs = [MagicMock(), MagicMock(), MagicMock()]
        textareas = [MagicMock(), MagicMock()]
        
        nodes = analyzer.get_field_nodes(inputs, textareas)
        
        assert len(nodes) == 3  # 2 inputs + 1 textarea


class TestFieldClassifier:
    """Test FieldClassifier."""
    
    def test_classify_search_as_junk(self):
        """Test classifying search field as junk."""
        classifier = FieldClassifier()
        
        field = FieldInfo(
            field_type="search",
            name="q",
            placeholder="Search...",
        )
        
        is_junk, is_contact = classifier.classify(field)
        
        assert is_junk is True
        assert is_contact is False
    
    def test_classify_email_as_contact(self):
        """Test classifying email field as contact."""
        classifier = FieldClassifier()
        
        field = FieldInfo(
            field_type="email",
            name="email",
            placeholder="Your email",
        )
        
        is_junk, is_contact = classifier.classify(field)
        
        assert is_junk is False
        assert is_contact is True
    
    def test_classify_cookie_as_junk(self):
        """Test classifying cookie consent field as junk."""
        classifier = FieldClassifier()
        
        field = FieldInfo(
            field_type="checkbox",
            name="cookie_consent",
            field_id="cmplz-consent",
        )
        
        is_junk, is_contact = classifier.classify(field)
        
        assert is_junk is True
        assert is_contact is False
    
    def test_classify_message_as_contact(self):
        """Test classifying message textarea as contact."""
        classifier = FieldClassifier()
        
        field = FieldInfo(
            tag="textarea",
            field_type="textarea",
            name="message",
            placeholder="Your message",
        )
        
        is_junk, is_contact = classifier.classify(field)
        
        assert is_junk is False
        assert is_contact is True
    
    def test_classify_batch(self):
        """Test batch classification."""
        classifier = FieldClassifier()
        
        fields = [
            FieldInfo(field_type="email", name="email"),
            FieldInfo(field_type="search", name="q"),
            FieldInfo(field_type="text", name="name"),
        ]
        
        contact_count, junk_count = classifier.classify_batch(fields)
        
        assert contact_count == 2  # email and name
        assert junk_count == 1  # search


class TestIframeAnalyzer:
    """Test IframeAnalyzer."""
    
    def test_analyze_with_form_in_iframe(self):
        """Test finding form in iframe."""
        analyzer = IframeAnalyzer()
        
        mock_frame = MagicMock()
        mock_frame.query_selector_all.side_effect = [
            [MagicMock()],  # inputs
            [MagicMock(), MagicMock()],  # textareas
        ]
        
        mock_iframe = MagicMock()
        mock_iframe.content_frame.return_value = mock_frame
        
        mock_page = MagicMock()
        mock_page.query_selector_all.return_value = [mock_iframe]
        
        has_form, field_count = analyzer.analyze(mock_page)
        
        assert has_form is True
        assert field_count == 3
    
    def test_analyze_no_iframes(self):
        """Test analyzing page without iframes."""
        analyzer = IframeAnalyzer()
        
        mock_page = MagicMock()
        mock_page.query_selector_all.return_value = []
        
        has_form, field_count = analyzer.analyze(mock_page)
        
        assert has_form is False
        assert field_count == 0


class TestLinkExtractor:
    """Test LinkExtractor."""
    
    def test_extract_links(self):
        """Test extracting links."""
        extractor = LinkExtractor(max_links=5)
        
        mock_link1 = MagicMock()
        mock_link1.get_attribute.return_value = "/about"
        
        mock_link2 = MagicMock()
        mock_link2.get_attribute.return_value = "https://example.com/contact"
        
        mock_page = MagicMock()
        mock_page.query_selector_all.return_value = [mock_link1, mock_link2]
        
        links = extractor.extract(mock_page, "https://example.com")
        
        assert len(links) == 2
        assert "https://example.com/about" in links
        assert "https://example.com/contact" in links
    
    def test_exclude_external_links(self):
        """Test excluding external domain links."""
        extractor = LinkExtractor()
        
        mock_link1 = MagicMock()
        mock_link1.get_attribute.return_value = "/about"
        
        mock_link2 = MagicMock()
        mock_link2.get_attribute.return_value = "https://other.com/page"
        
        mock_page = MagicMock()
        mock_page.query_selector_all.return_value = [mock_link1, mock_link2]
        
        links = extractor.extract(mock_page, "https://example.com")
        
        assert "https://example.com/about" in links
        assert "https://other.com/page" not in links
    
    def test_exclude_file_extensions(self):
        """Test excluding file download links."""
        extractor = LinkExtractor()
        
        mock_link1 = MagicMock()
        mock_link1.get_attribute.return_value = "/document.pdf"
        
        mock_link2 = MagicMock()
        mock_link2.get_attribute.return_value = "/page"
        
        mock_page = MagicMock()
        mock_page.query_selector_all.return_value = [mock_link1, mock_link2]
        
        links = extractor.extract(mock_page, "https://example.com")
        
        assert "/document.pdf" not in [l for l in links if "pdf" in l]
        assert any("/page" in l for l in links)
    
    def test_normalize_url(self):
        """Test URL normalization."""
        extractor = LinkExtractor()
        
        assert extractor._normalize_url("https://example.com/page#section") == "https://example.com/page"
        assert extractor._normalize_url("https://example.com/page/") == "https://example.com/page"


class TestPageAnalyzer:
    """Test PageAnalyzer orchestrator."""
    
    def test_analyze_complete(self):
        """Test complete page analysis."""
        analyzer = PageAnalyzer()
        
        mock_page = MagicMock()
        mock_page.title.return_value = "Test Page"
        mock_page.query_selector_all.side_effect = [
            [MagicMock(), MagicMock()],  # inputs
            [MagicMock()],  # textareas
            [],  # selects
            [],  # iframes
            [],  # links
        ]
        
        # Mock field extraction
        mock_input = MagicMock()
        mock_input.evaluate.return_value = "INPUT"
        mock_input.get_attribute.side_effect = lambda x: {
            "type": "email",
            "name": "email",
            "id": "email",
            "placeholder": "",
            "aria-label": "",
        }.get(x, "")
        
        # Reset for link extraction
        def mock_qsa(selector):
            if 'input' in selector or 'textarea' in selector or 'select' in selector:
                return []
            elif 'iframe' in selector:
                return []
            elif 'nav' in selector or 'a[href]' in selector:
                return []
            return []
        
        mock_page.query_selector_all = mock_qsa
        mock_page.query_selector_all = MagicMock(side_effect=[
            [mock_input],  # inputs
            [],  # textareas
            [],  # selects
            [],  # iframes
            [],  # nav links
            [],  # footer links
            [],  # all links
        ])
        
        result = analyzer.analyze(mock_page, "https://example.com")
        
        assert result.url == "https://example.com"
        assert result.title == "Test Page"
    
    def test_analyze_quick(self):
        """Test quick analysis with reduced limits."""
        analyzer = PageAnalyzer()
        
        mock_page = MagicMock()
        mock_page.title.return_value = "Quick Test"
        mock_page.query_selector_all.return_value = []
        
        result = analyzer.analyze_quick(mock_page, "https://example.com")
        
        assert result.url == "https://example.com"
        assert result.title == "Quick Test"


class TestIntegration:
    """Integration tests."""
    
    def test_full_analysis_flow(self):
        """Test complete analysis flow."""
        analyzer = PageAnalyzer(max_links=3)
        
        # Create mock page with realistic structure
        mock_page = MagicMock()
        mock_page.title.return_value = "Contact Us"
        
        # Mock form elements
        mock_email = MagicMock()
        mock_email.evaluate.return_value = "INPUT"
        mock_email.get_attribute.side_effect = lambda x: {
            "type": "email", "name": "email", "id": "email",
            "placeholder": "Your email", "aria-label": "",
        }.get(x, "")
        
        mock_message = MagicMock()
        mock_message.evaluate.return_value = "TEXTAREA"
        mock_message.get_attribute.side_effect = lambda x: {
            "type": "", "name": "message", "id": "message",
            "placeholder": "Your message", "aria-label": "",
        }.get(x, "")
        
        # Mock links
        mock_link = MagicMock()
        mock_link.get_attribute.return_value = "/contact"
        
        def mock_query_selector_all(selector):
            if 'input' in selector:
                return [mock_email]
            elif 'textarea' in selector:
                return [mock_message]
            elif 'select' in selector:
                return []
            elif 'iframe' in selector:
                return []
            elif 'a[href]' in selector:
                return [mock_link]
            return []
        
        mock_page.query_selector_all = mock_query_selector_all
        
        result = analyzer.analyze(mock_page, "https://example.com")
        
        assert result.has_form is True
        assert result.form_count >= 2
        assert len(result.fields) >= 2
        
        # Check classification
        contact_fields = [f for f in result.fields if f.is_contact]
        assert len(contact_fields) >= 2  # email and message
