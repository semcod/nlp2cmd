# DeploymentPlan - extracted from nlp2cmd_web_controller.py
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

from service_config import ServiceConfig

class DeploymentPlan:
    """Plan for deploying services."""
    services: list[ServiceConfig]
    network: str = "nlp2cmd-network"
    compose_version: str = "3.8"
    
    def _create_service_def(self, svc) -> dict[str, Any]:
        """Create service definition for docker-compose."""
        service_def = {
            "image": svc.image or f"nlp2cmd/{svc.name}:latest",
            "ports": [f"{svc.port}:{svc.port}"],
            "environment": svc.env_vars,
            "networks": [self.network],
        }
        if svc.volumes:
            service_def["volumes"] = svc.volumes
        if svc.depends_on:
            service_def["depends_on"] = svc.depends_on
        if svc.healthcheck:
            service_def["healthcheck"] = {
                "test": svc.healthcheck,
                "interval": "30s",
                "timeout": "10s",
                "retries": 3,
            }
        if svc.replicas > 1:
            service_def["deploy"] = {"replicas": svc.replicas}
        return service_def

    def _add_dependency_services(self, svc, dependency_services: dict[str, Any]) -> None:
        """Auto-add dependency services based on depends_on."""
        for dep in svc.depends_on:
            if dep == "redis" and dep not in dependency_services:
                dependency_services[dep] = self._create_redis_service()
            elif dep == "postgres" and dep not in dependency_services:
                dependency_services[dep] = self._create_postgres_service()

    def _collect_volumes(self, services: dict[str, Any]) -> dict[str, Any]:
        """Collect all named volumes from services."""
        volumes = {}
        for service_name, service_def in services.items():
            if 'volumes' in service_def:
                for volume in service_def['volumes']:
                    if ':' in volume and not volume.startswith('/'):
                        volume_name = volume.split(':')[0]
                        volumes[volume_name] = None
        return volumes

    def to_compose(self) -> dict[str, Any]:
        """Convert to docker-compose format."""
        services = {}
        dependency_services = {}
        
        for svc in self.services:
            services[svc.name] = self._create_service_def(svc)
            if svc.depends_on:
                self._add_dependency_services(svc, dependency_services)
        
        services.update(dependency_services)
        volumes = self._collect_volumes(services)
        
        return {
            "services": services,
            "networks": {
                self.network: {"driver": "bridge"}
            },
            "volumes": volumes
        }
    
    def _create_redis_service(self) -> dict[str, Any]:
        """Create Redis service configuration."""
        return {
            "image": "redis:7-alpine",
            "ports": ["6379:6379"],
            "networks": [self.network],
        }
    
    def _create_postgres_service(self) -> dict[str, Any]:
        """Create PostgreSQL service configuration."""
        return {
            "image": "postgres:15-alpine",
            "ports": ["5432:5432"],
            "environment": {
                "POSTGRES_DB": "nlp2cmd_db",
                "POSTGRES_USER": "nlp2cmd",
                "POSTGRES_PASSWORD": "${DB_PASSWORD}"
            },
            "networks": [self.network],
            "volumes": ["postgres_data:/var/lib/postgresql/data"],
            "healthcheck": {
                "test": "pg_isready -U nlp2cmd",
                "interval": "30s",
                "timeout": "10s",
                "retries": 3,
            }
        }
