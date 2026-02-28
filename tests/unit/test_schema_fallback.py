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
