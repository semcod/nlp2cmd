"""Tests for nlp2cmd.nlp.config — Etap 2: YAML config loading."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from nlp2cmd.nlp.config import (
    IntentConfig,
    IntentRegistry,
    ServiceConfig,
    ServiceRegistry,
)


# ── ServiceConfig ───────────────────────────────────────────────────────

class TestServiceConfig:
    def test_to_planner_dict(self):
        cfg = ServiceConfig(
            name="test",
            base_url="https://test.com",
            keys_url="https://test.com/keys",
            key_pattern="sk-test-.*",
            env_var="TEST_API_KEY",
            key_selectors=["code", "pre"],
        )
        d = cfg.to_planner_dict()
        assert d["base_url"] == "https://test.com"
        assert d["keys_url"] == "https://test.com/keys"
        assert d["key_pattern"] == "sk-test-.*"
        assert d["env_var"] == "TEST_API_KEY"
        assert d["key_selectors"] == ["code", "pre"]


# ── ServiceRegistry ─────────────────────────────────────────────────────

class TestServiceRegistry:
    def test_loads_default_services(self):
        registry = ServiceRegistry()
        assert len(registry) >= 6
        assert "openrouter" in registry
        assert "anthropic" in registry
        assert "openai" in registry
        assert "github" in registry
        assert "huggingface" in registry
        assert "replicate" in registry

    def test_get_service(self):
        registry = ServiceRegistry()
        svc = registry.get("openrouter")
        assert svc is not None
        assert svc.env_var == "OPENROUTER_API_KEY"
        assert "openrouter.ai" in svc.keys_url

    def test_get_unknown_service(self):
        registry = ServiceRegistry()
        assert registry.get("nonexistent") is None

    def test_list_names(self):
        registry = ServiceRegistry()
        names = registry.list_names()
        assert isinstance(names, list)
        assert len(names) >= 6
        assert names == sorted(names)

    def test_as_planner_dict(self):
        registry = ServiceRegistry()
        d = registry.as_planner_dict()
        assert isinstance(d, dict)
        assert "openrouter" in d
        assert "keys_url" in d["openrouter"]
        assert "env_var" in d["openrouter"]

    def test_custom_config_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            services_yaml = config_dir / "services.yaml"
            services_yaml.write_text(yaml.dump({
                "services": {
                    "custom_svc": {
                        "display_name": "Custom Service",
                        "base_url": "https://custom.com",
                        "keys_url": "https://custom.com/keys",
                        "env_var": "CUSTOM_KEY",
                    }
                }
            }), encoding="utf-8")

            registry = ServiceRegistry(config_dir=config_dir)
            assert len(registry) == 1
            assert "custom_svc" in registry
            svc = registry.get("custom_svc")
            assert svc.env_var == "CUSTOM_KEY"

    def test_missing_yaml_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = ServiceRegistry(config_dir=Path(tmpdir))
            assert len(registry) == 0

    def test_reload(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            services_yaml = config_dir / "services.yaml"
            services_yaml.write_text(yaml.dump({
                "services": {"svc1": {"env_var": "KEY1"}}
            }), encoding="utf-8")

            registry = ServiceRegistry(config_dir=config_dir)
            assert len(registry) == 1

            services_yaml.write_text(yaml.dump({
                "services": {
                    "svc1": {"env_var": "KEY1"},
                    "svc2": {"env_var": "KEY2"},
                }
            }), encoding="utf-8")
            registry.load()
            assert len(registry) == 2


# ── IntentConfig ────────────────────────────────────────────────────────

class TestIntentConfig:
    def test_get_examples(self):
        cfg = IntentConfig(
            domain="browser", intent="navigate",
            examples={"pl": ["otwórz"], "en": ["open"]},
        )
        assert cfg.get_examples("pl") == ["otwórz"]
        assert cfg.get_examples("en") == ["open"]
        assert cfg.get_examples("de") == ["open"]  # falls back to en

    def test_all_examples(self):
        cfg = IntentConfig(
            domain="browser", intent="navigate",
            examples={"pl": ["otwórz", "wejdź"], "en": ["open", "go to"]},
        )
        all_ex = cfg.all_examples()
        assert len(all_ex) == 4
        assert "otwórz" in all_ex
        assert "go to" in all_ex


# ── IntentRegistry ──────────────────────────────────────────────────────

class TestIntentRegistry:
    def test_loads_default_intents(self):
        registry = IntentRegistry()
        domains = registry.list_domains()
        assert "browser" in domains
        assert "docker" in domains
        assert "shell" in domains
        assert "sql" in domains

    def test_get_intent(self):
        registry = IntentRegistry()
        cfg = registry.get("browser", "navigate")
        assert cfg is not None
        assert cfg.confidence_base == 0.9
        pl_examples = cfg.get_examples("pl")
        assert any("otwórz" in ex for ex in pl_examples)

    def test_get_domain(self):
        registry = IntentRegistry()
        docker_intents = registry.get_domain("docker")
        assert "list" in docker_intents
        assert "run" in docker_intents

    def test_get_unknown(self):
        registry = IntentRegistry()
        assert registry.get("nonexistent", "foo") is None

    def test_all_examples_for_training(self):
        registry = IntentRegistry()
        training_data = registry.all_examples_for_training()
        assert isinstance(training_data, list)
        assert len(training_data) > 50
        assert all("text" in item and "label" in item for item in training_data)
        labels = {item["label"] for item in training_data}
        assert "browser/navigate" in labels
        assert "docker/list" in labels

    def test_custom_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            intents_yaml = config_dir / "intents.yaml"
            intents_yaml.write_text(yaml.dump({
                "custom_domain": {
                    "custom_intent": {
                        "confidence_base": 0.75,
                        "examples": {"en": ["hello", "world"]},
                    }
                }
            }), encoding="utf-8")

            registry = IntentRegistry(config_dir=config_dir)
            assert "custom_domain" in registry.list_domains()
            cfg = registry.get("custom_domain", "custom_intent")
            assert cfg is not None
            assert cfg.confidence_base == 0.75
            assert cfg.get_examples("en") == ["hello", "world"]

    def test_german_examples_present(self):
        registry = IntentRegistry()
        cfg = registry.get("browser", "navigate")
        assert cfg is not None
        de_examples = cfg.get_examples("de")
        assert len(de_examples) > 0
        assert any("öffne" in ex for ex in de_examples)


# ── Integration: action_planner uses YAML config ────────────────────────

class TestActionPlannerIntegration:
    def test_known_services_loaded_from_yaml(self):
        from nlp2cmd.automation.action_planner import KNOWN_SERVICES
        assert len(KNOWN_SERVICES) >= 6
        assert "openrouter" in KNOWN_SERVICES
        assert "keys_url" in KNOWN_SERVICES["openrouter"]

    def test_service_data_matches_yaml(self):
        from nlp2cmd.automation.action_planner import KNOWN_SERVICES
        registry = ServiceRegistry()
        for name in registry.list_names():
            assert name in KNOWN_SERVICES, f"Service {name} missing from KNOWN_SERVICES"
            yaml_data = registry.get(name).to_planner_dict()
            assert KNOWN_SERVICES[name]["env_var"] == yaml_data["env_var"]
