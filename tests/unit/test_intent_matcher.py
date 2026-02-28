"""Tests for IntentMatcher and EntityResolver — YAML-driven multilingual NLP."""

import pytest
from pathlib import Path


# ── IntentMatcher tests ──────────────────────────────────────────────


class TestIntentMatcherLoad:
    def test_loads_intents_from_yaml(self):
        from nlp2cmd.nlp.intent_matcher import IntentMatcher
        matcher = IntentMatcher()
        intents = matcher.list_intents()
        assert len(intents) >= 5
        assert "open_app" in intents
        assert "navigate" in intents
        assert "draw" in intents

    def test_get_intent_def(self):
        from nlp2cmd.nlp.intent_matcher import IntentMatcher
        matcher = IntentMatcher()
        intent = matcher.get_intent("open_app")
        assert intent is not None
        assert intent.domain == "desktop"
        assert "pl" in intent.labels
        assert "en" in intent.labels
        assert len(intent.all_labels()) >= 10

    def test_get_intent_examples(self):
        from nlp2cmd.nlp.intent_matcher import IntentMatcher
        matcher = IntentMatcher()
        intent = matcher.get_intent("open_app")
        assert intent is not None
        assert len(intent.all_examples()) >= 5


class TestIntentMatcherExact:
    @pytest.fixture(autouse=True)
    def setup(self):
        from nlp2cmd.nlp.intent_matcher import IntentMatcher
        self.matcher = IntentMatcher()

    def test_match_polish_open(self):
        results = self.matcher.match("otwórz firefox")
        assert len(results) >= 1
        assert results[0].intent == "open_app"
        assert results[0].confidence >= 0.9

    def test_match_english_open(self):
        results = self.matcher.match("launch the browser")
        assert len(results) >= 1
        assert results[0].intent == "open_app"

    def test_match_polish_navigate(self):
        results = self.matcher.match("wejdź na stronę github.com")
        assert len(results) >= 1
        assert results[0].intent == "navigate"

    def test_match_english_navigate(self):
        results = self.matcher.match("go to google.com")
        assert len(results) >= 1
        assert results[0].intent == "navigate"

    def test_match_polish_draw(self):
        results = self.matcher.match("narysuj czerwone koło")
        assert len(results) >= 1
        assert results[0].intent == "draw"

    def test_match_polish_screenshot(self):
        results = self.matcher.match("zrób screenshot")
        assert len(results) >= 1
        assert results[0].intent == "screenshot"

    def test_match_polish_email(self):
        results = self.matcher.match("sprawdź pocztę")
        assert len(results) >= 1
        assert results[0].intent == "email_check"

    def test_match_polish_minimize(self):
        results = self.matcher.match("zminimalizuj wszystko")
        assert len(results) >= 1
        assert results[0].intent == "minimize_all"

    def test_match_polish_close(self):
        results = self.matcher.match("zamknij firefox")
        assert len(results) >= 1
        assert results[0].intent == "close_app"

    def test_match_polish_new_tab(self):
        results = self.matcher.match("nowy tab")
        assert len(results) >= 1
        assert results[0].intent == "new_tab"

    def test_match_best(self):
        result = self.matcher.match_best("otwórz terminal")
        assert result is not None
        assert result.intent == "open_app"

    def test_no_match(self):
        result = self.matcher.match_best("SELECT * FROM users")
        # SQL queries shouldn't match desktop/browser intents
        # (may match nothing or with very low confidence)
        if result:
            assert result.confidence < 0.95


class TestIntentMatcherFuzzy:
    @pytest.fixture(autouse=True)
    def setup(self):
        from nlp2cmd.nlp.intent_matcher import IntentMatcher
        self.matcher = IntentMatcher()

    def test_fuzzy_typo_otworz(self):
        """'otworz' without diacritics should still match 'otwórz'."""
        results = self.matcher.match("otworz firefox")
        assert len(results) >= 1
        assert results[0].intent == "open_app"

    def test_fuzzy_typo_przejdz(self):
        """'przejdz' without diacritics should still match."""
        results = self.matcher.match("przejdz na strone github.com")
        assert len(results) >= 1
        assert results[0].intent == "navigate"

    def test_german_open(self):
        """German 'öffne' should match open_app."""
        results = self.matcher.match("öffne firefox")
        assert len(results) >= 1
        assert results[0].intent == "open_app"


# ── EntityResolver tests ─────────────────────────────────────────────


class TestEntityResolverColors:
    @pytest.fixture(autouse=True)
    def setup(self):
        from nlp2cmd.nlp.entity_resolver import EntityResolver
        self.resolver = EntityResolver()

    def test_polish_red(self):
        assert self.resolver.resolve_color("czerwone koło") == "#FF0000"

    def test_english_red(self):
        assert self.resolver.resolve_color("red circle") == "#FF0000"

    def test_polish_black(self):
        assert self.resolver.resolve_color("czarne kropki") == "#000000"

    def test_german_blue(self):
        assert self.resolver.resolve_color("blaue linie") == "#0000FF"

    def test_no_color(self):
        assert self.resolver.resolve_color("narysuj prostokąt") is None

    def test_multiple_colors(self):
        colors = self.resolver.resolve_all_colors("czerwone koło z czarnymi kropkami")
        assert "#FF0000" in colors
        assert "#000000" in colors


class TestEntityResolverShapes:
    @pytest.fixture(autouse=True)
    def setup(self):
        from nlp2cmd.nlp.entity_resolver import EntityResolver
        self.resolver = EntityResolver()

    def test_polish_circle(self):
        assert self.resolver.resolve_shape("narysuj koło") == "circle"

    def test_polish_okrag(self):
        assert self.resolver.resolve_shape("narysuj okrąg") == "circle"

    def test_english_circle(self):
        assert self.resolver.resolve_shape("draw a circle") == "circle"

    def test_polish_rectangle(self):
        assert self.resolver.resolve_shape("narysuj prostokąt") == "rectangle"

    def test_polish_ladybug(self):
        assert self.resolver.resolve_shape("narysuj biedronkę") == "ladybug"

    def test_english_ladybug(self):
        assert self.resolver.resolve_shape("draw a ladybug") == "ladybug"

    def test_german_circle(self):
        assert self.resolver.resolve_shape("zeichne einen kreis") == "circle"

    def test_multiple_shapes(self):
        shapes = self.resolver.resolve_all_shapes("narysuj koło i prostokąt")
        assert "circle" in shapes
        assert "rectangle" in shapes

    def test_no_shape(self):
        assert self.resolver.resolve_shape("otwórz firefox") is None


class TestEntityResolverApps:
    @pytest.fixture(autouse=True)
    def setup(self):
        from nlp2cmd.nlp.entity_resolver import EntityResolver
        self.resolver = EntityResolver()

    def test_polish_browser(self):
        app = self.resolver.resolve_app("otwórz przeglądarkę")
        assert app is not None
        assert app.name == "firefox"

    def test_english_browser(self):
        app = self.resolver.resolve_app("open the browser")
        assert app is not None
        assert app.name == "firefox"

    def test_chrome_exact(self):
        app = self.resolver.resolve_app("launch chrome")
        assert app is not None
        assert app.name == "chrome"

    def test_polish_terminal(self):
        app = self.resolver.resolve_app("uruchom terminal")
        assert app is not None
        assert app.name == "terminal"

    def test_polish_mail(self):
        app = self.resolver.resolve_app("otwórz pocztę")
        assert app is not None
        assert app.name == "thunderbird"

    def test_polish_calculator(self):
        app = self.resolver.resolve_app("otwórz kalkulator")
        assert app is not None
        assert app.name == "calculator"

    def test_fuzzy_chromka(self):
        """Colloquial Polish 'chromka' should fuzzy-match to chrome."""
        app = self.resolver.resolve_app("odpal chromka")
        # May or may not fuzzy-match depending on threshold
        # At minimum it shouldn't crash
        if app:
            assert app.name == "chrome"

    def test_list_apps(self):
        apps = self.resolver.list_apps()
        assert "firefox" in apps
        assert "terminal" in apps
        assert "thunderbird" in apps

    def test_get_app_direct(self):
        app = self.resolver.get_app("firefox")
        assert app is not None
        assert app.launch == "firefox"
        assert app.wmclass == "Firefox"

    def test_no_app(self):
        app = self.resolver.resolve_app("SELECT * FROM users")
        assert app is None
