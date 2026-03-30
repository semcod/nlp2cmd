# Python API Guide

This guide provides comprehensive documentation for using NLP2CMD programmatically with Python.

## 📚 Related Documentation

- **[Documentation Hub](../README.md)** - Entry point for all docs
- **[User Guide](../user-guide/user-guide.md)** - Complete usage tutorial
- **[CLI Reference](../reference/cli-reference.md)** - Command line usage
- **[API Reference](../api/README.md)** - Detailed API documentation
- **[Examples Guide](../reference/examples-guide.md)** - Examples overview

## Installation

```bash
pip install nlp2cmd
```

## Quick Start

### HybridThermodynamicGenerator (Recommended)

The easiest way to get started is with the `HybridThermodynamicGenerator`:

```python
import asyncio
from nlp2cmd.generation import HybridThermodynamicGenerator

async def main():
    generator = HybridThermodynamicGenerator()
    
    # Simple query → DSL generation
    result = await generator.generate("Pokaż użytkowników")
    print(f"Source: {result['source']}")
    print(f"Command: {result['result'].command}")
    
    # Optimization → Thermodynamic sampling
    result = await generator.generate("Zoptymalizuj przydzielanie zasobów")
    print(f"Source: {result['source']}")
    print(f"Solution: {result['result'].decoded_output}")

asyncio.run(main())
```

## Core Components

### 1. HybridThermodynamicGenerator

The main interface that automatically routes between DSL generation and thermodynamic optimization.

```python
from nlp2cmd.generation import HybridThermodynamicGenerator

generator = HybridThermodynamicGenerator()

# Basic usage
result = await generator.generate("your natural language query")

# With context
context = {
    'environment': 'production',
    'available_tools': ['docker', 'kubectl'],
    'os': 'linux'
}
result = await generator.generate("check system status", context=context)
```

#### Response Types

**DSL Response:**
```python
{
    'source': 'dsl',
    'result': HybridResult(
        command='docker ps -a',
        source='rules',
        domain='docker',
        confidence=0.95,
        latency_ms=3.2
    )
}
```

#### Custom Problem Types (Fallback Behavior)

If `problem_type` does not match a built-in energy model, the thermodynamic
engine falls back to `ConstraintEnergy` and returns only `raw_sample` in the
solution. You can project the sample back into variable ranges yourself.
See **[Thermodynamic Integration](../architecture/thermodynamic-computing.md)** for additional examples.

**Thermodynamic Response:**
```python
{
    'source': 'thermodynamic',
    'result': ThermodynamicResult(
        decoded_output='Optimized schedule: task_1 at 09:00, task_2 at 11:00...',
        energy=0.1234,
        entropy_production=0.0567,
        converged=True,
        n_samples=1000,
        solution_quality=SolutionQuality(
            is_feasible=True,
            optimality_gap=0.02,
            explanation='All constraints satisfied'
        )
    )
}
```

### 2. Decision Router

Intelligently routes queries to direct execution or LLM planner:

```python
from nlp2cmd import DecisionRouter, RoutingDecision

router = DecisionRouter()

routing = router.route(
    intent="select",
    entities={"table": "users"},
    text="show all users",
    confidence=0.9,
)

if routing.decision == RoutingDecision.DIRECT:
    print("Direct execution")
else:
    print("LLM planner needed")
```

### 3. Action Registry

Central registry of available actions:

```python
from nlp2cmd import get_registry

registry = get_registry()

# List all domains
domains = registry.list_domains()
print(domains)  # ['sql', 'shell', 'docker', 'kubernetes', 'utility']

# List actions by domain
sql_actions = registry.list_actions(domain="sql")
print(sql_actions)  # ['sql_select', 'sql_insert', 'sql_update', ...]

# Get destructive actions
destructive = registry.get_destructive_actions()
print(destructive)  # ['sql_delete', 'docker_run', ...]

# Generate LLM prompt
prompt = registry.to_llm_prompt(domain="sql")
```

### 4. Plan Executor

Executes multi-step plans with tracing and error handling:

```python
from nlp2cmd import PlanExecutor, ExecutionPlan, PlanStep

executor = PlanExecutor()

plan = ExecutionPlan(steps=[
    PlanStep(
        action="shell_find",
        params={"glob": "*.log"},
        store_as="log_files",
    ),
    PlanStep(
        action="shell_count_pattern",
        foreach="log_files",
        params={"file": "$item", "pattern": "ERROR"},
        store_as="error_counts",
    ),
])

result = executor.execute(plan)
print(f"Trace ID: {result.trace_id}")
print(f"Duration: {result.total_duration_ms}ms")
```

### 5. Result Aggregator

Formats results in multiple output formats:

```python
from nlp2cmd import ResultAggregator, OutputFormat

aggregator = ResultAggregator()

# Text format
text_result = aggregator.aggregate(exec_result, OutputFormat.TEXT)

# Table format
table_result = aggregator.aggregate(exec_result, OutputFormat.TABLE)

# JSON format
json_result = aggregator.aggregate(exec_result, OutputFormat.JSON)

# Markdown format
md_result = aggregator.aggregate(exec_result, OutputFormat.MARKDOWN)
```

## Advanced Usage

### Batch Processing

```python
import asyncio
from nlp2cmd.generation import HybridThermodynamicGenerator

async def batch_process():
    generator = HybridThermodynamicGenerator()
    
    queries = [
        "show all users",
        "find large files",
        "check docker status",
        "optimize resource allocation"
    ]
    
    # Process all queries concurrently
    results = await asyncio.gather(*[
        generator.generate(query) for query in queries
    ])
    
    for query, result in zip(queries, results):
        print(f"Query: {query}")
        print(f"Source: {result['source']}")
        print(f"Result: {result['result']}")
        print("-" * 50)

asyncio.run(batch_process())
```

### Context-Aware Queries

```python
from nlp2cmd.generation import HybridThermodynamicGenerator

async def contextual_queries():
    generator = HybridThermodynamicGenerator()
    
    # Define environment context
    context = {
        'environment': 'production',
        'os': 'linux',
        'shell': 'bash',
        'available_tools': {
            'docker': {'available': True, 'version': '29.1.5'},
            'kubectl': {'available': True, 'version': '1.28.0'},
            'git': {'available': True, 'version': '2.51.0'}
        },
        'constraints': {
            'max_memory': '8GB',
            'max_cpu_cores': 4
        }
    }
    
    # Query with context
    result = await generator.generate(
        "check all running services", 
        context=context
    )
    
    print(result['result'].command)

asyncio.run(contextual_queries())
```

### Custom DSL Adapters

```python
from nlp2cmd import NLP2CMD, BaseAdapter

class CustomAdapter(BaseAdapter):
    def transform(self, text: str, context: dict = None):
        # Custom transformation logic
        if "backup" in text.lower():
            return "rsync -av /data/ /backup/"
        return "# Custom command not implemented"

# Use with custom adapter
nlp = NLP2CMD(adapter=CustomAdapter())
result = nlp.transform("create backup")
print(result.command)
```

### Error Handling

```python
from nlp2cmd.generation import HybridThermodynamicGenerator
from nlp2cmd.exceptions import GenerationError, ValidationError

async def robust_queries():
    generator = HybridThermodynamicGenerator()
    
    queries = [
        "valid query",
        "",  # Empty query
        "invalid query with special chars !@#$%"
    ]
    
    for query in queries:
        try:
            result = await generator.generate(query)
            print(f"✅ {query}: {result['source']}")
        except GenerationError as e:
            print(f"❌ Generation error for '{query}': {e}")
        except ValidationError as e:
            print(f"⚠️ Validation error for '{query}': {e}")
        except Exception as e:
            print(f"🔥 Unexpected error for '{query}': {e}")

asyncio.run(robust_queries())
```

### Performance Monitoring

```python
import time
from nlp2cmd.generation import HybridThermodynamicGenerator

async def performance_test():
    generator = HybridThermodynamicGenerator()
    
    query = "show all docker containers"
    
    # Measure performance
    start_time = time.time()
    result = await generator.generate(query)
    end_time = time.time()
    
    print(f"Query: {query}")
    print(f"Source: {result['source']}")
    print(f"Total time: {(end_time - start_time) * 1000:.1f}ms")
    
    if result['source'] == 'dsl':
        print(f"Generation time: {result['result'].latency_ms}ms")
    elif result['source'] == 'thermodynamic':
        print(f"Energy: {result['result'].energy}")
        print(f"Samples: {result['result'].n_samples}")
        print(f"Converged: {result['result'].converged}")

asyncio.run(performance_test())
```

## Integration Examples

### Web Application

```python
from fastapi import FastAPI, HTTPException
from nlp2cmd.generation import HybridThermodynamicGenerator
import asyncio

app = FastAPI()
generator = HybridThermodynamicGenerator()

@app.post("/query")
async def process_query(query: str):
    try:
        result = await generator.generate(query)
        return {
            "query": query,
            "source": result['source'],
            "result": str(result['result'])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

### Data Pipeline

```python
import pandas as pd
from nlp2cmd.generation import HybridThermodynamicGenerator

async def analyze_data_pipeline():
    generator = HybridThermodynamicGenerator()
    
    # Load data
    df = pd.read_csv("system_logs.csv")
    
    # Generate analysis queries
    queries = [
        f"analyze {column} trends" for column in df.columns
    ]
    
    # Process queries
    results = await asyncio.gather(*[
        generator.generate(query) for query in queries
    ])
    
    # Compile report
    report = {}
    for column, result in zip(df.columns, results):
        report[column] = {
            "source": result['source'],
            "analysis": str(result['result'])
        }
    
    return report
```

### Monitoring System

```python
import asyncio
from datetime import datetime
from nlp2cmd.generation import HybridThermodynamicGenerator

class SystemMonitor:
    def __init__(self):
        self.generator = HybridThermodynamicGenerator()
        self.alerts = []
    
    async def check_system(self):
        queries = [
            "check disk space usage",
            "monitor memory consumption", 
            "verify service status",
            "analyze error logs"
        ]
        
        results = await asyncio.gather(*[
            self.generator.generate(query) for query in queries
        ])
        
        for query, result in zip(queries, results):
            if result['source'] == 'thermodynamic':
                # Optimization suggestions
                self.alerts.append({
                    "timestamp": datetime.now(),
                    "type": "optimization",
                    "query": query,
                    "suggestion": result['result'].decoded_output
                })
            else:
                # Direct commands
                self.alerts.append({
                    "timestamp": datetime.now(),
                    "type": "command",
                    "query": query,
                    "command": result['result'].command
                })
    
    def get_alerts(self):
        return self.alerts

# Usage
monitor = SystemMonitor()
asyncio.run(monitor.check_system())
print(monitor.get_alerts())
```

## Configuration

### Environment Variables

```python
import os
from nlp2cmd.generation import HybridThermodynamicGenerator

# Configure through environment
os.environ['NLP2CMD_LOG_LEVEL'] = 'DEBUG'
os.environ['NLP2CMD_CACHE_ENABLED'] = 'true'
os.environ['NLP2CMD_DEFAULT_DSL'] = 'shell'

generator = HybridThermodynamicGenerator()
```

### Custom Configuration

```python
from nlp2cmd.generation import HybridThermodynamicGenerator
from nlp2cmd.config import Config

config = Config(
    default_dsl='shell',
    enable_cache=True,
    log_level='INFO',
    thermodynamic_config={
        'max_samples': 2000,
        'convergence_threshold': 0.001,
        'parallel_sampling': True
    }
)

generator = HybridThermodynamicGenerator(config=config)
```

## Testing

### Unit Tests

```python
import pytest
from nlp2cmd.generation import HybridThermodynamicGenerator

@pytest.mark.asyncio
async def test_simple_query():
    generator = HybridThermodynamicGenerator()
    result = await generator.generate("show users")
    
    assert result['source'] == 'dsl'
    assert 'SELECT' in result['result'].command

@pytest.mark.asyncio
async def test_optimization_query():
    generator = HybridThermodynamicGenerator()
    result = await generator.generate("optimize resource allocation")
    
    assert result['source'] == 'thermodynamic'
    assert result['result'].converged is True
```

### Integration Tests

```python
import pytest
from nlp2cmd.generation import HybridThermodynamicGenerator

@pytest.mark.asyncio
async def test_batch_processing():
    generator = HybridThermodynamicGenerator()
    
    queries = ["query 1", "query 2", "query 3"]
    results = await asyncio.gather(*[
        generator.generate(query) for query in queries
    ])
    
    assert len(results) == len(queries)
    for result in results:
        assert 'source' in result
        assert 'result' in result
```

## Best Practices

1. **Use HybridThermodynamicGenerator** for most use cases
2. **Provide context** when available for better results
3. **Handle errors gracefully** with try-catch blocks
4. **Use batch processing** for multiple queries
5. **Monitor performance** with timing measurements
6. **Cache results** when appropriate
7. **Test thoroughly** with unit and integration tests

## See Also

- [CLI Reference](../reference/cli-reference.md) - Command line usage
- [Examples Guide](../reference/examples-guide.md) - Comprehensive examples
- [User Guide](../user-guide/user-guide.md) - Complete tutorial
