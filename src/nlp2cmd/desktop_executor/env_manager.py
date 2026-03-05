"""Environment Manager for .env file operations."""

from __future__ import annotations
import re
import logging
from pathlib import Path
from typing import Optional

from .base import ActionResult

log = logging.getLogger("nlp2cmd.desktop_executor.env")


class EnvManager:
    """Manage environment variables and .env files."""
    
    def __init__(self, default_file: str = ".env") -> None:
        self.default_file = default_file
    
    def verify_env(
        self,
        var_name: str,
        file_path: str,
        variables: dict,
    ) -> ActionResult:
        """Verify that environment variable is set.
        
        Args:
            var_name: Variable name to check
            file_path: Path to .env file
            variables: Execution variables dict
            
        Returns:
            ActionResult with verification status
        """
        try:
            # Check if already in variables
            if var_name in variables and variables[var_name]:
                value = variables[var_name]
                is_valid = self._validate_value(value, var_name)
                return ActionResult.success_result(
                    result=f"verified:{var_name}"
                )
            
            # Try loading from .env file
            full_path = Path(file_path).expanduser().resolve()
            if full_path.exists():
                env_vars = self._load_env_file(full_path)
                if var_name in env_vars and env_vars[var_name]:
                    return ActionResult.success_result(
                        result=f"loaded:{var_name}"
                    )
            
            return ActionResult.failed_result(
                f"Variable {var_name} not found in variables or {file_path}"
            )
            
        except Exception as e:
            return ActionResult.failed_result(str(e))
    
    def _validate_value(self, value: str, var_name: str) -> bool:
        """Validate that value looks like a valid token/key.
        
        Args:
            value: Value to validate
            var_name: Variable name for pattern matching
            
        Returns:
            True if value appears valid
        """
        if not value or len(value) < 8:
            return False
        
        # Common API key patterns
        patterns = {
            "HF_TOKEN": r"^hf_[a-zA-Z0-9_-]+$",
            "OPENAI_API_KEY": r"^sk-[a-zA-Z0-9]+$",
            "OPENROUTER_API_KEY": r"^sk-[a-zA-Z0-9_-]+$",
            "GITHUB_TOKEN": r"^gh[pousr]_[a-zA-Z0-9]+$",
        }
        
        pattern = patterns.get(var_name)
        if pattern:
            return bool(re.match(pattern, value))
        
        # Generic validation - just check it's not empty and has reasonable length
        return len(value) >= 8
    
    def _load_env_file(self, path: Path) -> dict[str, str]:
        """Load environment variables from .env file.
        
        Args:
            path: Path to .env file
            
        Returns:
            Dictionary of environment variables
        """
        env_vars = {}
        
        try:
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')
                        env_vars[key] = value
                        
        except Exception as e:
            log.debug(f"Failed to load .env file: {e}")
        
        return env_vars
