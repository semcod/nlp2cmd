# ServiceType - extracted from nlp2cmd_web_controller.py
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

class ServiceType(Enum):
    """Types of services that can be managed."""
    FRONTEND = "frontend"
    BACKEND_API = "backend_api"
    DATABASE = "database"
    CACHE = "cache"
    MESSAGE_QUEUE = "message_queue"
    EMAIL_SERVICE = "email_service"
    CHAT_SERVICE = "chat_service"
    CONTACT_FORM = "contact_form"
