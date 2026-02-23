"""
Test Docker command template generation.

This module tests Docker command template generation including
container management, image operations, and Docker Compose.
"""

import pytest

from nlp2cmd.generation.template_generator import TemplateGenerator, TemplateResult


class TestDockerTemplates:
    """Test Docker command template generation."""
    
    @pytest.fixture
    def generator(self) -> TemplateGenerator:
        return TemplateGenerator()
    
    def test_docker_list_containers(self, generator):
        """Test container listing command."""
        result = generator.generate(
            domain='docker',
            intent='list',
            entities={}
        )
        
        assert result.success
        assert 'docker' in result.command
        assert 'ps' in result.command
    
    def test_docker_run_container(self, generator):
        """Test container run command."""
        result = generator.generate(
            domain='docker',
            intent='run',
            entities={'image': 'nginx:latest', 'port': '8080:80'}
        )
        
        assert result.success
        assert 'docker run' in result.command
        assert 'nginx:latest' in result.command
        assert '8080:80' in result.command
    
    def test_docker_logs(self, generator):
        """Test container logs command."""
        result = generator.generate(
            domain='docker',
            intent='logs',
            entities={'container': 'webapp', 'tail_lines': '100'}
        )
        
        assert result.success
        assert 'docker logs' in result.command
        assert 'webapp' in result.command
        assert '100' in result.command
    
    def test_docker_exec(self, generator):
        """Test container exec command."""
        result = generator.generate(
            domain='docker',
            intent='exec',
            entities={'container': 'webapp', 'command': 'bash'}
        )
        
        assert result.success
        assert 'docker exec' in result.command
        assert 'webapp' in result.command
        assert 'bash' in result.command
    
    def test_docker_stop_container(self, generator):
        """Test container stop command."""
        result = generator.generate(
            domain='docker',
            intent='stop',
            entities={'container': 'webapp'}
        )
        
        assert result.success
        assert 'docker stop' in result.command
        assert 'webapp' in result.command
    
    def test_docker_remove_container(self, generator):
        """Test container remove command."""
        result = generator.generate(
            domain='docker',
            intent='remove',
            entities={'container': 'webapp'}
        )
        
        assert result.success
        assert 'docker rm' in result.command
        assert 'webapp' in result.command
