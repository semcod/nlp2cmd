#!/usr/bin/env python3
"""
Demo 02: Deployment Planning
Planowanie wdrożenia usług.
"""

import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Optional

sys.path.append(str(Path(__file__).resolve().parents[2]))


@dataclass
class SimpleServiceConfig:
    """Uproszczona konfiguracja usługi."""
    name: str
    port: int
    image: str
    env_vars: dict[str, str] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)


@dataclass
class DeploymentPlan:
    """Plan wdrożenia wielu usług."""
    services: list[SimpleServiceConfig]
    network: str = "nlp2cmd-network"
    compose_version: str = "3.8"
    
    def summary(self) -> dict[str, Any]:
        """Podsumowanie planu wdrożenia."""
        return {
            "services_count": len(self.services),
            "services": [s.name for s in self.services],
            "network": self.network,
            "compose_version": self.compose_version,
            "total_ports": len(set(s.port for s in self.services)),
            "dependencies": {
                s.name: s.depends_on for s in self.services if s.depends_on
            }
        }


def main():
    print("=" * 60)
    print("Demo 02: Deployment Planning")
    print("=" * 60)
    print()
    
    # Stworzenie planu wdrożenia
    services = [
        SimpleServiceConfig(name="web", port=3000, image="nginx:alpine"),
        SimpleServiceConfig(
            name="api", port=8080, image="python:3.11",
            env_vars={"DB_HOST": "db"},
            depends_on=["db"]
        ),
        SimpleServiceConfig(
            name="db", port=5432, image="postgres:15",
            env_vars={"POSTGRES_DB": "main"}
        ),
        SimpleServiceConfig(
            name="cache", port=6379, image="redis:7",
            depends_on=["db"]
        ),
    ]
    
    plan = DeploymentPlan(services=services)
    summary = plan.summary()
    
    print("📋 Plan wdrożenia:")
    print(f"   Docker Compose: v{summary['compose_version']}")
    print(f"   Sieć: {summary['network']}")
    print(f"   Liczba usług: {summary['services_count']}")
    print()
    
    print("🔹 Usługi:")
    for svc in services:
        print(f"   • {svc.name}:{svc.port} ({svc.image})")
    print()
    
    print("🔗 Zależności:")
    for name, deps in summary['dependencies'].items():
        print(f"   {name} → {', '.join(deps)}")
    
    print()
    print("=" * 60)
    print("✅ Koniec demo 02")
    print("=" * 60)


if __name__ == "__main__":
    main()
