# Enhanced NLP2CMD - Dynamic Schema Implementation

[![GitHub stars](https://img.shields.io/github/stars/wronai/nlp2cmd?style=social)](https://github.com/wronai/nlp2cmd/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/wronai/nlp2cmd?style=social)](https://github.com/wronai/nlp2cmd/network/members)
[![GitHub issues](https://img.shields.io/github/issues/wronai/nlp2cmd)](https://github.com/wronai/nlp2cmd/issues)
[![GitHub pull requests](https://img.shields.io/github/issues-pr/wronai/nlp2cmd)](https://github.com/wronai/nlp2cmd/pulls)
[![Tests](https://img.shields.io/github/actions/workflow/status/wronai/nlp2cmd/test.yml?label=tests)](https://github.com/wronai/nlp2cmd/actions)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Type checking: mypy](https://img.shields.io/badge/type%20checking-mypy-blue.svg)](http://mypy-lang.org/)
[![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macos%20%7C%20windows-lightgrey)](https://github.com/wronai/nlp2cmd)
[![Dependencies](https://img.shields.io/badge/dependencies-playwright%20%7C%20openapi-blue)](https://github.com/wronai/nlp2cmd)

This implementation replaces hardcoded keywords with dynamic schema extraction from multiple sources.

## Overview

The enhanced NLP2CMD system dynamically extracts command patterns, parameters, and metadata from:

- **OpenAPI/Swagger specifications** - Parse API docs and generate curl commands
- **Shell command help** - Extract parameters from `--help` output and man pages  
- **Python source code** - Introspect Click apps and decorated functions
- **Shell-gpt integration** - Use AI for intelligent command generation

## Key Improvements

### 1. Dynamic Schema Extraction
```python
from nlp2cmd.schema_extraction import DynamicSchemaRegistry

# Extract from OpenAPI spec
registry = DynamicSchemaRegistry()
schema = registry.register_openapi_schema("htt ps://api.example.com/openapi.json")

# Extract from shell help
schema = registry.register_shell_help("find")

# Extract from Python code
schema = registry.register_python_code("my_cli_app.py")
```

### 2. Enhanced NLP Backend
```python
from nlp2cmd.nlp_enhanced import HybridNLPBackend

# Uses shell-gpt, LLM, and rule-based fallbacks
backend = HybridNLPBackend(schema_registry=registry)
plan = backend.generate_plan("find all Python files larger than 1MB")
```

### 3. Dynamic Adapter
```python
from nlp2cmd.adapters.dynamic import DynamicAdapter

# No hardcoded patterns - uses extracted schemas
adapter = DynamicAdapter(schema_registry=registry)
command = adapter.generate(plan)
```

## Usage Examples

### Basic Usage
```python
from nlp2cmd.enhanced import create_enhanced_nlp2cmd

# Create enhanced instance with dynamic schemas
nlp2cmd = create_enhanced_nlp2cmd(
    schemas=["find", "git", "docker"],  # Shell commands
    nlp_backend="hybrid"  # shell-gpt + fallbacks
)

# Transform natural language
result = nlp2cmd.transform("find all Python files in current directory")
print(result.command)  # find . -name "*.py" -type f
```

### OpenAPI Integration
```python
# Register API specification
nlp2cmd.register_schema_source(
    "https://petstore.swagger.io/v2/swagger.json",
    source_type="openapi",
    category="petstore_api"
)

# Generate API calls
result = nlp2cmd.transform("list all available pets")
print(result.command)  # curl -X GET https://petstore.swagger.io/v2/pets
```

### Python Click Integration
```python
# Register Python CLI application
nlp2cmd.register_schema_source(
    "my_cli.py",
    source_type="python", 
    category="custom_tools"
)

# Generate CLI commands
result = nlp2cmd.transform("export data as JSON to output.json")
print(result.command)  # python my_cli.py export --format json --output output.json
```

## Architecture

### Schema Extraction Pipeline
1. **OpenAPI Extractor** - Parses specs, extracts endpoints/parameters
2. **Shell Help Extractor** - Runs `command --help`, parses output
3. **Python Code Extractor** - Uses AST to find Click decorators and functions
4. **Dynamic Registry** - Manages all extracted schemas

### NLP Processing Pipeline
1. **Shell-gpt Backend** - Primary AI-powered extraction
2. **LLM Backend** - Fallback to OpenAI/Claude APIs  
3. **Rule-based Backend** - Final fallback with regex patterns

### Command Generation Pipeline
1. **Schema Matching** - Find relevant commands by intent/entities
2. **Parameter Mapping** - Map extracted entities to command parameters
3. **Command Formatting** - Generate appropriate command syntax

## Installation

```bash
# Install enhanced requirements
pip install -r requirements-enhanced.txt

# Install shell-gpt for AI-powered commands
pip install shell-gpt

# Set up API keys (optional)
export OPENAI_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"
```

## Testing

```bash
# Run basic tests
python tools/manual_tests/test_enhanced.py

# Run full test suite
python -m pytest tools/manual_tests/test_enhanced.py -v

# Run demo
python -c "from nlp2cmd.enhanced import demo_dynamic_extraction; demo_dynamic_extraction()"
```

## Migration from Original

The enhanced version is backward compatible. Simply replace:

```python
# Old way
from nlp2cmd import NLP2CMD, ShellAdapter
nlp2cmd = NLP2CMD(adapter=ShellAdapter())

# New way  
from nlp2cmd.enhanced import EnhancedNLP2CMD
nlp2cmd = EnhancedNLP2CMD()
```

The enhanced version automatically extracts schemas and provides much more flexibility without hardcoded patterns.

## Benefits

- **No Hardcoded Keywords** - All patterns extracted dynamically
- **Multi-source Support** - OpenAPI, shell help, Python code, etc.
- **AI-powered** - shell-gpt integration for intelligent understanding
- **Extensible** - Easy to add new schema extractors
- **Backward Compatible** - Drop-in replacement for original
- **Better Accuracy** - Schema-aware command generation
- **Real-time Updates** - Schemas extracted when needed

## Configuration

```python
config = {
    "nlp_config": {
        "shell_gpt_path": "/usr/local/bin/sgpt",
        "fallback_enabled": True,
    },
    "adapter_config": {
        "safety_policy": "dynamic",
    },
    "initial_schemas": [
        "find", "grep", "git", "docker",  # Shell commands
        "https://api.example.com/openapi.json",  # API specs
        "my_cli.py",  # Python apps
    ]
}

nlp2cmd = EnhancedNLP2CMD(config=config)
```

This enhanced implementation provides a robust, flexible foundation for natural language to command transformation that adapts to your specific tools and APIs rather than relying on static patterns.
