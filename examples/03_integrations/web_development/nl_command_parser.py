# NLCommandParser - extracted from nlp2cmd_web_controller.py
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

from service_type import ServiceType

class NLCommandParser:
    """
    Parse natural language commands into structured actions.
    
    Supports Polish and English commands for:
    - Service deployment (uruchom, deploy, start)
    - Configuration (skonfiguruj, configure, setup)
    - Scaling (skaluj, scale)
    - Monitoring (pokaż, show, status)
    """
    
    # Intent patterns (Polish + English)
    DEPLOY_PATTERNS = [
        "uruchom", "deploy", "start", "wystartuj", "włącz", "run",
        "utwórz", "create", "zbuduj", "build"
    ]
    
    CONFIG_PATTERNS = [
        "skonfiguruj", "configure", "setup", "ustaw", "set",
        "połącz", "connect", "podłącz"
    ]
    
    SCALE_PATTERNS = [
        "skaluj", "scale", "zwiększ", "increase", "zmniejsz", "decrease"
    ]
    
    STATUS_PATTERNS = [
        "pokaż", "show", "status", "sprawdź", "check", "list", "wyświetl"
    ]
    
    STOP_PATTERNS = [
        "zatrzymaj", "stop", "wyłącz", "disable", "usuń", "remove", "delete"
    ]
    
    TEST_PATTERNS = [
        "testuj", "test", "sprawdź działanie", "ping", "połącz", "verify", "validate"
    ]
    
    MONITOR_PATTERNS = [
        "monitoring", "monitoruj", "zużycie", "zasoby", "resource", "metrics", "dashboard"
    ]
    
    LOG_PATTERNS = [
        "logi", "logs", "dziennik", "journal", "show logs", "pokaż logi"
    ]
    
    RESTART_PATTERNS = [
        "restartuj", "zrestartuj", "uruchom ponownie", "reboot", "reload"
    ]
    
    # Service type detection
    SERVICE_KEYWORDS = {
        ServiceType.CHAT_SERVICE: ["czat", "chat", "komunikator", "messenger", "websocket"],
        ServiceType.EMAIL_SERVICE: ["email", "mail", "poczta", "imap", "smtp"],
        ServiceType.CONTACT_FORM: ["kontakt", "contact", "formularz", "form"],
        ServiceType.DATABASE: ["baza", "database", "db", "postgres", "mysql", "mongo"],
        ServiceType.CACHE: ["cache", "redis", "memcached", "pamięć"],
        ServiceType.FRONTEND: ["frontend", "react", "vue", "angular", "strona", "page"],
        ServiceType.BACKEND_API: ["api", "backend", "serwer", "server", "rest"],
    }
    
    def parse(self, text: str) -> dict[str, Any]:
        """Parse natural language command."""
        text_lower = text.lower()
        
        # Detect intent
        intent = self._detect_intent(text_lower)
        
        # Detect service type
        service_type = self._detect_service_type(text_lower)
        
        # Extract entities
        entities = self._extract_entities(text_lower)
        
        return {
            "intent": intent,
            "service_type": service_type,
            "entities": entities,
            "original_text": text,
        }
    
    def _detect_intent(self, text: str) -> str:
        """Detect command intent."""
        for pattern in self.DEPLOY_PATTERNS:
            if pattern in text:
                return "deploy"
        
        for pattern in self.CONFIG_PATTERNS:
            if pattern in text:
                return "configure"
        
        for pattern in self.SCALE_PATTERNS:
            if pattern in text:
                return "scale"
        
        for pattern in self.STATUS_PATTERNS:
            if pattern in text:
                return "status"
        
        for pattern in self.LOG_PATTERNS:
            if pattern in text:
                return "logs"
        
        for pattern in self.TEST_PATTERNS:
            if pattern in text:
                return "test"
        
        for pattern in self.MONITOR_PATTERNS:
            if pattern in text:
                return "monitor"
        
        for pattern in self.RESTART_PATTERNS:
            if pattern in text:
                return "restart"
        
        for pattern in self.STOP_PATTERNS:
            if pattern in text:
                return "stop"
        
        return "unknown"
    
    def _detect_service_type(self, text: str) -> Optional[ServiceType]:
        """Detect service type from text."""
        for svc_type, keywords in self.SERVICE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    return svc_type
        return None
    
    def _extract_entities(self, text: str) -> dict[str, Any]:
        """Extract entities from text."""
        import re
        
        entities = {}
        
        # Extract port numbers
        port_match = re.search(r'port[ue]?\s*[:=]?\s*(\d+)|na\s+porcie\s+(\d+)|:(\d+)', text)
        if port_match:
            entities["port"] = int(next(g for g in port_match.groups() if g))
        
        # Extract email addresses
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        if email_match:
            entities["email"] = email_match.group()
        
        # Extract hostnames/URLs
        host_match = re.search(r'host[a]?\s*[:=]?\s*([\w\.-]+)|serwer[a]?\s+([\w\.-]+)', text)
        if host_match:
            entities["host"] = next(g for g in host_match.groups() if g)
        
        # Extract replica count
        replica_match = re.search(r'(\d+)\s*(replik|instancj|kopii|replicas?|instances?)', text)
        if replica_match:
            entities["replicas"] = int(replica_match.group(1))
        
        # Extract database name
        db_match = re.search(r'baz[aęy]\s+([\w_]+)|database\s+([\w_]+)', text)
        if db_match:
            entities["database"] = next(g for g in db_match.groups() if g)
        
        # Extract credentials hints
        if "hasło" in text or "password" in text:
            entities["needs_password"] = True
        if "użytkownik" in text or "user" in text:
            entities["needs_username"] = True
        
        return entities
