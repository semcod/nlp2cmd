# NLP2CMDWebController - extracted from nlp2cmd_web_controller.py
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

from deployment_plan import DeploymentPlan
from docker_manager import DockerManager
from nl_command_parser import NLCommandParser
from output_file_manager import OutputFileManager
from service_config import ServiceConfig
from service_type import ServiceType

class NLP2CMDWebController:
    """
    Main controller for NLP2CMD-powered web infrastructure.
    
    This class orchestrates the deployment and management of web services
    based on natural language commands, with integrated LLM fallback.
    """
    
    def __init__(self, output_dir: str = "./generated", use_llm_fallback: bool = True, auto_install: bool = False):
        self.parser = NLCommandParser()
        self.services: dict[str, ServiceConfig] = {}
        self.deployment_history: list[dict[str, Any]] = []
        self.file_manager = OutputFileManager(output_dir)
        self.docker_manager: Optional[DockerManager] = None
        self.use_llm_fallback = use_llm_fallback
        self.auto_install = auto_install
        
        # Initialize NLP2CMD components
        self.nlp2cmd_instances = {
            "shell": NLP2CMD(adapter=ShellAdapter()),
            "docker": NLP2CMD(adapter=DockerAdapter()),
            "kubernetes": NLP2CMD(adapter=KubernetesAdapter()),
        }
        
        # Initialize LLM fallback if enabled
        if self.use_llm_fallback:
            try:
                self.llm_client = LiteLLMClient()
            except ImportError:
                if auto_install:
                    subprocess.run(
                        [sys.executable, "-m", "pip", "install", "litellm"],
                        check=True,
                        capture_output=True,
                    )
                    self.llm_client = LiteLLMClient()
                else:
                    self.llm_client = None
        else:
            self.llm_client = None
        
        # Service templates
        self.templates = {
            ServiceType.CHAT_SERVICE: self._create_chat_template,
            ServiceType.EMAIL_SERVICE: self._create_email_template,
            ServiceType.CONTACT_FORM: self._create_contact_template,
            ServiceType.DATABASE: self._create_database_template,
            ServiceType.CACHE: self._create_cache_template,
        }
    
    async def execute(self, command: str, dsl: str = "auto") -> dict[str, Any]:
        """
        Execute a natural language command.
        
        Args:
            command: Natural language command in Polish or English
            dsl: DSL type to use (auto, shell, docker, kubernetes)
            
        Returns:
            Result dictionary with status and generated configurations
        """
        # First try the custom parser for DevOps-specific commands
        parsed = self.parser.parse(command)
        
        # If it's a DevOps command we understand, handle it
        if parsed["intent"] != "unknown" and parsed["service_type"] is not None:
            # Route to handler
            handlers = {
                "deploy": self._handle_deploy,
                "configure": self._handle_configure,
                "scale": self._handle_scale,
                "status": self._handle_status,
                "logs": self._handle_logs,
                "test": self._handle_test,
                "monitor": self._handle_monitor,
                "restart": self._handle_restart,
                "stop": self._handle_stop,
            }
            
            handler = handlers.get(parsed["intent"], self._handle_unknown)
            result = await handler(parsed)
        else:
            # Fall back to NLP2CMD core for general commands
            result = await self._execute_with_nlp2cmd(command, dsl)
        
        # Record in history
        self.deployment_history.append({
            "command": command,
            "parsed": parsed,
            "result": result,
            "timestamp": datetime.now().isoformat(),
        })
        
        return result
    
    async def _handle_deploy(self, parsed: dict) -> dict[str, Any]:
        """Handle deploy intent."""
        service_type = parsed.get("service_type")
        entities = parsed.get("entities", {})
        
        if service_type and service_type in self.templates:
            # Create service from template
            config = self.templates[service_type](entities)
            self.services[config.name] = config
            
            # Generate deployment artifacts
            plan = DeploymentPlan(services=[config])
            compose = plan.to_compose()
            
            # Save files to disk
            compose_file = self.file_manager.save_docker_compose(compose, f"{config.name}-docker-compose.yml")
            service_file = self.file_manager.save_service_config({
                "name": config.name,
                "service_type": config.service_type.value,
                "port": config.port,
                "image": config.image,
                "env_vars": config.env_vars,
                "volumes": config.volumes,
                "depends_on": config.depends_on,
                "healthcheck": config.healthcheck,
                "replicas": config.replicas,
            }, config.name)
            
            # Initialize Docker manager and start services
            compose_filename = f"{config.name}-docker-compose.yml"
            self.docker_manager = DockerManager(compose_filename, self.file_manager.output_dir)
            docker_result = await self.docker_manager.start_services(show_logs=False)
            
            result = {
                "status": "success",
                "action": "deploy",
                "service": config.name,
                "config": {
                    "port": config.port,
                    "image": config.image,
                    "env_vars": config.env_vars,
                },
                "docker_compose": compose,
                "files_saved": {
                    "docker_compose": compose_file,
                    "service_config": service_file,
                },
                "docker_execution": docker_result,
                "message": f"Przygotowano deployment dla {config.name} na porcie {config.port}",
                "note": f"Pliki zapisane w: {self.file_manager.output_dir}"
            }
            
            # Show container status if Docker started successfully
            if docker_result.get("status") == "success":
                container_status = docker_result.get("container_status", {})
                if container_status.get("containers"):
                    result["containers"] = container_status["containers"]
                    result["container_count"] = container_status["total"]
            
            return result
        
        return {
            "status": "error",
            "message": "Nie rozpoznano typu usługi. Dostępne: chat, email, contact, database, cache",
        }
    
    async def _handle_configure(self, parsed: dict) -> dict[str, Any]:
        """Handle configure intent."""
        service_type = parsed.get("service_type")
        entities = parsed.get("entities", {})
        
        if service_type == ServiceType.EMAIL_SERVICE:
            return await self._configure_email(entities)
        
        if service_type == ServiceType.CHAT_SERVICE:
            return await self._configure_chat(entities)
        
        return {
            "status": "needs_input",
            "message": "Potrzebuję więcej informacji do konfiguracji.",
            "required": ["service_type", "credentials"],
        }
    
    async def _handle_scale(self, parsed: dict) -> dict[str, Any]:
        """Handle scale intent."""
        entities = parsed.get("entities", {})
        replicas = entities.get("replicas", 2)
        
        return {
            "status": "success",
            "action": "scale",
            "replicas": replicas,
            "kubectl_command": f"kubectl scale deployment --replicas={replicas}",
            "docker_command": f"docker-compose up --scale service={replicas}",
        }
    
    async def _handle_status(self, parsed: dict) -> dict[str, Any]:
        """Handle status intent."""
        return {
            "status": "success",
            "action": "status",
            "services": {name: {"port": cfg.port, "type": cfg.service_type.value} 
                        for name, cfg in self.services.items()},
            "commands": {
                "docker": "docker-compose ps",
                "kubernetes": "kubectl get pods",
            }
        }
    
    async def _handle_stop(self, parsed: dict) -> dict[str, Any]:
        """Handle stop intent."""
        return {
            "status": "success",
            "action": "stop",
            "commands": {
                "docker": "docker-compose down",
                "kubernetes": "kubectl delete deployment",
            }
        }
    
    async def _handle_unknown(self, parsed: dict) -> dict[str, Any]:
        """
        Handle unknown intent by trying NLP2CMD core with LLM fallback.
        """
        command = parsed.get("original_text", "")
        
        # Try NLP2cmd core as fallback
        result = await self._execute_with_nlp2cmd(command, "auto")
        
        if result.get("status") == "error":
            return {
                "status": "clarification_needed",
                "message": "Nie zrozumiałem polecenia. Przykłady:",
                "examples": [
                    "Uruchom serwis czatu na porcie 8080",
                    "Skonfiguruj email dla jan@example.com",
                    "Pokaż status usług",
                    "Uruchom docker",
                    "Stwórz plik konfiguracyjny",
                ],
                "nlp2cmd_result": result,
            }
        
        return result
    
    async def _execute_with_nlp2cmd(self, command: str, dsl: str) -> dict[str, Any]:
        """
        Execute command using NLP2CMD core with LLM fallback.
        """
        try:
            # Use the appropriate NLP2CMD instance
            nlp2cmd = self.nlp2cmd_instances.get(dsl, self.nlp2cmd_instances["shell"])
            
            # Transform the command
            result = nlp2cmd.transform(command)
            
            if result.command and not result.command.startswith("#"):
                return {
                    "status": "success",
                    "action": "command_generated",
                    "command": result.command,
                    "dsl": dsl,
                    "confidence": getattr(result, "confidence", 0.0),
                    "plan": result.plan.model_dump() if hasattr(result, "plan") else None,
                    "message": f"Wygenerowano komendę: {result.command}",
                }
            else:
                # Try LLM fallback if enabled
                if self.use_llm_fallback and self.llm_client:
                    return await self._try_llm_fallback(command)
                else:
                    return {
                        "status": "error",
                        "message": "Nie udało się wygenerować komendy",
                        "suggestion": "Włącz --auto-install aby użyć LLM fallback",
                    }
        
        except Exception as e:
            return {
                "status": "error",
                "message": f"Błąd podczas przetwarzania: {str(e)}",
            }
    
    async def _try_llm_fallback(self, command: str) -> dict[str, Any]:
        """
        Try to generate command using LLM fallback.
        """
        try:
            system_prompt = """Jesteś ekspertem linii komend. Konwertuj prośbę użytkownika na prawidłową komendę shell.

Zasady:
- Odpowiedz TYLKO komendą, bez wyjaśnień
- Używaj standardowych komend shell/Dockera
- Dla polskich słów kluczowych (uruchom, stwórz, pokaż) użyj odpowiedników angielskich
- Trzymaj komendy proste i wykonywalne"""
            
            response = await self.llm_client.complete(
                user=command,
                system=system_prompt,
                max_tokens=200,
                temperature=0.1
            )
            
            command = response.strip()
            
            if command and not command.startswith("#") and not command.lower().startswith(("i'm sorry", "sorry", "i cannot", "cannot")):
                return {
                    "status": "success",
                    "action": "llm_fallback",
                    "command": command,
                    "dsl": "shell",
                    "message": "Wygenerowano komendę za pomocą LLM fallback",
                    "llm_used": True,
                }
            else:
                return {
                    "status": "error",
                    "message": "LLM fallback nie udał się wygenerować prawidłowej komendy",
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"LLM fallback nieudany: {str(e)}",
            }
    
    async def _handle_logs(self, parsed: dict) -> dict[str, Any]:
        """Handle logs intent."""
        service_type = parsed.get("service_type")
        
        if service_type:
            service_name = self._get_service_name_by_type(service_type)
            return {
                "status": "success",
                "action": "logs",
                "service": service_name,
                "message": f"Pokazywanie logów dla {service_name}",
                "docker_command": f"docker-compose logs -f {service_name}" if service_name else "docker-compose logs -f"
            }
        else:
            return {
                "status": "success",
                "action": "logs",
                "message": "Pokazywanie logów wszystkich usług",
                "docker_command": "docker-compose logs -f"
            }
    
    async def _handle_test(self, parsed: dict) -> dict[str, Any]:
        """Handle test intent."""
        service_type = parsed.get("service_type")
        entities = parsed.get("entities", {})
        
        if service_type:
            service_name = self._get_service_name_by_type(service_type)
            return {
                "status": "success",
                "action": "test",
                "service": service_name,
                "message": f"Testowanie połączenia z {service_name}",
                "test_commands": self._get_test_commands(service_type, entities)
            }
        else:
            return {
                "status": "needs_input",
                "message": "Potrzebuję więcej informacji do konfiguracji.",
                "required": ["service_type"]
            }
    
    async def _handle_monitor(self, parsed: dict) -> dict[str, Any]:
        """Handle monitor intent."""
        return {
            "status": "success",
            "action": "monitor",
            "message": "Uruchamianie monitoringu usług",
            "monitoring_tools": ["docker stats", "htop", "docker-compose ps"],
            "dashboard_url": "http://localhost:3000/grafana"
        }
    
    async def _handle_restart(self, parsed: dict) -> dict[str, Any]:
        """Handle restart intent."""
        service_type = parsed.get("service_type")
        
        if service_type:
            service_name = self._get_service_name_by_type(service_type)
            return {
                "status": "success",
                "action": "restart",
                "service": service_name,
                "message": f"Restartowanie {service_name}",
                "docker_command": f"docker-compose restart {service_name}"
            }
        else:
            return {
                "status": "success",
                "action": "restart",
                "message": "Restartowanie wszystkich usług",
                "docker_command": "docker-compose restart"
            }
    
    def _get_service_name_by_type(self, service_type: ServiceType) -> str:
        """Get service name by service type."""
        type_to_name = {
            ServiceType.CHAT_SERVICE: "chat-service",
            ServiceType.EMAIL_SERVICE: "email-service",
            ServiceType.CONTACT_FORM: "contact-service",
            ServiceType.DATABASE: "postgres",
            ServiceType.CACHE: "redis",
        }
        return type_to_name.get(service_type, "unknown")
    
    def _get_test_commands(self, service_type: ServiceType, entities: dict) -> list[str]:
        """Get test commands for service type."""
        commands = []
        
        if service_type == ServiceType.CACHE:
            commands.append("docker exec redis redis-cli ping")
            commands.append("telnet localhost 6379")
        elif service_type == ServiceType.DATABASE:
            commands.append("docker exec postgres pg_isready -U nlp2cmd")
            commands.append("psql -h localhost -U nlp2cmd -d postgresql -c 'SELECT 1;'")
        elif service_type == ServiceType.CHAT_SERVICE:
            port = entities.get("port", 8080)
            commands.append(f"curl -f http://localhost:{port}/health")
            commands.append(f"curl -f http://localhost:{port}/api/status")
        
        return commands
    
    async def save_full_deployment_plan(self, name: str = "full-deployment") -> dict[str, Any]:
        """Save complete deployment plan with all services."""
        if not self.services:
            return {
                "status": "error",
                "message": "Brak usług do zapisania. Najpierw dodaj usługi."
            }
        
        # Create deployment plan with all services
        plan = DeploymentPlan(services=list(self.services.values()))
        compose = plan.to_compose()
        
        # Save files
        compose_file = self.file_manager.save_docker_compose(compose, f"{name}-docker-compose.yml")
        
        # Include dependency services in deployment plan
        all_services = {}
        for name, config in self.services.items():
            all_services[name] = {
                "name": config.name,
                "service_type": config.service_type.value,
                "port": config.port,
                "image": config.image,
                "env_vars": config.env_vars,
                "volumes": config.volumes,
                "depends_on": config.depends_on,
                "healthcheck": config.healthcheck,
                "replicas": config.replicas,
            }
        
        # Add dependency services to the plan
        for service_name, service_def in compose["services"].items():
            if service_name not in all_services:
                # This is a dependency service (redis, postgres, etc.)
                if service_name == "redis":
                    all_services[service_name] = {
                        "name": service_name,
                        "service_type": "cache",
                        "port": 6379,
                        "image": "redis:7-alpine",
                        "env_vars": {},
                        "volumes": [],
                        "depends_on": [],
                        "healthcheck": None,
                        "replicas": 1,
                    }
                elif service_name == "postgres":
                    all_services[service_name] = {
                        "name": service_name,
                        "service_type": "database", 
                        "port": 5432,
                        "image": "postgres:15-alpine",
                        "env_vars": {
                            "POSTGRES_DB": "nlp2cmd_db",
                            "POSTGRES_USER": "nlp2cmd",
                            "POSTGRES_PASSWORD": "${DB_PASSWORD}"
                        },
                        "volumes": ["postgres_data:/var/lib/postgresql/data"],
                        "depends_on": [],
                        "healthcheck": "pg_isready -U nlp2cmd",
                        "replicas": 1,
                    }
        
        deployment_file = self.file_manager.save_deployment_plan({
            "services": all_services,
            "deployment_plan": compose,
            "generated_at": datetime.now().isoformat(),
            "total_services": len(all_services),
        }, name)
        
        return {
            "status": "success",
            "message": f"Zapisano pełen plan deployment z {len(all_services)} usługami (w tym zależności)",
            "files_saved": {
                "docker_compose": compose_file,
                "deployment_plan": deployment_file,
            },
            "output_directory": str(self.file_manager.output_dir)
        }
    
    def get_generated_files_info(self) -> dict[str, Any]:
        """Get information about generated files."""
        if not self.file_manager.output_dir.exists():
            return {
                "status": "info",
                "message": "Brak wygenerowanych plików",
                "output_directory": str(self.file_manager.output_dir)
            }
        
        files = []
        for file_path in self.file_manager.output_dir.iterdir():
            if file_path.is_file():
                files.append({
                    "name": file_path.name,
                    "path": str(file_path),
                    "size": file_path.stat().st_size,
                    "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                })
        
        return {
            "status": "info",
            "output_directory": str(self.file_manager.output_dir),
            "files": files,
            "total_files": len(files)
        }
    
    async def show_container_logs(self, follow: bool = False, lines: int = 20, service: Optional[str] = None) -> dict[str, Any]:
        """Show logs from running containers."""
        if not self.docker_manager:
            return {
                "status": "error",
                "message": "Brak aktywnego menedżera Docker. Najpierw uruchom usługę."
            }
        
        await self.docker_manager.show_logs(follow=follow, lines=lines, service=service)
        
        return {
            "status": "success",
            "message": "Logi wyświetlone"
        }
    
    async def get_container_status(self) -> dict[str, Any]:
        """Get current status of all containers."""
        if not self.docker_manager:
            return {
                "status": "error",
                "message": "Brak aktywnego menedżera Docker. Najpierw uruchom usługę."
            }
        
        return await self.docker_manager.get_container_status()
    
    async def stop_containers(self) -> dict[str, Any]:
        """Stop all running containers."""
        if not self.docker_manager:
            return {
                "status": "error",
                "message": "Brak aktywnego menedżera Docker. Najpierw uruchom usługę."
            }
        
        result = await self.docker_manager.stop_services()
        
        # Reset docker manager after stopping
        if result.get("status") == "success":
            self.docker_manager = None
        
        return result
    
    # Service templates
    def _create_chat_template(self, entities: dict) -> ServiceConfig:
        """Create chat service configuration."""
        port = entities.get("port", 8080)
        return ServiceConfig(
            name="chat-service",
            service_type=ServiceType.CHAT_SERVICE,
            port=port,
            image="nginx:alpine",  # Use nginx for testing
            env_vars={
                "PORT": str(port),
                "REDIS_URL": "redis://redis:6379",
                "WS_ENABLED": "true",
            },
            depends_on=["redis"],
        )
    
    def _create_email_template(self, entities: dict) -> ServiceConfig:
        """Create email service configuration."""
        port = entities.get("port", 8082)
        email = entities.get("email", "contact@example.com")
        
        # Extract domain from email for SMTP/IMAP hosts
        if "@" in email:
            domain = email.split("@")[1]
            imap_host = f"imap.{domain}"
            smtp_host = f"smtp.{domain}"
        else:
            imap_host = "imap.gmail.com"
            smtp_host = "smtp.gmail.com"
        
        return ServiceConfig(
            name="email-service",
            service_type=ServiceType.EMAIL_SERVICE,
            port=port,
            image="nginx:alpine",  # Use nginx for testing
            env_vars={
                "PORT": str(port),
                "EMAIL_ADDRESS": email,
                "IMAP_HOST": imap_host,
                "SMTP_HOST": smtp_host,
                "EMAIL_SERVICE_ENABLED": "true",
            },
        )
    
    def _create_contact_template(self, entities: dict) -> ServiceConfig:
        """Create contact form service configuration."""
        port = entities.get("port", 8081)
        email = entities.get("email", "contact@example.com")
        
        return ServiceConfig(
            name="contact-service",
            service_type=ServiceType.CONTACT_FORM,
            port=port,
            image="nginx:alpine",  # Use nginx for testing
            env_vars={
                "PORT": str(port),
                "CONTACT_FORM_ENABLED": "true",
                "RECIPIENT_EMAIL": email,
                "SMTP_HOST": "smtp.gmail.com",
            },
        )
    
    def _create_database_template(self, entities: dict) -> ServiceConfig:
        """Create database service configuration."""
        return ServiceConfig(
            name="postgres",
            service_type=ServiceType.DATABASE,
            port=5432,
            image="postgres:15-alpine",
            env_vars={
                "POSTGRES_DB": entities.get("database", "nlp2cmd_db"),
                "POSTGRES_USER": "nlp2cmd",
                "POSTGRES_PASSWORD": "${DB_PASSWORD}",
            },
            volumes=["postgres_data:/var/lib/postgresql/data"],
            healthcheck="pg_isready -U nlp2cmd",
        )
    
    def _create_cache_template(self, entities: dict) -> ServiceConfig:
        """Create cache service configuration."""
        return ServiceConfig(
            name="redis",
            service_type=ServiceType.CACHE,
            port=6379,
            image="redis:7-alpine",
            volumes=["redis_data:/data"],
            healthcheck="redis-cli ping",
        )
    
    async def _configure_email(self, entities: dict) -> dict[str, Any]:
        """Configure email service with credentials."""
        email = entities.get("email", "")
        
        return {
            "status": "configuration_ready",
            "service": "email",
            "config": {
                "email": email,
                "imap_host": self._guess_imap_host(email),
                "smtp_host": self._guess_smtp_host(email),
            },
            "env_file_content": f"""
# Email Configuration
EMAIL_ADDRESS={email}
EMAIL_PASSWORD=${{EMAIL_PASSWORD}}
IMAP_HOST={self._guess_imap_host(email)}
IMAP_PORT=993
SMTP_HOST={self._guess_smtp_host(email)}
SMTP_PORT=587
""".strip(),
            "next_step": "Ustaw zmienną EMAIL_PASSWORD w pliku .env",
        }
    
    async def _configure_chat(self, entities: dict) -> dict[str, Any]:
        """Configure chat service."""
        port = entities.get("port", 8080)
        
        return {
            "status": "configuration_ready",
            "service": "chat",
            "config": {
                "port": port,
                "websocket_path": "/ws",
                "redis_required": True,
            },
            "message": f"Serwis czatu gotowy na porcie {port}",
        }
    
    def _guess_imap_host(self, email: str) -> str:
        """Guess IMAP host from email domain."""
        if not email or "@" not in email:
            return "imap.example.com"
        
        domain = email.split("@")[1].lower()
        
        known_hosts = {
            "gmail.com": "imap.gmail.com",
            "outlook.com": "outlook.office365.com",
            "hotmail.com": "outlook.office365.com",
            "yahoo.com": "imap.mail.yahoo.com",
            "wp.pl": "imap.wp.pl",
            "onet.pl": "imap.poczta.onet.pl",
            "interia.pl": "imap.interia.pl",
        }
        
        return known_hosts.get(domain, f"imap.{domain}")
    
    def _guess_smtp_host(self, email: str) -> str:
        """Guess SMTP host from email domain."""
        if not email or "@" not in email:
            return "smtp.example.com"
        
        domain = email.split("@")[1].lower()
        
        known_hosts = {
            "gmail.com": "smtp.gmail.com",
            "outlook.com": "smtp.office365.com",
            "hotmail.com": "smtp.office365.com",
            "yahoo.com": "smtp.mail.yahoo.com",
            "wp.pl": "smtp.wp.pl",
            "onet.pl": "smtp.poczta.onet.pl",
            "interia.pl": "smtp.interia.pl",
        }
        
        return known_hosts.get(domain, f"smtp.{domain}")
