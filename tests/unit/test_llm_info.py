import os

import pytest

from nlp2cmd.llm.info import LLMInfo, describe_active_llm, format_llm_banner


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Ensure LLM env vars are clean between tests."""
    for key in ("LLM_MODEL", "LITELLM_MODEL", "NLP2CMD_PLANNER_MODEL", "NLP2CMD_LLM_MODEL", "OPENROUTER_API_KEY", "OLLAMA_BASE_URL"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")


def test_default_without_env_vars():
    info = describe_active_llm()
    assert info.model == "qwen2.5:3b"
    assert info.is_default is True
    assert info.source_env is None
    assert info.provider == "Ollama (local)"
    assert info.openrouter_key is False


def test_llm_model_sets_openrouter_provider(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "openrouter/deepseek/deepseek-v4-pro")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    info = describe_active_llm()
    assert info.model == "openrouter/deepseek/deepseek-v4-pro"
    assert info.provider == "OpenRouter"
    assert info.openrouter_key is True
    assert info.source_env == "LLM_MODEL"
    assert info.is_default is False


def test_openrouter_without_key_shows_warning(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "openrouter/deepseek/deepseek-v4-pro")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    banner = format_llm_banner()
    assert "OPENROUTER_API_KEY not set" in banner
    assert "falling back" in banner


def test_banner_contains_model_and_provider(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "ollama/llama3.2")
    banner = format_llm_banner()
    assert "llama3.2" in banner
    assert "Ollama (local)" in banner


def test_ollama_url_in_banner(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://192.168.1.5:11434")
    banner = format_llm_banner()
    assert "192.168.1.5:11434" in banner
