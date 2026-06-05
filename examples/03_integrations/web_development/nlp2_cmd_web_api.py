# NLP2CMDWebAPI - extracted from nlp2cmd_web_controller.py
"""
NLP2CMD Web Controller - Natural Language DevOps Layer.

This module provides a control plane that interprets natural language commands
to configure and manage web application infrastructure.

Example usage:
    controller = NLP2CMDWebController()
    
    # Deploy a chat service
    await controller.execute("Uruchom serwis czatu na porcie 8080 z Redis jako backend")
    
    # Configure email integration
    await controller.execute("Skonfiguruj klienta email dla konta jan@example.com")
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import subprocess
import yaml
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from enum import Enum
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).resolve().parents[2]))
from _example_helpers import print_rule

# Import NLP2CMD core components
from nlp2cmd.core import NLP2CMD, LLMBackend
from nlp2cmd.generation.llm_simple import LiteLLMClient
from nlp2cmd.adapters.shell import ShellAdapter
from nlp2cmd.adapters.docker import DockerAdapter
from nlp2cmd.adapters.kubernetes import KubernetesAdapter

from nlp2_cmd_web_controller import NLP2CMDWebController

class NLP2CMDWebAPI:
    """
    Example web API integration for NLP2CMD.
    
    This class shows how to integrate NLP2CMD with web frameworks
    like Flask or FastAPI.
    """
    
    def __init__(self):
        self.controller = NLP2CMDWebController(
            output_dir="./web_generated",
            use_llm_fallback=True,
            auto_install=True
        )
    
    async def process_command(self, command: str, dsl: str = "auto") -> dict[str, Any]:
        """
        Process command from web interface.
        
        Returns JSON-serializable result.
        """
        try:
            result = await self.controller.execute(command, dsl)
            
            # Add web-specific metadata
            result["web_api"] = {
                "version": "1.0",
                "timestamp": datetime.now().isoformat(),
                "processed_by": "nlp2cmd-web-api",
            }
            
            return result
        except Exception as e:
            return {
                "status": "error",
                "message": f"Web API error: {str(e)}",
                "web_api": {
                    "version": "1.0",
                    "timestamp": datetime.now().isoformat(),
                    "error": True,
                },
            }
    
    def get_status(self) -> dict[str, Any]:
        """Get API status and capabilities."""
        return {
            "status": "running",
            "capabilities": {
                "devops_commands": True,
                "llm_fallback": True,
                "auto_install": True,
                "supported_dsls": ["shell", "docker", "kubernetes", "auto"],
                "languages": ["pl", "en"],
            },
            "endpoints": {
                "/process": "POST - Process natural language command",
                "/status": "GET - Get API status",
                "/history": "GET - Get command history",
                "/services": "GET - List deployed services",
            },
        }
    
    def get_history(self, limit: int = 10) -> dict[str, Any]:
        """Get command history."""
        history = self.controller.deployment_history[-limit:]
        return {
            "status": "success",
            "history": history,
            "total": len(history),
        }
    
    def get_services(self) -> dict[str, Any]:
        """Get deployed services."""
        services = {}
        for name, config in self.controller.services.items():
            services[name] = {
                "type": config.service_type.value,
                "port": config.port,
                "image": config.image,
                "status": "deployed",
            }
        
        return {
            "status": "success",
            "services": services,
            "total": len(services),
        }
