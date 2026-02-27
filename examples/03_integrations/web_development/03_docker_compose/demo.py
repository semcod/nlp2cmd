#!/usr/bin/env python3
"""
Demo 03: Docker Compose Generation
Generowanie plików docker-compose.yml.
"""

import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Optional

sys.path.append(str(Path(__file__).resolve().parents[2]))


@dataclass
class Service:
    """Konfiguracja pojedynczej usługi."""
    name: str
    port: int
    image: str
    env_vars: dict[str, str] = field(default_factory=dict)
    volumes: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)


def generate_compose(services: list[Service]) -> dict[str, Any]:
    """Generuje strukturę docker-compose."""
    compose = {
        "version": "3.8",
        "services": {},
        "networks": {"nlp2cmd-network": {"driver": "bridge"}},
    }
    
    for svc in services:
        service_def = {
            "image": svc.image,
            "ports": [f"{svc.port}:{svc.port}"],
            "networks": ["nlp2cmd-network"],
        }
        if svc.env_vars:
            service_def["environment"] = svc.env_vars
        if svc.volumes:
            service_def["volumes"] = svc.volumes
        if svc.depends_on:
            service_def["depends_on"] = svc.depends_on
        
        compose["services"][svc.name] = service_def
    
    return compose


def main():
    print("=" * 60)
    print("Demo 03: Docker Compose Generation")
    print("=" * 60)
    print()
    
    services = [
        Service(name="web", port=3000, image="nginx:alpine"),
        Service(name="api", port=8080, image="python:3.11", depends_on=["db"]),
        Service(
            name="db", port=5432, image="postgres:15",
            env_vars={"POSTGRES_USER": "app", "POSTGRES_DB": "main"},
            volumes=["postgres_data:/var/lib/postgresql/data"]
        ),
    ]
    
    compose = generate_compose(services)
    
    print("🐳 Wygenerowany docker-compose.yml:")
    print()
    
    import json
    print(json.dumps(compose, indent=2, ensure_ascii=False))
    
    print()
    print("=" * 60)
    print("✅ Koniec demo 03")
    print("=" * 60)


if __name__ == "__main__":
    main()
