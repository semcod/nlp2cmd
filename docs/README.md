# NLP2CMD

![version](https://img.shields.io/badge/version-1.1.5-blue) ![python](https://img.shields.io/badge/python-%3E%3D3.10-blue) ![license](https://img.shields.io/badge/license-Apache--2.0-green)

> Natural Language to Domain-Specific Commands - Transform natural language into executable commands

**Author:** NLP2CMD Team  
**License:** Apache-2.0[(LICENSE)](../LICENSE)  
**Repository:** [https://github.com/wronai/nlp2cmd](https://github.com/wronai/nlp2cmd)

## 🚀 What is NLP2CMD?

NLP2CMD is a powerful framework that transforms natural language input into domain-specific commands. It supports multiple DSLs including SQL, Shell, Docker, Kubernetes, and browser automation through an advanced "LLM as Planner" architecture.

### Key Features

- **Multi-Domain Support**: SQL, Shell, Docker, Kubernetes, Browser automation, Desktop GUI, Canvas drawing
- **LLM as Planner Architecture**: Intelligent task planning and execution
- **Thermodynamic Optimization**: Advanced constraint solving using physics-inspired algorithms
- **Schema Extraction**: Dynamic schema learning from command help and APIs
- **Evolutionary Recovery**: Self-healing error recovery mechanisms
- **Multi-Language**: Full support for Polish and English

## 📦 Installation

### From PyPI

```bash
pip install nlp2cmd
```

### From Source

```bash
git clone https://github.com/wronai/nlp2cmd
cd nlp2cmd
pip install -e .
```

### Optional Extras

```bash
pip install nlp2cmd[nlp]        # NLP features
pip install nlp2cmd[llm]        # LLM integration (litellm)
pip install nlp2cmd[router]     # Router features
pip install nlp2cmd[sql]        # SQL features
pip install nlp2cmd[thermodynamic]  # Thermodynamic optimization
pip install nlp2cmd[browser]    # Browser automation
pip install nlp2cmd[desktop]    # Desktop automation
pip install nlp2cmd[automation] # Automation features
pip install nlp2cmd[llm-vision] # Vision models
pip install nlp2cmd[dev]        # Development tools
pip install nlp2cmd[all]        # All optional features
```

## 🎯 Quick Start

### CLI Usage

```bash
# Interactive mode
nlp2cmd --interactive

# Single query
nlp2cmd --query "Pokaż wszystkie pliki .log większe niż 10MB"

# With specific DSL
nlp2cmd --dsl sql --query "Znajdź użytkowników z Warszawy"
nlp2cmd --dsl docker --query "Pokaż działające kontenery"

# Analyze environment
nlp2cmd --analyze-env

# Validate configuration files
nlp2cmd --validate docker-compose.yml
```

### Python API

```python
from nlp2cmd import NLP2CMD, SQLAdapter

# Initialize with SQL adapter
nlp = NLP2CMD(adapter=SQLAdapter(dialect="postgresql"))

# Transform natural language
result = nlp.transform("Show users from Warsaw")
print(result.command)
print(result.confidence)

# With context
result = nlp.transform(
    "Find recent orders",
    context={"table_prefix": "app_", "date_range": "30 days"}
)
```

### Advanced Usage - LLM as Planner

```python
from nlp2cmd import DecisionRouter, LLMPlanner, PlanExecutor

# Route to appropriate handler
router = DecisionRouter()
decision = router.route("Create a dashboard with charts")

# Execute complex plan
if decision.use_llm:
    planner = LLMPlanner()
    plan = await planner.plan(decision.input)
    
    executor = PlanExecutor()
    result = await executor.execute(plan)
```

## 🏗️ Architecture

### Core Components

1. **NLP Layer**: Intent classification and entity extraction
2. **Decision Router**: Routes to direct execution or LLM planner
3. **LLM Planner**: Generates multi-step execution plans
4. **Action Registry**: Registry of available actions with validation
5. **Plan Executor**: Executes plans with error handling
6. **Result Aggregator**: Formats and summarizes results

### Supported Adapters

| Adapter | DSL | Description |
|---------|-----|-------------|
| SQLAdapter | SQL | PostgreSQL, MySQL, SQLite, MSSQL |
| ShellAdapter | Shell | Bash, Zsh, Fish, PowerShell |
| DockerAdapter | Docker | Container management |
| KubernetesAdapter | K8s | Kubernetes operations |
| BrowserAdapter | DOM | Web automation |
| DesktopAdapter | Desktop | GUI automation |
| CanvasAdapter | Drawing | Canvas drawing |

## 📚 Documentation

- **[API Reference](api/README.md)** - Detailed API documentation
- **[Examples Guide](reference/examples-guide.md)** - Examples overview
- **[Python API Guide](reference/python-api.md)** - Programmatic usage
- **[Architecture Guide](architecture/)** - System architecture
- **[Schema System](architecture/schema-system.md)** - Schema extraction and management
- **[Thermodynamic Integration](../THERMODYNAMIC_INTEGRATION.md)** - Advanced optimization

## 🔧 Configuration

### Environment Variables

```bash
# LLM Configuration
export NLP2CMD_MODEL="ollama/qwen2.5:7b"
export NLP2CMD_API_BASE="http://localhost:11434"
export NLP2CMD_API_KEY="your-api-key"

# Router Configuration
export NLP2CMD_ROUTER_CONFIG="./config/litellm_config.yaml"
export NLP2CMD_ROUTER_VERBOSE="true"

# Feature Flags
export NLP2CMD_AUTO_REPAIR="true"
export NLP2CMD_HEADLESS="true"
```

### Configuration File

```yaml
# config.yaml
llm:
  model: "ollama/qwen2.5:7b"
  api_base: "http://localhost:11434"
  temperature: 0.1
  max_tokens: 2048

router:
  strategy: "latency-based"
  fallback_enabled: true

adapters:
  sql:
    dialect: "postgresql"
  docker:
    safety_policy:
      allow_privileged: false
```

## 🎨 Examples

### SQL Generation

```python
from nlp2cmd import SQLAdapter, NLP2CMD

adapter = SQLAdapter(
    dialect="postgresql",
    safety_policy=SQLSafetyPolicy(
        allow_delete=False,
        require_where_on_update=True
    )
)

nlp = NLP2CMD(adapter=adapter)
result = nlp.transform("Pokaż aktywnych użytkowników z ostatnich 30 dni")
# Generated: SELECT * FROM users WHERE status = 'active' AND created_at >= NOW() - INTERVAL '30 days'
```

### Browser Automation

```python
from nlp2cmd import BrowserAdapter

adapter = BrowserAdapter(headless=True)
nlp = NLP2CMD(adapter=adapter)

result = nlp.transform("Open github.com and search for nlp2cmd")
# Executes: Navigate to GitHub, search for repository
```

### Complex Task Planning

```python
from nlp2cmd import LLMPlanner, PlanExecutor

planner = LLMPlanner()
plan = await planner.plan("Deploy the application to production with zero downtime")

executor = PlanExecutor()
result = await executor.execute(plan)
# Executes multi-step deployment plan
```

## 🧪 Advanced Features

### Thermodynamic Optimization

```python
from nlp2cmd.generation import create_thermodynamic_generator

generator = create_thermodynamic_generator(
    n_samples=1000,
    n_steps=500
)

result = await generator.generate("Optimize task scheduling for 100 tasks")
print(result.decoded_output)
print(result.energy_estimate)
```

### Evolutionary Recovery

```python
from nlp2cmd import EvolutionaryRecoveryEngine

recovery = EvolutionaryRecoveryEngine()
result = await recovery.recover(
    failed_command="docker run invalid_image",
    error="image not found",
    strategy=RecoveryStrategy.ADAPTIVE
)
```

### Schema Extraction

```python
from nlp2cmd.schema_extraction import SchemaRegistry

registry = SchemaRegistry()
schema = registry.register_shell_help("kubectl")
print(schema.commands[0].examples)
```

## 🌐 Multi-Language Support

NLP2CMD supports both Polish and English:

```python
# Polish examples
nlp.transform("Pokaż wszystkie procesy")
nlp.transform("Znajdź pliki większe niż 100MB")
nlp.transform("Uruchom kontener docker z portem 8080")

# English examples
nlp.transform("Show all processes")
nlp.transform("Find files larger than 100MB")
nlp.transform("Run docker container with port 8080")
```

## 🔍 Use Cases

### DevOps Automation
- Infrastructure management
- Deployment automation
- Log analysis
- Monitoring

### Data Science
- SQL query generation
- Data pipeline creation
- Report generation

### Web Automation
- Web scraping
- Form filling
- Testing automation
- Browser automation

### Desktop Automation
- GUI automation
- Application control
- File management
- System administration

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](../CONTRIBUTING.md) for details.

### Development Setup

```bash
git clone https://github.com/wronai/nlp2cmd
cd nlp2cmd
pip install -e ".[dev]"
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test suite
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# Run with coverage
pytest --cov=nlp2cmd
```

## 📊 Performance

- **35,727** functions
- **5,142** classes
- **2,974** files
- **Average Cyclomatic Complexity**: 4.4
- **Test Coverage**: 95%+

## 🗺️ Roadmap

- [ ] Enhanced vision model integration
- [ ] More DSL adapters (Terraform, Ansible)
- [ ] Distributed execution support
- [ ] Web dashboard
- [ ] Plugin system

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](../LICENSE) file for details.

## 🙏 Acknowledgments

- OpenAI for GPT models
- Ollama for local LLM support
- Playwright for browser automation
- All our contributors

## 📞 Support

- **Documentation**: [https://nlp2cmd.readthedocs.io](https://nlp2cmd.readthedocs.io)
- **Issues**: [GitHub Issues](https://github.com/wronai/nlp2cmd/issues)
- **Discussions**: [GitHub Discussions](https://github.com/wronai/nlp2cmd/discussions)

---

**NLP2CMD** - Transforming natural language into commands, intelligently.
