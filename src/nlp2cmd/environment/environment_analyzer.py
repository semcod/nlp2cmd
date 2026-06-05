# EnvironmentAnalyzer - extracted from __init__.py
"""
Environment Analysis module for NLP2CMD.

Provides system environment detection, tool availability checking,
and context-aware command validation.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from nlp2cmd.environment.environment_report import EnvironmentReport
from nlp2cmd.environment.service_info import ServiceInfo
from nlp2cmd.environment.tool_info import ToolInfo

class EnvironmentAnalyzer:
    """
    Analyzes the system environment for available tools, services,
    and configuration files.

    This information is used to provide context-aware command generation
    and validation.
    """

    TOOL_CHECKS = {
        "docker": {
            "command": ["docker", "--version"],
            "version_pattern": r"Docker version ([\d.]+)",
            "config_files": ["~/.docker/config.json", "/etc/docker/daemon.json"],
        },
        "docker-compose": {
            "command": ["docker-compose", "--version"],
            "version_pattern": r"version ([\d.]+)",
        },
        "kubectl": {
            "command": ["kubectl", "version", "--client", "--short"],
            "version_pattern": r"v([\d.]+)",
            "config_files": ["~/.kube/config"],
        },
        "git": {
            "command": ["git", "--version"],
            "version_pattern": r"git version ([\d.]+)",
            "config_files": ["~/.gitconfig"],
        },
        "python": {
            "command": ["python3", "--version"],
            "version_pattern": r"Python ([\d.]+)",
        },
        "node": {
            "command": ["node", "--version"],
            "version_pattern": r"v([\d.]+)",
        },
        "psql": {
            "command": ["psql", "--version"],
            "version_pattern": r"psql \(PostgreSQL\) ([\d.]+)",
        },
        "mysql": {
            "command": ["mysql", "--version"],
            "version_pattern": r"mysql\s+Ver ([\d.]+)",
        },
        "terraform": {
            "command": ["terraform", "--version"],
            "version_pattern": r"Terraform v([\d.]+)",
        },
        "aws": {
            "command": ["aws", "--version"],
            "version_pattern": r"aws-cli/([\d.]+)",
            "config_files": ["~/.aws/credentials", "~/.aws/config"],
        },
        "gcloud": {
            "command": ["gcloud", "--version"],
            "version_pattern": r"Google Cloud SDK ([\d.]+)",
        },
        "helm": {
            "command": ["helm", "version", "--short"],
            "version_pattern": r"v([\d.]+)",
        },
        "ansible": {
            "command": ["ansible", "--version"],
            "version_pattern": r"ansible.*?([\d.]+)",
        },
    }

    SERVICE_CHECKS = {
        "docker_daemon": {"port": None},
        "postgresql": {"port": 5432},
        "mysql": {"port": 3306},
        "redis": {"port": 6379},
        "mongodb": {"port": 27017},
        "elasticsearch": {"port": 9200},
        "nginx": {"port": 80},
    }

    def __init__(self):
        self._cache: dict[str, Any] = {}

    def analyze(self) -> dict[str, Any]:
        """
        Perform basic environment analysis.

        Returns:
            Dictionary with OS, shell, user, and environment info
        """
        return {
            "os": self._get_os_info(),
            "shell": self._get_shell_info(),
            "user": self._get_user_info(),
            "cwd": str(Path.cwd()),
            "env_vars": self._get_relevant_env_vars(),
        }

    def _get_os_info(self) -> dict[str, str]:
        """Get operating system information."""
        return {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor() or "unknown",
            "python_version": platform.python_version(),
        }

    def _get_shell_info(self) -> dict[str, str]:
        """Get current shell information."""
        shell = os.environ.get("SHELL", "")
        return {
            "path": shell,
            "name": Path(shell).name if shell else "unknown",
        }

    def _get_user_info(self) -> dict[str, Any]:
        """Get current user information."""
        is_root = False
        if hasattr(os, "geteuid"):
            is_root = os.geteuid() == 0

        return {
            "name": os.environ.get("USER", os.environ.get("USERNAME", "unknown")),
            "home": str(Path.home()),
            "is_root": is_root,
        }

    def _get_relevant_env_vars(self) -> dict[str, str]:
        """Get relevant environment variables."""
        relevant = [
            "PATH",
            "PYTHONPATH",
            "NODE_PATH",
            "DOCKER_HOST",
            "KUBECONFIG",
            "AWS_PROFILE",
            "AWS_REGION",
            "DATABASE_URL",
            "REDIS_URL",
            "VIRTUAL_ENV",
            "CONDA_DEFAULT_ENV",
        ]
        return {k: os.environ.get(k, "") for k in relevant if os.environ.get(k)}

    def detect_tools(
        self,
        tool_names: Optional[list[str]] = None,
    ) -> dict[str, ToolInfo]:
        """
        Detect available tools.

        Args:
            tool_names: List of tool names to check (default: all known tools)

        Returns:
            Dictionary mapping tool names to ToolInfo
        """
        if tool_names is None:
            tool_names = list(self.TOOL_CHECKS.keys())

        results = {}

        for name in tool_names:
            check = self.TOOL_CHECKS.get(name, {"command": [name, "--version"]})
            info = ToolInfo(name=name, available=False)

            # Check if tool exists
            path = shutil.which(name)
            if not path:
                cmd = check.get("command")
                if isinstance(cmd, list) and cmd:
                    candidate = cmd[0]
                    if isinstance(candidate, str) and candidate and candidate != name:
                        path = shutil.which(candidate)
            if path:
                info.available = True
                info.path = path

                # Get version
                try:
                    cmd = check.get("command", [name, "--version"])
                    output = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )

                    if output.returncode == 0:
                        combined_output = output.stdout + output.stderr
                        pattern = check.get("version_pattern", r"([\d.]+)")
                        match = re.search(pattern, combined_output)
                        if match:
                            info.version = match.group(1)

                except (subprocess.TimeoutExpired, Exception):
                    pass

                # Check config files
                for config_path in check.get("config_files", []):
                    expanded = Path(config_path).expanduser()
                    if expanded.exists():
                        info.config_files.append(str(expanded))

            results[name] = info

        return results

    def check_services(self) -> dict[str, ServiceInfo]:
        """
        Check status of common services.

        Returns:
            Dictionary mapping service names to ServiceInfo
        """
        results = {}

        for name, config in self.SERVICE_CHECKS.items():
            info = ServiceInfo(
                name=name,
                running=False,
                port=config.get("port"),
            )

            port = config.get("port")

            # Check by port
            if port:
                info.reachable = self._check_port("localhost", port)
                info.running = info.reachable

            # Special check for Docker
            if name == "docker_daemon":
                info.running = self._check_docker_daemon()

            results[name] = info

        return results

    def _check_port(self, host: str, port: int) -> bool:
        """Check if a port is open."""
        import socket

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                return s.connect_ex((host, port)) == 0
        except Exception:
            return False

    def _check_docker_daemon(self) -> bool:
        """Check if Docker daemon is running."""
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False

    def find_config_files(
        self,
        directory: Path,
        patterns: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        """
        Find configuration files in directory.

        Args:
            directory: Directory to search
            patterns: File patterns to match

        Returns:
            List of found config files with metadata
        """
        if patterns is None:
            patterns = [
                "docker-compose*.yml",
                "docker-compose*.yaml",
                "Dockerfile*",
                "*.sql",
                "schema.prisma",
                "*.tf",
                ".env*",
                "package.json",
                "requirements.txt",
                "pyproject.toml",
                ".github/workflows/*.yml",
            ]

        results = []

        for pattern in patterns:
            # Handle patterns with subdirectories
            if "/" in pattern:
                parts = pattern.split("/")
                subdir = "/".join(parts[:-1])
                file_pattern = parts[-1]
                search_dir = directory / subdir
            else:
                search_dir = directory
                file_pattern = pattern

            if not search_dir.exists():
                continue

            for file_path in search_dir.glob(file_pattern):
                if file_path.is_file():
                    results.append({
                        "path": str(file_path),
                        "name": file_path.name,
                        "size": file_path.stat().st_size,
                        "modified": file_path.stat().st_mtime,
                    })

        return results

    def validate_command(
        self,
        command: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Validate a command against the environment.

        Args:
            command: Command to validate
            context: Environment context

        Returns:
            Validation result with warnings
        """
        warnings = []

        # Extract first command
        parts = command.split()
        if not parts:
            return {"valid": True, "warnings": []}

        first_cmd = parts[0]

        # Skip shell builtins
        builtins = {"cd", "echo", "export", "source", "alias", "if", "for", "while"}
        if first_cmd in builtins:
            return {"valid": True, "warnings": []}

        # Check if tool is available
        available_tools = context.get("available_tools", {})
        if first_cmd not in available_tools:
            if not shutil.which(first_cmd):
                warnings.append(f"Command '{first_cmd}' not found in PATH")

        # Check Docker
        if "docker" in command.lower():
            services = context.get("services", {})
            docker_info = services.get("docker_daemon", {})
            if isinstance(docker_info, dict) and not docker_info.get("running"):
                warnings.append("Docker daemon may not be running")
            elif isinstance(docker_info, ServiceInfo) and not docker_info.running:
                warnings.append("Docker daemon may not be running")

        # Check kubectl
        if "kubectl" in command.lower():
            kubeconfig = os.environ.get("KUBECONFIG")
            default_config = Path.home() / ".kube" / "config"
            if not kubeconfig and not default_config.exists():
                warnings.append("No Kubernetes config found")

        return {"valid": len(warnings) == 0, "warnings": warnings}

    def full_report(self) -> EnvironmentReport:
        """
        Generate a full environment report.

        Returns:
            EnvironmentReport with all gathered information
        """
        tools = self.detect_tools()
        services = self.check_services()
        config_files = self.find_config_files(Path.cwd())

        recommendations = self._generate_recommendations(tools, services)

        return EnvironmentReport(
            os_info=self._get_os_info(),
            tools=tools,
            services=services,
            config_files=config_files,
            resources=self._get_resources(),
            recommendations=recommendations,
        )

    def _get_resources(self) -> dict[str, Any]:
        """Get system resource information."""
        resources = {}

        # Disk usage
        try:
            total, used, free = shutil.disk_usage("/")
            resources["disk"] = {
                "total_gb": round(total / (1024**3), 1),
                "used_gb": round(used / (1024**3), 1),
                "free_gb": round(free / (1024**3), 1),
                "percent_used": round(used / total * 100, 1),
            }
        except Exception:
            pass

        # Memory (Linux)
        try:
            with open("/proc/meminfo") as f:
                meminfo = f.read()
                total_match = re.search(r"MemTotal:\s+(\d+)", meminfo)
                available_match = re.search(r"MemAvailable:\s+(\d+)", meminfo)

                if total_match and available_match:
                    total_kb = int(total_match.group(1))
                    available_kb = int(available_match.group(1))
                    resources["memory"] = {
                        "total_gb": round(total_kb / (1024**2), 1),
                        "available_gb": round(available_kb / (1024**2), 1),
                        "percent_used": round((1 - available_kb / total_kb) * 100, 1),
                    }
        except Exception:
            pass

        return resources

    def _generate_recommendations(
        self,
        tools: dict[str, ToolInfo],
        services: dict[str, ServiceInfo],
    ) -> list[str]:
        """Generate recommendations based on environment analysis."""
        recommendations = []

        # Check essential tools
        essential = ["docker", "git"]
        for tool in essential:
            if tool in tools and not tools[tool].available:
                recommendations.append(f"Consider installing {tool}")

        # Check tool versions
        docker_info = tools.get("docker")
        if docker_info and docker_info.version:
            try:
                major = int(docker_info.version.split(".")[0])
                if major < 20:
                    recommendations.append(
                        f"Docker {docker_info.version} is outdated, consider upgrading"
                    )
            except (ValueError, IndexError):
                pass

        # Check services
        docker_service = services.get("docker_daemon")
        if docker_service:
            docker_tool = tools.get("docker")
            if docker_tool and docker_tool.available and not docker_service.running:
                recommendations.append("Docker is installed but daemon is not running")

        return recommendations
