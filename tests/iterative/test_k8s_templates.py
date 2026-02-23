"""
Test Kubernetes command template generation.

This module tests Kubernetes command template generation including
pod management, deployments, services, and namespace operations.
"""

import pytest

from nlp2cmd.generation.template_generator import TemplateGenerator, TemplateResult


class TestK8sTemplates:
    """Test Kubernetes command template generation."""
    
    @pytest.fixture
    def generator(self) -> TemplateGenerator:
        return TemplateGenerator()
    
    def test_k8s_get_pods(self, generator):
        """Test kubectl get pods command."""
        result = generator.generate(
            domain='kubernetes',
            intent='get',
            entities={'resource_type': 'pods', 'namespace': 'default'}
        )
        
        assert result.success
        assert 'kubectl' in result.command
        assert 'get' in result.command
        assert 'pods' in result.command
        assert 'default' in result.command
    
    def test_k8s_scale_deployment(self, generator):
        """Test kubectl scale deployment command."""
        result = generator.generate(
            domain='kubernetes',
            intent='scale',
            entities={'resource_type': 'deployment', 'name': 'webapp', 'replica_count': '3'}
        )
        
        assert result.success
        assert 'kubectl scale' in result.command
        assert 'deployment' in result.command
        assert 'webapp' in result.command
        assert '3' in result.command
    
    def test_k8s_logs(self, generator):
        """Test kubectl logs command."""
        result = generator.generate(
            domain='kubernetes',
            intent='logs',
            entities={'resource_type': 'pod', 'name': 'webapp-123', 'tail_lines': '50'}
        )
        
        assert result.success
        assert 'kubectl logs' in result.command
        assert 'webapp-123' in result.command
        assert '50' in result.command
    
    def test_k8s_describe(self, generator):
        """Test kubectl describe command."""
        result = generator.generate(
            domain='kubernetes',
            intent='describe',
            entities={'resource_type': 'pod', 'name': 'webapp-123'}
        )
        
        assert result.success
        assert 'kubectl describe' in result.command
        assert 'pod' in result.command
        assert 'webapp-123' in result.command
    
    def test_k8s_create_deployment(self, generator):
        """Test kubectl create deployment command."""
        result = generator.generate(
            domain='kubernetes',
            intent='create',
            entities={'resource_type': 'deployment', 'name': 'webapp', 'image': 'nginx:latest'}
        )
        
        assert result.success
        assert 'kubectl create' in result.command
        assert 'deployment' in result.command
        assert 'webapp' in result.command
        assert 'nginx:latest' in result.command
    
    def test_k8s_delete_resource(self, generator):
        """Test kubectl delete resource command."""
        result = generator.generate(
            domain='kubernetes',
            intent='delete',
            entities={'resource_type': 'pod', 'name': 'webapp-123'}
        )
        
        assert result.success
        assert 'kubectl delete' in result.command
        assert 'pod' in result.command
        assert 'webapp-123' in result.command
