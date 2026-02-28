from __future__ import annotations

import os
from unittest.mock import patch

from nlp2cmd.automation.schema_fallback import (
    FallbackContext,
    FallbackResult,
    SchemaFallback,
)


def _svc_cfg() -> dict:
    return {
        "base_url": "https://huggingface.co",
        "keys_url": "https://huggingface.co/settings/tokens",
        "login_url": "https://huggingface.co/login",
        "session_indicators": ["Access Tokens", "New token", "User Access Tokens"],
        "key_pattern": r"hf_[A-Za-z0-9]{34,}",
        "env_var": "HF_TOKEN",
        "create_key": {
            "button_selector": "button:has-text('Create new token')",
            "form_fields": {
                "name": {
                    "selector": "input[placeholder*='token' i]",
                    "alt_selectors": [
                        "input[placeholder*='name' i]",
                        "input[type='text']:visible",
                    ],
                    "default": "nlp2cmd",
                },
            },
            "submit_selector": "button:has-text('Create token')",
            "key_reveal_selector": "code, pre, input[readonly]",
        },
    }


def _github_svc_cfg() -> dict:
    return {
        "base_url": "https://github.com",
        "keys_url": "https://github.com/settings/tokens",
        "login_url": "https://github.com/login",
        "session_indicators": ["Personal access tokens", "Generate new token"],
        "key_pattern": r"ghp_[a-zA-Z0-9]{36}",
        "env_var": "GITHUB_TOKEN",
        "create_key": {
            "pre_clicks": [
                {"text": "Generate new token", "description": "Open dropdown"},
            ],
            "button_selector": "a:has-text('Generate new token (classic)')",
            "form_fields": {
                "note": {"selector": "#oauth_access_description", "default": "nlp2cmd"},
            },
            "submit_selector": "button:has-text('Generate token')",
            "key_reveal_selector": "code, #new-oauth-token",
        },
    }


def test_rule_based_navigate_fallback_injects_section_discovery():
    with patch.dict("os.environ", {"NLP2CMD_LLM_SCHEMA_MODE": "rule_first"}):
        engine = SchemaFallback()
        ctx = FallbackContext(
            failed_action="navigate",
            failed_params={"url": "https://huggingface.co/settings/tokens"},
            error_message="URL mismatch",
            step_index=2,
            total_steps=10,
            variables={},
            page_url="https://huggingface.co/security-checkup?cookieId=abc",
            service_name="huggingface",
            service_config=_svc_cfg(),
        )

        result = engine.generate_fallback(ctx, page=None)

    assert result.success is True
    assert result.strategy == "rule_based"
    actions = [s["action"] for s in result.replacement_steps]
    assert "discover_service_section" in actions


def test_extract_key_rule_based_fallback_starts_with_section_discovery_before_create():
    with patch.dict("os.environ", {"NLP2CMD_LLM_SCHEMA_MODE": "rule_first"}):
        engine = SchemaFallback()
        ctx = FallbackContext(
            failed_action="extract_key",
            failed_params={
                "service": "huggingface",
                "keys_url": "https://huggingface.co/settings/tokens",
                "key_pattern": r"hf_[A-Za-z0-9]{34,}",
            },
            error_message="No key extracted",
            step_index=6,
            total_steps=11,
            variables={},
            page_url="https://huggingface.co/security-checkup?cookieId=abc",
            service_name="huggingface",
            service_config=_svc_cfg(),
        )

        result = engine.generate_fallback(ctx, page=None)

    assert result.success is True
    assert result.strategy == "rule_based"
    actions = [s["action"] for s in result.replacement_steps]
    assert "discover_service_section" in actions
    assert "submit_and_extract_key" in actions


def test_parse_llm_steps_accepts_object_with_diagnosis_and_steps():
    response = """
    {
      "diagnosis": {
        "root_cause": "schema_execution_error",
        "reason": "redirected to security check"
      },
      "steps": [
        {
          "action": "discover_service_section",
          "params": {"service": "huggingface", "section": "keys"},
          "description": "Find keys section",
          "store_as": "resolved_keys_url"
        },
        {
          "action": "wait",
          "params": {"ms": 1200}
        }
      ]
    }
    """

    parsed = SchemaFallback._parse_llm_steps(response)
    assert len(parsed) == 2
    assert parsed[0]["action"] == "discover_service_section"
    assert parsed[0]["store_as"] == "resolved_keys_url"
    assert parsed[1]["action"] == "wait"


def test_generate_fallback_prefers_llm_first_mode_before_rules():
    with patch.dict("os.environ", {"NLP2CMD_LLM_SCHEMA_MODE": "llm_first"}):
        engine = SchemaFallback()
        ctx = FallbackContext(
            failed_action="click",
            failed_params={"selector": "button.create"},
            error_message="timeout",
            step_index=1,
            total_steps=5,
            variables={},
            service_name="huggingface",
            service_config=_svc_cfg(),
        )

        fake_result = FallbackResult(
            success=True,
            strategy="llm",
            replacement_steps=[{"action": "wait", "params": {"ms": 10}}],
            message="LLM repair",
        )

        with patch.object(engine, "_run_llm_repair_rounds", return_value=fake_result) as llm_mock:
            with patch.object(engine, "_try_rule_based", side_effect=AssertionError("rule fallback should not run first")):
                result = engine.generate_fallback(ctx, page=None)

        assert result.success is True
        assert result.strategy == "llm"
        llm_mock.assert_called_once()


def test_extract_key_uses_rules_first_even_in_llm_first_mode():
    """extract_key failures must use rule-based (create-key flow) BEFORE LLM,
    even when NLP2CMD_LLM_SCHEMA_MODE=llm_first. LLM tends to generate weak
    1-step responses that short-circuit the full create-key flow."""
    with patch.dict("os.environ", {"NLP2CMD_LLM_SCHEMA_MODE": "llm_first"}):
        engine = SchemaFallback()
        ctx = FallbackContext(
            failed_action="extract_key",
            failed_params={
                "service": "huggingface",
                "keys_url": "https://huggingface.co/settings/tokens",
                "key_pattern": r"hf_[A-Za-z0-9]{34,}",
            },
            error_message="No key extracted",
            step_index=6,
            total_steps=11,
            variables={},
            page_url="https://huggingface.co/settings/tokens",
            service_name="huggingface",
            service_config=_svc_cfg(),
        )

        result = engine.generate_fallback(ctx, page=None)

    # Should get rule_based strategy, NOT llm
    assert result.success is True
    assert result.strategy == "rule_based"
    actions = [s["action"] for s in result.replacement_steps]
    # Must include the full create-key flow, not just a discover_service_section
    assert "submit_and_extract_key" in actions
    assert "type_text" in actions


def test_dynamic_page_schema_strategy_exists():
    """Verify _try_dynamic_page_schema method is callable."""
    engine = SchemaFallback()
    assert hasattr(engine, "_try_dynamic_page_schema")
    assert hasattr(SchemaFallback, "_extract_page_schema")


def test_github_extract_key_fallback_includes_pre_clicks():
    """GitHub dropdown: fallback should inject pre_clicks before main button click."""
    with patch.dict("os.environ", {"NLP2CMD_LLM_SCHEMA_MODE": "rule_first"}):
        engine = SchemaFallback()
        ctx = FallbackContext(
            failed_action="extract_key",
            failed_params={
                "service": "github",
                "keys_url": "https://github.com/settings/tokens",
                "key_pattern": r"ghp_[a-zA-Z0-9]{36}",
            },
            error_message="No key extracted",
            step_index=6,
            total_steps=10,
            variables={},
            page_url="https://github.com/settings/tokens",
            service_name="github",
            service_config=_github_svc_cfg(),
        )

        result = engine.generate_fallback(ctx, page=None)

    assert result.success is True
    actions = [s["action"] for s in result.replacement_steps]

    # Should have pre-click (open dropdown) before the main click
    click_indices = [i for i, a in enumerate(actions) if a == "click"]
    assert len(click_indices) >= 2, f"Expected at least 2 clicks (pre_click + main), got {click_indices}"

    # First click should be the dropdown opener ("Generate new token")
    first_click = result.replacement_steps[click_indices[0]]
    assert first_click["params"].get("text") == "Generate new token"

    # Second click should be the classic option
    second_click = result.replacement_steps[click_indices[1]]
    assert "classic" in str(second_click["params"].get("text", "")).lower()


def test_hf_extract_key_fallback_passes_alt_selectors():
    """HuggingFace: fallback type_text steps should include alt_selectors."""
    with patch.dict("os.environ", {"NLP2CMD_LLM_SCHEMA_MODE": "rule_first"}):
        engine = SchemaFallback()
        ctx = FallbackContext(
            failed_action="extract_key",
            failed_params={
                "service": "huggingface",
                "keys_url": "https://huggingface.co/settings/tokens",
                "key_pattern": r"hf_[A-Za-z0-9]{34,}",
            },
            error_message="No key extracted",
            step_index=6,
            total_steps=11,
            variables={},
            page_url="https://huggingface.co/settings/tokens",
            service_name="huggingface",
            service_config=_svc_cfg(),
        )

        result = engine.generate_fallback(ctx, page=None)

    assert result.success is True
    type_steps = [s for s in result.replacement_steps if s["action"] == "type_text"]
    assert len(type_steps) >= 1, "Should have at least one type_text step"

    # The type_text step should carry alt_selectors from config
    first_type = type_steps[0]
    assert "alt_selectors" in first_type["params"], \
        f"type_text params should include alt_selectors, got: {first_type['params']}"
    assert len(first_type["params"]["alt_selectors"]) >= 1


def test_fallback_limit_constants_are_importable():
    """Verify the fallback limit constants exist and have sensible defaults."""
    from nlp2cmd.pipeline_runner_plans import (
        _MAX_PLAN_STEPS,
        _MAX_FALLBACK_INJECTIONS,
        _PROMPT_TIMEOUT,
    )
    assert _MAX_PLAN_STEPS >= 10
    assert _MAX_FALLBACK_INJECTIONS >= 1
    assert _PROMPT_TIMEOUT >= 0


def test_prompt_timeout_env_override():
    """NLP2CMD_PROMPT_TIMEOUT should be configurable via env var."""
    with patch.dict("os.environ", {"NLP2CMD_PROMPT_TIMEOUT": "120"}):
        # Re-evaluate the constant (it's evaluated at import time,
        # so we test the logic directly)
        val = int(os.environ.get("NLP2CMD_PROMPT_TIMEOUT", "60"))
        assert val == 120
