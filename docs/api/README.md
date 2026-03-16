# NLP2CMD API Reference

## 📚 Related Documentation

- **[Documentation Hub](../README.md)** - Entry point for all docs
- **[User Guide](../user-guide/user-guide.md)** - Complete usage tutorial
- **[Installation Guide](../../INSTALLATION.md)** - Setup instructions
- **[Thermodynamic Integration](../../THERMODYNAMIC_INTEGRATION.md)** - Advanced optimization
- **[Contributing Guide](../../CONTRIBUTING.md)** - Development guidelines
- **[Examples](../../examples/)** - Practical code examples

## Core Module

### NLP2CMD

Main class for transforming natural language into DSL commands.

```python
from nlp2cmd import NLP2CMD, SQLAdapter

nlp = NLP2CMD(
    adapter=SQLAdapter(dialect="postgresql"),
    validation_mode="strict"
)

result = nlp.transform("Show all users from Warsaw")
```

#### Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `adapter` | `BaseDSLAdapter` | required | DSL adapter for command generation |
| `nlp_backend` | `NLPBackend` | `RuleBasedBackend()` | NLP processing backend |
| `validator` | `BaseValidator` | `None` | Command validator |
| `feedback_analyzer` | `FeedbackAnalyzer` | `None` | Feedback loop analyzer |
| `validation_mode` | `str` | `"normal"` | Validation strictness |
| `auto_fix` | `bool` | `False` | Auto-fix detected issues |

#### Methods

##### `transform(text, context=None, dry_run=False) -> TransformResult`

Transform natural language text into a DSL command.

**Parameters:**
- `text` (str): Natural language input
- `context` (dict, optional): Additional context
- `dry_run` (bool): If True, don't execute, just generate

**Returns:** `TransformResult`

**Example:**
```python
result = nlp.transform(
    "Find users registered last month",
    context={"table_prefix": "app_"}
)
print(result.command)
print(result.confidence)
```

##### `set_context(key, value)`

Set a context value for subsequent transformations.

##### `clear_context()`

Clear all context.

##### `get_history() -> list[TransformResult]`

Get transformation history.

---

### TransformResult

Result of a transformation operation.

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `status` | `TransformStatus` | Status of transformation |
| `command` | `str` | Generated command |
| `plan` | `ExecutionPlan` | Execution plan |
| `confidence` | `float` | Confidence score (0.0-1.0) |
| `dsl_type` | `str` | DSL type name |
| `errors` | `list[str]` | Error messages |
| `warnings` | `list[str]` | Warning messages |
| `suggestions` | `list[str]` | Improvement suggestions |
| `alternatives` | `list[str]` | Alternative commands |

#### Properties

- `is_success` (bool): Check if transformation was successful
- `is_blocked` (bool): Check if blocked by security policy

---

## Adapters

### SQLAdapter

SQL adapter supporting PostgreSQL, MySQL, SQLite, and MSSQL.

```python
from nlp2cmd import SQLAdapter, SQLSafetyPolicy

adapter = SQLAdapter(
    dialect="postgresql",
    schema_context={
        "tables": ["users", "orders", "products"],
        "relations": {
            "orders.user_id": "users.id"
        }
    },
    safety_policy=SQLSafetyPolicy(
        allow_delete=False,
        require_where_on_update=True
    )
)
```

#### Supported Dialects

- `postgresql`
- `mysql`
- `sqlite`
- `mssql`

#### SQLSafetyPolicy

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `allow_delete` | bool | False | Allow DELETE statements |
| `allow_truncate` | bool | False | Allow TRUNCATE |
| `allow_drop` | bool | False | Allow DROP |
| `require_where_on_update` | bool | True | Require WHERE on UPDATE |
| `require_where_on_delete` | bool | True | Require WHERE on DELETE |
| `max_rows_affected` | int | 1000 | Max rows limit |
| `blocked_tables` | list[str] | [] | Tables to block |

---

### ShellAdapter

Shell adapter for Bash, Zsh, Fish, and PowerShell.

```python
from nlp2cmd import ShellAdapter, ShellSafetyPolicy

adapter = ShellAdapter(
    shell_type="bash",
    environment_context={
        "os": "linux",
        "available_tools": ["docker", "kubectl", "git"]
    },
    safety_policy=ShellSafetyPolicy(
        allow_sudo=False,
        blocked_commands=["rm -rf /"]
    )
)
```

#### ShellSafetyPolicy

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `blocked_commands` | list[str] | [...] | Commands to block |
| `require_confirmation_for` | list[str] | [...] | Commands needing confirmation |
| `allow_sudo` | bool | False | Allow sudo |
| `allow_pipe_to_shell` | bool | False | Allow piping to sh/bash |
| `max_pipe_depth` | int | 5 | Max pipe chain depth |
| `sandbox_mode` | bool | True | Enable sandbox |

---

### DockerAdapter

Docker adapter for CLI and Compose operations.

```python
from nlp2cmd import DockerAdapter, DockerSafetyPolicy

adapter = DockerAdapter(
    safety_policy=DockerSafetyPolicy(
        allow_privileged=False,
        require_image_tag=True
    )
)
```

#### DockerSafetyPolicy

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `allow_privileged` | bool | False | Allow --privileged |
| `allow_host_network` | bool | False | Allow --network host |
| `allow_host_pid` | bool | False | Allow --pid host |
| `blocked_images` | list[str] | [] | Blocked images |
| `require_image_tag` | bool | True | Require image tags |

---

### KubernetesAdapter

Kubernetes adapter for kubectl commands.

```python
from nlp2cmd import KubernetesAdapter, KubernetesSafetyPolicy

adapter = KubernetesAdapter(
    safety_policy=KubernetesSafetyPolicy(
        blocked_namespaces=["kube-system"],
        allow_delete=False
    )
)
```

#### KubernetesSafetyPolicy

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `allowed_namespaces` | list[str] | ["default"] | Allowed namespaces |
| `blocked_namespaces` | list[str] | [...] | Blocked namespaces |
| `allow_delete` | bool | False | Allow delete operations |
| `allow_exec` | bool | True | Allow exec into pods |
| `max_replicas` | int | 10 | Max replica count |

---

### DQLAdapter

Doctrine Query Language adapter for PHP/Symfony.

```python
from nlp2cmd import DQLAdapter

adapter = DQLAdapter(
    entity_context={
        "entities": {
            "User": {"fields": ["id", "name", "email"]},
            "Order": {"fields": ["id", "user_id", "total"]}
        }
    }
)
```

---

## Schemas

### SchemaRegistry

Registry for file format validation and repair.

```python
from nlp2cmd import SchemaRegistry

registry = SchemaRegistry()

# Detect format
schema = registry.detect_format(Path("docker-compose.yml"))

# Validate
result = registry.validate(content, "docker-compose")

# Repair
repaired = registry.repair(content, "docker-compose", auto_fix=True)
```

#### Supported Formats

- Dockerfile
- docker-compose.yml
- Kubernetes manifests
- GitHub Actions workflows
- .env files
- nginx.conf
- SQL migrations

---

## Feedback

### FeedbackAnalyzer

Analyzes transformation results and provides feedback.

```python
from nlp2cmd import FeedbackAnalyzer

analyzer = FeedbackAnalyzer()

feedback = analyzer.analyze(
    original_input="Delete all users",
    generated_output="DELETE FROM users;",
    validation_errors=["Missing WHERE clause"],
    dsl_type="sql"
)

print(feedback.suggestions)
```

### FeedbackResult

| Attribute | Type | Description |
|-----------|------|-------------|
| `type` | `FeedbackType` | Feedback type |
| `original_input` | `str` | Original input |
| `generated_output` | `str` | Generated command |
| `errors` | `list[str]` | Errors |
| `warnings` | `list[str]` | Warnings |
| `suggestions` | `list[str]` | Suggestions |
| `auto_corrections` | `dict` | Auto-corrections |
| `confidence` | `float` | Confidence score |

---

## Environment

### EnvironmentAnalyzer

Analyzes the system environment.

```python
from nlp2cmd import EnvironmentAnalyzer

analyzer = EnvironmentAnalyzer()

# Basic analysis
env = analyzer.analyze()

# Detect tools
tools = analyzer.detect_tools(["docker", "kubectl", "git"])

# Check services
services = analyzer.check_services()

# Find config files
configs = analyzer.find_config_files(Path.cwd())

# Full report
report = analyzer.full_report()
```

---

## Thermodynamic Optimization API

### HybridThermodynamicGenerator

Routes between DSL generation and thermodynamic optimization based on problem complexity.

```python
from nlp2cmd.generation import create_hybrid_generator

# Create hybrid generator
hybrid = create_hybrid_generator()

# Generate solution
result = await hybrid.generate("Zaplanuj 5 zadań w 10 slotach")
print(result['source'])  # 'dsl' or 'thermodynamic'
```

### ThermodynamicGenerator

Direct thermodynamic optimization using Langevin dynamics.

```python
from nlp2cmd.generation import create_thermodynamic_generator

# Create generator
thermo = create_thermodynamic_generator(
    n_samples=5,      # Multiple solutions
    n_steps=500,      # Langevin steps
)

# Generate solution
result = await thermo.generate("Zaplanuj 5 zadań w 10 slotach")
print(result.decoded_output)
print(result.energy_estimate)
```

### Energy Models

Domain-specific energy functions for constraint satisfaction.

```python
from nlp2cmd.generation.thermodynamic import (
    SchedulingEnergy,
    AllocationEnergy,
    ConstraintEnergy,
)

# Scheduling energy model
energy = SchedulingEnergy()

# Add custom constraint
energy.add_penalty(
    "custom_constraint",
    lambda z, c: violation_function(z, c),
    lambda z, c: gradient_function(z, c),
    weight=10.0
)
```

### Langevin Configuration

Configure Langevin dynamics sampling parameters.

```python
from nlp2cmd.generation.thermodynamic import LangevinConfig

config = LangevinConfig(
    mu=1.0,              # Mobility coefficient
    kT=0.5,              # Thermal energy
    dt=0.01,             # Time step
    n_steps=1000,        # Integration steps
    dim=64,              # Latent dimension
    record_trajectory=True,
)
```

---

## CLI Reference

```bash
# Interactive mode
nlp2cmd --interactive

# Single query
nlp2cmd --query "Find large files"

# Repair file
nlp2cmd --repair docker-compose.yml --backup

# Validate file
nlp2cmd --validate ./k8s/*.yaml

# Analyze environment
nlp2cmd --analyze-env --output report.json

# Watch mode
nlp2cmd --watch ./config/ --format kubernetes
```

### CLI Options

| Option | Description |
|--------|-------------|
| `-i, --interactive` | Interactive REPL mode |
| `-d, --dsl` | DSL type (auto, sql, shell, docker, kubernetes) |
| `-f, --files` | Files to process |
| `-s, --schema` | Schema file (JSON/YAML) |
| `-w, --watch` | Watch directory for changes |
| `--repair` | Repair configuration file |
| `--validate` | Validate file |
| `--analyze-env` | Analyze environment |
| `-o, --output` | Output file |
| `--auto-repair` | Auto-fix issues |
| `--backup` | Create backups |
| `-q, --query` | Single query |
