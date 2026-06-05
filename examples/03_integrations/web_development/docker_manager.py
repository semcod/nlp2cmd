# DockerManager - extracted from nlp2cmd_web_controller.py
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

class DockerManager:
    """Manages Docker Compose operations and container lifecycle."""
    
    def __init__(self, compose_file_path: str, output_dir: str = "./generated"):
        self.compose_file = Path(output_dir) / compose_file_path
        self.compose_dir = Path(output_dir)
        self.running_containers = set()
    
    async def start_services(self, show_logs: bool = True) -> dict[str, Any]:
        """Start Docker Compose services and optionally show logs."""
        if not self.compose_file.exists():
            return {
                "status": "error",
                "message": f"Plik Docker Compose nie istnieje: {self.compose_file}"
            }
        
        try:
            # Start services in detached mode
            print(f"\n🚀 Uruchamianie usług z: {self.compose_file}")
            print_rule()
            
            result = subprocess.run(
                ["docker-compose", "-f", self.compose_file.name, "up", "-d"],
                cwd=self.compose_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return {
                    "status": "error",
                    "message": f"Błąd uruchamiania: {result.stderr}"
                }
            
            print("✅ Usługi uruchomione pomyślnie")
            
            # Get container status
            status_result = await self.get_container_status()
            
            # Show logs if requested
            if show_logs:
                await self.show_logs(follow=False, lines=10)
            
            return {
                "status": "success",
                "message": "Usługi uruchomione pomyślnie",
                "container_status": status_result
            }
            
        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "message": "Timeout podczas uruchamiania usług"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Błąd: {str(e)}"
            }
    
    async def get_container_status(self) -> dict[str, Any]:
        """Get status of all containers."""
        try:
            result = subprocess.run(
                ["docker-compose", "-f", self.compose_file.name, "ps"],
                cwd=self.compose_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                # Skip header line (first line with column names)
                container_lines = [line.strip() for line in lines[1:] if line.strip()]
                
                containers = []
                for line in container_lines:
                    parts = line.split()
                    if len(parts) >= 6:
                        container_name = parts[0]
                        image = parts[1]
                        
                        # Find status column (contains "Up" or other status)
                        status = "unknown"
                        ports = ""
                        
                        # Status is typically around column 5-6, look for "Up"
                        for i, part in enumerate(parts):
                            if part == "Up" and i > 0:
                                # Status spans from this position to before ports
                                status = " ".join(parts[i:i+3])  # Up + time info
                                # Find ports (usually after status)
                                if i + 3 < len(parts):
                                    remaining = " ".join(parts[i+3:])
                                    if "->" in remaining:
                                        ports = remaining
                                break
                        
                        containers.append({
                            "name": container_name,
                            "status": status,
                            "ports": ports,
                            "image": image
                        })
                
                return {
                    "status": "success",
                    "containers": containers,
                    "total": len(containers)
                }
            else:
                return {
                    "status": "error",
                    "message": f"Błąd sprawdzania statusu: {result.stderr}"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Błąd sprawdzania statusu: {str(e)}"
            }
    
    async def show_logs(self, follow: bool = False, lines: int = 20, service: Optional[str] = None) -> None:
        """Show logs from containers."""
        try:
            cmd = ["docker-compose", "-f", self.compose_file.name, "logs"]
            
            if follow:
                cmd.append("--follow")
            if lines:
                cmd.extend(["--tail", str(lines)])
            if service:
                cmd.append(service)
            
            print(f"\n📋 Logi kontenerów{' (follow)' if follow else ''}:")
            print_rule()
            
            if follow:
                # For follow mode, we need to stream the output
                process = subprocess.Popen(
                    cmd,
                    cwd=self.compose_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                
                try:
                    for line in iter(process.stdout.readline, ''):
                        if line:
                            print(line.rstrip())
                        else:
                            break
                except KeyboardInterrupt:
                    print("\n👋 Przerywam pokazywanie logów...")
                    process.terminate()
                    process.wait()
            else:
                # For non-follow mode, just capture and show
                result = subprocess.run(
                    cmd,
                    cwd=self.compose_dir,
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                
                if result.stdout:
                    print(result.stdout)
                if result.stderr:
                    print(f"⚠️ Błędy: {result.stderr}")
                    
        except subprocess.TimeoutExpired:
            print("⏰ Timeout podczas pobierania logów")
        except Exception as e:
            print(f"❌ Błąd pokazywania logów: {str(e)}")
    
    async def stop_services(self) -> dict[str, Any]:
        """Stop and remove containers."""
        try:
            print(f"\n🛑 Zatrzymywanie usług...")
            
            result = subprocess.run(
                ["docker-compose", "-f", self.compose_file.name, "down"],
                cwd=self.compose_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print("✅ Usługi zatrzymane pomyślnie")
                return {
                    "status": "success",
                    "message": "Usługi zatrzymane i usunięte"
                }
            else:
                return {
                    "status": "error",
                    "message": f"Błąd zatrzymywania: {result.stderr}"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Błąd zatrzymywania: {str(e)}"
            }
