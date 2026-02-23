"""
Test SQL template generation.

This module tests SQL template generation functionality including
SELECT, INSERT, UPDATE, DELETE operations with various entities.
"""

import pytest

from nlp2cmd.generation.template_generator import TemplateGenerator, TemplateResult


class TestSQLTemplates:
    """Test SQL template generation."""
    
    @pytest.fixture
    def generator(self) -> TemplateGenerator:
        return TemplateGenerator()
    
    def test_sql_select_basic(self, generator):
        """Test basic SQL SELECT generation."""
        result = generator.generate(
            domain='sql',
            intent='select',
            entities={'table': 'users', 'columns': ['id', 'name']}
        )
        
        assert result.success
        assert 'SELECT' in result.command
        assert 'id' in result.command
        assert 'name' in result.command
        assert 'FROM users' in result.command
    
    def test_sql_select_all_columns(self, generator):
        """Test SQL SELECT with all columns."""
        result = generator.generate(
            domain='sql',
            intent='select',
            entities={'table': 'orders'}
        )
        
        assert result.success
        assert 'SELECT *' in result.command
        assert 'FROM orders' in result.command
    
    def test_sql_select_with_where(self, generator):
        """Test SQL SELECT with WHERE clause."""
        result = generator.generate(
            domain='sql',
            intent='select',
            entities={
                'table': 'products',
                'filters': [{'field': 'status', 'operator': '=', 'value': 'active'}]
            }
        )
        
        assert result.success
        assert 'SELECT' in result.command
        assert 'FROM products' in result.command
        assert 'WHERE' in result.command
        assert 'status' in result.command
        assert 'active' in result.command
    
    def test_sql_select_with_limit(self, generator):
        """Test SQL SELECT with LIMIT."""
        result = generator.generate(
            domain='sql',
            intent='select',
            entities={'table': 'logs', 'limit': '10'}
        )
        
        assert result.success
        assert 'SELECT' in result.command
        assert 'FROM logs' in result.command
        assert 'LIMIT 10' in result.command
    
    def test_sql_select_with_order(self, generator):
        """Test SQL SELECT with ORDER BY."""
        result = generator.generate(
            domain='sql',
            intent='select',
            entities={
                'table': 'users',
                'ordering': [{'field': 'created_at', 'direction': 'desc'}]
            }
        )
        
        assert result.success
        assert 'SELECT' in result.command
        assert 'FROM users' in result.command
        assert 'ORDER BY' in result.command
        assert 'created_at' in result.command
        assert 'DESC' in result.command
    
    def test_sql_aggregate(self, generator):
        """Test SQL aggregate query."""
        result = generator.generate(
            domain='sql',
            intent='select',
            entities={
                'table': 'orders',
                'aggregation': 'count',
                'columns': ['id']
            }
        )
        
        assert result.success
        assert 'COUNT' in result.command
        assert 'orders' in result.command
