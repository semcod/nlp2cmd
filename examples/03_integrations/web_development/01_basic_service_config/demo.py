#!/usr/bin/env python3
"""
Demo 01: Basic Service Configuration
Konfiguracja podstawowych usług w nlp2cmd.
"""

import sys
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional

sys.path.append(str(Path(__file__).resolve().parents[2]))


class ServiceType(Enum):
    """Typy usług obsługiwanych przez nlp2cmd."""
    FRONTEND = "frontend"
    BACKEND_API = "backend_api"
    DATABASE = "database"
    CACHE = "cache"
    MESSAGE_QUEUE = "message_queue"
    EMAIL_SERVICE = "email_service"
    CHAT_SERVICE = "chat_service"
    CONTACT_FORM = "contact_form"


@dataclass
class ServiceConfig:
    """Konfiguracja usługi do wdrożenia."""
    name: str
    service_type: ServiceType
    port: int
    image: Optional[str] = None
    env_vars: dict[str, str] = field(default_factory=dict)
    volumes: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    healthcheck: Optional[str] = None
    replicas: int = 1


def main():
    print("=" * 60)
    print("Demo 01: Basic Service Configuration")
    print("=" * 60)
    print()
    
    # Przykładowe konfiguracje usług
    services = [
        ServiceConfig(
            name="frontend",
            service_type=ServiceType.FRONTEND,
            port=3000,
            image="nginx:alpine",
            env_vars={"NGINX_HOST": "localhost"},
        ),
        ServiceConfig(
            name="backend-api",
            service_type=ServiceType.BACKEND_API,
            port=8080,
            image="python:3.11-slim",
            env_vars={"DB_HOST": "postgres", "REDIS_HOST": "redis"},
            depends_on=["postgres", "redis"],
        ),
        ServiceConfig(
            name="postgres",
            service_type=ServiceType.DATABASE,
            port=5432,
            image="postgres:15",
            env_vars={"POSTGRES_USER": "app", "POSTGRES_DB": "main"},
            volumes=["postgres_data:/var/lib/postgresql/data"],
        ),
        ServiceConfig(
            name="redis",
            service_type=ServiceType.CACHE,
            port=6379,
            image="redis:7-alpine",
        ),
    ]
    
    print("📋 Skonfigurowane usługi:")
    print()
    for svc in services:
        print(f"  🔹 {svc.name} ({svc.service_type.value})")
        print(f"     Port: {svc.port}")
        print(f"     Image: {svc.image}")
        if svc.env_vars:
            print(f"     Env: {svc.env_vars}")
        if svc.depends_on:
            print(f"     Dependencies: {svc.depends_on}")
        print()
    
    print("=" * 60)
    print("✅ Koniec demo 01")
    print("=" * 60)


if __name__ == "__main__":
    main()
