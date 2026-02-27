"""
Auto-repair system for NLP2CMD generated commands.

LLM-based repair of invalid commands before execution.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from nlp2cmd.cli.helpers import console
from nlp2cmd.cli.markdown_output import print_yaml_block


class CommandRepairer:
    """Repairs invalid commands using LLM fallback."""
    
    def __init__(self, llm_client: Optional[Any] = None):
        """Initialize repairer with optional LLM client."""
        self.llm_client = llm_client
    
    def repair_command(
        self,
        command: str,
        error: str,
        context: Optional[Dict[str, Any]] = None,
        max_attempts: int = 3
    ) -> Dict[str, Any]:
        """
        Attempt to repair a failed command.
        
        Args:
            command: The failed command
            error: Error message from execution
            context: Additional context (domain, intent, etc.)
            max_attempts: Maximum repair attempts
            
        Returns:
            Dict with repair results
        """
        context = context or {}
        
        print_yaml_block({
            "status": "auto_repair_started",
            "original_command": command,
            "error": error[:200],  # Truncate long errors
        })
        
        for attempt in range(1, max_attempts + 1):
            try:
                repaired = self._attempt_repair(command, error, context, attempt)
                
                if repaired["success"]:
                    print_yaml_block({
                        "status": "auto_repair_success",
                        "attempt": attempt,
                        "repaired_command": repaired["command"],
                    })
                    return repaired
                else:
                    print_yaml_block({
                        "status": "auto_repair_failed",
                        "attempt": attempt,
                        "reason": repaired.get("reason", "Unknown"),
                    })
                    
            except Exception as e:
                print_yaml_block({
                    "status": "auto_repair_error",
                    "attempt": attempt,
                    "error": str(e),
                })
        
        return {
            "success": False,
            "command": command,
            "reason": f"Failed after {max_attempts} attempts",
            "attempts": max_attempts,
        }
    
    def _attempt_repair(
        self,
        command: str,
        error: str,
        context: Dict[str, Any],
        attempt: int
    ) -> Dict[str, Any]:
        """Single repair attempt."""
        
        # Simple rule-based repairs first
        rule_result = self._rule_based_repair(command, error, context)
        if rule_result["success"]:
            return rule_result
        
        # LLM-based repair as fallback
        if self.llm_client:
            return self._llm_repair(command, error, context, attempt)
        
        return {
            "success": False,
            "command": command,
            "reason": "No repair strategy available",
        }
    
    def _rule_based_repair(
        self,
        command: str,
        error: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply rule-based repairs."""
        
        # Common error patterns and fixes
        repairs = {
            # File not found -> add sudo or check path
            "No such file or directory": self._fix_file_not_found,
            # Permission denied -> add sudo
            "Permission denied": self._fix_permission_denied,
            # Command not found -> suggest alternatives
            "command not found": self._fix_command_not_found,
            # Syntax error -> fix quotes/escaping
            "syntax error": self._fix_syntax_error,
            # Docker errors
            "docker: command not found": self._fix_docker_missing,
            "permission denied while trying to connect": self._fix_docker_permission,
        }
        
        for error_pattern, fixer in repairs.items():
            if error_pattern.lower() in error.lower():
                return fixer(command, error, context)
        
        return {"success": False, "command": command}
    
    def _fix_file_not_found(
        self,
        command: str,
        error: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fix file not found errors."""
        
        # Try adding sudo if it looks like a system file operation
        if any(cmd in command for cmd in ["mv ", "cp ", "rm ", "mkdir "]):
            if not command.startswith("sudo "):
                return {
                    "success": True,
                    "command": f"sudo {command}",
                    "reason": "Added sudo for system file operation",
                }
        
        # Try expanding ~ to home directory
        if " ~/" in command:
            fixed = command.replace(" ~/", " $HOME/")
            return {
                "success": True,
                "command": fixed,
                "reason": "Expanded ~ to $HOME",
            }
        
        return {"success": False, "command": command}
    
    def _fix_permission_denied(
        self,
        command: str,
        error: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fix permission denied errors."""
        
        if not command.startswith("sudo "):
            return {
                "success": True,
                "command": f"sudo {command}",
                "reason": "Added sudo for permission",
            }
        
        return {"success": False, "command": command}
    
    def _fix_command_not_found(
        self,
        command: str,
        error: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fix command not found errors."""
        
        # Common command alternatives
        alternatives = {
            "python": "python3",
            "pip": "pip3",
            "node": "nodejs",
            "yarn": "npm",
            "docker-compose": "docker compose",
        }
        
        for cmd, alt in alternatives.items():
            if f" {cmd} " in command or command.startswith(f"{cmd} "):
                fixed = command.replace(f" {cmd} ", f" {alt} ").replace(
                    command.split()[0], alt, 1
                )
                return {
                    "success": True,
                    "command": fixed,
                    "reason": f"Replaced {cmd} with {alt}",
                }
        
        return {"success": False, "command": command}
    
    def _fix_syntax_error(
        self,
        command: str,
        error: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fix syntax errors."""
        
        # Fix unmatched quotes
        if command.count('"') % 2 == 1:
            fixed = command + '"'
            return {
                "success": True,
                "command": fixed,
                "reason": "Fixed unmatched quote",
            }
        
        if command.count("'") % 2 == 1:
            fixed = command + "'"
            return {
                "success": True,
                "command": fixed,
                "reason": "Fixed unmatched single quote",
            }
        
        return {"success": False, "command": command}
    
    def _fix_docker_missing(
        self,
        command: str,
        error: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fix missing Docker."""
        
        return {
            "success": True,
            "command": f"# Install Docker first\nsudo apt update && sudo apt install docker.io -y\n# Then run:\n{command}",
            "reason": "Added Docker installation command",
        }
    
    def _fix_docker_permission(
        self,
        command: str,
        error: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fix Docker permission errors."""
        
        return {
            "success": True,
            "command": f"sudo {command}",
            "reason": "Added sudo for Docker command",
        }
    
    def _llm_repair(
        self,
        command: str,
        error: str,
        context: Dict[str, Any],
        attempt: int
    ) -> Dict[str, Any]:
        """LLM-based command repair."""
        
        if not self.llm_client:
            return {"success": False, "command": command}
        
        prompt = f"""
Repair this failed command based on the error:

Original command: {command}
Error: {error}
Context: {json.dumps(context, indent=2)}
Attempt: {attempt}

Provide a repaired command that should work. Return only the command, no explanation.
"""
        
        try:
            response = self.llm_client.generate(prompt)
            repaired = response.strip()
            
            # Basic validation
            if repaired and repaired != command:
                return {
                    "success": True,
                    "command": repaired,
                    "reason": "LLM-based repair",
                }
        except Exception as e:
            console.print(f"[red]LLM repair failed: {e}[/red]")
        
        return {"success": False, "command": command}


def should_attempt_repair(error: str, context: Dict[str, Any]) -> bool:
    """Determine if auto-repair should be attempted."""
    
    # Don't repair certain critical errors
    skip_patterns = [
        "segmentation fault",
        "killed",
        "terminated",
        "out of memory",
        "disk full",
        "network unreachable",
    ]
    
    error_lower = error.lower()
    for pattern in skip_patterns:
        if pattern in error_lower:
            return False
    
    # Always repair common errors
    repair_patterns = [
        "no such file",
        "permission denied",
        "command not found",
        "syntax error",
        "not found",
        "cannot",
    ]
    
    for pattern in repair_patterns:
        if pattern in error_lower:
            return True
    
    # Repair based on context
    if context.get("domain") in ["shell", "docker", "system"]:
        return True
    
    return False
