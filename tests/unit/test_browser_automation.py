"""
Comprehensive tests for browser automation pipeline.

Tests cover:
- BrowserAdapter URL extraction, action detection, ActionIR generation
- transform_ir integration (dsl_kind='dom', not 'shell')
- Polish and English queries
- Various URL formats and websites
- fill_form, submit, type, press_enter action detection
- PipelineRunner networkidle fallback
"""

import json
import pytest

from nlp2cmd.adapters.browser import BrowserAdapter
from nlp2cmd.core.core_transform import NLP2CMD
from nlp2cmd.ir import ActionIR
from nlp2cmd.pipeline_runner import PipelineRunner


def _make_ir(query: str) -> ActionIR:
    """Helper: generate ActionIR from a browser query."""
    adapter = BrowserAdapter()
    nlp = NLP2CMD(adapter=adapter)
    return nlp.transform_ir(query)


def _parse_ir(ir: ActionIR) -> dict:
    """Helper: parse ActionIR.dsl as JSON and return payload."""
    return json.loads(ir.dsl)


def _get_actions(ir: ActionIR) -> list[str]:
    """Helper: extract action names from a multi-action IR."""
    payload = _parse_ir(ir)
    actions = payload.get("actions")
    if isinstance(actions, list):
        return [a.get("action") for a in actions if isinstance(a, dict)]
    action = payload.get("action")
    return [action] if action else []


# ---------------------------------------------------------------------------
# 1. Simple navigation (goto only) — Polish queries
# ---------------------------------------------------------------------------

class TestBrowserSimpleNavigationPL:

    def test_open_google(self):
        ir = _make_ir("otwórz https://google.com")
        assert ir.dsl_kind == "dom"
        assert "google.com" in _parse_ir(ir).get("url", "")
        assert _get_actions(ir) == ["goto"]

    def test_open_github(self):
        ir = _make_ir("otwórz https://github.com")
        assert ir.dsl_kind == "dom"
        assert "github.com" in _parse_ir(ir)["url"]

    def test_open_stackoverflow(self):
        ir = _make_ir("otwórz stronę https://stackoverflow.com")
        assert ir.dsl_kind == "dom"
        assert "stackoverflow.com" in _parse_ir(ir)["url"]

    def test_open_wikipedia(self):
        ir = _make_ir("otwórz https://pl.wikipedia.org/wiki/Python")
        assert ir.dsl_kind == "dom"
        payload = _parse_ir(ir)
        assert "pl.wikipedia.org" in payload["url"]
        assert "/wiki/Python" in payload["url"]

    def test_open_with_path(self):
        ir = _make_ir("otwórz https://example.com/about/team")
        assert ir.dsl_kind == "dom"
        assert "/about/team" in _parse_ir(ir)["url"]


# ---------------------------------------------------------------------------
# 2. Simple navigation — English queries
# ---------------------------------------------------------------------------

class TestBrowserSimpleNavigationEN:

    def test_open_url_en(self):
        ir = _make_ir("open https://docs.python.org/3/")
        assert ir.dsl_kind == "dom"
        assert "docs.python.org" in _parse_ir(ir)["url"]

    def test_go_to_url(self):
        ir = _make_ir("go to https://reddit.com")
        assert ir.dsl_kind == "dom"
        assert "reddit.com" in _parse_ir(ir)["url"]

    def test_navigate_to(self):
        ir = _make_ir("navigate to https://news.ycombinator.com")
        assert ir.dsl_kind == "dom"
        assert "news.ycombinator.com" in _parse_ir(ir)["url"]


# ---------------------------------------------------------------------------
# 3. Navigation + fill_form + submit — Polish queries
# ---------------------------------------------------------------------------

class TestBrowserFillFormPL:

    def test_prototypowanie_fill_and_submit(self):
        ir = _make_ir("otwórz https://www.prototypowanie.pl/kontakt/ i wypełnij formularz i wyślij")
        assert ir.dsl_kind == "dom"
        actions = _get_actions(ir)
        assert "goto" in actions
        assert "fill_form" in actions
        assert "submit" in actions
        assert ir.confidence > 0

    def test_softreck_fill_and_submit(self):
        ir = _make_ir("otwórz https://softreck.com/contact/ i wypełnij formularz i wyślij")
        assert ir.dsl_kind == "dom"
        actions = _get_actions(ir)
        assert "goto" in actions
        assert "fill_form" in actions
        assert "submit" in actions
        assert "softreck.com" in _parse_ir(ir)["url"]

    def test_example_fill_and_submit(self):
        ir = _make_ir("otwórz https://example.com/contact i wypełnij formularz i wyślij")
        assert ir.dsl_kind == "dom"
        actions = _get_actions(ir)
        assert actions == ["goto", "fill_form", "submit"]

    def test_fill_form_without_submit(self):
        ir = _make_ir("otwórz https://example.com/register i wypełnij formularz")
        assert ir.dsl_kind == "dom"
        actions = _get_actions(ir)
        assert "goto" in actions
        assert "fill_form" in actions
        assert "submit" not in actions

    def test_fill_form_wyslij_variant(self):
        ir = _make_ir("otwórz https://example.com/form i wypelnij formularz i wyslij")
        assert ir.dsl_kind == "dom"
        actions = _get_actions(ir)
        assert "fill_form" in actions
        assert "submit" in actions


# ---------------------------------------------------------------------------
# 4. Navigation + fill_form + submit — English queries
# ---------------------------------------------------------------------------

class TestBrowserFillFormEN:

    def test_fill_form_en(self):
        ir = _make_ir("open https://example.com/contact and fill the form and submit")
        assert ir.dsl_kind == "dom"
        actions = _get_actions(ir)
        assert "goto" in actions
        assert "fill_form" in actions
        assert "submit" in actions


# ---------------------------------------------------------------------------
# 4b. Navigation + extract_article — Polish queries
# ---------------------------------------------------------------------------

class TestBrowserExtractArticlePL:

    def test_open_site_and_show_article(self):
        ir = _make_ir("otwórz https://wp.pl i wyświetl artykuł")
        assert ir.dsl_kind == "dom"
        payload = _parse_ir(ir)
        assert payload["dsl"] == "dom_dql.v1"
        actions = _get_actions(ir)
        assert actions[0] == "goto"
        assert "extract_article" in actions


# ---------------------------------------------------------------------------
# 4c. LLM fallback helper parsing (no real Playwright run)
# ---------------------------------------------------------------------------

class TestBrowserLLMSelectorHelpers:

    def test_extract_json_from_fenced_block(self):
        text = """```json
{\"article_link_selectors\": [\"main a[href]\"], \"article_content_selectors\": [\"article\"]}
```"""
        payload = PipelineRunner._extract_json_from_llm_response(text)
        assert isinstance(payload, dict)
        assert payload.get("article_link_selectors") == ["main a[href]"]

    def test_normalize_payload_filters_non_strings(self):
        normalized = PipelineRunner._normalize_llm_article_selector_payload(
            {
                "article_link_selectors": ["a[href]", None, 123, "  ", "h2 a[href]"],
                "article_content_selectors": ["article", "  main article  "],
            }
        )
        assert normalized["article_link_selectors"] == ["a[href]", "h2 a[href]"]
        assert normalized["article_content_selectors"] == ["article", "main article"]


# ---------------------------------------------------------------------------
# 5. URL extraction edge cases
# ---------------------------------------------------------------------------

class TestBrowserURLExtraction:

    def test_url_with_https(self):
        ir = _make_ir("otwórz https://www.example.com/path?q=test")
        payload = _parse_ir(ir)
        assert payload["url"].startswith("https://")
        assert "example.com" in payload["url"]

    def test_url_with_http(self):
        ir = _make_ir("otwórz http://localhost:8080/admin")
        payload = _parse_ir(ir)
        assert "localhost:8080" in payload["url"]

    def test_url_preserves_path(self):
        ir = _make_ir("otwórz https://github.com/wronai/nlp2cmd/issues")
        payload = _parse_ir(ir)
        assert "/wronai/nlp2cmd/issues" in payload["url"]

    def test_domain_without_scheme(self):
        """Domain-like tokens should get https:// prefix."""
        adapter = BrowserAdapter()
        url = adapter._extract_url("otwórz stronę google.com")
        assert url is not None
        assert url.startswith("https://")
        assert "google.com" in url


# ---------------------------------------------------------------------------
# 6. ActionIR structure and metadata
# ---------------------------------------------------------------------------

class TestBrowserActionIRStructure:

    def test_action_id_goto_only(self):
        ir = _make_ir("otwórz https://example.com")
        assert ir.action_id == "dom.goto"

    def test_action_id_fill_form_and_submit(self):
        ir = _make_ir("otwórz https://example.com/contact i wypełnij formularz i wyślij")
        assert "fill_form" in ir.action_id
        assert "submit" in ir.action_id

    def test_dsl_is_valid_json(self):
        ir = _make_ir("otwórz https://example.com i wypełnij formularz")
        payload = _parse_ir(ir)
        assert payload["dsl"] == "dom_dql.v1"

    def test_confidence_positive(self):
        ir = _make_ir("otwórz https://example.com")
        assert ir.confidence > 0

    def test_metadata_contains_url(self):
        ir = _make_ir("otwórz https://mysite.com/form")
        assert "mysite.com" in ir.metadata.get("url", "")


# ---------------------------------------------------------------------------
# 7. Various real-world websites
# ---------------------------------------------------------------------------

class TestBrowserRealWorldSites:

    @pytest.mark.parametrize("url", [
        "https://www.prototypowanie.pl/kontakt/",
        "https://softreck.com/contact/",
        "https://github.com/login",
        "https://stackoverflow.com/questions/ask",
        "https://www.wikipedia.org",
        "https://news.ycombinator.com",
        "https://www.reddit.com/submit",
        "https://gitlab.com/explore",
    ])
    def test_navigate_to_real_site(self, url):
        ir = _make_ir(f"otwórz {url}")
        assert ir.dsl_kind == "dom"
        payload = _parse_ir(ir)
        assert payload["dsl"] == "dom_dql.v1"
        # URL should be preserved (minus potential trailing slash differences)
        domain = url.split("//")[1].split("/")[0]
        assert domain in payload["url"]

    @pytest.mark.parametrize("url,expected_actions", [
        ("https://www.prototypowanie.pl/kontakt/", ["goto", "fill_form", "submit"]),
        ("https://softreck.com/contact/", ["goto", "fill_form", "submit"]),
        ("https://example.com/register", ["goto", "fill_form", "submit"]),
        ("https://myapp.com/feedback", ["goto", "fill_form", "submit"]),
    ])
    def test_fill_and_submit_real_sites(self, url, expected_actions):
        ir = _make_ir(f"otwórz {url} i wypełnij formularz i wyślij")
        assert ir.dsl_kind == "dom"
        actions = _get_actions(ir)
        assert actions == expected_actions


# ---------------------------------------------------------------------------
# 8. BrowserAdapter.validate_syntax
# ---------------------------------------------------------------------------

class TestBrowserValidateSyntax:

    def test_valid_single_action(self):
        adapter = BrowserAdapter()
        payload = json.dumps({"dsl": "dom_dql.v1", "action": "goto", "url": "https://example.com", "params": {}})
        result = adapter.validate_syntax(payload)
        assert result["valid"]

    def test_valid_multi_action(self):
        adapter = BrowserAdapter()
        payload = json.dumps({
            "dsl": "dom_dql.v1",
            "url": "https://example.com",
            "actions": [
                {"action": "goto", "url": "https://example.com"},
                {"action": "fill_form"},
                {"action": "submit"},
            ],
        })
        result = adapter.validate_syntax(payload)
        assert result["valid"]

    def test_invalid_missing_url(self):
        adapter = BrowserAdapter()
        payload = json.dumps({"dsl": "dom_dql.v1", "action": "goto"})
        result = adapter.validate_syntax(payload)
        assert not result["valid"]

    def test_invalid_json(self):
        adapter = BrowserAdapter()
        result = adapter.validate_syntax("not json")
        assert not result["valid"]


# ---------------------------------------------------------------------------
# 9. Article extraction — Polish and English queries
# ---------------------------------------------------------------------------

class TestBrowserArticleExtraction:

    def test_extract_article_polish(self):
        ir = _make_ir("otwórz https://wp.pl i wyświetl artykuł")
        assert ir.dsl_kind == "dom"
        actions = _get_actions(ir)
        assert "goto" in actions
        assert "extract_article" in actions
        assert "wp.pl" in _parse_ir(ir)["url"]

    def test_extract_article_english(self):
        ir = _make_ir("open https://news.ycombinator.com and show article")
        assert ir.dsl_kind == "dom"
        actions = _get_actions(ir)
        assert "goto" in actions
        assert "extract_article" in actions

    def test_extract_article_pokaz_variant(self):
        ir = _make_ir("otwórz https://bbc.com i pokaż artykuł")
        assert ir.dsl_kind == "dom"
        actions = _get_actions(ir)
        assert "extract_article" in actions

    def test_extract_article_action_id(self):
        ir = _make_ir("otwórz https://example.com i wyświetl artykuł")
        assert "extract_article" in ir.action_id

    def test_extract_article_validation(self):
        adapter = BrowserAdapter()
        payload = json.dumps({
            "dsl": "dom_dql.v1",
            "url": "https://example.com",
            "actions": [
                {"action": "goto", "url": "https://example.com"},
                {"action": "extract_article"},
            ],
        })
        result = adapter.validate_syntax(payload)
        assert result["valid"]

    def test_extract_article_metadata(self):
        ir = _make_ir("otwórz https://news.site.com i wyświetl artykuł")
        assert ir.metadata.get("extract_article") is True

    def test_extract_articles_plural_polish(self):
        ir = _make_ir("otwórz https://wp.pl i wyświetl artykuły")
        assert ir.dsl_kind == "dom"
        actions = _get_actions(ir)
        assert "goto" in actions
        assert "extract_article" in actions
        # Check for list mode in action
        payload = _parse_ir(ir)
        extract_action = next((a for a in payload.get("actions", []) if a.get("action") == "extract_article"), None)
        assert extract_action is not None
        assert extract_action.get("mode") == "list"

    def test_extract_articles_plural_english(self):
        ir = _make_ir("open https://news.ycombinator.com and list articles")
        assert ir.dsl_kind == "dom"
        payload = _parse_ir(ir)
        extract_action = next((a for a in payload.get("actions", []) if a.get("action") == "extract_article"), None)
        assert extract_action is not None
        assert extract_action.get("mode") == "list"

    def test_extract_article_with_topic_polish(self):
        ir = _make_ir("otwórz https://wp.pl i wyświetl artykuł o polityce")
        assert ir.dsl_kind == "dom"
        payload = _parse_ir(ir)
        extract_action = next((a for a in payload.get("actions", []) if a.get("action") == "extract_article"), None)
        assert extract_action is not None
        assert extract_action.get("topic") == "polityce"

    def test_extract_article_with_topic_english(self):
        ir = _make_ir("open https://bbc.com and show article about technology")
        assert ir.dsl_kind == "dom"
        payload = _parse_ir(ir)
        extract_action = next((a for a in payload.get("actions", []) if a.get("action") == "extract_article"), None)
        assert extract_action is not None
        assert extract_action.get("topic") == "technology"

    def test_extract_articles_plural_with_topic(self):
        ir = _make_ir("otwórz https://onet.pl i wyświetl artykuły o sporcie")
        assert ir.dsl_kind == "dom"
        payload = _parse_ir(ir)
        extract_action = next((a for a in payload.get("actions", []) if a.get("action") == "extract_article"), None)
        assert extract_action is not None
        assert extract_action.get("mode") == "list"
        assert extract_action.get("topic") == "sporcie"

    def test_list_articles_action_id(self):
        ir = _make_ir("otwórz https://wp.pl i wyświetl artykuły")
        assert "list_articles" in ir.action_id

    def test_extract_article_topic_metadata(self):
        ir = _make_ir("otwórz https://news.com i wyświetl artykuł o ekonomii")
        assert ir.metadata.get("article_topic") == "ekonomii"
        assert ir.metadata.get("extract_mode") is None  # singular mode

    def test_extract_articles_list_metadata(self):
        ir = _make_ir("otwórz https://news.com i wyświetl artykuły")
        assert ir.metadata.get("extract_mode") == "list"


# ---------------------------------------------------------------------------
# 10. PipelineRunner networkidle fallback (unit-level)
# ---------------------------------------------------------------------------

class TestPipelineRunnerFallback:

    def test_run_returns_dom_kind(self):
        """PipelineRunner.run with dsl_kind='dom' should invoke _run_dom_dql."""
        from nlp2cmd.pipeline_runner import PipelineRunner, RunnerResult

        runner = PipelineRunner(headless=True)
        ir = _make_ir("otwórz https://example.com i wypełnij formularz i wyślij")

        # Dry run with confirm=True (submit requires confirmation)
        result = runner.run(ir, dry_run=True, confirm=True)
        assert result.success
        assert result.kind == "dom"
        assert result.data.get("dry_run") is True

    def test_dry_run_single_action(self):
        from nlp2cmd.pipeline_runner import PipelineRunner

        runner = PipelineRunner(headless=True)
        ir = _make_ir("otwórz https://example.com")

        result = runner.run(ir, dry_run=True)
        assert result.success
        assert result.kind == "dom"
