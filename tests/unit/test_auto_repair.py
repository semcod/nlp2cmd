"""
Tests for auto-repair system.
"""

import pytest
from unittest.mock import Mock

from nlp2cmd.generation.auto_repair import (
    CommandRepairer,
    should_attempt_repair,
)


class TestCommandRepairer:
    """Test CommandRepairer functionality."""
    
    def test_rule_based_repair_file_not_found(self):
        """Test file not found repair."""
        repairer = CommandRepairer()
        
        # Test adding sudo for system commands
        result = repairer._fix_file_not_found(
            "mv /etc/config.txt /backup/",
            "mv: cannot move '/etc/config.txt': No such file or directory",
            {}
        )
        assert result["success"] is True
        assert result["command"] == "sudo mv /etc/config.txt /backup/"
        
        # Test ~ expansion
        result = repairer._fix_file_not_found(
            "ls ~/documents",
            "ls: cannot access '~/documents': No such file or directory",
            {}
        )
        assert result["success"] is True
        assert result["command"] == "ls $HOME/documents"
    
    def test_rule_based_repair_permission_denied(self):
        """Test permission denied repair."""
        repairer = CommandRepairer()
        
        result = repairer._fix_permission_denied(
            "cat /var/log/syslog",
            "cat: /var/log/syslog: Permission denied",
            {}
        )
        assert result["success"] is True
        assert result["command"] == "sudo cat /var/log/syslog"
        
        # Already has sudo
        result = repairer._fix_permission_denied(
            "sudo cat /var/log/syslog",
            "cat: /var/log/syslog: Permission denied",
            {}
        )
        assert result["success"] is False
    
    def test_rule_based_repair_command_not_found(self):
        """Test command not found repair."""
        repairer = CommandRepairer()
        
        # Python -> python3
        result = repairer._fix_command_not_found(
            "python script.py",
            "python: command not found",
            {}
        )
        assert result["success"] is True
        assert result["command"] == "python3 script.py"
        
        # docker-compose -> docker compose
        result = repairer._fix_command_not_found(
            "docker-compose up",
            "docker-compose: command not found",
            {}
        )
        assert result["success"] is True
        assert result["command"] == "docker compose up"
    
    def test_rule_based_repair_syntax_error(self):
        """Test syntax error repair."""
        repairer = CommandRepairer()
        
        # Unmatched double quote
        result = repairer._fix_syntax_error(
            'echo "hello world',
            'bash: unexpected EOF while looking for matching `"\'',
            {}
        )
        assert result["success"] is True
        assert result['command'] == 'echo "hello world"'
        
        # Unmatched single quote
        result = repairer._fix_syntax_error(
            "echo 'hello world",
            "bash: unexpected EOF while looking for matching `''",
            {}
        )
        assert result["success"] is True
        assert result["command"] == "echo 'hello world'"
    
    def test_rule_based_repair_docker(self):
        """Test Docker-related repairs."""
        repairer = CommandRepairer()
        
        # Missing Docker
        result = repairer._fix_docker_missing(
            "docker run nginx",
            "docker: command not found",
            {}
        )
        assert result["success"] is True
        assert "Install Docker first" in result["command"]
        assert "docker run nginx" in result["command"]
        
        # Docker permission
        result = repairer._fix_docker_permission(
            "docker run nginx",
            "permission denied while trying to connect to the Docker daemon socket",
            {}
        )
        assert result["success"] is True
        assert result["command"] == "sudo docker run nginx"
    
    def test_llm_repair(self):
        """Test LLM-based repair."""
        mock_llm = Mock()
        mock_llm.generate.return_value = "ls -la /home/user"
        
        repairer = CommandRepairer(llm_client=mock_llm)
        
        result = repairer._llm_repair(
            "ls /home/user",
            "ls: cannot access '/home/user': No such file or directory",
            {"domain": "shell"},
            1
        )
        
        assert result["success"] is True
        assert result["command"] == "ls -la /home/user"
        mock_llm.generate.assert_called_once()
    
    def test_llm_repair_no_client(self):
        """Test LLM repair without client."""
        repairer = CommandRepairer(llm_client=None)
        
        result = repairer._llm_repair(
            "ls /home/user",
            "ls: cannot access '/home/user': No such file or directory",
            {"domain": "shell"},
            1
        )
        
        assert result["success"] is False
    
    def test_repair_command_success(self):
        """Test successful command repair."""
        repairer = CommandRepairer()
        
        result = repairer.repair_command(
            "python script.py",
            "python: command not found",
            {"domain": "shell"},
            max_attempts=1
        )
        
        assert result["success"] is True
        assert result["command"] == "python3 script.py"
    
    def test_repair_command_failure(self):
        """Test failed command repair."""
        repairer = CommandRepairer()
        
        result = repairer.repair_command(
            "unknown_command",
            "unknown_command: command not found",
            {"domain": "shell"},
            max_attempts=1
        )
        
        assert result["success"] is False
        assert result["reason"] == "Failed after 1 attempts"


class TestShouldAttemptRepair:
    """Test should_attempt_repair function."""
    
    def test_should_repair_common_errors(self):
        """Test repair for common error patterns."""
        assert should_attempt_repair(
            "No such file or directory",
            {"domain": "shell"}
        ) is True
        
        assert should_attempt_repair(
            "Permission denied",
            {"domain": "shell"}
        ) is True
        
        assert should_attempt_repair(
            "command not found",
            {"domain": "shell"}
        ) is True
    
    def test_should_not_repair_critical_errors(self):
        """Test skipping repair for critical errors."""
        assert should_attempt_repair(
            "segmentation fault",
            {"domain": "shell"}
        ) is False
        
        assert should_attempt_repair(
            "killed",
            {"domain": "shell"}
        ) is False
        
        assert should_attempt_repair(
            "out of memory",
            {"domain": "shell"}
        ) is False
    
    def test_should_repair_by_domain(self):
        """Test repair based on domain context."""
        assert should_attempt_repair(
            "some error",
            {"domain": "docker"}
        ) is True
        
        assert should_attempt_repair(
            "some error",
            {"domain": "system"}
        ) is True
        
        # Unknown domain - don't repair
        assert should_attempt_repair(
            "some error",
            {"domain": "unknown"}
        ) is False
