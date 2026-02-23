"""
Shell DSL Adapter for NLP2CMD.

Supports Bash, Zsh, Fish, and PowerShell.
"""

from __future__ import annotations

import re
import shlex
import shutil
from dataclasses import dataclass, field
from typing import Any, Optional

from nlp2cmd.adapters.base import AdapterConfig, BaseDSLAdapter, SafetyPolicy
from nlp2cmd.adapters.shell_generators import (
    FileOperationGenerator,
    ProcessManagementGenerator,
    NetworkGenerator,
    SystemMaintenanceGenerator,
    DevelopmentGenerator,
    GitGenerator,
    DockerGenerator,
    TextProcessingGenerator,
)


@dataclass
class ShellSafetyPolicy(SafetyPolicy):
    """Shell-specific safety policy."""

    blocked_commands: list[str] = field(
        default_factory=lambda: [
            "rm -rf /",
            "rm -rf /*",
            "mkfs",
            "dd if=/dev/zero",
            ":(){:|:&};:",  # fork bomb
            "chmod -R 777 /",
            "chown -R",
        ]
    )
    require_confirmation_for: list[str] = field(
        default_factory=lambda: [
            "rm",
            "rmdir",
            "kill",
            "killall",
            "shutdown",
            "reboot",
            "systemctl stop",
            "docker rm",
            "docker rmi",
        ]
    )
    allow_sudo: bool = False
    allow_pipe_to_shell: bool = False
    max_pipe_depth: int = 5
    sandbox_mode: bool = True
    allowed_directories: list[str] = field(default_factory=list)
    blocked_directories: list[str] = field(
        default_factory=lambda: ["/", "/etc", "/boot", "/root", "/sys", "/proc"]
    )


@dataclass
class EnvironmentContext:
    """System environment context."""

    os: str = "linux"
    distro: str = "ubuntu"
    shell: str = "bash"
    available_tools: list[str] = field(default_factory=list)
    environment_variables: dict[str, str] = field(default_factory=dict)


class ShellAdapter(BaseDSLAdapter):
    """
    Shell adapter supporting multiple shell types.

    Transforms natural language into shell commands with
    safety checks and environment awareness.
    """

    DSL_NAME = "shell"
    DSL_VERSION = "1.0"

    SHELL_TYPES = ["bash", "zsh", "fish", "powershell"]

    INTENTS = {
        "file_search": {
            "patterns": [
                "znajdź plik", "znajdź", "znajdz", "szukaj", "find", "search", "locate", 
                "show files", "list files", "pokaż pliki", "wyszukaj pliki", "listuj pliki",
                "znajdź pliki z rozszerzeniem", "znajdź pliki większe niż", "znajdź pliki zmodyfikowane",
                "pokaż zawartość pliku", "wyświetl plik", "cat plik", "odczytaj plik",
                "pokaż ostatnie linii pliku", "tail plik", "koniec pliku"
            ],
            "required_entities": ["target"],
            "optional_entities": ["filters", "scope"],
        },
        "file_operation": {
            "patterns": [
                "kopiuj", "przenieś", "usuń", "utwórz", "copy", "move", "delete", "create", "remove", "compress",
                "skopiuj plik", "przenieś plik", "usuń plik", "usuń wszystkie pliki", "utwórz katalog",
                "zmień nazwę pliku", "mv plik", "rename plik", "zmień nazwę", "zmień nazwę pliku na",
                "sprawdź rozmiar pliku", "rozmiar pliku", "du plik", "wielkość pliku"
            ],
            "required_entities": ["operation", "target"],
            "optional_entities": ["destination"],
        },
        "process_management": {
            "patterns": [
                "zabij proces", "zatrzymaj", "wznów", "uruchom", "kill", "stop", "resume", "start",
                "pokaż procesy", "lista procesów", "show processes", "list processes", "ps",
                "monitoruj procesy", "process monitor", "cpu usage", "memory usage"
            ],
            "required_entities": ["action"],
            "optional_entities": ["process_name", "metric"],
        },
        "network": {
            "patterns": [
                "ping", "sprawdź połączenie", "check connection", "test connection",
                "pokaż porty", "show ports", "netstat", "pobierz plik", "download file",
                "interfejsy sieciowe", "network interfaces", "ip address"
            ],
            "required_entities": ["action"],
            "optional_entities": ["host"],
        },
        "system_maintenance": {
            "patterns": [
                "aktualizuj system", "update system", "czyszczenie systemu", "system cleanup",
                "restart", "shutdown", "logi systemowe", "system logs", "status systemu"
            ],
            "required_entities": ["action"],
            "optional_entities": [],
        },
        "development": {
            "patterns": [
                "uruchom program", "run program", "testuj", "test", "instaluj zależności", "install dependencies",
                "build", "buduj", "lint", "format", "debug"
            ],
            "required_entities": ["action"],
            "optional_entities": ["target"],
        },
        "git": {
            "patterns": [
                "git init", "git clone", "git add", "git commit", "git push", "git pull",
                "git status", "git branch", "git log", "git merge"
            ],
            "required_entities": ["action"],
            "optional_entities": ["branch", "remote"],
        },
        "docker": {
            "patterns": [
                "docker run", "docker stop", "docker rm", "docker ps", "docker images",
                "docker build", "docker logs", "docker exec"
            ],
            "required_entities": ["action"],
            "optional_entities": ["container", "image"],
        },
        "text_processing": {
            "patterns": [
                "grep", "szukaj tekstu", "search text", "zamień tekst", "replace text",
                "licz linie", "count lines", "sortuj", "sort", "uniq"
            ],
            "required_entities": ["action"],
            "optional_entities": ["pattern", "file"],
        },
    }

    def __init__(self, config: Optional[AdapterConfig] = None, environment_context: Optional[EnvironmentContext] = None):
        super().__init__(config)
        self.environment_context = environment_context or EnvironmentContext()
        
        # Initialize generators
        self.file_generator = FileOperationGenerator()
        self.process_generator = ProcessManagementGenerator()
        self.network_generator = NetworkGenerator()
        self.system_generator = SystemMaintenanceGenerator()
        self.dev_generator = DevelopmentGenerator()
        self.git_generator = GitGenerator()
        self.docker_generator = DockerGenerator()
        self.text_generator = TextProcessingGenerator()

    def transform(self, text: str) -> "ExecutionPlan":
        """Transform natural language to shell command."""
        # Detect intent and extract entities
        intent = self._detect_intent(text)
        entities = self._extract_entities(text, intent)
        
        # Generate command
        command = self.generate({"intent": intent, "entities": entities})
        
        # Create execution plan
        from nlp2cmd.core.core_models import ExecutionPlan
        return ExecutionPlan(
            intent=intent,
            entities=entities,
            confidence=self._calculate_confidence(intent, entities),
            metadata={"shell_type": self.environment_context.shell},
            text=text,
            command=command,
        )

    def generate(self, plan: dict[str, Any]) -> str:
        """Generate shell command from execution plan."""
        intent = plan.get("intent", "")
        entities = plan.get("entities", {})
        
        # Route to appropriate generator
        if intent == "file_search":
            return self.file_generator.generate_file_search(entities)
        elif intent == "file_operation":
            return self.file_generator.generate_file_operation(entities)
        elif intent == "process_management":
            return self.process_generator.generate_process_management(entities)
        elif intent == "network":
            return self.network_generator.generate_network(entities)
        elif intent == "system_maintenance":
            return self.system_generator.generate_system_maintenance(entities)
        elif intent == "development":
            return self.dev_generator.generate_development(entities)
        elif intent == "git":
            return self.git_generator.generate_git(entities)
        elif intent == "docker":
            return self.docker_generator.generate_docker(entities)
        elif intent == "text_processing":
            return self.text_generator.generate_text_processing(entities)
        else:
            # Fallback: try to construct command from entities
            return self._generate_generic(entities)

    def _detect_intent(self, text: str) -> str:
        """Detect intent from text."""
        text_lower = text.lower()
        
        for intent, config in self.INTENTS.items():
            for pattern in config["patterns"]:
                if pattern in text_lower:
                    return intent
        
        return "file_search"  # Default intent

    def _extract_entities(self, text: str, intent: str) -> dict[str, Any]:
        """Extract entities from text based on intent."""
        entities = {}
        
        # Extract file paths
        file_patterns = [
            r'([~/][\w/.-]+)',
            r'(\w+\.\w+)',
            r'(".*?")',
        ]
        
        for pattern in file_patterns:
            matches = re.findall(pattern, text)
            if matches:
                entities["target"] = matches[0].strip('"')
                break
        
        # Extract actions
        if intent == "file_operation":
            actions = ["kopiuj", "copy", "przenieś", "move", "usuń", "delete", "remove", 
                      "utwórz", "create", "zmień nazwę", "rename"]
            for action in actions:
                if action in text_lower:
                    entities["operation"] = action
                    break
        
        # Extract process names
        if intent == "process_management":
            words = text.split()
            for word in words:
                if word.isalpha() and len(word) > 2:
                    entities["process_name"] = word
                    break
        
        return entities

    def _calculate_confidence(self, intent: str, entities: dict[str, Any]) -> float:
        """Calculate confidence score."""
        base_confidence = 0.7
        
        # Boost confidence if we have required entities
        intent_config = self.INTENTS.get(intent, {})
        required_entities = intent_config.get("required_entities", [])
        
        for entity in required_entities:
            if entity in entities:
                base_confidence += 0.1
        
        return min(base_confidence, 1.0)

    def _generate_generic(self, entities: dict[str, Any]) -> str:
        """Generate generic command from entities."""
        command = entities.get("command", "")
        args = entities.get("args", [])
        
        if command:
            cmd_parts = [shlex.quote(command)]
            cmd_parts.extend([shlex.quote(str(arg)) for arg in args])
            return " ".join(cmd_parts)
        
        return "# Could not generate command"

    def validate_command(self, command: str) -> dict[str, Any]:
        """Validate shell command for safety."""
        issues = []
        
        # Check for blocked commands
        for blocked in self.config.safety_policy.blocked_commands:
            if blocked in command:
                issues.append(f"Blocked command detected: {blocked}")
        
        # Check for dangerous operations
        dangerous_patterns = [
            r"rm\s+-rf\s+/",
            r":\(\)\{\:\|:&\;\}:",
            r"dd\s+if=/dev/zero",
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, command):
                issues.append(f"Dangerous pattern detected: {pattern}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "requires_confirmation": any(
                req in command for req in self.config.safety_policy.require_confirmation_for
            ),
        }

    def validate_syntax(self, command: str) -> dict[str, Any]:
        """Validate shell command syntax."""
        return self.validate_command(command)

    def _resolve_user_home_path(self, path: str) -> str:
        """Resolve user home path."""
        if path.startswith("~"):
            import os
            return os.path.expanduser(path)
        return path

    def _build_process_context(self, entities: dict[str, Any]) -> dict[str, Any]:
        """Build context for process management."""
        return {
            "process_name": entities.get("process_name", ""),
            "action": entities.get("action", ""),
            "direct_ps": entities.get("action") in ["pokaż", "show", "lista", "list"],
        }
