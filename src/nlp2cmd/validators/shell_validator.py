"""ShellValidator - extracted from __init__.py."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
import re
from nlp2cmd.validators.base_validator import BaseValidator
from nlp2cmd.validators.syntax_validator import SyntaxValidator
from nlp2cmd.validators.validation_result import ValidationResult

class ShellValidator(BaseValidator):
    """Shell command validator."""

    DANGEROUS_COMMANDS = [
        "rm -rf /",
        "rm -rf /*",
        "mkfs",
        ":(){:|:&};:",
        "dd if=/dev/zero",
        "chmod -R 777 /",
        "> /dev/sda",
    ]

    def __init__(self, allow_sudo: bool = False):
        self.allow_sudo = allow_sudo

    def validate(self, content: str) -> ValidationResult:
        """Validate shell command."""
        errors = []
        warnings = []
        suggestions = []

        content_lower = content.lower()

        # Check for dangerous commands - mark as errors
        for dangerous in self.DANGEROUS_COMMANDS:
            if dangerous.lower() in content_lower:
                errors.append(f"Dangerous command detected: {dangerous}")

        # Check sudo usage
        if content.strip().startswith("sudo") and not self.allow_sudo:
            warnings.append("sudo usage detected - requires elevated privileges")
            suggestions.append("Consider if root privileges are necessary")

        # Check for rm with wildcards - mark as error for safety
        if "rm " in content and "*" in content:
            errors.append("rm with wildcard - verify target carefully")

        # Check pipe to shell - warning only
        if "| sh" in content or "| bash" in content:
            warnings.append("Piping to shell is potentially dangerous")

        # Check for eval command - error for security
        if "eval " in content_lower:
            errors.append("eval command detected - potential code injection risk")

        # Check for command injection patterns
        injection_patterns = ["&&", "||", ";", "$(", "`"]
        for pattern in injection_patterns:
            if pattern in content and not pattern in ["&&", "||"]:  # Allow logical operators in safe contexts
                if pattern == ";":
                    errors.append("Command separator detected - potential injection risk")
                elif pattern == "$(":
                    warnings.append("Command substitution detected - review for safety")
                elif pattern == "`":
                    warnings.append("Backtick command substitution detected - review for safety")

        # Check for dangerous permission changes
        if "chmod" in content_lower and ("777" in content or "a+rwx" in content):
            warnings.append("777 permissions change detected - security risk")
            suggestions.append("Consider more restrictive permissions")

        # Check for process killing
        if "kill" in content_lower and ("-9" in content or "SIGKILL" in content):
            warnings.append("kill -9 or SIGKILL detected - consider graceful termination")
            suggestions.append("Try SIGTERM (kill -15) first")

        # Check for system file modification
        system_paths = ["/etc/", "/boot/", "/sys/", "/proc/", "/dev/", "/root/", "/usr/bin/"]
        for path in system_paths:
            if path in content and (">>" in content or ">" in content):
                errors.append(f"System file modification detected: {path}")

        # Check for background job patterns
        if "nohup" in content_lower or (content.endswith("&") and not content.endswith(" &")):
            errors.append("Background job detected - verify job management")

        # Check for path traversal
        if "../" in content or "..\\" in content:
            errors.append("Path traversal pattern detected")

        # Syntax check
        syntax_result = SyntaxValidator().validate(content)
        errors.extend(syntax_result.errors)
        warnings.extend(syntax_result.warnings)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
        )

