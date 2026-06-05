"""
Test shell command template generation.

This module tests shell command template generation including
file operations, process management, and system commands.
"""

import pytest

from nlp2cmd.generation.template_generator import TemplateGenerator, TemplateResult


class TestShellTemplates:
    """Test shell command template generation."""
    
    @pytest.fixture
    def generator(self) -> TemplateGenerator:
        return TemplateGenerator()
    
    def test_shell_find_files(self, generator):
        """Test file search command generation."""
        result = generator.generate(
            domain='shell',
            intent='find',
            entities={'path': '/home/user', 'pattern': '*.py'}
        )
        
        assert result.success
        assert 'find' in result.command
        assert '/home/user' in result.command
        assert '*.py' in result.command
    
    def test_shell_list_directory(self, generator):
        """Test directory listing command."""
        result = generator.generate(
            domain='shell',
            intent='list',
            entities={'path': '/var/log'}
        )
        
        assert result.success
        assert 'ls' in result.command
        assert '/var/log' in result.command
    
    def test_shell_grep(self, generator):
        """Test grep command generation."""
        result = generator.generate(
            domain='shell',
            intent='search',
            entities={'pattern': 'error', 'path': '/var/log'}
        )
        
        assert result.success
        assert 'grep' in result.command
        assert 'error' in result.command
        assert '/var/log' in result.command
    
    def test_shell_process_list(self, generator):
        """Test process listing command."""
        result = generator.generate(
            domain='shell',
            intent='list_processes',
            entities={}
        )
        
        assert result.success
        assert 'ps' in result.command
    
    def test_shell_file_size_filter(self, generator):
        """Test file size filtering."""
        result = generator.generate(
            domain='shell',
            intent='find',
            entities={'path': '.', 'size': '100MB', 'size_operator': '>'}
        )
        
        assert result.success
        assert 'find' in result.command
        assert '-size +100M' in result.command

    def test_shell_find_exec_flag(self, generator):
        """Test find exec flag for list intent in text."""
        result = generator.generate(
            domain='shell',
            intent='find',
            entities={
                'path': '/tmp',
                'pattern': '*.log',
                'target': 'files',
                'text': 'lista plików log',
            },
        )

        assert result.success
        assert '-ls' in result.command

    def test_shell_find_time_flag_recent(self, generator):
        """Test find time flag for recent files."""
        result = generator.generate(
            domain='shell',
            intent='find',
            entities={
                'path': '.',
                'age': {'value': 7},
                'text': 'pokaż pliki z ostatnich 7 dni',
            },
        )

        assert result.success
        assert '-mtime -7' in result.command

    def test_shell_file_operation_remove_all(self, generator):
        """Test file_operation routes to remove_all template."""
        result = generator.generate(
            domain='shell',
            intent='file_operation',
            entities={'text': 'usuń wszystkie pliki .log', 'extension': 'log'},
        )

        assert result.success
        assert 'find' in result.command
        assert '*.log' in result.command
        assert '-delete' in result.command

    def test_shell_file_operation_rename(self, generator):
        """Test file_operation routes to rename template."""
        result = generator.generate(
            domain='shell',
            intent='file_operation',
            entities={'text': 'zmień nazwę pliku', 'old_name': 'a.txt', 'new_name': 'b.txt'},
        )

        assert result.success
        assert result.command.strip() == 'mv a.txt b.txt'
