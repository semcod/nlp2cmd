"""
Test template customization and pipeline functionality.

This module tests template customization, pipeline creation,
and performance metrics for template-based generation.
"""

import pytest
import time

from nlp2cmd.generation.template_generator import TemplateGenerator, TemplateResult
from nlp2cmd.generation.pipeline import (
    RuleBasedPipeline,
    PipelineResult,
    PipelineMetrics,
    create_pipeline,
)


@pytest.fixture
def generator() -> TemplateGenerator:
    return TemplateGenerator()


class TestTemplateCustomization:
    """Test template customization."""
    
    def test_add_custom_template(self):
        """Test adding custom templates."""
        generator = TemplateGenerator()
        
        generator.add_template('sql', 'custom_select', 
            "SELECT * FROM {table} WHERE status = 'active'")
        
        result = generator.generate(
            domain='sql',
            intent='custom_select',
            entities={'table': 'users'}
        )
        
        assert result.success
        assert 'SELECT * FROM users' in result.command
        assert "status = 'active'" in result.command
    
    def test_custom_templates_dict(self):
        """Test initializing with custom templates dict."""
        custom = {
            'shell': {
                'custom_find': 'find {path} -name "{pattern}" -type f'
            }
        }
        
        generator = TemplateGenerator(custom_templates=custom)
        
        result = generator.generate(
            domain='shell',
            intent='custom_find',
            entities={'path': '/home', 'pattern': '*.py'}
        )
        
        assert result.success
        assert 'find /home' in result.command
        assert '-name "*.py"' in result.command
        assert '-type f' in result.command
    
    def test_list_templates(self, generator):
        """Test listing available templates."""
        templates = generator.list_templates()
        
        assert isinstance(templates, dict)
        assert 'sql' in templates
        assert 'shell' in templates
        assert 'docker' in templates
        assert 'kubernetes' in templates


class TestRuleBasedPipeline:
    """Test rule-based pipeline functionality."""
    
    @pytest.fixture
    def pipeline(self) -> RuleBasedPipeline:
        return create_pipeline()
    
    def test_pipeline_sql_select(self, pipeline):
        """Test pipeline for SQL SELECT."""
        result = pipeline.process("Pokaż dane z tabeli users")
        
        assert result.success
        assert 'SELECT' in result.command
        assert 'users' in result.command
    
    def test_pipeline_sql_with_filter(self, pipeline):
        """Test pipeline for SQL with filter."""
        result = pipeline.process("Pokaż użytkowników gdzie status = active")
        
        assert result.success
        assert 'SELECT' in result.command
        assert 'WHERE' in result.command
        assert 'status' in result.command
    
    def test_pipeline_sql_with_limit(self, pipeline):
        """Test pipeline for SQL with limit."""
        result = pipeline.process("Pokaż 10 rekordów")
        
        assert result.success
        assert 'LIMIT 10' in result.command
    
    def test_pipeline_shell_find(self, pipeline):
        """Test pipeline for shell find."""
        result = pipeline.process("Znajdź pliki *.py")
        
        assert result.success
        assert 'find' in result.command
        assert '.py' in result.command
    
    def test_pipeline_shell_process(self, pipeline):
        """Test pipeline for shell process."""
        result = pipeline.process("Pokaż procesy")
        
        assert result.success
        assert 'ps' in result.command
    
    def test_pipeline_docker_list(self, pipeline):
        """Test pipeline for docker list."""
        result = pipeline.process("Pokaż kontenery")
        
        assert result.success
        assert 'docker ps' in result.command
    
    def test_pipeline_docker_logs(self, pipeline):
        """Test pipeline for docker logs."""
        result = pipeline.process("Logi kontenera webapp")
        
        assert result.success
        assert 'docker logs' in result.command
        assert 'webapp' in result.command
    
    def test_pipeline_k8s_get_pods(self, pipeline):
        """Test pipeline for kubectl get pods."""
        result = pipeline.process("Pokaż pody")
        
        assert result.success
        assert 'kubectl get pods' in result.command
    
    def test_pipeline_k8s_scale(self, pipeline):
        """Test pipeline for kubectl scale."""
        result = pipeline.process("Skaluj do 3 replik")
        
        assert result.success
        assert 'kubectl scale' in result.command
        assert '3' in result.command
    
    def test_pipeline_unknown_input(self, pipeline):
        """Test pipeline with unknown input."""
        result = pipeline.process("Nieznane polecenie")
        
        assert not result.success
        assert 'Unknown' in result.command
    
    def test_pipeline_empty_input(self, pipeline):
        """Test pipeline with empty input."""
        result = pipeline.process("")
        
        assert not result.success


class TestPipelineResult:
    """Test pipeline result conversion."""
    
    def test_to_plan(self):
        """Test conversion to execution plan."""
        result = PipelineResult(
            success=True,
            command="SELECT * FROM users",
            domain='sql',
            intent='select',
            entities={'table': 'users'},
            confidence=0.9
        )
        
        plan = result.to_plan()
        
        assert plan.intent == 'select'
        assert plan.entities['table'] == 'users'
        assert plan.confidence == 0.9


class TestPipelineMetrics:
    """Test pipeline metrics recording."""
    
    def test_metrics_recording(self):
        """Test recording pipeline results."""
        metrics = PipelineMetrics()
        
        # Record some results
        metrics.record_result(True, 0.05)  # 50ms
        metrics.record_result(True, 0.03)  # 30ms
        metrics.record_result(False, 0.10)  # 100ms
        
        report = metrics.generate_report()
        
        assert 'success_rate' in report
        assert 'avg_latency' in report
        assert 'total_processed' in report
        assert report['total_processed'] == 3
    
    def test_metrics_report(self):
        """Test generating metrics report."""
        metrics = PipelineMetrics()
        
        # Add more test data
        for i in range(10):
            metrics.record_result(i % 8 != 0, 0.01 + i * 0.01)
        
        report = metrics.generate_report()
        
        assert report['success_rate'] == 0.8  # 8/10
        assert 'avg_latency' in report
        assert 'min_latency' in report
        assert 'max_latency' in report


class TestPipelineFactory:
    """Test pipeline factory functions."""
    
    def test_create_pipeline_default(self):
        """Test creating default pipeline."""
        pipeline = create_pipeline()
        
        assert isinstance(pipeline, RuleBasedPipeline)
        assert hasattr(pipeline, 'process')
    
    def test_create_pipeline_custom_threshold(self):
        """Test creating pipeline with custom threshold."""
        pipeline = create_pipeline(confidence_threshold=0.8)
        
        assert isinstance(pipeline, RuleBasedPipeline)
        # Test that threshold affects behavior
        result = pipeline.process("Pokaż dane z tabeli users")
        assert result.success
    
    def test_create_pipeline_custom_patterns(self):
        """Test creating pipeline with custom patterns."""
        custom_patterns = {
            'custom_domain': {
                'custom_intent': [r'test pattern (\w+)']
            }
        }
        
        pipeline = create_pipeline(custom_patterns=custom_patterns)
        
        assert isinstance(pipeline, RuleBasedPipeline)


class TestPipelinePerformance:
    """Test pipeline performance."""
    
    @pytest.fixture
    def pipeline(self) -> RuleBasedPipeline:
        return create_pipeline()
    
    def test_pipeline_latency(self, pipeline):
        """Test that pipeline latency is reasonable (<150ms)."""
        start_time = time.time()
        
        for _ in range(10):
            pipeline.process("Pokaż dane z tabeli users")
        
        end_time = time.time()
        avg_latency = (end_time - start_time) / 10 * 1000  # Convert to ms
        
        assert avg_latency < 150, f"Pipeline too slow: {avg_latency:.1f}ms average"
    
    def test_pipeline_throughput(self, pipeline):
        """Test pipeline throughput."""
        start_time = time.time()
        
        # Process 100 queries
        for i in range(100):
            pipeline.process(f"Pokaż dane z tabeli test{i % 10}")
        
        end_time = time.time()
        throughput = 100 / (end_time - start_time)  # queries per second
        
        assert throughput > 5, f"Throughput too low: {throughput:.1f} qps"
