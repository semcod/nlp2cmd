"""DockerValidator - extracted from __init__.py."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
import re
from nlp2cmd.validators.base_validator import BaseValidator
from nlp2cmd.validators.validation_result import ValidationResult

class DockerValidator(BaseValidator):
    """Docker command and Dockerfile validator."""

    _IMAGE_RE = re.compile(
        r"^(?:(?:[a-z0-9]+(?:[._-][a-z0-9]+)*)/)*[a-z0-9]+(?:[._-][a-z0-9]+)*(?::[A-Za-z0-9][A-Za-z0-9._-]{0,127})?$"
    )

    @staticmethod
    def _iter_publish_ports(tokens: list[str]) -> list[int]:
        ports: list[int] = []
        i = 0
        while i < len(tokens):
            t = tokens[i]
            if t in {"-p", "--publish"}:
                if i + 1 < len(tokens):
                    spec = tokens[i + 1]
                    ports.extend(DockerValidator._parse_ports_from_spec(spec))
                    i += 2
                    continue
            if t.startswith("--publish="):
                spec = t.split("=", 1)[1]
                ports.extend(DockerValidator._parse_ports_from_spec(spec))
            i += 1
        return ports

    @staticmethod
    def _parse_ports_from_spec(spec: str) -> list[int]:
        # handle forms:
        # - 8080:80
        # - 127.0.0.1:8080:80
        # - 8080:80/tcp
        if not isinstance(spec, str) or not spec:
            return []
        cleaned = spec.split("/", 1)[0]
        parts = cleaned.split(":")
        numeric: list[int] = []
        for p in parts:
            if p.isdigit():
                try:
                    numeric.append(int(p))
                except Exception:
                    continue
        return numeric

    @classmethod
    def _is_valid_image_name(cls, image: str) -> bool:
        if not isinstance(image, str) or not image:
            return False
        if "@" in image:
            return False
        return cls._IMAGE_RE.match(image) is not None

    @staticmethod
    def _find_docker_image(tokens: list[str], *, subcommand: str) -> Optional[str]:
        if not tokens:
            return None
        tokens_lower = [t.lower() for t in tokens]
        if subcommand not in tokens_lower:
            return None
        idx = tokens_lower.index(subcommand)

        if subcommand == "pull":
            for t in tokens[idx + 1 :]:
                if t.startswith("-"):
                    continue
                return t
            return None

        if subcommand != "run":
            return None

        opts_with_arg = {
            "-p",
            "--publish",
            "-e",
            "--env",
            "-v",
            "--volume",
            "--entrypoint",
            "--user",
            "-u",
            "--network",
            "--name",
            "--label",
            "--memory",
            "--cpus",
            "--security-opt",
        }
        inline_prefixes = ("-p", "-e", "-v", "-u")
        inline_equals_prefixes = (
            "--publish=",
            "--env=",
            "--volume=",
            "--entrypoint=",
            "--user=",
            "--network=",
            "--name=",
            "--label=",
            "--memory=",
            "--cpus=",
            "--security-opt=",
        )

        i = idx + 1
        while i < len(tokens):
            t = tokens[i]
            tl = tokens_lower[i]

            if tl == "--":
                i += 1
                continue

            if tl.startswith("-"):
                if tl.startswith(inline_equals_prefixes):
                    i += 1
                    continue
                if any(tl.startswith(p) and tl != p for p in inline_prefixes):
                    i += 1
                    continue
                if tl in opts_with_arg:
                    i += 2
                    continue
                i += 1
                continue

            return t
        return None

    def validate(self, content: str) -> ValidationResult:
        """Validate Docker command or Dockerfile."""
        errors = []
        warnings = []
        suggestions = []

        content_stripped = (content or "").strip()
        content_lower = content_stripped.lower()

        is_docker_cmd = (
            content_lower.startswith("docker ")
            or content_lower.startswith("docker-compose")
            or content_lower.startswith("docker compose")
        )
        is_dockerfile = (
            "\n" in content_stripped
            and ("from " in content_lower or "cmd " in content_lower or "entrypoint " in content_lower)
            and any(line.strip().lower().startswith("from ") for line in content_stripped.splitlines() if line.strip())
        )
        if not is_docker_cmd and not is_dockerfile:
            return ValidationResult(
                is_valid=False,
                errors=["Not a docker command"],
                warnings=[],
                suggestions=["Prefix the command with 'docker' or provide a Dockerfile"],
            )

        tokens = content_stripped.split()
        tokens_lower = [t.lower() for t in tokens]

        # Root user warning
        is_root_user = False
        for i, t in enumerate(tokens_lower):
            if t in {"--user", "-u"} and i + 1 < len(tokens_lower):
                if tokens_lower[i + 1] == "root":
                    is_root_user = True
                    break
            if t.startswith("--user=") and t.split("=", 1)[1] == "root":
                is_root_user = True
                break
        if is_root_user:
            warnings.append("Running container as root user")

        # docker rm force warning
        if content_lower.startswith("docker rm") and (" -f" in content_lower or " --force" in content_lower or "-f" in tokens_lower):
            warnings.append("Force removal detected (-f/--force)")

        # docker kill warning
        if content_lower.startswith("docker kill"):
            warnings.append("docker kill sends SIGKILL immediately")

        # docker build context warning
        if content_lower.startswith("docker build"):
            # find last token that isn't a flag
            context = None
            for t in reversed(tokens[2:]):
                if not t.startswith("-"):
                    context = t
                    break
            if context == "/":
                warnings.append("Build context is root directory")
                suggestions.append("Use a narrower build context than '/'")

        # Validate published ports
        for port in self._iter_publish_ports(tokens):
            if port < 1 or port > 65535:
                errors.append(f"Invalid port: {port}")

        # Validate image name for docker run / pull
        if content_lower.startswith("docker run"):
            image = self._find_docker_image(tokens, subcommand="run")
            if image and not self._is_valid_image_name(image):
                errors.append(f"Invalid image name: {image}")
        elif content_lower.startswith("docker pull"):
            image = self._find_docker_image(tokens, subcommand="pull")
            if image and not self._is_valid_image_name(image):
                errors.append(f"Invalid image name: {image}")

        # Check for privileged mode
        if "--privileged" in content:
            warnings.append("Privileged mode grants full host access")
            suggestions.append("Consider using specific capabilities instead")

        # Check for host network
        if "--network host" in content or "--net=host" in content:
            warnings.append("Host network bypasses network isolation")

        # Check for dangerous volume mounts
        dangerous_mounts = ["-v /:/", "-v /etc:", "-v /var/run/docker.sock"]
        for mount in dangerous_mounts:
            if mount in content:
                if "docker.sock" in mount:
                    warnings.append("Docker socket mount detected")
                else:
                    warnings.append(f"Dangerous volume mount: {mount}")

        # docker socket mount warning (more general check)
        if "docker.sock" in content_lower:
            warnings.append("Docker socket mount detected")

        # Check for image tag
        parts = content_lower.split()
        for i, part in enumerate(parts):
            if part in ["run", "pull"] and i + 1 < len(parts):
                image = parts[i + 1]
                if not image.startswith("-") and ":" not in image:
                    warnings.append(f"Image '{image}' has no tag, using :latest")
                    suggestions.append("Specify explicit image tag for reproducibility")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
        )

