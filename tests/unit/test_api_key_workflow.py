"""
Comprehensive tests for the enhanced API key workflow.

Tests:
- ActionPlanner service resolution (all 11 providers)
- Intent detection (create key, new tab, existing Firefox, save .env)
- Session check step generation
- Create-key form filling step generation
- Email client configuration
- Multi-tab decomposition
- Verbose logging output
- Example prompts validation
"""

from __future__ import annotations

import logging
import re
from unittest.mock import patch

import pytest

from nlp2cmd.automation.action_planner import (
    KNOWN_SERVICES,
    SERVICE_ALIASES,
    EMAIL_CLIENTS,
    EMAIL_ALIASES,
    ActionPlan,
    ActionPlanner,
    ActionStep,
)


# ═══════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════

@pytest.fixture
def planner():
    return ActionPlanner()


# ═══════════════════════════════════════════════════════════════════════
# KNOWN_SERVICES configuration tests
# ═══════════════════════════════════════════════════════════════════════

class TestKnownServices:
    """Test that all known services have required configuration."""

    REQUIRED_FIELDS = ["base_url", "keys_url", "key_pattern", "env_var", "key_selectors"]
    EXPECTED_PROVIDERS = [
        "openrouter", "anthropic", "openai", "groq", "mistral",
        "deepseek", "together", "github", "huggingface", "replicate",
    ]

    def test_all_expected_providers_present(self):
        for provider in self.EXPECTED_PROVIDERS:
            assert provider in KNOWN_SERVICES, f"Missing provider: {provider}"

    @pytest.mark.parametrize("provider", EXPECTED_PROVIDERS)
    def test_provider_has_required_fields(self, provider):
        svc = KNOWN_SERVICES[provider]
        for field in self.REQUIRED_FIELDS:
            assert field in svc, f"{provider} missing field: {field}"

    @pytest.mark.parametrize("provider", EXPECTED_PROVIDERS)
    def test_provider_has_login_url(self, provider):
        svc = KNOWN_SERVICES[provider]
        assert "login_url" in svc, f"{provider} missing login_url"
        assert svc["login_url"].startswith("http"), f"{provider} login_url invalid"

    @pytest.mark.parametrize("provider", EXPECTED_PROVIDERS)
    def test_provider_has_session_indicators(self, provider):
        svc = KNOWN_SERVICES[provider]
        assert "session_indicators" in svc, f"{provider} missing session_indicators"
        assert len(svc["session_indicators"]) > 0

    @pytest.mark.parametrize("provider", EXPECTED_PROVIDERS)
    def test_provider_has_login_indicators(self, provider):
        svc = KNOWN_SERVICES[provider]
        assert "login_indicators" in svc, f"{provider} missing login_indicators"
        assert len(svc["login_indicators"]) > 0

    @pytest.mark.parametrize("provider", EXPECTED_PROVIDERS)
    def test_provider_has_create_key_config(self, provider):
        svc = KNOWN_SERVICES[provider]
        assert "create_key" in svc, f"{provider} missing create_key"
        ck = svc["create_key"]
        assert "button_selector" in ck
        assert "submit_selector" in ck
        assert "form_fields" in ck

    @pytest.mark.parametrize("provider", EXPECTED_PROVIDERS)
    def test_provider_key_pattern_is_valid_regex(self, provider):
        svc = KNOWN_SERVICES[provider]
        try:
            re.compile(svc["key_pattern"])
        except re.error as e:
            pytest.fail(f"{provider} key_pattern is invalid regex: {e}")

    @pytest.mark.parametrize("provider", EXPECTED_PROVIDERS)
    def test_provider_env_var_format(self, provider):
        svc = KNOWN_SERVICES[provider]
        env_var = svc["env_var"]
        assert env_var == env_var.upper(), f"{provider} env_var should be uppercase"
        assert re.match(r'^[A-Z][A-Z0-9_]+$', env_var), f"{provider} env_var format invalid"


# ═══════════════════════════════════════════════════════════════════════
# SERVICE_ALIASES tests
# ═══════════════════════════════════════════════════════════════════════

class TestServiceAliases:
    """Test service name resolution via aliases."""

    def test_all_canonical_names_have_self_alias(self):
        for provider in KNOWN_SERVICES:
            assert provider in SERVICE_ALIASES, f"Missing self-alias for: {provider}"
            assert SERVICE_ALIASES[provider] == provider

    def test_claude_resolves_to_anthropic(self):
        assert SERVICE_ALIASES["claude"] == "anthropic"

    def test_gpt_resolves_to_openai(self):
        assert SERVICE_ALIASES["gpt"] == "openai"

    def test_chatgpt_resolves_to_openai(self):
        assert SERVICE_ALIASES["chatgpt"] == "openai"

    def test_hf_resolves_to_huggingface(self):
        assert SERVICE_ALIASES["hf"] == "huggingface"

    def test_together_ai_resolves(self):
        assert SERVICE_ALIASES["together.ai"] == "together"

    def test_deep_seek_resolves(self):
        assert SERVICE_ALIASES["deep seek"] == "deepseek"


# ═══════════════════════════════════════════════════════════════════════
# Email client configuration tests
# ═══════════════════════════════════════════════════════════════════════

class TestEmailClients:
    """Test email client configuration."""

    def test_roundcube_config(self):
        assert "roundcube" in EMAIL_CLIENTS
        rc = EMAIL_CLIENTS["roundcube"]
        assert rc["type"] == "webmail"
        assert "login_selectors" in rc
        assert "user" in rc["login_selectors"]
        assert "pass" in rc["login_selectors"]

    def test_thunderbird_config(self):
        assert "thunderbird" in EMAIL_CLIENTS
        tb = EMAIL_CLIENTS["thunderbird"]
        assert tb["type"] == "desktop"
        assert "shortcuts" in tb
        assert "get_mail" in tb["shortcuts"]
        assert "search" in tb["shortcuts"]

    def test_gmail_config(self):
        assert "gmail" in EMAIL_CLIENTS
        assert EMAIL_CLIENTS["gmail"]["type"] == "webmail"

    def test_outlook_config(self):
        assert "outlook" in EMAIL_CLIENTS
        assert EMAIL_CLIENTS["outlook"]["type"] == "webmail"

    def test_email_aliases(self):
        assert EMAIL_ALIASES["webmail"] == "roundcube"
        assert EMAIL_ALIASES["poczta"] == "thunderbird"
        assert EMAIL_ALIASES["hotmail"] == "outlook"


# ═══════════════════════════════════════════════════════════════════════
# ActionPlanner._resolve_service tests
# ═══════════════════════════════════════════════════════════════════════

class TestResolveService:
    """Test service name resolution from natural language text."""

    def test_resolve_openrouter(self, planner):
        name, svc = planner._resolve_service("pobierz klucz z openrouter")
        assert name == "openrouter"
        assert svc["env_var"] == "OPENROUTER_API_KEY"

    def test_resolve_claude_to_anthropic(self, planner):
        name, svc = planner._resolve_service("wyciągnij klucz claude")
        assert name == "anthropic"

    def test_resolve_chatgpt_to_openai(self, planner):
        name, svc = planner._resolve_service("get chatgpt api key")
        assert name == "openai"

    def test_resolve_groq(self, planner):
        name, svc = planner._resolve_service("pobierz klucz groq")
        assert name == "groq"

    def test_resolve_mistral(self, planner):
        name, svc = planner._resolve_service("klucz api mistral")
        assert name == "mistral"

    def test_resolve_deepseek(self, planner):
        name, svc = planner._resolve_service("deep seek api key")
        assert name == "deepseek"

    def test_resolve_together(self, planner):
        name, svc = planner._resolve_service("together.ai klucz")
        assert name == "together"

    def test_resolve_hf(self, planner):
        name, svc = planner._resolve_service("pobierz hf token")
        assert name == "huggingface"

    def test_resolve_unknown_returns_none(self, planner):
        name, svc = planner._resolve_service("random text without service name")
        assert name is None
        assert svc == {}


# ═══════════════════════════════════════════════════════════════════════
# Intent detection tests
# ═══════════════════════════════════════════════════════════════════════

class TestIntentDetection:
    """Test intent detection helper methods."""

    def test_wants_new_tab_polish(self):
        assert ActionPlanner._wants_new_tab("otwórz tab z kluczem")
        assert ActionPlanner._wants_new_tab("nowa karta w przeglądarce")
        assert ActionPlanner._wants_new_tab("owtorz tab w firefox")

    def test_wants_new_tab_english(self):
        assert ActionPlanner._wants_new_tab("open new tab")

    def test_not_wants_new_tab(self):
        assert not ActionPlanner._wants_new_tab("pobierz klucz api")

    def test_wants_existing_firefox(self):
        assert ActionPlanner._wants_existing_firefox("w już otwartym firefox")
        assert ActionPlanner._wants_existing_firefox("w otwartym oknie firefox")
        assert ActionPlanner._wants_existing_firefox("existing firefox window")

    def test_not_wants_existing_firefox_no_firefox(self):
        assert not ActionPlanner._wants_existing_firefox("otwórz przeglądarkę")

    def test_not_wants_existing_firefox_no_existing(self):
        assert not ActionPlanner._wants_existing_firefox("otwórz firefox")

    def test_wants_create_key_polish(self):
        assert ActionPlanner._wants_create_key("stwórz nowy klucz")
        assert ActionPlanner._wants_create_key("utwórz klucz api")
        assert ActionPlanner._wants_create_key("wygeneruj token")

    def test_wants_create_key_english(self):
        assert ActionPlanner._wants_create_key("create new key")
        assert ActionPlanner._wants_create_key("generate api token")

    def test_not_wants_create_key(self):
        assert not ActionPlanner._wants_create_key("pobierz klucz api")
        assert not ActionPlanner._wants_create_key("wyciągnij klucz")


# ═══════════════════════════════════════════════════════════════════════
# Rule decomposition integration tests
# ═══════════════════════════════════════════════════════════════════════

class TestRuleDecomposition:
    """Test full rule-based decomposition for various scenarios."""

    def test_openrouter_basic_save(self, planner):
        plan = planner.decompose_sync("pobierz klucz API z openrouter i zapisz do .env")
        assert plan.source == "rule_decomposer"
        assert plan.confidence >= 0.9
        actions = [s.action for s in plan.steps]
        assert "navigate" in actions
        assert "prompt_secret" in actions
        assert "save_env" in actions
        assert "check_session" in actions

    def test_openrouter_firefox_tab_forces_playwright(self, planner):
        """ALL API-key workflows use Playwright for DOM access.

        Even when user mentions 'existing Firefox', we override to Playwright
        because DOM access is needed for check_session, extract_key, etc.
        """
        plan = planner.decompose_sync(
            "otwórz tab w już otwartym oknie firefox wyciągnij klucz API z OpenRouter i zapisz do .env"
        )
        actions = [s.action for s in plan.steps]
        assert "navigate" in actions
        assert "open_firefox_tab" not in actions
        assert "desktop_wait" not in actions
        assert "extract_key" in actions
        assert "save_env" in actions

    def test_openrouter_create_key(self, planner):
        plan = planner.decompose_sync("stwórz nowy klucz API na openrouter i zapisz do .env")
        actions = [s.action for s in plan.steps]
        assert "click" in actions  # Click "Create" button
        assert "prompt_secret" in actions
        assert "save_env" in actions
        assert "screenshot" in actions  # Screenshot after creation

    def test_dynamic_schema_mode_avoids_manual_create_templates(self):
        with patch.dict("os.environ", {"NLP2CMD_DYNAMIC_SCHEMA_ONLY": "1"}):
            planner = ActionPlanner()
            plan = planner.decompose_sync("stwórz nowy klucz API na openrouter i zapisz do .env")

        actions = [s.action for s in plan.steps]
        # In dynamic mode we avoid hardcoded create-form templates in initial plan
        assert "extract_key" in actions
        assert "check_clipboard" in actions
        assert "prompt_secret" in actions
        assert "click" not in actions
        assert "screenshot" not in actions

    def test_anthropic_create_key(self, planner):
        plan = planner.decompose_sync("wygeneruj nowy klucz claude i zapisz")
        actions = [s.action for s in plan.steps]
        assert plan.source == "rule_decomposer"
        assert "click" in actions

    def test_groq_basic(self, planner):
        plan = planner.decompose_sync("pobierz klucz API z groq i zapisz do .env")
        actions = [s.action for s in plan.steps]
        assert "navigate" in actions
        assert "save_env" in actions
        # Check that the correct URL is used
        nav_steps = [s for s in plan.steps if s.action == "navigate"]
        assert any("groq.com" in s.params.get("url", "") for s in nav_steps)

    def test_mistral_basic(self, planner):
        plan = planner.decompose_sync("pobierz klucz api mistral i zapisz do .env")
        actions = [s.action for s in plan.steps]
        assert "navigate" in actions
        nav_steps = [s for s in plan.steps if s.action == "navigate"]
        assert any("mistral.ai" in s.params.get("url", "") for s in nav_steps)

    def test_deepseek_basic(self, planner):
        plan = planner.decompose_sync("pobierz klucz API z deepseek i zapisz do .env")
        actions = [s.action for s in plan.steps]
        assert "save_env" in actions

    def test_together_basic(self, planner):
        plan = planner.decompose_sync("pobierz klucz API z together i zapisz do .env")
        assert plan.source == "rule_decomposer"

    def test_github_token(self, planner):
        plan = planner.decompose_sync("wygeneruj nowy token github i zapisz do .env")
        actions = [s.action for s in plan.steps]
        assert "click" in actions
        save_steps = [s for s in plan.steps if s.action == "save_env"]
        assert any(s.params.get("var_name") == "GITHUB_TOKEN" for s in save_steps)

    def test_huggingface_token(self, planner):
        plan = planner.decompose_sync("pobierz token z huggingface i zapisz do .env")
        actions = [s.action for s in plan.steps]
        assert "save_env" in actions
        save_steps = [s for s in plan.steps if s.action == "save_env"]
        assert any(s.params.get("var_name") == "HF_TOKEN" for s in save_steps)

    def test_huggingface_plan_has_section_discovery_step(self, planner):
        plan = planner.decompose_sync("wyciągnij klucz API z huggingface i zapisz do .env")
        discover_steps = [s for s in plan.steps if s.action == "discover_service_section"]
        assert len(discover_steps) >= 1
        ds = discover_steps[0]
        assert ds.params.get("service") == "huggingface"
        assert ds.params.get("section") == "keys"
        assert ds.params.get("keys_url") == "https://huggingface.co/settings/tokens"
        assert ds.params.get("base_url") == "https://huggingface.co"
        assert ds.store_as == "resolved_keys_url"

    def test_openrouter_plan_has_section_discovery_step(self, planner):
        plan = planner.decompose_sync("pobierz klucz API z openrouter")
        actions = [s.action for s in plan.steps]
        assert "discover_service_section" in actions

    def test_no_service_returns_none(self, planner):
        plan = planner._try_rule_decomposition("zrób zrzut ekranu")
        assert plan is None

    def test_no_key_keyword_returns_none(self, planner):
        plan = planner._try_rule_decomposition("otwórz stronę openrouter")
        assert plan is None


# ═══════════════════════════════════════════════════════════════════════
# Session check step tests
# ═══════════════════════════════════════════════════════════════════════

class TestSessionCheckSteps:
    """Test session detection step generation."""

    def test_session_check_included(self, planner):
        plan = planner.decompose_sync("pobierz klucz API z openrouter i zapisz do .env")
        actions = [s.action for s in plan.steps]
        assert "check_session" in actions

    def test_session_check_params(self, planner):
        plan = planner.decompose_sync("pobierz klucz API z openrouter i zapisz do .env")
        check_steps = [s for s in plan.steps if s.action == "check_session"]
        assert len(check_steps) == 1
        params = check_steps[0].params
        assert params["service"] == "openrouter"
        assert "session_indicators" in params
        assert "login_indicators" in params
        assert "login_url" in params
        assert params["login_url"] == "https://openrouter.ai/auth/login"


# ═══════════════════════════════════════════════════════════════════════
# Create key step tests
# ═══════════════════════════════════════════════════════════════════════

class TestCreateKeySteps:
    """Test create-key form filling step generation."""

    def test_create_key_has_click(self, planner):
        plan = planner.decompose_sync("stwórz nowy klucz API na openrouter i zapisz do .env")
        click_steps = [s for s in plan.steps if s.action == "click"]
        assert len(click_steps) >= 1

    def test_create_key_has_form_fill(self, planner):
        plan = planner.decompose_sync("stwórz nowy klucz API na openrouter i zapisz do .env")
        type_steps = [s for s in plan.steps if s.action == "type_text"]
        # OpenRouter has 'name' field with default 'nlp2cmd'
        assert len(type_steps) >= 1
        assert any("nlp2cmd" in s.params.get("text", "") for s in type_steps)

    def test_create_key_has_screenshot(self, planner):
        plan = planner.decompose_sync("stwórz nowy klucz API na openrouter i zapisz do .env")
        screenshot_steps = [s for s in plan.steps if s.action == "screenshot"]
        assert len(screenshot_steps) >= 1

    def test_create_key_has_wait_steps(self, planner):
        plan = planner.decompose_sync("stwórz nowy klucz API na openrouter i zapisz do .env")
        wait_steps = [s for s in plan.steps if s.action == "wait"]
        assert len(wait_steps) >= 2  # After opening form + after generating key


# ═══════════════════════════════════════════════════════════════════════
# Verbose logging tests
# ═══════════════════════════════════════════════════════════════════════

class TestVerboseLogging:
    """Test that verbose echo steps are included in plans."""

    def test_plan_has_summary_echo(self, planner):
        plan = planner.decompose_sync("pobierz klucz API z openrouter i zapisz do .env")
        echo_steps = [s for s in plan.steps if s.action == "echo"]
        assert len(echo_steps) >= 2  # Summary + navigation log + save confirmation
        # First echo should be plan summary
        first_echo = echo_steps[0]
        assert "OPENROUTER" in first_echo.params.get("text", "")

    def test_plan_has_save_verification(self, planner):
        plan = planner.decompose_sync("pobierz klucz API z openrouter i zapisz do .env")
        verify_steps = [s for s in plan.steps if s.action == "verify_env"]
        assert len(verify_steps) >= 1, "Plan should have a verify_env step after save_env"
        assert verify_steps[0].params.get("var_name") == "OPENROUTER_API_KEY"

    def test_create_key_has_detailed_logs(self, planner):
        plan = planner.decompose_sync("stwórz nowy klucz API na openrouter i zapisz do .env")
        echo_steps = [s for s in plan.steps if s.action == "echo"]
        texts = " ".join(s.params.get("text", "") for s in echo_steps)
        assert "Tworzę nowy klucz" in texts or "Pattern" in texts


# ═══════════════════════════════════════════════════════════════════════
# Multi-tab decomposition tests
# ═══════════════════════════════════════════════════════════════════════

class TestMultiTabDecomposition:
    """Test multi-tab pattern decomposition."""

    def test_multi_tab_with_domains(self, planner):
        plan = planner._try_multi_tab_decomposition(
            "otwórz 3 taby: google.com, github.com, openrouter.ai"
        )
        assert plan is not None
        actions = [s.action for s in plan.steps]
        assert actions.count("navigate") == 3

    def test_multi_tab_no_match(self, planner):
        plan = planner._try_multi_tab_decomposition("pobierz klucz api")
        assert plan is None


# ═══════════════════════════════════════════════════════════════════════
# ActionStep / ActionPlan data class tests
# ═══════════════════════════════════════════════════════════════════════

class TestActionDataClasses:
    """Test ActionStep and ActionPlan serialization."""

    def test_action_step_to_dict(self):
        step = ActionStep(
            action="navigate",
            params={"url": "https://example.com"},
            description="Go to example",
            store_as="result",
        )
        d = step.to_dict()
        assert d["action"] == "navigate"
        assert d["params"]["url"] == "https://example.com"
        assert d["description"] == "Go to example"
        assert d["store_as"] == "result"

    def test_action_plan_cache_roundtrip(self):
        plan = ActionPlan(
            query="test query",
            steps=[
                ActionStep(action="navigate", params={"url": "https://test.com"}),
                ActionStep(action="click", params={"selector": "button"}),
            ],
            confidence=0.95,
            source="rule_decomposer",
        )
        cache_dict = plan.to_cache_dict()
        restored = ActionPlan.from_cache_dict(cache_dict)
        assert restored.query == plan.query
        assert len(restored.steps) == len(plan.steps)
        assert restored.steps[0].action == "navigate"
        assert restored.steps[1].action == "click"
        assert restored.source == "cache"
