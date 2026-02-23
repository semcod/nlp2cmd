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
                "proces", "uruchom", "zatrzymaj", "kill", "start", "stop", "process", "show processes", "top processes",
                "zabij proces", "uruchom proces", "zatrzymaj proces", "restartuj proces", "uruchom ponownie",
                "uruchom w tle", "uruchom skrypt", "zatrzymaj usługę", "uruchom usługę", "status usługi",
                "sprawdź status", "monitor systemowy", "htop", "top",
                # Specific services
                "apache", "apache2", "httpd", "nginx", "mysql", "mariadb", "postgresql", "postgres",
                "docker", "redis", "mongodb", "mongod", "serwer apache", "serwer nginx", "serwer mysql"
            ],
            "required_entities": ["action"],
            "optional_entities": ["process_name", "pid"],
        },
        "process_monitoring": {
            "patterns": [
                "pokaż procesy", "top", "htop", "ps", "monitoruj", "show top", "memory usage", "cpu usage",
                "sprawdź procesy", "działające procesy", "procesy zużywające pamięć", "procesy zużywające cpu",
                "znajdź procesy", "procesy użytkownika", "zombie procesy", "drzewo procesów"
            ],
            "required_entities": [],
            "optional_entities": ["metric", "limit", "filters"],
        },
        "network": {
            "patterns": [
                "ping", "curl", "wget", "port", "sieć", "network", "network status",
                "sprawdź połączenie", "testuj łączność", "pinguj", "sprawdź ping",
                "pokaż adres ip", "adres ip", "ip address", "konfiguracja sieciowa",
                "znajdź porty", "otwarte porty", "porty nasłuchujące", "aktywne połączenia",
                "znajdź urządzenia", "skanuj sieć", "nmap", "prędkość internetu"
            ],
            "required_entities": ["action"],
            "optional_entities": ["host", "port"],
        },
        "disk": {
            "patterns": [
                "dysk", "miejsce", "disk", "space", "df", "du", "disk usage", "show disk",
                "pokaż dysk", "użycie dysku", "miejsce na dysku", "sprawdź miejsce na dysku",
                "sprawdź dysk twardy", "dysk twardy", "zdrowie dysku", "defragmentacja"
            ],
            "required_entities": ["action"],
            "optional_entities": ["path"],
        },
        "archive": {
            "patterns": [
                "spakuj", "rozpakuj", "zip", "tar", "compress", "extract", "archive",
                "utwórz backup", "skompresuj", "archiwum", "backup", "kopia zapasowa",
                "skopiuj backup", "odtwórz z backupu", "integralność backupu", "status backupu",
                "usuń stare backupi", "rozmiar backupu", "harmonogram backup"
            ],
            "required_entities": ["action", "target"],
            "optional_entities": ["destination", "format"],
        },
        "text_processing": {
            "patterns": [
                "grep", "sed", "awk", "filtruj", "wyszukaj tekst", "search text", "find text",
                "znajdź błędy", "wyszukaj błędy", "grep error", "filtruj logi", "przeglądaj logi"
            ],
            "required_entities": ["action", "pattern"],
            "optional_entities": ["file", "options"],
        },
        "system_maintenance": {
            "patterns": [
                "aktualizacja", "upgrade", "czyszczenie", "maintenance", "update", "clean",
                "czyść cache", "aktualizuj system", "uruchom aktualizację", "czyszczenie systemowe",
                "sprawdź logi", "logi systemowe", "oczyszczanie plików tymczasowych", "usuń stare pliki",
                "sprawdź cron", "status cron", "uruchom defragmentację"
            ],
            "required_entities": ["action"],
            "optional_entities": ["target"],
        },
        "development": {
            "patterns": [
                "test", "build", "compile", "run", "debug", "lint", "version", "install",
                "uruchom testy", "testy jednostkowe", "zbuduj projekt", "maven", "npm install",
                "serwer deweloperski", "uruchom serwer", "debugger", "linter", "analiza kodu",
                "logi aplikacji", "czyszczenie cache", "generuj dokumentację", "wersja node"
            ],
            "required_entities": ["action"],
            "optional_entities": ["target", "tool"],
        },
        "security": {
            "patterns": [
                "bezpieczeństwo", "security", "who", "last", "ssh", "permissions", "firewall",
                "kto jest zalogowany", "historia logowań", "sesje ssh", "uprawnienia pliku",
                "pliki suid", "firewall rules", "logi bezpieczeństwa", "podejrzane procesy",
                "zainstalowane pakiety", "użytkownicy systemu"
            ],
            "required_entities": ["action"],
            "optional_entities": ["target"],
        },
        "git": {
            "patterns": ["git", "commit", "push", "pull", "branch", "merge", "show commits", "git status"],
            "required_entities": ["action"],
            "optional_entities": ["branch", "message", "remote"],
        },
        "docker": {
            "patterns": ["docker", "kontener", "obraz", "container", "image", "docker ps"],
            "required_entities": ["action"],
            "optional_entities": ["container_name", "image_name", "options"],
        },
        "user_management": {
            "patterns": [
                "użytkownik", "user", "grupa", "group", "whoami", "who", "last", "id",
                "dodaj użytkownika", "usuń użytkownika", "zmień hasło", "passwd",
                "useradd", "userdel", "usermod", "groupadd", "kim jestem"
            ],
            "required_entities": ["action"],
            "optional_entities": ["username", "group"],
        },
        "hardware_info": {
            "patterns": [
                "cpu", "procesor", "pamięć", "ram", "hardware", "sprzęt", "lscpu", "lspci",
                "lsusb", "lshw", "urządzenia", "devices", "info o cpu", "info o sprzęcie"
            ],
            "required_entities": ["action"],
            "optional_entities": ["device"],
        },
        "disk_management": {
            "patterns": [
                "mount", "umount", "zamontuj", "odmontuj", "partycja", "partition",
                "fdisk", "mkfs", "fsck", "blkid", "lsblk", "dyski", "disks"
            ],
            "required_entities": ["action"],
            "optional_entities": ["device", "mountpoint"],
        },
        "package_management": {
            "patterns": [
                "apt", "apt-get", "dpkg", "yum", "dnf", "pacman", "snap", "flatpak",
                "zainstaluj", "odinstaluj", "aktualizuj pakiety", "install package"
            ],
            "required_entities": ["action"],
            "optional_entities": ["package"],
        },
        "service_management": {
            "patterns": [
                "systemctl", "service", "usługa", "daemon", "cron", "crontab",
                "uruchom usługę", "zatrzymaj usługę", "status usługi", "journalctl"
            ],
            "required_entities": ["action"],
            "optional_entities": ["service_name"],
        },
        "text_file_ops": {
            "patterns": [
                "cat", "head", "tail", "less", "more", "wc", "sort", "uniq", "cut", "tr",
                "pokaż plik", "wyświetl plik", "pierwsze linie", "ostatnie linie",
                "policz linie", "sortuj", "unikalne", "śledź log"
            ],
            "required_entities": ["action"],
            "optional_entities": ["file", "lines"],
        },
        "checksum": {
            "patterns": [
                "md5", "sha256", "sha1", "checksum", "suma kontrolna", "hash",
                "base64", "koduj", "dekoduj", "encode", "decode"
            ],
            "required_entities": ["action"],
            "optional_entities": ["file"],
        },
        "terminal_session": {
            "patterns": [
                "screen", "tmux", "byobu", "sesja", "session", "multiplexer",
                "nowa sesja", "lista sesji", "dołącz do sesji"
            ],
            "required_entities": ["action"],
            "optional_entities": ["session_name"],
        },
    }

    def __init__(
        self,
        shell_type: str = "bash",
        environment_context: Optional[dict[str, Any]] = None,
        safety_policy: Optional[ShellSafetyPolicy] = None,
        config: Optional[AdapterConfig] = None,
    ):
        """
        Initialize Shell adapter.

        Args:
            shell_type: Target shell (bash, zsh, fish, powershell)
            environment_context: System environment information
            safety_policy: Shell-specific safety policy
            config: Adapter configuration
        """
        super().__init__(config, safety_policy or ShellSafetyPolicy())

        if shell_type not in self.SHELL_TYPES:
            raise ValueError(f"Unsupported shell: {shell_type}. Use one of: {self.SHELL_TYPES}")

        self.shell_type = shell_type
        self.env = self._parse_environment_context(environment_context or {})

    def _parse_environment_context(self, ctx: dict[str, Any]) -> EnvironmentContext:
        """Parse environment context."""
        return EnvironmentContext(
            os=ctx.get("os", "linux"),
            distro=ctx.get("distr", "ubuntu"),
            shell=ctx.get("shell", self.shell_type),
            available_tools=ctx.get("available_tools", []),
            environment_variables=ctx.get("environment_variables", {}),
        )

    def _resolve_user_home_path(self, path: Any) -> Any:
        if not isinstance(path, str):
            return path

        path_str = path.strip()
        if not path_str.startswith("~"):
            return path

        if path_str == "~" or path_str.startswith("~/"):
            return path

        m = re.match(r"^~([a-zA-Z0-9_-]+)(/.*)?$", path_str)
        if not m:
            return path

        user = m.group(1)
        rest = m.group(2) or ""

        if str(self.env.os).lower() != "linux":
            return path

        if user == "root":
            return f"/root{rest}"

        try:
            import pwd  # noqa: WPS433

            home = pwd.getpwnam(user).pw_dir
            return f"{home}{rest}"
        except Exception:
            return f"/home/{user}{rest}"

    def generate(self, plan: dict[str, Any]) -> str:
        """Generate shell command from execution plan."""
        intent = plan.get("intent", "")
        entities = plan.get("entities", {})
        
        # Store full text for fallback processing
        if "_full_text" not in entities:
            # Try multiple sources for the full text
            full_text = plan.get("text", "") or plan.get("query", "") or plan.get("input", "") or ""
            entities["_full_text"] = full_text
        
        # Add fallback service detection
        if not entities.get("process_name"):
            full_text = str(entities.get("_full_text", ""))
            for service in ["apache", "apache2", "httpd", "nginx", "mysql", "mariadb", "postgresql", "postgres", "docker", "redis", "mongodb"]:
                if service in full_text.lower():
                    entities["process_name"] = service
                    break
        
        # Add fallback action detection
        if not entities.get("action"):
            full_text = str(entities.get("_full_text", "")).lower()
            if "uruchom" in full_text or "start" in full_text:
                entities["action"] = "uruchom"
            elif "zatrzymaj" in full_text or "stop" in full_text:
                entities["action"] = "zatrzymaj"
            elif "zabij" in full_text or "kill" in full_text:
                entities["action"] = "zabij"
            elif "restartuj" in full_text or "restart" in full_text:
                entities["action"] = "restartuj"

        generators = {
            "file_search": self._generate_file_search,
            "find": self._generate_find,
            "list": self._generate_list,
            "list_dirs": self._generate_list_dirs,
            "file_operation": self._generate_file_operation,
            "process_management": self._generate_process_management,
            "process_monitoring": self._generate_process_monitoring,
            "network": self._generate_network,
            "disk": self._generate_disk,
            "archive": self._generate_archive,
            "text_processing": self._generate_text_processing,
            "search": self._generate_text_processing,  # grep alias
            "grep": self._generate_text_processing,  # grep alias
            "system_maintenance": self._generate_system_maintenance,
            "development": self._generate_development,
            "security": self._generate_security,
            "git": self._generate_git,
            "docker": self._generate_docker,
            "container_management": self._generate_docker,  # alias
            "user_management": self._generate_user_management,
            "hardware_info": self._generate_hardware_info,
            "disk_management": self._generate_disk_management,
            "package_management": self._generate_package_management,
            "service_management": self._generate_service_management,
            "text_file_ops": self._generate_text_file_ops,
            "checksum": self._generate_checksum,
            "terminal_session": self._generate_terminal_session,
            "cat": self._generate_cat,
            "head": self._generate_head_tail,
            "tail": self._generate_head_tail,
            "wc": self._generate_wc,
        }

        generator = generators.get(intent)
        if generator:
            return generator(entities)

        # Fallback: try to construct command from entities
        return self._generate_generic(entities)

    def _generate_file_search(self, entities: dict[str, Any]) -> str:
        """Generate find command."""
        target = entities.get("target", "files")
        filters = entities.get("filters", [])
        scope = entities.get("path", entities.get("scope", "."))
        mtime_filtered = False
        
        # Build find command with entities
        cmd_parts = ["find", scope]
        
        # Add type filter
        if target == "files" or "plik" in str(target).lower():
            cmd_parts.append("-type f")
        elif target == "directories" or "katalog" in str(target).lower():
            cmd_parts.append("-type d")
        
        # Add name pattern
        if "filename" in entities:
            cmd_parts.extend(["-name", f'"{entities["filename"]}"'])
        elif "file_pattern" in entities:
            cmd_parts.extend(["-name", f'"{entities["file_pattern"]}"'])
        
        # Process filters list
        for filter_item in filters:
            if isinstance(filter_item, dict):
                attr = filter_item.get("attribute")
                operator = filter_item.get("operator", ">")
                value = filter_item.get("value")
                
                if attr == "size" and value:
                    # Handle size filter
                    if isinstance(value, str):
                        # Parse string like "100M"
                        m = re.match(r"^(\d+)\s*([a-zA-Z]+)$", value.strip())
                        if m:
                            num = m.group(1)
                            unit = m.group(2).upper()
                            # Convert MB->M, GB->G, KB->k, etc.
                            if unit.startswith('M') and len(unit) > 1:
                                unit = 'M'
                            elif unit.startswith('G') and len(unit) > 1:
                                unit = 'G'
                            elif unit.startswith('K') and len(unit) > 1:
                                unit = 'k'
                            elif unit.startswith('T') and len(unit) > 1:
                                unit = 'T'
                            cmd_parts.append(f"-size +{num}{unit}")
                        else:
                            cmd_parts.append(f"-size +{value}")
                
                elif attr == "mtime" and value:
                    # Handle modification time filter
                    m = re.search(r"(\d+)", str(value))
                    days = m.group(1) if m else str(value)
                    cmd_parts.append(f"-mtime -{days}")
                    mtime_filtered = True
                
                elif attr == "age" and value:
                    # Handle age filter
                    m = re.search(r"(\d+)", str(value))
                    days = m.group(1) if m else str(value)
                    cmd_parts.append(f"-mtime -{days}")
                    mtime_filtered = True
        # Add name pattern
        if "file_pattern" in entities:
            cmd_parts.extend(["-name", f'"*.{entities["file_pattern"]}"'])
        
        # Add size filter
        if "size" in entities and isinstance(entities["size"], dict):
            size_info = entities["size"]
            if "value" in size_info and "unit" in size_info:
                unit = size_info['unit']
                # Convert MB->M, GB->G, KB->k, etc.
                if unit.startswith('M') and len(unit) > 1:
                    unit = 'M'
                elif unit.startswith('G') and len(unit) > 1:
                    unit = 'G'
                elif unit.startswith('K') and len(unit) > 1:
                    unit = 'k'
                elif unit.startswith('T') and len(unit) > 1:
                    unit = 'T'
                cmd_parts.append(f"-size +{size_info['value']}{unit}")
        elif "size" in entities:
            size_str = entities["size"]
            # Parse string like "10MB" and convert
            m = re.match(r"^(\d+)\s*([a-zA-Z]+)$", size_str.strip())
            if m:
                value = m.group(1)
                unit = m.group(2).upper()
                # Convert MB->M, GB->G, KB->k, etc.
                if unit.startswith('M') and len(unit) > 1:
                    unit = 'M'
                elif unit.startswith('G') and len(unit) > 1:
                    unit = 'G'
                elif unit.startswith('K') and len(unit) > 1:
                    unit = 'k'
                elif unit.startswith('T') and len(unit) > 1:
                    unit = 'T'
                cmd_parts.append(f"-size +{value}{unit}")
            else:
                cmd_parts.append(f"-size +{entities['size']}")
        
        # Add age/time filter
        if "age" in entities and isinstance(entities["age"], dict):
            age_info = entities["age"]
            if "value" in age_info and "unit" in age_info:
                unit_map = {"days": "mtime", "hours": "mmin", "minutes": "mmin"}
                time_unit = unit_map.get(age_info["unit"].lower(), "mtime")
                cmd_parts.append(f"-{time_unit} -{age_info['value']}")
                if time_unit == "mtime":
                    mtime_filtered = True
        
        # Handle specific Polish patterns from natural language (fallback)
        elif "rozszerzeniem" in str(target) or "extension" in str(target):
            extension = entities.get("extension", "py")
            cmd_parts.extend(["-name", f"*.{extension}"])
        elif "większe niż" in str(target) or "size" in str(target):
            size = entities.get("size", "100M")
            cmd_parts.append(f"-size +{size}")
        elif "zmodyfikowane" in str(target) or "mtime" in str(target):
            days = entities.get("days", "7")
            m = re.search(r"(\d+)", str(days))
            days = m.group(1) if m else str(days)
            cmd_parts.append(f"-mtime -{days}")
            mtime_filtered = True
        
        if mtime_filtered:
            printf_format = "'%T@\\t%TY-%Tm-%Td %TH:%TM:%TS\\t%s\\t%p\\n'"
            find_cmd = " ".join(cmd_parts + ["-printf", printf_format])
            return f"{find_cmd} | sort -nr | cut -f2-"

        return " ".join(cmd_parts)

    def _generate_find(self, entities: dict[str, Any]) -> str:
        """Generate find command using entities."""
        scope = entities.get("path", entities.get("scope", "."))
        cmd_parts = ["find", scope]
        mtime_filtered = False
        
        # Add type filter
        target = entities.get("target", "files")
        if target == "files" or "plik" in str(target).lower():
            cmd_parts.append("-type f")
        elif target == "directories" or "katalog" in str(target).lower():
            cmd_parts.append("-type d")
        
        # Add name pattern
        if "filename" in entities:
            cmd_parts.extend(["-name", f'"{entities["filename"]}"'])
        elif "file_pattern" in entities:
            cmd_parts.extend(["-name", f"*.{entities['file_pattern']}"])
        
        # Process filters list
        filters = entities.get("filters", [])
        for filter_item in filters:
            if isinstance(filter_item, dict):
                attr = filter_item.get("attribute")
                operator = filter_item.get("operator", ">")
                value = filter_item.get("value")
                
                if attr == "size" and value:
                    # Handle size filter
                    if isinstance(value, str):
                        # Parse string like "100M"
                        m = re.match(r"^(\d+)\s*([a-zA-Z]+)$", value.strip())
                        if m:
                            num = m.group(1)
                            unit = m.group(2).upper()
                            # Convert MB->M, GB->G, KB->k, etc.
                            if unit.startswith('M') and len(unit) > 1:
                                unit = 'M'
                            elif unit.startswith('G') and len(unit) > 1:
                                unit = 'G'
                            elif unit.startswith('K') and len(unit) > 1:
                                unit = 'k'
                            elif unit.startswith('T') and len(unit) > 1:
                                unit = 'T'
                            cmd_parts.append(f"-size +{num}{unit}")
                        else:
                            cmd_parts.append(f"-size +{value}")
                    else:
                        cmd_parts.append(f"-size +{value}")
                
                elif attr == "mtime" and value:
                    # Handle modification time filter
                    m = re.search(r"(\d+)", str(value))
                    days = m.group(1) if m else str(value)
                    cmd_parts.append(f"-mtime -{days}")
                    mtime_filtered = True
                
                elif attr == "age" and value:
                    # Handle age filter
                    m = re.search(r"(\d+)", str(value))
                    days = m.group(1) if m else str(value)
                    cmd_parts.append(f"-mtime -{days}")
                    mtime_filtered = True
        
        # Add size filter
        if "size" in entities and isinstance(entities["size"], dict):
            size_info = entities["size"]
            if "value" in size_info and "unit" in size_info:
                unit = size_info['unit']
                # Convert MB->M, GB->G, KB->k, etc.
                if unit.startswith('M') and len(unit) > 1:
                    unit = 'M'
                elif unit.startswith('G') and len(unit) > 1:
                    unit = 'G'
                elif unit.startswith('K') and len(unit) > 1:
                    unit = 'k'
                elif unit.startswith('T') and len(unit) > 1:
                    unit = 'T'
                cmd_parts.append(f"-size +{size_info['value']}{unit}")
        
        # Handle string size (e.g., "10MB")
        elif "size" in entities and isinstance(entities["size"], str):
            size_str = entities["size"]
            # Parse string like "10MB" and convert
            m = re.match(r"^(\d+)\s*([a-zA-Z]+)$", size_str.strip())
            if m:
                value = m.group(1)
                unit = m.group(2).upper()
                # Convert MB->M, GB->G, KB->k, etc.
                if unit.startswith('M') and len(unit) > 1:
                    unit = 'M'
                elif unit.startswith('G') and len(unit) > 1:
                    unit = 'G'
                elif unit.startswith('K') and len(unit) > 1:
                    unit = 'k'
                elif unit.startswith('T') and len(unit) > 1:
                    unit = 'T'
                cmd_parts.append(f"-size +{value}{unit}")
        
        # Add age/time filter
        if "age" in entities and isinstance(entities["age"], dict):
            age_info = entities["age"]
            if "value" in age_info and "unit" in age_info:
                unit_map = {"days": "mtime", "hours": "mmin", "minutes": "mmin"}
                time_unit = unit_map.get(age_info["unit"].lower(), "mtime")
                cmd_parts.append(f"-{time_unit} -{age_info['value']}")
                if time_unit == "mtime":
                    mtime_filtered = True
        
        # Handle specific Polish patterns from natural language (fallback)
        full_text = str(entities.get("_full_text", "")).lower()
        if "zmodyfikowane" in full_text or "mtime" in str(target).lower():
            days = entities.get("days", "7")
            m = re.search(r"(\d+)", str(days))
            days = m.group(1) if m else str(days)
            cmd_parts.append(f"-mtime -{days}")
            mtime_filtered = True

        if mtime_filtered:
            printf_format = "'%T@\\t%TY-%Tm-%Td %TH:%TM:%TS\\t%s\\t%p\\n'"
            find_cmd = " ".join(cmd_parts + ["-printf", printf_format])
            return f"{find_cmd} | sort -nr | cut -f2-"
        
        return " ".join(cmd_parts)

    @staticmethod
    def _normalize_find_size_value(value: Any) -> str:
        """Normalize values like '10KB'/'1MB' into GNU find -size suffixes (k/M/G/T/c)."""
        s = str(value or "").strip()
        if not s:
            return ""

        m = re.match(r"^(\d+)(?:\s*)([a-zA-Z]+)?$", s)
        if not m:
            return s

        num = m.group(1)
        unit = (m.group(2) or "").strip().upper()

        if unit in {"KB", "K"}:
            return f"{num}k"
        if unit in {"MB", "M"}:
            return f"{num}M"
        if unit in {"GB", "G"}:
            return f"{num}G"
        if unit in {"TB", "T"}:
            return f"{num}T"
        if unit in {"B", "BYTE", "BYTES", "C"}:
            return f"{num}c"

        return s

    def _generate_file_operation(self, entities: dict[str, Any]) -> str:
        """Generate file operation command."""
        operation = entities.get("operation", "")
        target = entities.get("target", "")
        destination = entities.get("destination", "")
        
        # Extract operation from matched keyword if not in entities
        if not operation and "matched_keyword" in entities:
            matched = entities["matched_keyword"]
            if any(kw in matched for kw in ["zainstaluj", "install", "apt install", "apt-get install"]):
                operation = "install"
            elif any(kw in matched for kw in ["dodaj", "pobierz", "wget", "curl"]):
                operation = "download"
        
        # Handle install operations
        if "zainstaluj" in operation or "install" in operation or "apt install" in operation or "apt-get install" in operation:
            package = entities.get("package", target)
            if package:
                return f"sudo apt-get install {package}"
            else:
                return "sudo apt-get install"
        elif "dodaj" in operation or "pobierz" in operation or "wget" in operation or "curl" in operation:
            if target:
                return f"wget {target}"
            else:
                return "wget"
        
        # Handle specific Polish patterns
        if "kopiuj" in operation or "copy" in operation:
            if destination:
                return f"cp {target} {destination}"
            else:
                return f"cp {target} ."
        elif "przenieś" in operation or "move" in operation:
            if destination:
                return f"mv {target} {destination}"
            else:
                return f"mv {target} ."
        elif "usuń" in operation or "delete" in operation or "remove" in operation:
            if "wszystkie" in str(target) or "all" in str(target):
                extension = entities.get("extension", "tmp")
                return f"find . -name '*.{extension}' -delete"
            else:
                return f"rm {target}"
        elif "utwórz" in operation or "create" in operation:
            if "katalog" in str(target) or "directory" in str(target):
                return f"mkdir {target}"
            else:
                return f"touch {target}"
        elif "zmień nazwę" in operation or "rename" in operation or "mv" in operation:
            if "na" in str(target):
                parts = str(target).split(" na ")
                if len(parts) == 2:
                    old_name = parts[0].replace("zmień nazwę pliku", "").strip()
                    new_name = parts[1].strip()
                    return f"mv {old_name} {new_name}"
            return f"mv {target} {destination}"
        elif "rozmiar" in str(target) or "du" in str(target):
            return f"du -h {target}"

        operations = {
            "copy": f"cp -r {shlex.quote(target)} {shlex.quote(destination)}",
            "move": f"mv {shlex.quote(target)} {shlex.quote(destination)}",
            "delete": f"rm -rf {shlex.quote(target)}",
            "create": f"touch {shlex.quote(target)}",
            "mkdir": f"mkdir -p {shlex.quote(target)}",
        }

        return operations.get(operation, f"# Unknown operation: {operation}")

    def _generate_process_management(self, entities: dict[str, Any]) -> str:
        """Generate process management command."""
        context = self._build_process_context(entities)
        if context["direct_ps"]:
            return "ps aux"

        action, process_name = self._resolve_process_action(context)
        service_name, is_service = self._map_service_name(process_name)

        action_str = str(action)
        process_str = str(process_name)

        dispatch = self._dispatch_process_action(
            entities=entities,
            action_str=action_str,
            process_str=process_str,
            pid=context["pid"],
            is_service=is_service,
            service_name=service_name,
        )
        if dispatch is not None:
            return dispatch

        fallback = self._handle_process_fallback(action, process_str, context["pid"])
        if fallback is not None:
            return fallback

        return f"# Process action: {action}"

    def _build_process_context(self, entities: dict[str, Any]) -> dict[str, Any]:
        full_text = str(entities.get("_full_text", "")).lower()
        return {
            "action": entities.get("action", ""),
            "process_name": entities.get("process_name", ""),
            "pid": entities.get("pid", ""),
            "full_text": full_text,
            "direct_ps": self._process_is_direct_ps_request(full_text),
        }

    def _resolve_process_action(self, context: dict[str, Any]) -> tuple[str, str]:
        action = context["action"]
        process_name = context["process_name"]
        if not action and not process_name:
            action, process_name = self._infer_process_action_and_name(context["full_text"])
        return action, process_name

    def _dispatch_process_action(
        self,
        *,
        entities: dict[str, Any],
        action_str: str,
        process_str: str,
        pid: str,
        is_service: bool,
        service_name: str,
    ) -> Optional[str]:
        handlers = self._build_process_handlers(
            entities=entities,
            action_str=action_str,
            process_str=process_str,
            pid=pid,
            is_service=is_service,
            service_name=service_name,
        )
        for predicate, handler in handlers:
            if predicate(action_str):
                return handler()
        return None

    def _build_process_handlers(
        self,
        *,
        entities: dict[str, Any],
        action_str: str,
        process_str: str,
        pid: str,
        is_service: bool,
        service_name: str,
    ) -> tuple[tuple[callable, callable], ...]:
        return (
            (self._process_action_is_kill, lambda: self._handle_process_kill(pid, process_str)),
            (
                self._process_action_is_start,
                lambda: self._handle_process_start(
                    action_str=action_str,
                    process_name=process_str,
                    is_service=is_service,
                    service_name=service_name,
                ),
            ),
            (
                self._process_action_is_stop,
                lambda: self._handle_process_stop(
                    action_str=action_str,
                    process_name=process_str,
                    is_service=is_service,
                    service_name=service_name,
                ),
            ),
            (
                self._process_action_is_restart,
                lambda: self._handle_process_restart(
                    entities=entities,
                    action_str=action_str,
                    process_name=process_str,
                ),
            ),
            (self._process_action_is_status, lambda: self._handle_process_status(entities, action_str, process_str)),
        )

    def _process_is_direct_ps_request(self, full_text: str) -> bool:
        if "ps aux" in full_text or "ps " in full_text:
            return True
        return full_text.strip() == "ps"

    def _infer_process_action_and_name(self, full_text: str) -> tuple[str, str]:
        action = ""
        process_name = ""

        if "uruchom" in full_text or "start" in full_text:
            action = "uruchom"
        elif "zatrzymaj" in full_text or "stop" in full_text:
            action = "zatrzymaj"
        elif "zabij" in full_text or "kill" in full_text:
            action = "zabij"
        elif "restartuj" in full_text or "restart" in full_text:
            action = "restartuj"

        for service in [
            "apache",
            "apache2",
            "httpd",
            "nginx",
            "mysql",
            "mariadb",
            "postgresql",
            "postgres",
            "docker",
            "redis",
            "mongodb",
        ]:
            if service in full_text:
                process_name = service
                break

        return action, process_name

    def _map_service_name(self, process_name: str) -> tuple[str, bool]:
        service_mappings = {
            "apache": "apache2",
            "apache2": "apache2",
            "httpd": "httpd",
            "nginx": "nginx",
            "mysql": "mysql",
            "mariadb": "mariadb",
            "postgresql": "postgresql",
            "postgres": "postgresql",
            "docker": "docker",
            "redis": "redis",
            "mongodb": "mongod",
        }

        key = str(process_name or "").lower()
        if key in service_mappings:
            return service_mappings[key], True
        return process_name, False

    def _process_action_is_kill(self, action: str) -> bool:
        return "zabij" in action or "kill" in action

    def _process_action_is_start(self, action: str) -> bool:
        return "uruchom" in action or "start" in action

    def _process_action_is_stop(self, action: str) -> bool:
        return "zatrzymaj" in action or "stop" in action

    def _process_action_is_restart(self, action: str) -> bool:
        return "restartuj" in action or "restart" in action or "ponownie" in action

    def _process_action_is_status(self, action: str) -> bool:
        return "status" in action

    def _handle_process_kill(self, pid: str, process_name: str) -> str:
        if pid:
            return f"kill -9 {pid}"
        if process_name:
            return f"pkill -f {process_name}"
        return "kill -9 PID"

    def _handle_process_start(self, action_str: str, process_name: str, is_service: bool, service_name: str) -> str:
        if "w tle" in action_str or "background" in action_str:
            if process_name:
                return f"nohup {process_name} &"
            return "nohup python script.py &"
        if "skrypt" in process_name or "script" in process_name:
            return f"./{process_name}"
        if "usługę" in action_str or "service" in action_str or is_service or "serwer" in process_name:
            return f"systemctl start {service_name}"
        if not process_name and ("serwer" in action_str or "usługę" in action_str):
            return "systemctl start"
        if process_name:
            return f"{process_name}"
        return "# Process action"

    def _handle_process_stop(self, action_str: str, process_name: str, is_service: bool, service_name: str) -> str:
        if "usługę" in action_str or "service" in action_str or is_service or "serwer" in process_name:
            return f"systemctl stop {service_name}"
        if process_name:
            return f"pkill -f {process_name}"
        return "stop"

    def _handle_process_restart(self, entities: dict[str, Any], action_str: str, process_name: str) -> str:
        if "serwer" in process_name or "server" in process_name:
            service_name = entities.get("service_name", "apache2")
            return f"systemctl restart {service_name}"
        if "usługę" in action_str or "service" in action_str:
            service_name = entities.get("service_name", process_name)
            return f"systemctl restart {service_name}"
        return f"restart {process_name}"

    def _handle_process_status(self, entities: dict[str, Any], action_str: str, process_name: str) -> str:
        if "usługi" in action_str or "service" in action_str:
            service_name = entities.get("service_name", process_name)
            return f"systemctl status {service_name}"
        return f"status {process_name}"

    def _handle_process_fallback(self, action: str, process_name: str, pid: str) -> str | None:
        if action in ["kill", "stop"]:
            if pid:
                return f"kill {pid}"
            if process_name:
                return f"pkill {shlex.quote(process_name)}"
        if action == "start":
            return f"{process_name} &"
        return None

    def _generate_process_monitoring(self, entities: dict[str, Any]) -> str:
        """Generate process monitoring command."""
        metric = entities.get("metric", "cpu")
        limit = entities.get("limit", 10)
        projection = entities.get("projection", [])
        metric_lower = str(metric).lower()
        metric_str = str(metric)

        handlers = (
            (lambda: self._process_monitoring_is_top(metric_lower), lambda: "top -n 1"),
            (lambda: self._process_monitoring_is_ps(metric_str), lambda: "ps aux"),
            (lambda: self._process_monitoring_is_consumers(metric_str), lambda: self._process_monitoring_consumers(metric_str)),
            (lambda: self._process_monitoring_is_user(metric_str), lambda: self._process_monitoring_user(entities)),
            (lambda: self._process_monitoring_is_zombie(metric_str), lambda: "ps aux | awk '{print $8}' | grep -v '^\\[' | sort | uniq -c"),
            (lambda: self._process_monitoring_is_tree(metric_str), lambda: "pstree"),
            (lambda: self._process_monitoring_is_htop(metric_str), lambda: "htop"),
        )

        for predicate, handler in handlers:
            if predicate():
                return handler()

        sort_flag = self._process_monitoring_sort_flag(metric)
        cmd = self._process_monitoring_base_cmd(sort_flag, limit)
        cmd = self._process_monitoring_apply_projection(cmd, projection, limit)
        return cmd

    def _process_monitoring_is_top(self, metric_lower: str) -> bool:
        return "cpu" in metric_lower and "memory" not in metric_lower and "pamię" not in metric_lower

    def _process_monitoring_is_ps(self, metric_str: str) -> bool:
        return "procesy" in metric_str or "działające" in metric_str

    def _process_monitoring_is_consumers(self, metric_str: str) -> bool:
        return "zużywające" in metric_str

    def _process_monitoring_is_user(self, metric_str: str) -> bool:
        return "użytkownika" in metric_str

    def _process_monitoring_is_zombie(self, metric_str: str) -> bool:
        return "zombie" in metric_str

    def _process_monitoring_is_tree(self, metric_str: str) -> bool:
        return "drzewo" in metric_str or "tree" in metric_str

    def _process_monitoring_is_htop(self, metric_str: str) -> bool:
        return "monitor" in metric_str or "htop" in metric_str

    def _process_monitoring_consumers(self, metric_str: str) -> str:
        if "pamięć" in metric_str or "memory" in metric_str:
            return "ps aux --sort=-%mem | head -10"
        if "cpu" in metric_str:
            return "ps aux --sort=-%cpu | head -10"
        return "ps aux | head -10"

    def _process_monitoring_user(self, entities: dict[str, Any]) -> str:
        user = entities.get("user", "tom")
        return f"ps aux | grep {user}"

    def _process_monitoring_sort_flag(self, metric: Any) -> str:
        if metric == "memory_usage" or metric == "memory":
            return "-%mem"
        return "-%cpu"

    def _process_monitoring_base_cmd(self, sort_flag: str, limit: Any) -> str:
        return f"ps aux --sort={sort_flag} | head -{limit + 1}"

    def _process_monitoring_apply_projection(self, cmd: str, projection: Any, limit: Any) -> str:
        if projection:
            if "process_name" in projection and "memory_percent" in projection:
                cmd += " | tail -{} | awk '{{print $11, $4\"%\"}}'".format(limit)
            elif "process_name" in projection:
                cmd += " | tail -{} | awk '{{print $11}}'".format(limit)
        return cmd

    def _generate_network(self, entities: dict[str, Any]) -> str:
        """Generate network command."""
        action = entities.get("action", "")
        host = entities.get("host", "")
        port = entities.get("port", "")

        action_str = str(action)

        handlers = (
            (lambda: self._network_is_ping(action_str), lambda: self._network_ping(host)),
            (lambda: self._network_is_ports(action_str), lambda: self._network_ports(action_str, port)),
            (lambda: self._network_is_ip(action_str), lambda: "ip addr show"),
            (lambda: self._network_is_config(action_str), lambda: "ifconfig -a"),
            (lambda: self._network_is_nmap(action_str), lambda: "nmap -sn 192.168.1.0/24"),
            (lambda: self._network_is_speedtest(action_str), lambda: "curl -o /dev/null -s -w '%{time_total}' http://speedtest.net"),
            (lambda: self._network_is_connections(action_str), lambda: "ss -tulpn"),
        )

        for predicate, handler in handlers:
            if predicate():
                return handler()

        fallback = self._network_action_fallback(action, host, port)
        if fallback is not None:
            return fallback

        return f"# Network action: {action}"

    def _network_is_ping(self, action_str: str) -> bool:
        return "połączenie" in action_str or "ping" in action_str

    def _network_is_ports(self, action_str: str) -> bool:
        return "port" in action_str or "porty" in action_str

    def _network_is_ip(self, action_str: str) -> bool:
        return "adres" in action_str or "ip" in action_str

    def _network_is_config(self, action_str: str) -> bool:
        return "konfiguracja" in action_str or "config" in action_str

    def _network_is_nmap(self, action_str: str) -> bool:
        return "urządzenia" in action_str or "nmap" in action_str

    def _network_is_speedtest(self, action_str: str) -> bool:
        return "prędkość" in action_str or "speed" in action_str

    def _network_is_connections(self, action_str: str) -> bool:
        return "aktywne" in action_str or "connections" in action_str

    def _network_ping(self, host: str) -> str:
        if host:
            return f"ping -c 4 {host}"
        return "ping -c 4 google.com"

    def _network_ports(self, action_str: str, port: Any) -> str:
        if "otwarte" in action_str or "nasłuchujące" in action_str:
            return "netstat -tuln | grep LISTEN"
        if port:
            return f"lsof -i :{port}"
        return "netstat -tuln"

    def _network_action_fallback(self, action: str, host: str, port: Any) -> str | None:
        if action == "ping":
            return f"ping -c 4 {shlex.quote(host)}"
        if action == "check_port":
            return f"nc -zv {shlex.quote(host)} {port}"
        if action == "curl":
            return f"curl -s {shlex.quote(host)}"
        if action == "wget":
            return f"wget {shlex.quote(host)}"
        if action == "ports":
            return "netstat -tuln"
        return None

    def _generate_disk(self, entities: dict[str, Any]) -> str:
        """Generate disk command."""
        action = entities.get("action", "usage")
        path = entities.get("path", ".")

        action_str = str(action)

        handlers = (
            (lambda: self._disk_is_usage_pattern(action_str), lambda: "df -h"),
            (lambda: self._disk_is_health(action_str), lambda: "fsck -n /dev/sda1"),
            (lambda: self._disk_is_defrag(action_str), lambda: "defrag /dev/sda1"),
        )

        for predicate, handler in handlers:
            if predicate():
                return handler()

        fallback = self._disk_action_fallback(action, path)
        if fallback is not None:
            return fallback

        return f"df -h {path}"

    def _disk_is_usage_pattern(self, action_str: str) -> bool:
        return "dysk" in action_str or "miejsce" in action_str or "usage" in action_str

    def _disk_is_health(self, action_str: str) -> bool:
        return "zdrowie" in action_str or "health" in action_str

    def _disk_is_defrag(self, action_str: str) -> bool:
        return "defragmentacja" in action_str or "defrag" in action_str

    def _disk_action_fallback(self, action: str, path: str) -> str | None:
        if action == "usage":
            return f"df -h {path}"
        if action == "size":
            return f"du -sh {path}"
        if action == "tree":
            return f"tree -L 2 {path}"
        return None

    def _generate_archive(self, entities: dict[str, Any]) -> str:
        """Generate archive command."""
        action = entities.get("action", "")
        target = entities.get("target", "")
        destination = entities.get("destination", "")
        fmt = entities.get("format", "tar.gz")

        action_str = str(action)
        target_str = str(target)

        if self._archive_is_backup(action_str):
            backup_cmd = self._archive_backup_command(action_str, target_str, target, destination)
            if backup_cmd:
                return backup_cmd
        elif self._archive_is_compress(action_str):
            return f"tar -czf archive.tar.gz {target}"
        elif self._archive_is_pack(action_str):
            return f"tar -czf {fmt} {target}"

        fallback = self._archive_action_fallback(action, target, destination, fmt)
        if fallback is not None:
            return fallback

        return f"# Archive action: {action}"

    def _archive_is_backup(self, action_str: str) -> bool:
        return "backup" in action_str or "kopia" in action_str

    def _archive_is_compress(self, action_str: str) -> bool:
        return "skompresuj" in action_str or "compress" in action_str

    def _archive_is_pack(self, action_str: str) -> bool:
        return "spakuj" in action_str or "pack" in action_str

    def _archive_backup_command(
        self,
        action_str: str,
        target_str: str,
        target: str,
        destination: str,
    ) -> str | None:
        if "utwórz" in action_str or "create" in action_str:
            if "katalogu" in target_str or "directory" in target_str:
                return f"tar -czf backup.tar.gz {target}"
            return f"tar -czf backup.tar.gz {target}"
        if "skopiuj" in action_str or "copy" in action_str:
            return f"rsync -av {target} {destination}"
        if "odtwórz" in action_str or "restore" in action_str:
            return f"tar -xzf backup.tar.gz {target}"
        if "integralność" in action_str or "integrity" in action_str:
            return f"md5sum {target}"
        if "status" in action_str:
            return f"ls -la {destination}"
        if "stare" in action_str and "backupi" in target_str:
            return f"find {destination} -mtime +7 -delete"
        if "rozmiar" in target_str or "size" in target_str:
            return f"du -sh {target}"
        if "harmonogram" in action_str or "schedule" in action_str:
            return "crontab -l"
        return None

    def _archive_action_fallback(
        self,
        action: str,
        target: str,
        destination: str,
        fmt: str,
    ) -> str | None:
        if action in ["compress", "pack", "spakuj"]:
            if fmt == "zip":
                return f"zip -r {shlex.quote(destination or target + '.zip')} {shlex.quote(target)}"
            return f"tar -czvf {shlex.quote(destination or target + '.tar.gz')} {shlex.quote(target)}"
        if action in ["extract", "unpack", "rozpakuj"]:
            if target.endswith(".zip"):
                return f"unzip {shlex.quote(target)}"
            return f"tar -xzvf {shlex.quote(target)}"
        return None

    def _generate_text_processing(self, entities: dict[str, Any]) -> str:
        """Generate text processing command."""
        action = entities.get("action", "grep")
        pattern = entities.get("pattern", "")
        file = entities.get("file", "")

        if action == "grep" or action == "search":
            return f"grep -r {shlex.quote(pattern)} {shlex.quote(file) if file else '.'}"
        elif action == "count":
            return f"grep -c {shlex.quote(pattern)} {shlex.quote(file)}"
        elif action == "replace":
            replacement = entities.get("replacement", "")
            return f"sed -i 's/{pattern}/{replacement}/g' {shlex.quote(file)}"

        return f"grep {shlex.quote(pattern)} {shlex.quote(file)}"

    def _generate_git(self, entities: dict[str, Any]) -> str:
        """Generate git command."""
        action = entities.get("action", "")
        branch = entities.get("branch", "")
        message = entities.get("message", "")
        remote = entities.get("remote", "origin")

        commands = {
            "status": "git status",
            "pull": f"git pull {remote} {branch}" if branch else f"git pull {remote}",
            "push": f"git push {remote} {branch}" if branch else f"git push {remote}",
            "commit": f"git commit -m {shlex.quote(message)}" if message else "git commit",
            "add": "git add .",
            "branch": f"git checkout -b {branch}" if branch else "git branch",
            "checkout": f"git checkout {branch}",
            "log": "git log --oneline -10",
            "diff": "git diff",
            "stash": "git stash",
        }

        return commands.get(action, f"git {action}")

    def _generate_system_maintenance(self, entities: dict[str, Any]) -> str:
        """Generate system maintenance command."""
        action = entities.get("action", "")
        target = entities.get("target", "")
        full_text = str(entities.get("_full_text", "")).lower()

        action, target = self._system_maintenance_apply_fallbacks(action, target, full_text)
        action_str = str(action)
        target_str = str(target)

        handlers = (
            (lambda: self._system_maintenance_is_update(action_str, full_text), self._system_maintenance_update_cmd),
            (lambda: self._system_maintenance_is_clean(action_str), lambda: self._system_maintenance_clean_cmd(target_str)),
            (lambda: self._system_maintenance_is_logs(target_str), lambda: "tail -n 50 /var/log/syslog"),
            (lambda: self._system_maintenance_is_cron(target_str), lambda: "systemctl status cron"),
            (lambda: self._system_maintenance_is_defrag(action_str), lambda: "defrag /dev/sda1"),
        )

        for predicate, handler in handlers:
            if predicate():
                return handler()

        return f"# System maintenance: {action}"

    def _system_maintenance_apply_fallbacks(
        self,
        action: str,
        target: str,
        full_text: str,
    ) -> tuple[str, str]:
        new_action = action
        new_target = target

        if not new_action and full_text:
            if "aktualizuj" in full_text or "update" in full_text or "aktualizacja" in full_text:
                new_action = "aktualizuj"
            elif "czyść" in full_text or "clean" in full_text:
                new_action = "czyść"
            elif "sprawdź" in full_text:
                new_action = "sprawdź"

        if not new_target and full_text:
            if "system" in full_text or "systemu" in full_text:
                new_target = "system"
            elif "cache" in full_text:
                new_target = "cache"
            elif "logi" in full_text:
                new_target = "logi"
            elif "cron" in full_text:
                new_target = "cron"

        return new_action, new_target

    def _system_maintenance_is_update(self, action_str: str, full_text: str) -> bool:
        return "aktualizuj" in action_str or "update" in action_str or "aktualizacja" in full_text

    def _system_maintenance_update_cmd(self) -> str:
        return "apt list --upgradable 2>/dev/null | grep -v 'WARNING:' || sudo apt update && sudo apt upgrade -y"

    def _system_maintenance_is_clean(self, action_str: str) -> bool:
        return "czyść" in action_str or "clean" in action_str

    def _system_maintenance_clean_cmd(self, target_str: str) -> str:
        if "cache" in target_str:
            return "apt clean && apt autoclean"
        if "tmp" in target_str:
            return "rm -rf /tmp/*"
        return "apt autoremove"

    def _system_maintenance_is_logs(self, target_str: str) -> bool:
        return "logi" in target_str

    def _system_maintenance_is_cron(self, target_str: str) -> bool:
        return "cron" in target_str

    def _system_maintenance_is_defrag(self, action_str: str) -> bool:
        return "defragmentacja" in action_str

    def _generate_development(self, entities: dict[str, Any]) -> str:
        """Generate development command."""
        action = entities.get("action", "")
        target = entities.get("target", "")
        tool = entities.get("tool", "")

        action_str = str(action)
        target_str = str(target)
        tool_str = str(tool)

        handlers = (
            (lambda: self._development_is_test(action_str), lambda: self._development_test_cmd(tool_str)),
            (lambda: self._development_is_build(action_str), lambda: self._development_build_cmd(tool_str)),
            (lambda: self._development_is_install(action_str), lambda: self._development_install_cmd(tool_str)),
            (lambda: self._development_is_run(action_str, target_str), lambda: self._development_run_cmd(tool_str)),
            (lambda: self._development_is_debug(action_str), lambda: "python -m pdb script.py"),
            (lambda: self._development_is_lint(action_str), lambda: self._development_lint_cmd(tool_str)),
            (lambda: self._development_is_version(action_str), lambda: self._development_version_cmd(tool_str)),
            (lambda: self._development_is_logs(target_str), lambda: "tail -f app.log"),
            (lambda: self._development_is_cache(target_str), lambda: "rm -rf __pycache__"),
            (lambda: self._development_is_docs(target_str), lambda: "sphinx-build -b html docs/"),
        )

        for predicate, handler in handlers:
            if predicate():
                return handler()

        return f"# Development: {action}"

    def _development_is_test(self, action_str: str) -> bool:
        return "test" in action_str

    def _development_is_build(self, action_str: str) -> bool:
        return "build" in action_str

    def _development_is_install(self, action_str: str) -> bool:
        return "install" in action_str

    def _development_is_run(self, action_str: str, target_str: str) -> bool:
        return "run" in action_str or "serwer" in target_str

    def _development_is_debug(self, action_str: str) -> bool:
        return "debug" in action_str

    def _development_is_lint(self, action_str: str) -> bool:
        return "lint" in action_str

    def _development_is_version(self, action_str: str) -> bool:
        return "version" in action_str

    def _development_is_logs(self, target_str: str) -> bool:
        return "logi" in target_str

    def _development_is_cache(self, target_str: str) -> bool:
        return "cache" in target_str

    def _development_is_docs(self, target_str: str) -> bool:
        return "dokumentacja" in target_str

    def _development_test_cmd(self, tool_str: str) -> str:
        if "pytest" in tool_str or "python" in tool_str:
            return "pytest tests/"
        if "maven" in tool_str:
            return "mvn test"
        return "python -m pytest"

    def _development_build_cmd(self, tool_str: str) -> str:
        if "maven" in tool_str:
            return "mvn clean install"
        if "npm" in tool_str:
            return "npm run build"
        return "make build"

    def _development_install_cmd(self, tool_str: str) -> str:
        if "npm" in tool_str:
            return "npm install"
        if "pip" in tool_str:
            return "pip install -r requirements.txt"
        return "apt install"

    def _development_run_cmd(self, tool_str: str) -> str:
        if "django" in tool_str:
            return "python manage.py runserver"
        if "flask" in tool_str:
            return "flask run"
        return "python main.py"

    def _development_lint_cmd(self, tool_str: str) -> str:
        if "python" in tool_str:
            return "pylint src/"
        if "javascript" in tool_str:
            return "eslint ."
        return "lint"

    def _development_version_cmd(self, tool_str: str) -> str:
        if "node" in tool_str:
            return "node --version"
        if "python" in tool_str:
            return "python --version"
        return "version"

    def _generate_security(self, entities: dict[str, Any]) -> str:
        """Generate security command."""
        action = entities.get("action", "")
        target = entities.get("target", "")

        action_str = str(action)
        target_str = str(target)

        handlers = (
            (lambda: self._security_is_who(target_str, action_str), lambda: "who"),
            (lambda: self._security_is_history(target_str), lambda: "last -n 10"),
            (lambda: self._security_is_permissions(target_str), lambda: self._security_permissions_cmd(entities)),
            (lambda: self._security_is_suid(target_str), lambda: "find / -perm -4000 -type f"),
            (lambda: self._security_is_firewall(target_str), lambda: "iptables -L"),
            (lambda: self._security_is_auth_logs(target_str), lambda: "tail -n 100 /var/log/auth.log"),
            (lambda: self._security_is_suspicious(target_str), lambda: "ps aux | grep -v '\\['"),
            (lambda: self._security_is_packages(target_str), lambda: "dpkg -l | grep -i security"),
            (lambda: self._security_is_users(target_str), lambda: "cat /etc/passwd"),
        )

        for predicate, handler in handlers:
            if predicate():
                return handler()

        return f"# Security: {action}"

    def _security_is_who(self, target_str: str, action_str: str) -> bool:
        return "zalogowany" in target_str or "who" in action_str

    def _security_is_history(self, target_str: str) -> bool:
        return "historia" in target_str or "logowań" in target_str

    def _security_is_permissions(self, target_str: str) -> bool:
        return "uprawnienia" in target_str

    def _security_is_suid(self, target_str: str) -> bool:
        return "suid" in target_str

    def _security_is_firewall(self, target_str: str) -> bool:
        return "firewall" in target_str

    def _security_is_auth_logs(self, target_str: str) -> bool:
        return "bezpieczeństwa" in target_str

    def _security_is_suspicious(self, target_str: str) -> bool:
        return "podejrzane" in target_str

    def _security_is_packages(self, target_str: str) -> bool:
        return "pakiety" in target_str

    def _security_is_users(self, target_str: str) -> bool:
        return "użytkownicy" in target_str

    def _security_permissions_cmd(self, entities: dict[str, Any]) -> str:
        file_path = entities.get("file_path", "config.conf")
        return f"ls -la {file_path}"

    def _generate_docker(self, entities: dict[str, Any]) -> str:
        """Generate docker command."""
        action = entities.get("action", "")
        actions = entities.get("actions", [action] if action else [])
        container_name = entities.get("container_name", "")
        image_name = entities.get("image_name", "")
        filters = entities.get("filters", [])

        # Handle complex multi-action scenarios
        if len(actions) > 1:
            return self._generate_docker_script(actions, entities)

        action = actions[0] if actions else "ps"

        commands = {
            "ps": "docker ps",
            "images": "docker images",
            "run": f"docker run -d {shlex.quote(image_name)}",
            "stop": f"docker stop {shlex.quote(container_name)}",
            "start": f"docker start {shlex.quote(container_name)}",
            "restart": f"docker restart {shlex.quote(container_name)}",
            "rm": f"docker rm {shlex.quote(container_name)}",
            "rmi": f"docker rmi {shlex.quote(image_name)}",
            "logs": f"docker logs -f {shlex.quote(container_name)} --tail=100",
            "exec": f"docker exec -it {shlex.quote(container_name)} /bin/bash",
            "build": f"docker build -t {shlex.quote(image_name)} .",
            "pull": f"docker pull {shlex.quote(image_name)}",
            "prune": "docker system prune -f",
        }

        return commands.get(action, f"docker {action}")

    def _generate_docker_script(
        self, actions: list[str], entities: dict[str, Any]
    ) -> str:
        """Generate multi-step docker script."""
        filters = entities.get("filters", [])
        
        script_lines = ["#!/bin/bash", "# WARNING: Review before executing", ""]

        # Build filter condition
        filter_condition = ""
        for f in filters:
            if f.get("attribute") == "running_time":
                # Complex filtering for running time
                filter_condition = "running > 24h"

        if "stop_containers" in actions:
            script_lines.extend([
                "# Find and stop old containers",
                'OLD_CONTAINERS=$(docker ps --filter "status=running" --format "{{.ID}}")',
                "",
                'if [ -n "$OLD_CONTAINERS" ]; then',
                '    echo "Stopping containers..."',
                "    docker stop $OLD_CONTAINERS",
            ])

            if "remove_images" in actions:
                script_lines.extend([
                    "",
                    "    # Get images from stopped containers",
                    "    IMAGES=$(docker inspect --format='{{.Image}}' $OLD_CONTAINERS 2>/dev/null)",
                    '    if [ -n "$IMAGES" ]; then',
                    "        docker rmi $IMAGES 2>/dev/null",
                    "    fi",
                ])

            script_lines.extend([
                "else",
                '    echo "No containers found matching criteria"',
                "fi",
            ])

        return "\n".join(script_lines)

    def _generate_list(self, entities: dict[str, Any]) -> str:
        """Generate list command."""
        path = entities.get("path", ".")
        username = entities.get("username", "")
        target = entities.get("target", "")
        full_text = entities.get("_full_text", "")
        text = entities.get("text", "")
        
        # Extract path from full text if not already found
        if path == "." and full_text:
            # Match paths like /app/test_data, /home/user, etc.
            path_match = re.search(r'(/[\w./-]+)', full_text)
            if path_match:
                path = path_match.group(1)
        
        # Check if listing directories/folders specifically
        is_listing_folders = (
            "folder" in target.lower() or 
            "katalog" in target.lower() or 
            "directories" in target.lower() or
            "folder" in full_text.lower() or
            "katalog" in full_text.lower() or
            "folder" in str(text).lower() or
            "katalog" in str(text).lower()
        )
        
        if is_listing_folders:
            # Clean path by removing 'folders' if present
            if path.endswith("folders"):
                path = path[:-7].strip()
                if not path:
                    path = "~"
            
            # Handle user-specific paths
            if "user" in str(path).lower():
                path = "~"

            path = self._resolve_user_home_path(path)
            return f"find {path} -maxdepth 1 -type d"
        
        # Handle user home directory explicitly
        if path == "~" or path == "~/":
            return "ls -la ~"
        
        # Handle user-specific paths
        if username:
            # Check for user-related keywords
            user_keywords = ["użytkownika", "usera", "user", "użytkownik"]
            if any(keyword in username.lower() for keyword in user_keywords):
                # Default to current user home directory for generic user references
                if username.lower() in ["użytkownika", "usera", "user", "użytkownik", "folders"]:
                    return "ls -la ~"
                else:
                    # Try to extract actual username
                    m = re.search(r'(?:użytkownika|usera|user)\s+([a-zA-Z0-9_-]+)', username, re.IGNORECASE)
                    if m:
                        user = m.group(1)
                        user_home = self._resolve_user_home_path(f"~{user}")
                        return f"ls -la {user_home}"
                    else:
                        return "ls -la ~"
        
        # Default list command
        if "folders" in path.lower():
            clean_path = path.lower().replace("folders", "").strip()
            if not clean_path or clean_path == "~":
                clean_path = "~"
            return f"ls -la {clean_path} | grep '^d'"
        
        # Check if we're listing folders based on target or full text
        text = entities.get("text", "")
        if (target and "folder" in target.lower()) or (full_text and "folder" in full_text.lower()) or "folders" in str(full_text).lower() or "folders" in str(text).lower():
            path = self._resolve_user_home_path(path)
            return f"find {path} -maxdepth 1 -type d"
        
        return f"ls -la {path}"

    def _generate_list_dirs(self, entities: dict[str, Any]) -> str:
        """Generate list directories command."""
        path = entities.get("path", "~")
        full_text = entities.get("_full_text", "")
        
        # Clean path for user folders
        if "user" in str(path).lower() and "folders" in str(path).lower():
            path = "~"
        elif path.endswith("folders"):
            path = path[:-7].strip()
            if not path:
                path = "~"
        
        # Handle user-specific paths
        if "user" in full_text.lower():
            path = "~"

        path = self._resolve_user_home_path(path)
        return f"find {path} -maxdepth 1 -type d"

    def _generate_generic(self, entities: dict[str, Any]) -> str:
        """Generate generic command from entities."""
        command = entities.get("command", "")
        args = entities.get("args", [])

        if command:
            return f"{command} {' '.join(args)}"
        
        # Fallback logic for process management when intent is not detected
        full_text = str(entities.get("_full_text", "")).lower()
        action = entities.get("action", "")
        process_name = entities.get("process_name", "")
        
        # Detect action if not set
        if not action:
            if "uruchom" in full_text or "start" in full_text:
                action = "uruchom"
            elif "zatrzymaj" in full_text or "stop" in full_text:
                action = "zatrzymaj"
            elif "zabij" in full_text or "kill" in full_text:
                action = "zabij"
            elif "restartuj" in full_text or "restart" in full_text:
                action = "restartuj"
        
        # Detect service name if not set
        if not process_name:
            for service in ["apache", "apache2", "httpd", "nginx", "mysql", "mariadb", "postgresql", "postgres", "docker", "redis", "mongodb"]:
                if service in full_text:
                    process_name = service
                    break
        
        # Generate command if we have action and/or process_name
        if action and process_name:
            if "uruchom" in action or "start" in action:
                return f"systemctl start {process_name}"
            elif "zatrzymaj" in action or "stop" in action:
                return f"systemctl stop {process_name}"
            elif "restartuj" in action or "restart" in action:
                return f"systemctl restart {process_name}"
            elif "zabij" in action or "kill" in action:
                return f"pkill -f {process_name}"
        elif action:
            if "uruchom" in action or "start" in action:
                return "systemctl start"
            elif "zatrzymaj" in action or "stop" in action:
                return "systemctl stop"
            elif "restartuj" in action or "restart" in action:
                return "systemctl restart"
            elif "zabij" in action or "kill" in action:
                return "kill -9 PID"

        return "# Could not generate command"

    def _generate_user_management(self, entities: dict[str, Any]) -> str:
        """Generate user management command."""
        action = entities.get("action", "")
        username = entities.get("username", "")
        group = entities.get("group", "")
        full_text = str(entities.get("_full_text", "")).lower()
        
        if "whoami" in full_text or "kim jestem" in full_text:
            return "whoami"
        elif "who" in action or "zalogowani" in full_text:
            return "who"
        elif "last" in action or "historia logowań" in full_text:
            return "last -n 10"
        elif "id" in action or "identyfikator" in full_text:
            if username:
                return f"id {username}"
            return "id"
        elif "groups" in action or "grupy" in full_text:
            if username:
                return f"groups {username}"
            return "groups"
        elif "dodaj" in action or "useradd" in action or "add user" in full_text:
            if username:
                return f"sudo useradd -m {username}"
            return "sudo useradd -m USERNAME"
        elif "usuń" in action or "userdel" in action or "delete user" in full_text:
            if username:
                return f"sudo userdel -r {username}"
            return "sudo userdel -r USERNAME"
        elif "modyfikuj" in action or "usermod" in action:
            if username and group:
                return f"sudo usermod -aG {group} {username}"
            return "sudo usermod -aG GROUP USERNAME"
        elif "groupadd" in action or "dodaj grupę" in full_text:
            if group:
                return f"sudo groupadd {group}"
            return "sudo groupadd GROUP"
        elif "passwd" in action or "hasło" in full_text:
            if username:
                return f"sudo passwd {username}"
            return "passwd"
        elif "su" in action or "przełącz" in full_text:
            if username:
                return f"su - {username}"
            return "su -"
        
        return "whoami"

    def _generate_hardware_info(self, entities: dict[str, Any]) -> str:
        """Generate hardware info command."""
        action = entities.get("action", "")
        device = entities.get("device", "")
        full_text = str(entities.get("_full_text", "")).lower()
        
        if "lscpu" in full_text or "cpu" in action or "procesor" in full_text:
            return "lscpu"
        elif "lspci" in full_text or "pci" in action:
            return "lspci"
        elif "lsusb" in full_text or "usb" in action:
            return "lsusb"
        elif "lshw" in full_text or "hardware" in action or "sprzęt" in full_text:
            return "sudo lshw -short"
        elif "dmidecode" in full_text or "bios" in action:
            return "sudo dmidecode -t system"
        elif "pamięć" in full_text or "ram" in full_text or "memory" in action:
            return "free -h"
        elif "hdparm" in full_text or "dysk twardy" in full_text:
            if device:
                return f"sudo hdparm -I {device}"
            return "sudo hdparm -I /dev/sda"
        elif "smartctl" in full_text or "smart" in action or "zdrowie" in full_text:
            if device:
                return f"sudo smartctl -a {device}"
            return "sudo smartctl -a /dev/sda"
        
        return "lscpu"

    def _generate_disk_management(self, entities: dict[str, Any]) -> str:
        """Generate disk management command."""
        action = entities.get("action", "")
        device = entities.get("device", "")
        mountpoint = entities.get("mountpoint", "")
        full_text = str(entities.get("_full_text", "")).lower()
        
        if "lsblk" in full_text or "lista dysków" in full_text or "list disks" in action:
            return "lsblk -f"
        elif "blkid" in full_text or "uuid" in full_text:
            return "blkid"
        elif "mount" in action and "umount" not in action:
            if device and mountpoint:
                return f"sudo mount {device} {mountpoint}"
            return "mount"
        elif "umount" in action or "odmontuj" in full_text:
            if mountpoint:
                return f"sudo umount {mountpoint}"
            elif device:
                return f"sudo umount {device}"
            return "sudo umount /mnt"
        elif "fdisk" in full_text or "partycja" in full_text:
            if device:
                return f"sudo fdisk -l {device}"
            return "sudo fdisk -l"
        elif "mkfs" in full_text or "formatuj" in full_text:
            if device:
                return f"sudo mkfs.ext4 {device}"
            return "sudo mkfs.ext4 /dev/sdX"
        elif "fsck" in full_text or "sprawdź" in full_text:
            if device:
                return f"sudo fsck {device}"
            return "sudo fsck /dev/sda1"
        
        return "lsblk"

    def _generate_package_management(self, entities: dict[str, Any]) -> str:
        """Generate package management command."""
        action = entities.get("action", "")
        package = entities.get("package", "")
        full_text = str(entities.get("_full_text", "")).lower()
        
        # Detect package manager from context
        if "yum" in full_text:
            pm = "yum"
        elif "dnf" in full_text:
            pm = "dnf"
        elif "pacman" in full_text:
            pm = "pacman"
        elif "snap" in full_text:
            pm = "snap"
        elif "flatpak" in full_text:
            pm = "flatpak"
        elif "pip" in full_text:
            pm = "pip"
        else:
            pm = "apt"
        
        if "zainstaluj" in action or "install" in action:
            if pm == "apt":
                return f"sudo apt install -y {package}" if package else "sudo apt install -y PACKAGE"
            elif pm == "yum":
                return f"sudo yum install -y {package}" if package else "sudo yum install -y PACKAGE"
            elif pm == "dnf":
                return f"sudo dnf install -y {package}" if package else "sudo dnf install -y PACKAGE"
            elif pm == "pacman":
                return f"sudo pacman -S {package}" if package else "sudo pacman -S PACKAGE"
            elif pm == "snap":
                return f"sudo snap install {package}" if package else "sudo snap install PACKAGE"
            elif pm == "pip":
                return f"pip install {package}" if package else "pip install PACKAGE"
        elif "odinstaluj" in action or "remove" in action or "usuń" in action:
            if pm == "apt":
                return f"sudo apt remove {package}" if package else "sudo apt remove PACKAGE"
            elif pm == "pip":
                return f"pip uninstall {package}" if package else "pip uninstall PACKAGE"
        elif "aktualizuj" in action or "update" in action or "upgrade" in action:
            if pm == "apt":
                return "sudo apt update && sudo apt upgrade -y"
            elif pm == "yum":
                return "sudo yum update -y"
            elif pm == "dnf":
                return "sudo dnf update -y"
            elif pm == "pacman":
                return "sudo pacman -Syu"
        elif "szukaj" in action or "search" in action:
            if pm == "apt":
                return f"apt search {package}" if package else "apt search PATTERN"
        elif "lista" in action or "list" in action:
            if pm == "apt":
                return "apt list --installed"
            elif pm == "pip":
                return "pip list"
        
        return "sudo apt update"

    def _generate_service_management(self, entities: dict[str, Any]) -> str:
        """Generate service management command."""
        action = entities.get("action", "")
        service_name = entities.get("service_name", "")
        full_text = str(entities.get("_full_text", "")).lower()
        
        # Detect service from text
        if not service_name:
            for svc in ["nginx", "apache2", "mysql", "postgresql", "docker", "ssh", "redis"]:
                if svc in full_text:
                    service_name = svc
                    break
        
        if "status" in action or "status" in full_text:
            if service_name:
                return f"systemctl status {service_name}"
            return "systemctl status"
        elif "uruchom" in action or "start" in action:
            if service_name:
                return f"sudo systemctl start {service_name}"
            return "sudo systemctl start SERVICE"
        elif "zatrzymaj" in action or "stop" in action:
            if service_name:
                return f"sudo systemctl stop {service_name}"
            return "sudo systemctl stop SERVICE"
        elif "restart" in action or "restartuj" in full_text:
            if service_name:
                return f"sudo systemctl restart {service_name}"
            return "sudo systemctl restart SERVICE"
        elif "enable" in action or "włącz" in full_text:
            if service_name:
                return f"sudo systemctl enable {service_name}"
            return "sudo systemctl enable SERVICE"
        elif "disable" in action or "wyłącz" in full_text:
            if service_name:
                return f"sudo systemctl disable {service_name}"
            return "sudo systemctl disable SERVICE"
        elif "lista" in action or "list" in action:
            return "systemctl list-units --type=service"
        elif "journalctl" in full_text or "logi" in full_text:
            if service_name:
                return f"journalctl -u {service_name} -f"
            return "journalctl -f"
        elif "crontab" in full_text or "cron" in action:
            if "edytuj" in full_text or "edit" in action:
                return "crontab -e"
            return "crontab -l"
        
        return "systemctl list-units --type=service"

    def _generate_text_file_ops(self, entities: dict[str, Any]) -> str:
        """Generate text file operations command."""
        action = entities.get("action", "")
        file = entities.get("file", "")
        lines = entities.get("lines", "10")
        full_text = str(entities.get("_full_text", "")).lower()
        
        if "cat" in action or "pokaż plik" in full_text or "wyświetl plik" in full_text:
            if file:
                return f"cat {file}"
            return "cat FILE"
        elif "head" in action or "pierwsze linie" in full_text:
            if file:
                return f"head -n {lines} {file}"
            return f"head -n {lines} FILE"
        elif "tail" in action or "ostatnie linie" in full_text:
            if "śledź" in full_text or "follow" in action:
                if file:
                    return f"tail -f {file}"
                return "tail -f FILE"
            if file:
                return f"tail -n {lines} {file}"
            return f"tail -n {lines} FILE"
        elif "less" in action:
            if file:
                return f"less {file}"
            return "less FILE"
        elif "wc" in action or "policz" in full_text:
            if "linie" in full_text or "lines" in action:
                if file:
                    return f"wc -l {file}"
                return "wc -l FILE"
            if file:
                return f"wc {file}"
            return "wc FILE"
        elif "sort" in action or "sortuj" in full_text:
            if file:
                return f"sort {file}"
            return "sort FILE"
        elif "uniq" in action or "unikalne" in full_text:
            if file:
                return f"sort {file} | uniq"
            return "sort FILE | uniq"
        elif "cut" in action:
            if file:
                return f"cut -d',' -f1 {file}"
            return "cut -d',' -f1 FILE"
        elif "tr" in action:
            return "tr '[:lower:]' '[:upper:]'"
        
        return "cat FILE"

    def _generate_checksum(self, entities: dict[str, Any]) -> str:
        """Generate checksum/encoding command."""
        action = entities.get("action", "")
        file = entities.get("file", "")
        full_text = str(entities.get("_full_text", "")).lower()
        
        if "md5" in action or "md5" in full_text:
            if file:
                return f"md5sum {file}"
            return "md5sum FILE"
        elif "sha256" in action or "sha256" in full_text:
            if file:
                return f"sha256sum {file}"
            return "sha256sum FILE"
        elif "sha1" in action or "sha1" in full_text:
            if file:
                return f"sha1sum {file}"
            return "sha1sum FILE"
        elif "base64" in action or "base64" in full_text:
            if "dekoduj" in full_text or "decode" in action:
                if file:
                    return f"base64 -d {file}"
                return "base64 -d FILE"
            if file:
                return f"base64 {file}"
            return "base64 FILE"
        elif "xxd" in action or "hex" in full_text:
            if file:
                return f"xxd {file}"
            return "xxd FILE"
        
        return "md5sum FILE"

    def _generate_terminal_session(self, entities: dict[str, Any]) -> str:
        """Generate terminal multiplexer command."""
        action = entities.get("action", "")
        session_name = entities.get("session_name", "")
        full_text = str(entities.get("_full_text", "")).lower()
        
        # Detect tool
        if "screen" in full_text:
            tool = "screen"
        elif "byobu" in full_text:
            tool = "byobu"
        else:
            tool = "tmux"
        
        if "nowa" in action or "new" in action or "utwórz" in full_text:
            if tool == "tmux":
                if session_name:
                    return f"tmux new -s {session_name}"
                return "tmux new -s session"
            elif tool == "screen":
                if session_name:
                    return f"screen -S {session_name}"
                return "screen -S session"
        elif "lista" in action or "list" in action:
            if tool == "tmux":
                return "tmux ls"
            elif tool == "screen":
                return "screen -ls"
        elif "dołącz" in action or "attach" in action:
            if tool == "tmux":
                if session_name:
                    return f"tmux attach -t {session_name}"
                return "tmux attach"
            elif tool == "screen":
                if session_name:
                    return f"screen -r {session_name}"
                return "screen -r"
        elif "zamknij" in action or "kill" in action:
            if tool == "tmux":
                if session_name:
                    return f"tmux kill-session -t {session_name}"
                return "tmux kill-session"
        
        return "tmux ls"

    def validate_syntax(self, command: str) -> dict[str, Any]:
        """Validate shell command syntax."""
        errors = []
        warnings = []

        # Check for unclosed quotes
        single_quotes = command.count("'")
        double_quotes = command.count('"')
        if single_quotes % 2 != 0:
            errors.append("Unclosed single quote")
        if double_quotes % 2 != 0:
            errors.append("Unclosed double quote")

        # Check for unclosed parentheses/braces
        if command.count("(") != command.count(")"):
            errors.append("Unbalanced parentheses")
        if command.count("{") != command.count("}"):
            errors.append("Unbalanced braces")
        if command.count("[") != command.count("]"):
            errors.append("Unbalanced brackets")

        # Check pipe depth
        pipe_count = command.count("|")
        policy: ShellSafetyPolicy = self.config.safety_policy  # type: ignore
        if pipe_count > policy.max_pipe_depth:
            warnings.append(f"Deep pipe chain ({pipe_count} pipes)")

        # Check for common mistakes
        if "rm -rf *" in command:
            warnings.append("Dangerous: rm -rf with wildcard")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def check_safety(self, command: str) -> dict[str, Any]:
        """Check shell command against safety policy."""
        policy: ShellSafetyPolicy = self.config.safety_policy  # type: ignore

        # Check blocked commands
        command_lower = command.lower()
        for blocked in policy.blocked_commands:
            if blocked.lower() in command_lower:
                return {
                    "allowed": False,
                    "reason": f"Command contains blocked pattern: {blocked}",
                }

        # Check sudo
        if not policy.allow_sudo and command.strip().startswith("sudo"):
            return {
                "allowed": False,
                "reason": "sudo is not allowed by safety policy",
            }

        # Check pipe to shell
        if not policy.allow_pipe_to_shell:
            dangerous_pipes = ["| sh", "| bash", "| zsh", "|sh", "|bash"]
            for dp in dangerous_pipes:
                if dp in command:
                    return {
                        "allowed": False,
                        "reason": "Piping to shell is not allowed",
                    }

        # Check blocked directories
        try:
            argv = shlex.split(command)
        except ValueError:
            argv = command.split()

        for blocked_dir in policy.blocked_directories:
            for arg in argv:
                value = arg
                if "=" in arg:
                    value = arg.split("=", 1)[1]

                if blocked_dir == "/":
                    if value == "/":
                        return {
                            "allowed": False,
                            "reason": f"Operations on {blocked_dir} are not allowed",
                        }
                    continue

                if value == blocked_dir or value.startswith(blocked_dir + "/"):
                    return {
                        "allowed": False,
                        "reason": f"Operations on {blocked_dir} are not allowed",
                    }

        # Check commands requiring confirmation
        requires_confirmation = False
        for pattern in policy.require_confirmation_for:
            if pattern.lower() in command_lower:
                requires_confirmation = True
                break

        return {
            "allowed": True,
            "requires_confirmation": requires_confirmation,
        }

    def _generate_cat(self, entities: dict[str, Any]) -> str:
        """Generate cat command for viewing file contents."""
        file = entities.get("file", entities.get("path", entities.get("filename", "")))
        full_text = str(entities.get("_full_text", "")).lower()
        
        # Extract file path from full text if not in entities
        if not file and full_text:
            import re
            # Match common file patterns
            match = re.search(r'([/\w.-]+\.\w+)', full_text)
            if match:
                file = match.group(1)
        
        if file:
            return f"cat {shlex.quote(file)}"
        return "cat"

    def _generate_head_tail(self, entities: dict[str, Any]) -> str:
        """Generate head or tail command."""
        action = entities.get("action", "head")
        file = entities.get("file", entities.get("path", ""))
        lines = entities.get("lines", entities.get("count", "10"))
        full_text = str(entities.get("_full_text", "")).lower()
        
        # Determine head or tail from full text
        if "tail" in full_text or "ostatni" in full_text or "końc" in full_text:
            cmd = "tail"
        elif "head" in full_text or "pierwsz" in full_text or "począt" in full_text:
            cmd = "head"
        else:
            cmd = action if action in ("head", "tail") else "head"
        
        # Extract file from full text if not in entities
        if not file and full_text:
            import re
            match = re.search(r'([/\w.-]+\.\w+)', full_text)
            if match:
                file = match.group(1)
        
        # Extract line count from full text
        if full_text:
            import re
            match = re.search(r'(\d+)\s*(lini|line)', full_text)
            if match:
                lines = match.group(1)
        
        if file:
            return f"{cmd} -n {lines} {shlex.quote(file)}"
        return f"{cmd} -n {lines}"

    def _generate_wc(self, entities: dict[str, Any]) -> str:
        """Generate wc command for counting lines/words/chars."""
        file = entities.get("file", entities.get("path", ""))
        mode = entities.get("mode", "lines")
        full_text = str(entities.get("_full_text", "")).lower()
        
        # Extract file from full text if not in entities
        if not file and full_text:
            import re
            match = re.search(r'([/\w.-]+\.\w+)', full_text)
            if match:
                file = match.group(1)
        
        # Determine counting mode
        flag = "-l"  # default: lines
        if "słow" in full_text or "word" in full_text:
            flag = "-w"
        elif "znak" in full_text or "char" in full_text or "byte" in full_text:
            flag = "-c"
        
        if file:
            return f"wc {flag} {shlex.quote(file)}"
        return f"wc {flag}"

    def check_tool_availability(self, command: str) -> dict[str, Any]:
        """Check if required tools are available."""
        # Extract first command from pipeline
        first_cmd = command.split("|")[0].strip().split()[0]

        # Check if tool exists
        if shutil.which(first_cmd):
            return {"available": True, "tool": first_cmd}
        else:
            return {
                "available": False,
                "tool": first_cmd,
                "suggestion": f"Install {first_cmd} or check PATH",
            }
