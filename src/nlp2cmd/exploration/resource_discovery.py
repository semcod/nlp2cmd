"""
Resource Discovery Manager - Automatic resource discovery when execution fails.

Integrates exploration capabilities into the execution pipeline to:
1. Detect missing resources during command execution
2. Automatically explore and discover missing resources
3. Suggest alternatives or auto-retry with discovered resources
4. Make decisions about resource discovery vs. failure
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional
from pathlib import Path

from nlp2cmd.exploration import (
    explore,
    DiskExplorer,
    ServiceExplorer,
    DataTreeExplorer,
    ExplorationContext,
    ExplorationResult,
    ExplorerRegistry,
)


@dataclass
class MissingResource:
    """Information about a missing resource."""
    resource_type: str  # file, directory, endpoint, data, command, package
    resource_name: str
    search_hints: list[str] = field(default_factory=list)
    suggested_locations: list[str] = field(default_factory=list)


@dataclass
class DiscoveryDecision:
    """Decision about whether to attempt discovery or fail."""
    should_discover: bool
    reason: str
    confidence: float  # 0.0 - 1.0
    fallback_action: Optional[str] = None  # "fail", "skip", "prompt"


class ResourceDiscoveryManager:
    """
    Manages automatic resource discovery during command execution.
    
    This is a standardized method called by the execution pipeline when
    a command cannot be executed due to missing resources.
    
    Usage:
        manager = ResourceDiscoveryManager()
        
        # Check if we should try to discover missing resource
        decision = manager.should_attempt_discovery(error_output, attempted_command)
        
        if decision.should_discover:
            result = manager.discover_missing_resource(missing_resource)
            if result.success:
                # Retry command with discovered resource
                new_command = manager.adapt_command(attempted_command, result)
    """
    
    # Error patterns that indicate missing resources
    MISSING_FILE_PATTERNS = [
        r"No such file or directory:\s*(.+)",
        r"cannot open ['\"](.+)['\"]: No such file",
        r"FileNotFoundError.*['\"](.+)['\"]",
        r"ls: cannot access ['\"](.+)['\"]",
        r"cat:\s*(.+): No such file",
        r"source:\s*(.+): No such file",
    ]
    
    MISSING_COMMAND_PATTERNS = [
        r"command not found:\s*(\S+)",
        r"(\S+): command not found",
        r"'(.+)' is not recognized",
        r"Could not find command: (.+)",
    ]
    
    MISSING_PACKAGE_PATTERNS = [
        r"ModuleNotFoundError: No module named ['\"](.+)['\"]",
        r"ImportError.*cannot import name ['\"](.+)['\"]",
        r"No module named ['\"](.+)['\"]",
        r"Error: Cannot find module ['\"](.+)['\"]",
    ]
    
    MISSING_ENDPOINT_PATTERNS = [
        r"Connection refused.*:\s*(\d+)",
        r"Could not resolve host:\s*(\S+)",
        r"404.*Not Found.*(http[s]?://\S+)",
        r"Connection to (.+) refused",
    ]
    
    MISSING_DIRECTORY_PATTERNS = [
        r"chdir:\s*(.+): No such file",
        r"cd:\s*(.+): No such file",
    ]
    
    def __init__(
        self,
        auto_discover: bool = True,
        max_discovery_depth: int = 3,
        discovery_timeout: float = 10.0,
        console: Optional[Any] = None,
    ):
        self.auto_discover = auto_discover
        self.max_discovery_depth = max_discovery_depth
        self.discovery_timeout = discovery_timeout
        self.console = console
        
        # Initialize explorers
        self._disk_explorer = DiskExplorer(max_depth=max_discovery_depth)
        self._service_explorer = ServiceExplorer(timeout_seconds=discovery_timeout)
        self._data_explorer = DataTreeExplorer(max_depth=max_discovery_depth)
    
    def analyze_error(
        self,
        error_output: str,
        command: str,
    ) -> Optional[MissingResource]:
        """
        Analyze error output to identify missing resource.
        
        Returns:
            MissingResource if a missing resource is detected, None otherwise
        """
        error_lower = error_output.lower()
        
        # Check for missing file
        for pattern in self.MISSING_FILE_PATTERNS:
            match = re.search(pattern, error_output, re.IGNORECASE)
            if match:
                return MissingResource(
                    resource_type="file",
                    resource_name=match.group(1).strip(),
                    search_hints=["config", "data", "settings"],
                )
        
        # Check for missing directory
        for pattern in self.MISSING_DIRECTORY_PATTERNS:
            match = re.search(pattern, error_output, re.IGNORECASE)
            if match:
                return MissingResource(
                    resource_type="directory",
                    resource_name=match.group(1).strip(),
                    search_hints=["workspace", "project", "home"],
                )
        
        # Check for missing command
        for pattern in self.MISSING_COMMAND_PATTERNS:
            match = re.search(pattern, error_output, re.IGNORECASE)
            if match:
                return MissingResource(
                    resource_type="command",
                    resource_name=match.group(1).strip(),
                    search_hints=["bin", "scripts", "tools"],
                )
        
        # Check for missing package/module
        for pattern in self.MISSING_PACKAGE_PATTERNS:
            match = re.search(pattern, error_output, re.IGNORECASE)
            if match:
                return MissingResource(
                    resource_type="package",
                    resource_name=match.group(1).strip(),
                    search_hints=["dependencies", "requirements"],
                )
        
        # Check for missing endpoint/service
        for pattern in self.MISSING_ENDPOINT_PATTERNS:
            match = re.search(pattern, error_output, re.IGNORECASE)
            if match:
                return MissingResource(
                    resource_type="endpoint",
                    resource_name=match.group(1).strip(),
                    search_hints=["api", "service", "localhost"],
                )
        
        return None
    
    def should_attempt_discovery(
        self,
        error_output: str,
        command: str,
        attempt_count: int = 0,
    ) -> DiscoveryDecision:
        """
        Decide whether to attempt resource discovery or fail.
        
        This is the core decision-making method that determines if we should
        try to automatically discover missing resources.
        
        Args:
            error_output: The error message/output from failed command
            command: The command that was attempted
            attempt_count: Number of previous discovery attempts
            
        Returns:
            DiscoveryDecision with recommendation
        """
        # Check if auto-discovery is enabled
        if not self.auto_discover:
            return DiscoveryDecision(
                should_discover=False,
                reason="Auto-discovery disabled",
                confidence=0.0,
                fallback_action="fail",
            )
        
        # Check attempt limit
        if attempt_count >= 3:
            return DiscoveryDecision(
                should_discover=False,
                reason="Too many discovery attempts",
                confidence=0.0,
                fallback_action="fail",
            )
        
        # Analyze error for missing resource
        missing = self.analyze_error(error_output, command)
        
        if missing is None:
            return DiscoveryDecision(
                should_discover=False,
                reason="No missing resource detected in error",
                confidence=0.0,
                fallback_action="fail",
            )
        
        # Check if we can discover this resource type
        discoverable_types = ["file", "directory", "endpoint", "data"]
        if missing.resource_type not in discoverable_types:
            return DiscoveryDecision(
                should_discover=False,
                reason=f"Resource type '{missing.resource_type}' not discoverable",
                confidence=0.3,
                fallback_action="prompt",  # Ask user what to do
            )
        
        # Check command patterns that are good candidates for discovery
        discovery_friendly_patterns = [
            r"cat\s+",
            r"source\s+",
            r"\.\s+",
            r"python\s+",
            r"node\s+",
            r"cd\s+",
            r"ls\s+",
            r"config",
            r"edit\s+",
            r"open\s+",
        ]
        
        command_friendly = any(
            re.search(pattern, command, re.IGNORECASE)
            for pattern in discovery_friendly_patterns
        )
        
        if command_friendly:
            confidence = 0.8
        else:
            confidence = 0.5
        
        return DiscoveryDecision(
            should_discover=True,
            reason=f"Detected missing {missing.resource_type}: {missing.resource_name}",
            confidence=confidence,
            fallback_action="prompt" if not command_friendly else None,
        )
    
    def discover_missing_resource(
        self,
        missing: MissingResource,
        search_root: Optional[str] = None,
    ) -> ExplorationResult:
        """
        Attempt to discover the missing resource.
        
        Args:
            missing: Information about the missing resource
            search_root: Where to start searching (auto-detected if None)
            
        Returns:
            ExplorationResult with discovered resource
        """
        if missing.resource_type in ["file", "directory"]:
            return self._discover_file_resource(missing, search_root)
        elif missing.resource_type == "endpoint":
            return self._discover_endpoint_resource(missing, search_root)
        elif missing.resource_type == "data":
            return self._discover_data_resource(missing, search_root)
        else:
            return ExplorationResult(
                success=False,
                target=None,
                error=f"Cannot discover resource type: {missing.resource_type}",
            )
    
    def _discover_file_resource(
        self,
        missing: MissingResource,
        search_root: Optional[str],
    ) -> ExplorationResult:
        """Discover missing file or directory."""
        # Determine search root
        if search_root is None:
            if missing.resource_name.startswith("/"):
                search_root = "/"
            elif missing.resource_name.startswith("~/"):
                search_root = str(Path.home())
            else:
                search_root = "."
        
        # Extract just the filename if full path was given
        resource_name = Path(missing.resource_name).name
        
        # Create exploration context
        intent = "config" if "config" in resource_name.lower() else "file"
        context = ExplorationContext(
            intent=intent,
            search_term=resource_name,
            max_depth=self.max_discovery_depth,
        )
        
        # Search
        result = self._disk_explorer.explore(search_root, context)
        
        return result
    
    def _discover_endpoint_resource(
        self,
        missing: MissingResource,
        search_root: Optional[str],
    ) -> ExplorationResult:
        """Discover missing API endpoint."""
        # Default to localhost for service discovery
        base_url = search_root or "http://localhost"
        
        context = ExplorationContext(
            intent="endpoint",
            search_term=missing.resource_name,
        )
        
        return self._service_explorer.explore(base_url, context)
    
    def _discover_data_resource(
        self,
        missing: MissingResource,
        search_root: Optional[str],
    ) -> ExplorationResult:
        """Discover missing data field/structure."""
        # Try to find data in common locations
        if search_root is None:
            # Try to load from common data sources
            search_root = missing.search_hints[0] if missing.search_hints else "data"
        
        context = ExplorationContext(
            intent="data",
            search_term=missing.resource_name,
        )
        
        # This would need actual data to search through
        # For now, return a failure that suggests where to look
        return ExplorationResult(
            success=False,
            target=None,
            error=f"Data exploration requires data source. Searched: {search_root}",
        )
    
    def adapt_command(
        self,
        original_command: str,
        discovery_result: ExplorationResult,
    ) -> str:
        """
        Adapt the original command to use discovered resource.
        
        Args:
            original_command: The command that failed
            discovery_result: Result of resource discovery
            
        Returns:
            Modified command with discovered resource path
        """
        if not discovery_result.success or not discovery_result.target:
            return original_command
        
        discovered_path = discovery_result.target
        
        # Handle different target types
        if hasattr(discovered_path, 'path'):
            # DiskExplorer returns FileInfo
            new_path = discovered_path.path
        elif hasattr(discovered_path, 'url'):
            # ServiceExplorer returns EndpointInfo
            new_path = discovered_path.url
        elif hasattr(discovered_path, 'path'):
            # DataTreeExplorer returns DataNode
            new_path = discovered_path.path
        else:
            new_path = str(discovered_path)
        
        # Replace in command - find the missing part and replace
        # This is a simple implementation - more sophisticated would parse the command
        
        # Try to find a quoted or bare path in the original command and replace it
        patterns = [
            r"(['\"])(.+?)\1",  # Quoted strings
            r"\s(\S+\.(?:txt|json|yaml|yml|py|js|sh|conf|config))(?:\s|$)",  # Common file extensions
        ]
        
        modified = original_command
        for pattern in patterns:
            match = re.search(pattern, original_command)
            if match:
                old_path = match.group(0)
                modified = original_command.replace(old_path, f" '{new_path}'")
                break
        
        return modified
    
    def handle_execution_failure(
        self,
        command: str,
        error_output: str,
        attempt_count: int = 0,
    ) -> tuple[bool, Optional[str]]:
        """
        Main entry point for handling execution failures.
        
        This is the standardized method called by the execution pipeline
        when a command cannot be executed due to missing resources.
        
        Returns:
            (success, new_command_or_none)
            - success: True if recovery was successful
            - new_command: Modified command to retry, or None if should fail
        """
        # Decide whether to attempt discovery
        decision = self.should_attempt_discovery(error_output, command, attempt_count)
        
        if not decision.should_discover:
            if decision.fallback_action == "prompt" and self.console:
                # Could prompt user here
                pass
            return False, None
        
        # Identify missing resource
        missing = self.analyze_error(error_output, command)
        if not missing:
            return False, None
        
        # Attempt discovery
        if self.console:
            self.console.print(f"🔍 Auto-discovering missing {missing.resource_type}: {missing.resource_name}")
        
        result = self.discover_missing_resource(missing)
        
        if result.success and result.target:
            # Adapt command with discovered resource
            new_command = self.adapt_command(command, result)
            
            if self.console:
                discovered = result.target.path if hasattr(result.target, 'path') else str(result.target)
                self.console.print(f"✓ Found alternative: {discovered}")
                self.console.print(f"🔄 Retrying with: {new_command}")
            
            return True, new_command
        else:
            if self.console:
                self.console.print(f"✗ Could not discover missing {missing.resource_name}")
            
            return False, None


# Singleton instance for easy access
_resource_discovery_manager: Optional[ResourceDiscoveryManager] = None


def get_resource_discovery_manager() -> ResourceDiscoveryManager:
    """Get or create the global resource discovery manager."""
    global _resource_discovery_manager
    if _resource_discovery_manager is None:
        _resource_discovery_manager = ResourceDiscoveryManager()
    return _resource_discovery_manager
