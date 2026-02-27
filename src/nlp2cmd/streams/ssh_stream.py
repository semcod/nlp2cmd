"""
SSH Stream Adapter — execute commands on remote machines.

Usage:
    nlp2cmd --source ssh://user@host "list large log files"
    nlp2cmd --source ssh://root@192.168.1.100:22 "check disk usage"
"""

from __future__ import annotations

import subprocess
import shlex
from typing import Any, Optional

from nlp2cmd.streams.base import StreamAdapter, StreamResult, SourceURI


class SSHStreamAdapter(StreamAdapter):
    PROTOCOL = "ssh"

    def __init__(self, source: SourceURI):
        super().__init__(source)
        self._ssh_target = self._build_ssh_target()

    def _build_ssh_target(self) -> str:
        user = self.source.user or "root"
        host = self.source.host
        return f"{user}@{host}"

    def _build_ssh_cmd(self, remote_cmd: str) -> list[str]:
        cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10"]
        if self.source.port:
            cmd += ["-p", str(self.source.port)]
        cmd.append(self._ssh_target)
        cmd.append(remote_cmd)
        return cmd

    def connect(self) -> StreamResult:
        try:
            result = subprocess.run(
                self._build_ssh_cmd("echo connected"),
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0:
                self._connected = True
                return StreamResult(success=True, output="SSH connected")
            return StreamResult(success=False, error=result.stderr.strip())
        except Exception as e:
            return StreamResult(success=False, error=str(e))

    def execute(self, task: str, **kwargs) -> StreamResult:
        """Execute command or NL task on remote host via SSH."""
        # If task looks like a shell command, execute directly
        remote_cmd = task
        if not self._looks_like_command(task):
            remote_cmd = self._nl_to_command(task)

        try:
            result = subprocess.run(
                self._build_ssh_cmd(remote_cmd),
                capture_output=True, text=True, timeout=kwargs.get("timeout", 30),
            )
            return StreamResult(
                success=result.returncode == 0,
                output=result.stdout.strip(),
                error=result.stderr.strip() if result.returncode != 0 else None,
                data={"exit_code": result.returncode, "command": remote_cmd},
                metadata={"target": self._ssh_target},
            )
        except subprocess.TimeoutExpired:
            return StreamResult(success=False, error="SSH command timed out")
        except Exception as e:
            return StreamResult(success=False, error=str(e))

    def query(self, question: str, **kwargs) -> StreamResult:
        """Query remote system info."""
        queries = {
            "uptime": "uptime",
            "disk": "df -h",
            "memory": "free -h",
            "cpu": "nproc && cat /proc/loadavg",
            "os": "cat /etc/os-release | head -5",
            "processes": "ps aux --sort=-%mem | head -10",
            "network": "ip addr show | grep 'inet '",
        }
        cmd = queries.get(question.lower().split()[0], f"echo 'Query: {question}'")
        return self.execute(cmd, **kwargs)

    def _looks_like_command(self, text: str) -> bool:
        first = text.strip().split()[0] if text.strip() else ""
        commands = {"ls", "cd", "cat", "grep", "find", "df", "du", "ps", "top",
                    "free", "uname", "hostname", "ip", "ss", "systemctl", "docker",
                    "apt", "yum", "dnf", "pip", "python", "echo", "mkdir", "rm",
                    "cp", "mv", "chmod", "chown", "tar", "wget", "curl", "git"}
        return first in commands or first.startswith("/") or first.startswith("./")

    def _nl_to_command(self, task: str) -> str:
        """Convert natural language to shell command using pipeline."""
        try:
            from nlp2cmd.generation.pipeline import RuleBasedPipeline
            pipeline = RuleBasedPipeline()
            result = pipeline.process(task)
            if result.success and result.command:
                return result.command
        except Exception:
            pass
        return f"echo 'Could not parse: {task}'"
