from __future__ import annotations

from nlp2cmd.automation.schema_fallback import (
    FallbackContext,
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
            "button_selector": "button:has-text('New token')",
            "form_fields": {
                "name": {"selector": "input[name='name']", "default": "nlp2cmd"},
            },
            "submit_selector": "button:has-text('Generate')",
            "key_reveal_selector": "code, pre, input[readonly]",
        },
    }


def test_rule_based_navigate_fallback_injects_section_discovery():
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
