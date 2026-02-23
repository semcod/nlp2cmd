"""
Shell command generators for NLP2CMD.

Contains specialized generators for different command categories.
"""

from __future__ import annotations

import shlex
from typing import Any, Optional


class FileOperationGenerator:
    """Generator for file operations."""
    
    def generate_file_search(self, entities: dict[str, Any]) -> str:
        """Generate find command."""
        target = entities.get("target", "files")
        filters = entities.get("filters", [])
        
        cmd_parts = ["find", "."]
        
        # Add name filter
        if target != "files":
            if "*" in target or "?" in target:
                cmd_parts.extend(["-name", shlex.quote(target)])
            else:
                cmd_parts.extend(["-name", f"*{target}*"])
        
        # Handle structured filters
        for filter_item in filters:
            if isinstance(filter_item, dict):
                attribute = filter_item.get("attribute", "")
                operator = filter_item.get("operator", "")
                value = filter_item.get("value", "")
                
                if attribute == "size" and operator == ">" and value:
                    # Convert "100M" to "100M"
                    size_value = str(value).replace(" ", "")
                    cmd_parts.extend(["-size", f"+{size_value}"])
                elif attribute == "size" and operator == "<" and value:
                    size_value = str(value).replace(" ", "")
                    cmd_parts.extend(["-size", f"-{size_value}"])
                elif attribute == "mtime" and value:
                    # Handle time filters like "7_days"
                    if "days" in str(value):
                        days = str(value).replace("_days", "").replace("days", "")
                        cmd_parts.extend(["-mtime", f"-{days}"])
            else:
                # Handle legacy string filters
                if "większe niż" in str(filter_item) or "larger than" in str(filter_item):
                    size = self._extract_size(filter_item)
                    if size:
                        cmd_parts.extend(["-size", f"+{size}"])
                elif "mniejsze niż" in str(filter_item) or "smaller than" in str(filter_item):
                    size = self._extract_size(filter_item)
                    if size:
                        cmd_parts.extend(["-size", f"-{size}"])
        
        cmd_parts.extend(["-type", "f"])
        
        # Add print format and sorting for structured queries
        if any(isinstance(f, dict) for f in filters):
            cmd_parts.extend(["-printf", "%s %p\\n"])
            cmd_parts.extend(["|", "sort", "-nr"])
        
        return " ".join(cmd_parts)
    
    def generate_file_operation(self, entities: dict[str, Any]) -> str:
        """Generate file operation command."""
        operation = entities.get("operation", "")
        target = entities.get("target", "")
        destination = entities.get("destination", "")
        
        operations = {
            "kopiuj": f"cp {shlex.quote(target)} {shlex.quote(destination)}" if destination else f"cp {shlex.quote(target)} .",
            "copy": f"cp {shlex.quote(target)} {shlex.quote(destination)}" if destination else f"cp {shlex.quote(target)} .",
            "przenieś": f"mv {shlex.quote(target)} {shlex.quote(destination)}" if destination else f"mv {shlex.quote(target)} .",
            "move": f"mv {shlex.quote(target)} {shlex.quote(destination)}" if destination else f"mv {shlex.quote(target)} .",
            "usuń": f"rm -rf {shlex.quote(target)}",
            "delete": f"rm -rf {shlex.quote(target)}",
            "remove": f"rm -rf {shlex.quote(target)}",
            "utwórz": f"mkdir -p {shlex.quote(target)}",
            "create": f"mkdir -p {shlex.quote(target)}",
            "zmień nazwę": f"mv {shlex.quote(target)} {shlex.quote(destination)}" if destination else f"mv {shlex.quote(target)} NEW_NAME",
            "rename": f"mv {shlex.quote(target)} {shlex.quote(destination)}" if destination else f"mv {shlex.quote(target)} NEW_NAME",
        }
        
        return operations.get(operation, f"# Unknown operation: {operation}")
    
    def _extract_size(self, filter_text: str) -> Optional[str]:
        """Extract size from filter text."""
        import re
        size_match = re.search(r'(\d+)(KB|MB|GB)?', filter_text, re.IGNORECASE)
        if size_match:
            size = int(size_match.group(1))
            unit = size_match.group(2) or "B"
            
            if unit.upper() == "KB":
                return f"{size}k"
            elif unit.upper() == "MB":
                return f"{size}M"
            elif unit.upper() == "GB":
                return f"{size}G"
            else:
                return str(size)
        return None


class ProcessManagementGenerator:
    """Generator for process management commands."""
    
    def generate_process_management(self, entities: dict[str, Any]) -> str:
        """Generate process management command."""
        action = entities.get("action", "")
        process_name = entities.get("process_name", "")
        pid = entities.get("pid", "")
        
        # Handle PID-based operations
        if pid and action in ["kill", "zabij"]:
            return f"kill -9 {pid}"
        
        # Handle service management (systemctl)
        if process_name and action in ["start", "uruchom", "status", "stop", "zatrzymaj", "restart"]:
            systemctl_actions = {
                "start": "start",
                "uruchom": "start", 
                "status": "status",
                "stop": "stop",
                "zatrzymaj": "stop",
                "restart": "restart"
            }
            systemctl_action = systemctl_actions.get(action, "status")
            return f"systemctl {systemctl_action} {process_name}"
        
        actions = {
            "zabij": f"pkill -f {shlex.quote(process_name)}" if process_name else "pkill -f process_name",
            "kill": f"pkill -f {shlex.quote(process_name)}" if process_name else "pkill -f process_name",
            "zatrzymaj": f"pkill -STOP {shlex.quote(process_name)}" if process_name else "pkill -STOP process_name",
            "stop": f"pkill -STOP {shlex.quote(process_name)}" if process_name else "pkill -STOP process_name",
            "wznów": f"pkill -CONT {shlex.quote(process_name)}" if process_name else "pkill -CONT process_name",
            "resume": f"pkill -CONT {shlex.quote(process_name)}" if process_name else "pkill -CONT process_name",
            "uruchom": f"{shlex.quote(process_name)} &" if process_name else "command &",
            "start": f"{shlex.quote(process_name)} &" if process_name else "command &",
            "pokaż": "ps aux",
            "show": "ps aux",
            "lista": "ps aux",
            "list": "ps aux",
        }
        
        return actions.get(action, f"ps aux | grep {shlex.quote(process_name)}" if process_name else "ps aux")
    
    def generate_process_monitoring(self, entities: dict[str, Any]) -> str:
        """Generate process monitoring command."""
        metric = entities.get("metric", "cpu")
        limit = entities.get("limit", 10)
        
        if metric == "cpu":
            return f"ps aux --sort=-%cpu | head -{limit}"
        elif metric == "memory":
            return f"ps aux --sort=-%mem | head -{limit}"
        elif metric == "time":
            return f"ps aux --sort=-etime | head -{limit}"
        else:
            return f"ps aux | head -{limit}"


class NetworkGenerator:
    """Generator for network commands."""
    
    def generate_network(self, entities: dict[str, Any]) -> str:
        """Generate network command."""
        action = entities.get("action", "")
        host = entities.get("host", "")
        
        actions = {
            "ping": f"ping {shlex.quote(host)}" if host else "ping google.com",
            "sprawdź": f"ping {shlex.quote(host)}" if host else "ping google.com",
            "check": f"ping {shlex.quote(host)}" if host else "ping google.com",
            "połączenie": f"telnet {shlex.quote(host)} 80" if host else "netstat -tuln",
            "connection": f"telnet {shlex.quote(host)} 80" if host else "netstat -tuln",
            "porty": "netstat -tuln",
            "ports": "netstat -tuln",
            "interfejsy": "ip addr show",
            "interfaces": "ip addr show",
            "pobierz": f"wget {shlex.quote(host)}" if host else "wget URL",
            "download": f"wget {shlex.quote(host)}" if host else "wget URL",
        }
        
        return actions.get(action, "netstat -tuln")


class SystemMaintenanceGenerator:
    """Generator for system maintenance commands."""
    
    def generate_system_maintenance(self, entities: dict[str, Any]) -> str:
        """Generate system maintenance command."""
        action = entities.get("action", "")
        
        actions = {
            "aktualizuj": "sudo apt update && sudo apt upgrade -y",
            "update": "sudo apt update && sudo apt upgrade -y",
            "czyszczenie": "sudo apt autoremove && sudo apt autoclean",
            "cleanup": "sudo apt autoremove && sudo apt autoclean",
            "restart": "sudo reboot",
            "wyłącz": "sudo shutdown -h now",
            "shutdown": "sudo shutdown -h now",
            "logi": "journalctl -f",
            "logs": "journalctl -f",
            "status": "systemctl status",
            "services": "systemctl list-units --type=service",
        }
        
        return actions.get(action, f"systemctl {action}")


class DevelopmentGenerator:
    """Generator for development commands."""
    
    def generate_development(self, entities: dict[str, Any]) -> str:
        """Generate development command."""
        action = entities.get("action", "")
        target = entities.get("target", "")
        
        actions = {
            "uruchom": f"python {shlex.quote(target)}" if target else "python app.py",
            "run": f"python {shlex.quote(target)}" if target else "python app.py",
            "test": "python -m pytest",
            "testy": "python -m pytest",
            "instaluj": "pip install -r requirements.txt",
            "install": "pip install -r requirements.txt",
            "build": "python -m build",
            "buduj": "python -m build",
            "lint": "flake8 .",
            "format": "black .",
            "formatuj": "black .",
        }
        
        return actions.get(action, f"python {shlex.quote(target)}" if target else "python app.py")


class GitGenerator:
    """Generator for git commands."""
    
    def generate_git(self, entities: dict[str, Any]) -> str:
        """Generate git command."""
        action = entities.get("action", "")
        branch = entities.get("branch", "")
        
        commands = {
            "init": "git init",
            "klonuj": "git clone",
            "clone": "git clone",
            "dodaj": "git add .",
            "add": "git add .",
            "zapisz": "git commit -m 'Update'",
            "commit": "git commit -m 'Update'",
            "wypchnij": f"git push origin {branch}" if branch else "git push",
            "push": f"git push origin {branch}" if branch else "git push",
            "pobierz": f"git pull origin {branch}" if branch else "git pull",
            "pull": f"git pull origin {branch}" if branch else "git pull",
            "status": "git status",
            "gałąź": f"git checkout {branch}" if branch else "git branch",
            "branch": f"git checkout {branch}" if branch else "git branch",
            "historia": "git log --oneline -10",
            "log": "git log --oneline -10",
        }
        
        return commands.get(action, f"git {action}")


class DockerGenerator:
    """Generator for docker commands."""
    
    def generate_docker(self, entities: dict[str, Any]) -> str:
        """Generate docker command."""
        action = entities.get("action", "")
        container = entities.get("container", "")
        image = entities.get("image", "")
        
        commands = {
            "uruchom": f"docker run -d {image}" if image else "docker run -d IMAGE",
            "run": f"docker run -d {image}" if image else "docker run -d IMAGE",
            "zatrzymaj": f"docker stop {container}" if container else "docker stop CONTAINER",
            "stop": f"docker stop {container}" if container else "docker stop CONTAINER",
            "usuń": f"docker rm {container}" if container else "docker rm CONTAINER",
            "rm": f"docker rm {container}" if container else "docker rm CONTAINER",
            "pokaż": "docker ps -a",
            "show": "docker ps -a",
            "obrazy": "docker images",
            "images": "docker images",
            "logi": f"docker logs {container}" if container else "docker logs CONTAINER",
            "logs": f"docker logs {container}" if container else "docker logs CONTAINER",
            "buduj": "docker build -t IMAGE .",
            "build": "docker build -t IMAGE .",
        }
        
        return commands.get(action, f"docker {action}")


class TextProcessingGenerator:
    """Generator for text processing commands."""
    
    def generate_text_processing(self, entities: dict[str, Any]) -> str:
        """Generate text processing command."""
        action = entities.get("action", "")
        pattern = entities.get("pattern", "")
        file = entities.get("file", "")
        
        if action == "grep" or action == "szukaj":
            if file:
                return f"grep {shlex.quote(pattern)} {shlex.quote(file)}"
            else:
                return f"grep -r {shlex.quote(pattern)} ."
        elif action == "replace" or action == "zamień":
            return f"sed -i 's/{pattern}/NEW/g' {shlex.quote(file)}" if file else "sed -i 's/OLD/NEW/g' FILE"
        elif action == "count" or action == "licz":
            return f"wc -l {shlex.quote(file)}" if file else "wc -l FILE"
        else:
            return f"grep {shlex.quote(pattern)} {shlex.quote(file)}" if file else f"grep {shlex.quote(pattern)}"
