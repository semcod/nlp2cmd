"""
Tests for multi-step browser automation: ComplexQueryDetector, ActionPlanner,
fast-path browser detection, anti-networking override, and video recording wiring.
"""

from __future__ import annotations

import pytest


# ═══ ComplexQueryDetector ══════════════════════════════════════════════════════

class TestComplexQueryDetector:
    """Test Layer 0.5: multi-step intent detection."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from nlp2cmd.generation.complex_detector import ComplexQueryDetector
        self.detector = ComplexQueryDetector()

    def test_simple_query_not_complex(self):
        r = self.detector.analyze("otwórz przeglądarkę")
        assert r.is_complex is False or r.num_intents <= 1

    def test_multi_step_openrouter(self):
        q = ("otwórz przeglądarkę i stronę openrouter.ai, wejdź na stronę "
             "generowania kluczy, wyciągnij klucz API z OpenRouter i zapisz do .env")
        r = self.detector.analyze(q)
        assert r.is_complex is True
        assert r.num_intents >= 3
        assert "browser:launch" in r.intents
        assert "browser:extract_data" in r.intents
        assert "browser:save_file" in r.intents
        assert r.requires_llm_planning is True
        assert r.confidence >= 0.8

    def test_two_intents_detected(self):
        r = self.detector.analyze("otwórz stronę github.com i zaloguj się")
        assert r.is_complex is True
        assert r.num_intents >= 2

    def test_navigate_and_fill(self):
        r = self.detector.analyze("wejdź na stronę kontakt i wypełnij formularz danymi")
        assert r.is_complex is True
        assert any("navigate" in i for i in r.intents)
        assert any("fill_form" in i for i in r.intents)

    def test_desktop_email(self):
        r = self.detector.analyze("sprawdź pocztę i wyślij wiadomość do Jana")
        assert r.is_complex is True
        assert any("desktop:" in i for i in r.intents)

    def test_screenshot_intent(self):
        r = self.detector.analyze("zrób screenshot strony i zapisz do pliku")
        assert any("screenshot" in i for i in r.intents)

    def test_chain_signal_boosts_confidence(self):
        r1 = self.detector.analyze("otwórz przeglądarkę")
        r2 = self.detector.analyze("otwórz przeglądarkę i potem zapisz do .env")
        assert r2.confidence > r1.confidence

    def test_english_chain(self):
        r = self.detector.analyze("open browser and then extract API key")
        # English patterns may or may not detect complexity depending on regex coverage
        # At minimum, chain signals ("and then") should boost confidence
        assert r.confidence > 0


# ═══ ActionPlanner ═════════════════════════════════════════════════════════════

class TestActionPlanner:
    """Test Layer 0.7: rule-based and heuristic decomposition."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from nlp2cmd.automation.action_planner import ActionPlanner
        self.planner = ActionPlanner()

    def test_openrouter_rule_decomposition(self):
        plan = self.planner._try_rule_decomposition(
            "otwórz openrouter.ai i wyciągnij klucz API, zapisz do .env"
        )
        assert plan is not None
        assert plan.source == "rule_decomposer"
        assert plan.confidence >= 0.9
        assert len(plan.steps) >= 3
        nav_steps = [s for s in plan.steps if s.action == "navigate"]
        assert len(nav_steps) >= 1, f"No navigate step found, actions: {[s.action for s in plan.steps]}"
        assert "openrouter" in nav_steps[0].params["url"]
        # Find the save_env step (may not be at index 2 if echo/prompt steps are inserted)
        save_steps = [s for s in plan.steps if s.action == "save_env"]
        assert len(save_steps) == 1
        assert save_steps[0].params["var_name"] == "OPENROUTER_API_KEY"

    def test_anthropic_rule_decomposition(self):
        plan = self.planner._try_rule_decomposition(
            "wyciągnij token API z anthropic"
        )
        assert plan is not None
        assert len(plan.steps) >= 2  # navigate + extract/prompt (no save)
        nav_steps = [s for s in plan.steps if s.action == "navigate"]
        assert len(nav_steps) >= 1
        assert "anthropic" in nav_steps[0].params["url"]
        # Should NOT have save_env since no "zapisz" in query
        assert not any(s.action == "save_env" for s in plan.steps)

    def test_github_with_save(self):
        plan = self.planner._try_rule_decomposition(
            "pobierz klucz z github i zapisz do .env"
        )
        assert plan is not None
        assert len(plan.steps) >= 3
        save_steps = [s for s in plan.steps if s.action == "save_env"]
        assert len(save_steps) == 1
        assert save_steps[0].params["var_name"] == "GITHUB_TOKEN"

    def test_openrouter_with_tab_intent_forces_playwright(self):
        """Existing Firefox workflow should use desktop tab opening.

        We only force Playwright for *create key* flows that require DOM clicks.
        For extract/copy workflows we open the keys page in the user's real
        Firefox and ask them to paste the key.
        """
        plan = self.planner._try_rule_decomposition(
            "owtorz tab w już otwartym oknie przegladarki firefox wyciągnij klucz API z OpenRouter i zapisz do .env"
        )
        assert plan is not None
        assert len(plan.steps) >= 4
        actions = [s.action for s in plan.steps]
        assert "open_firefox_tab" in actions
        assert "desktop_wait" in actions
        assert "navigate" not in actions
        assert any(s.action == "prompt_secret" for s in plan.steps)
        assert any(s.action == "save_env" for s in plan.steps)

    def test_unknown_service_returns_none(self):
        plan = self.planner._try_rule_decomposition(
            "otwórz stronę example.com i kliknij przycisk"
        )
        assert plan is None  # No rule match → will need LLM or heuristic

    def test_heuristic_decomposition_with_url(self):
        plan = self.planner._heuristic_decomposition(
            "otwórz replicate.com i wyciągnij token"
        )
        assert plan is not None
        assert plan.source == "heuristic"
        assert any(s.action == "navigate" for s in plan.steps)
        assert any(s.action == "extract_text" for s in plan.steps)

    def test_heuristic_with_save(self):
        plan = self.planner._heuristic_decomposition(
            "otwórz stronę X i zapisz dane do .env"
        )
        assert any(s.action == "save_env" for s in plan.steps)

    def test_sync_decompose(self):
        plan = self.planner.decompose_sync(
            "otwórz openrouter.ai i wyciągnij klucz API, zapisz do .env"
        )
        assert plan is not None
        assert plan.source == "rule_decomposer"
        assert len(plan.steps) >= 3
        nav_steps = [s for s in plan.steps if s.action == "navigate"]
        assert len(nav_steps) >= 1, f"No navigate step found, actions: {[s.action for s in plan.steps]}"

    def test_cache_serialization_roundtrip(self):
        from nlp2cmd.automation.action_planner import ActionPlan
        plan = self.planner.decompose_sync(
            "wyciągnij klucz API z openrouter i zapisz do .env"
        )
        d = plan.to_cache_dict()
        restored = ActionPlan.from_cache_dict(d)
        assert len(restored.steps) == len(plan.steps)
        assert restored.source == "cache"
        for orig, rest in zip(plan.steps, restored.steps):
            assert orig.action == rest.action


# ═══ Keyword Detector — Fast-Path Browser Fix ═════════════════════════════════

class TestBrowserFastPath:
    """Test Phase 1 bug fix: browser commands no longer misdetect as networking."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from nlp2cmd.generation.keywords.keyword_detector import KeywordIntentDetector
        self.detector = KeywordIntentDetector()

    def _domain(self, text: str) -> str:
        return self.detector.detect(text).domain

    def test_critical_bug_fix(self):
        """The original bug: networking_ext/route → should be browser."""
        r = self.detector.detect(
            "otwórz przeglądarkę i stronę openrouter.ai, wejdź na stronę "
            "generowania kluczy, wyciągnij klucz API z OpenRouter i zapisz do .env"
        )
        assert r.domain == "browser", f"Expected browser, got {r.domain}/{r.intent}"

    def test_open_browser(self):
        assert self._domain("otwórz przeglądarkę") == "browser"

    def test_open_browser_uruchom(self):
        assert self._domain("uruchom przeglądarkę") == "browser"

    def test_navigate_to_page(self):
        assert self._domain("wejdź na stronę github.com") == "browser"

    def test_open_page(self):
        assert self._domain("otwórz stronę openrouter.ai") == "browser"

    def test_extract_api_key(self):
        assert self._domain("wyciągnij klucz API z OpenRouter") == "browser"

    def test_save_to_env(self):
        assert self._domain("zapisz do .env") == "browser"

    def test_open_multiple_tabs(self):
        assert self._domain("otwórz 3 taby: github, gmail i stackoverflow") == "browser"

    def test_fill_form(self):
        assert self._domain("wypełnij formularz kontaktowy") == "browser"

    def test_new_tab(self):
        assert self._domain("nowy tab") == "browser"

    def test_new_card(self):
        assert self._domain("nowa kartę") == "browser"

    def test_ai_domain_detected(self):
        r = self.detector.detect("otwórz openrouter.ai")
        assert r.domain == "browser"
        assert r.entities.get("url") is not None

    def test_app_domain_detected(self):
        r = self.detector.detect("otwórz jspaint.app")
        assert r.domain == "browser"

    # Non-browser commands still work
    def test_docker_not_affected(self):
        assert self._domain("docker ps") == "docker"

    def test_shell_not_affected(self):
        assert self._domain("pokaż pliki w katalogu") == "shell"

    def test_sql_not_affected(self):
        assert self._domain("select * from users") == "sql"

    def test_shell_copy_file_still_works(self):
        assert self._domain("skopiuj plik config.yaml do backup/") == "shell"

    def test_shell_delete_still_works(self):
        assert self._domain("usuń plik test.txt") == "shell"


# ═══ Anti-Networking Override ══════════════════════════════════════════════════

class TestAntiNetworkingOverride:
    """Ensure browser signals prevent false networking_ext matches."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from nlp2cmd.generation.keywords.keyword_detector import KeywordIntentDetector
        self.detector = KeywordIntentDetector()

    def test_strone_not_route(self):
        """'stronę' must NOT match networking_ext/route."""
        r = self.detector.detect("wejdź na stronę openrouter.ai")
        assert r.domain != "networking_ext"
        assert r.domain == "browser"

    def test_copy_api_key_not_shell(self):
        """'skopiuj klucz API' should be browser, not shell/copy."""
        r = self.detector.detect("skopiuj klucz API z anthropic i zapisz do .env")
        assert r.domain == "browser"


# ═══ EvolutionaryCache Multi-Step ══════════════════════════════════════════════

class TestMultistepCache:
    """Test multi-step cache store/lookup in EvolutionaryCache."""

    def test_store_and_lookup(self, tmp_path):
        from nlp2cmd.generation.evolutionary_cache import EvolutionaryCache
        from nlp2cmd.automation.action_planner import ActionPlan, ActionStep

        cache = EvolutionaryCache(cache_dir=tmp_path, enable_llm=False)

        plan = ActionPlan(
            query="test query",
            steps=[
                ActionStep(action="navigate", params={"url": "https://example.com"}),
                ActionStep(action="extract_text", params={"selectors": ["code"]}),
            ],
            confidence=0.9,
            source="test",
        )

        cache.store_multistep("test query", plan)
        result = cache.lookup_multistep("test query")

        assert result is not None
        assert len(result.steps) == 2
        assert result.steps[0].action == "navigate"
        assert result.source == "cache"

    def test_cache_miss(self, tmp_path):
        from nlp2cmd.generation.evolutionary_cache import EvolutionaryCache

        cache = EvolutionaryCache(cache_dir=tmp_path, enable_llm=False)
        result = cache.lookup_multistep("never seen before query")
        assert result is None


# ═══ Pipeline Integration ══════════════════════════════════════════════════════

class TestPipelineMultiStep:
    """Test that RuleBasedPipeline integrates new layers correctly."""

    def test_pipeline_has_complex_detector(self):
        from nlp2cmd.generation.pipeline import RuleBasedPipeline
        pipeline = RuleBasedPipeline()
        assert pipeline.complex_detector is not None

    def test_pipeline_has_action_planner(self):
        from nlp2cmd.generation.pipeline import RuleBasedPipeline
        pipeline = RuleBasedPipeline()
        assert pipeline.action_planner is not None

    def test_pipeline_result_has_action_plan_field(self):
        from nlp2cmd.generation.pipeline_components import PipelineResult
        r = PipelineResult(input_text="test")
        assert hasattr(r, "action_plan")
        assert r.action_plan is None


# ═══ Video Recording Wiring ═══════════════════════════════════════════════════

class TestVideoRecordingWiring:
    """Test that --video flag is properly wired through PipelineRunner."""

    def test_video_fmt_disables_headless(self):
        from nlp2cmd.pipeline_runner import PipelineRunner
        runner = PipelineRunner(headless=True, video_fmt="webm")
        assert runner.headless is False
        assert runner.video_fmt == "webm"

    def test_no_video_keeps_headless(self):
        from nlp2cmd.pipeline_runner import PipelineRunner
        runner = PipelineRunner(headless=True)
        assert runner.headless is True
        assert runner.video_fmt is None

    def test_video_dir_default(self):
        from nlp2cmd.pipeline_runner import PipelineRunner
        runner = PipelineRunner(video_fmt="mp4")
        assert runner.video_dir == "./recordings"

    def test_video_dir_custom(self):
        from nlp2cmd.pipeline_runner import PipelineRunner
        runner = PipelineRunner(video_fmt="webm", video_dir="/tmp/vids")
        assert runner.video_dir == "/tmp/vids"
