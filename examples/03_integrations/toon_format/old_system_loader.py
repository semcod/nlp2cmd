"""Shared mock loader for the legacy JSON/YAML command schema system."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


class OldSystemLoader:
    """Mock old system using separate JSON/YAML files."""

    def __init__(self, base_path: Path | None = None):
        self.base_path = base_path or Path(__file__).resolve().parents[3]
        self.cache: Dict[str, Any] = {}

    def load_command_schemas(self) -> Dict[str, Any]:
        """Load command schemas from multiple JSON files."""
        if "commands" in self.cache:
            return self.cache["commands"]

        commands: Dict[str, Any] = {}
        command_schemas_dir = self.base_path / "command_schemas"

        shell_dir = command_schemas_dir / "commands"
        if shell_dir.exists():
            for json_file in shell_dir.glob("*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        commands[data.get("command", json_file.stem)] = data
                except Exception as e:
                    print(f"Error loading {json_file}: {e}")

        browser_dir = command_schemas_dir / "browser"
        if browser_dir.exists():
            for json_file in browser_dir.glob("*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        commands[data.get("name", json_file.stem)] = data
                except Exception as e:
                    print(f"Error loading {json_file}: {e}")

        self.cache["commands"] = commands
        return commands

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if "config" in self.cache:
            return self.cache["config"]

        config_file = self.base_path / "config.yaml"
        config: Dict[str, Any] = {}

        if config_file.exists():
            try:
                import yaml

                with open(config_file, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f) or {}
            except ImportError:
                config = {
                    "schema_generation": {"use_llm": True},
                    "test_commands": [],
                }

        self.cache["config"] = config
        return config

    def get_command_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get specific command by searching loaded schemas."""
        commands = self.load_command_schemas()
        return commands.get(name)

    def search_commands(self, query: str) -> list[dict[str, Any]]:
        """Search commands via linear scan."""
        commands = self.load_command_schemas()
        results: list[dict[str, Any]] = []

        for cmd_name, cmd_data in commands.items():
            search_text = (
                f"{cmd_name} {cmd_data.get('description', '')} "
                f"{' '.join(cmd_data.get('patterns', []))}"
            )
            if query.lower() in search_text.lower():
                results.append({"name": cmd_name, "data": cmd_data})

        return results
