# NLP2CMD User Guide

## 📚 Related Documentation

- **[Documentation Hub](../README.md)** - Entry point for all docs
- **[Installation Guide](../../INSTALLATION.md)** - Setup instructions
- **[API Reference](../api/README.md)** - Detailed API documentation
- **[Thermodynamic Integration](../../THERMODYNAMIC_INTEGRATION.md)** - Advanced optimization
- **[Contributing Guide](../../CONTRIBUTING.md)** - Development guidelines
- **[Examples](../../examples/)** - Practical code examples

## Configuration

### JSON configuration files

NLP2CMD loads rule-based keywords and templates from JSON files. Resolution order is:

- packaged defaults (`nlp2cmd/data/*.json`)
- project overrides (`./data/*.json`)
- user overrides (`~/.config/nlp2cmd/*.json` and legacy `~/.nlp2cmd/*.json`)
- explicit env path (highest precedence)

Environment variables:

- `NLP2CMD_CONFIG_DIR`: user config directory (overrides XDG default)
- `NLP2CMD_PATTERNS_FILE`: explicit `patterns.json`
- `NLP2CMD_KEYWORD_DETECTOR_CONFIG`: explicit `keyword_intent_detector_config.json`
- `NLP2CMD_TEMPLATES_FILE`: explicit `templates.json`
- `NLP2CMD_DEFAULTS_FILE`: explicit `defaults.json`

## Introduction

NLP2CMD is a framework for transforming natural language into domain-specific commands. It supports multiple DSLs including SQL, Shell, Docker, Kubernetes, and more.

## Quick Start

### Installation

```bash
pip install nlp2cmd

# With optional dependencies
pip install nlp2cmd[nlp]      # spaCy support
pip install nlp2cmd[llm]      # LLM support (Claude, GPT)
pip install nlp2cmd[sql]      # SQL parsing
pip install nlp2cmd[all]      # Everything
```

### Basic Usage

```python
from nlp2cmd import NLP2CMD, SQLAdapter

# Create adapter
adapter = SQLAdapter(dialect="postgresql")

# Initialize NLP2CMD
nlp = NLP2CMD(adapter=adapter)

# Transform natural language
result = nlp.transform("Show all users from Warsaw")

print(result.command)
# SELECT * FROM users WHERE city = 'Warsaw';
```

## Interactive Mode

The interactive mode provides a REPL interface with intelligent feedback.

```bash
nlp2cmd --interactive
```

### REPL Commands

| Command | Description |
|---------|-------------|
| `!help` | Show help |
| `!env` | Show environment analysis |
| `!files` | List detected config files |
| `!schema` | Show loaded schema |
| `!history` | Session history |
| `!repair FILE` | Repair config file |
| `!validate FILE` | Validate file |
| `!export FILE` | Export session |
| `exit` | Exit REPL |

### Example Session

```
nlp2cmd> Find all users registered last month

✅ Status: success
📊 Confidence: 94%

📝 Generated command:
   SELECT * FROM users
   WHERE created_at >= NOW() - INTERVAL '1 month'
   ORDER BY created_at DESC;

🚀 Execute? [y/n/preview] y

┌────┬──────────┬────────────────────┐
│ id │ name     │ created_at         │
├────┼──────────┼────────────────────┤
│ 42 │ John Doe │ 2024-01-15 10:30   │
│ 43 │ Jane Doe │ 2024-01-16 14:22   │
└────┴──────────┴────────────────────┘
```

## Working with Different DSLs

### SQL

```python
from nlp2cmd import NLP2CMD, SQLAdapter, SQLSafetyPolicy

adapter = SQLAdapter(
    dialect="postgresql",
    schema_context={
        "tables": ["users", "orders", "products"],
        "relations": {
            "orders.user_id": "users.id",
            "orders.product_id": "products.id"
        }
    },
    safety_policy=SQLSafetyPolicy(
        allow_delete=False,
        require_where_on_update=True
    )
)

nlp = NLP2CMD(adapter=adapter)

# Simple query
result = nlp.transform("Show users from Warsaw")
# SELECT * FROM users WHERE city = 'Warsaw';

# Aggregation
result = nlp.transform("Count orders per user this year")
# SELECT user_id, COUNT(*) FROM orders 
# WHERE created_at >= '2024-01-01' GROUP BY user_id;

# Joins
result = nlp.transform("Show orders with user names")
# SELECT o.*, u.name FROM orders o 
# JOIN users u ON o.user_id = u.id;
```

### Shell

```python
from nlp2cmd import NLP2CMD, ShellAdapter

adapter = ShellAdapter(
    shell_type="bash",
    environment_context={
        "os": "linux",
        "available_tools": ["docker", "git", "kubectl"]
    }
)

nlp = NLP2CMD(adapter=adapter)

# File operations
result = nlp.transform("Find files larger than 100MB")
# find . -type f -size +100M -exec ls -lh {} \;

# Process monitoring
result = nlp.transform("Show top 10 memory consumers")
# ps aux --sort=-%mem | head -11

# Docker operations
result = nlp.transform("List all running containers")
# docker ps

# Git operations
result = nlp.transform("Show commits from last week")
# git log --since='1 week ago' --oneline
```

### Docker

```python
from nlp2cmd import NLP2CMD, DockerAdapter

adapter = DockerAdapter()
nlp = NLP2CMD(adapter=adapter)

# Run container
result = nlp.transform("Run nginx on port 8080")
# docker run -d --name nginx -p 8080:80 nginx:latest

# Docker Compose
result = nlp.transform("Start the stack in background")
# docker-compose up -d

# Cleanup
result = nlp.transform("Remove stopped containers")
# docker container prune -f
```

### Kubernetes

```python
from nlp2cmd import NLP2CMD, KubernetesAdapter

adapter = KubernetesAdapter()
nlp = NLP2CMD(adapter=adapter)

# Get resources
result = nlp.transform("Show all pods in production")
# kubectl get pods -n production

# Scale
result = nlp.transform("Scale nginx to 5 replicas")
# kubectl scale deployment/nginx --replicas=5

# Logs
result = nlp.transform("Show logs for nginx pod")
# kubectl logs nginx-xyz -f --tail=100
```

## File Validation and Repair

### Validating Files

```python
from nlp2cmd import SchemaRegistry
from pathlib import Path

registry = SchemaRegistry()

# Validate docker-compose.yml
with open("docker-compose.yml") as f:
    content = f.read()

result = registry.validate(content, "docker-compose")

if not result["valid"]:
    print("Errors:", result["errors"])
    print("Warnings:", result["warnings"])
```

### Repairing Files

```python
# Auto-repair
repaired = registry.repair(content, "docker-compose", auto_fix=True)

if repaired["repaired"]:
    print("Changes made:")
    for change in repaired["changes"]:
        print(f"  - {change['reason']}")
    
    # Save repaired content
    with open("docker-compose.yml", "w") as f:
        f.write(repaired["content"])
```

### CLI Repair

```bash
# Repair with backup
nlp2cmd --repair docker-compose.yml --backup

# Validate Kubernetes manifests
nlp2cmd --validate ./k8s/*.yaml

# Auto-repair all config files
nlp2cmd --repair ./config/ --auto-repair
```

## Feedback Loop

NLP2CMD includes an intelligent feedback loop that helps refine commands.

### Automatic Corrections

```python
from nlp2cmd import NLP2CMD, SQLAdapter, FeedbackAnalyzer

adapter = SQLAdapter(dialect="postgresql")
analyzer = FeedbackAnalyzer()

nlp = NLP2CMD(
    adapter=adapter,
    feedback_analyzer=analyzer,
    auto_fix=True
)

# This will trigger feedback loop
result = nlp.transform("Delete all inactive users")

# If blocked by policy, suggestions are provided
if result.status == "blocked":
    print("Blocked:", result.errors[0])
    print("Suggestion:", result.suggestions[0])
    # Use soft-delete: UPDATE users SET deleted_at = NOW() WHERE active = false
```

### Interactive Refinement

```
nlp2cmd> Update user email

❓ Needs clarification:
   1. Which user? (specify by ID or name)
   2. What's the new email?

   > user 123, email john@example.com

✅ Status: success
📝 Command:
   UPDATE users SET email = 'john@example.com' WHERE id = 123;
```

## Environment Analysis

### Analyzing Your System

```python
from nlp2cmd import EnvironmentAnalyzer

analyzer = EnvironmentAnalyzer()

# Full analysis
report = analyzer.full_report()

print(f"OS: {report.os_info['system']}")
print(f"Tools available: {[t for t, i in report.tools.items() if i.available]}")
print(f"Services running: {[s for s, i in report.services.items() if i.running]}")
print(f"Recommendations: {report.recommendations}")
```

### CLI Analysis

```bash
# Full environment report
nlp2cmd --analyze-env --output report.json

# Validate command against environment
nlp2cmd --validate-command "kubectl get pods"
```

## Safety Policies

### SQL Safety

```python
from nlp2cmd import SQLSafetyPolicy

policy = SQLSafetyPolicy(
    allow_delete=False,           # Block DELETE
    allow_truncate=False,         # Block TRUNCATE
    allow_drop=False,             # Block DROP
    require_where_on_update=True, # Require WHERE on UPDATE
    max_rows_affected=1000,       # Limit affected rows
    blocked_tables=["audit_log"]  # Block specific tables
)
```

### Shell Safety

```python
from nlp2cmd import ShellSafetyPolicy

policy = ShellSafetyPolicy(
    blocked_commands=["rm -rf /", "mkfs"],
    require_confirmation_for=["rm", "kill"],
    allow_sudo=False,
    sandbox_mode=True
)
```

### Docker Safety

```python
from nlp2cmd import DockerSafetyPolicy

policy = DockerSafetyPolicy(
    allow_privileged=False,
    allow_host_network=False,
    blocked_images=["malicious/*"],
    require_image_tag=True
)
```

## LLM Integration

### Using Claude

```python
from nlp2cmd import NLP2CMD, SQLAdapter, LLMBackend
import os

backend = LLMBackend(
    model="claude-sonnet-4-20250514",
    api_key=os.environ["ANTHROPIC_API_KEY"]
)

nlp = NLP2CMD(
    adapter=SQLAdapter(dialect="postgresql"),
    nlp_backend=backend
)

# More accurate natural language understanding
result = nlp.transform(
    "Find products that sell better than average in their category"
)
```

### Using OpenAI

```python
backend = LLMBackend(
    model="gpt-4",
    api_key=os.environ["OPENAI_API_KEY"]
)
```

## Creating Custom Adapters

```python
from nlp2cmd import BaseDSLAdapter

class RedisAdapter(BaseDSLAdapter):
    DSL_NAME = "redis"
    
    INTENTS = {
        "get": {"patterns": ["get", "fetch", "read"]},
        "set": {"patterns": ["set", "store", "save"]},
        "delete": {"patterns": ["delete", "remove", "del"]},
    }
    
    def generate(self, plan: dict) -> str:
        intent = plan.get("intent")
        entities = plan.get("entities", {})
        
        if intent == "get":
            return f"GET {entities.get('key')}"
        elif intent == "set":
            return f"SET {entities.get('key')} {entities.get('value')}"
        elif intent == "delete":
            return f"DEL {entities.get('key')}"
        
        return ""
    
    def validate_syntax(self, command: str) -> dict:
        # Implement validation
        return {"valid": True, "errors": [], "warnings": []}

# Use custom adapter
adapter = RedisAdapter()
nlp = NLP2CMD(adapter=adapter)
```

## Best Practices

1. **Always configure safety policies** for production use
2. **Use schema context** for better SQL generation
3. **Enable environment analysis** for command validation
4. **Use the feedback loop** for iterative refinement
5. **Create backups** when using auto-repair
6. **Test with dry_run=True** before executing
7. **Review generated commands** before execution

## Troubleshooting

### Common Issues

**Q: Commands are not accurate enough**
- A: Use LLM backend for better NLP
- A: Provide more schema context
- A: Use specific terminology

**Q: Safety policy blocks my command**
- A: Review and adjust policy settings
- A: Use alternative suggested commands

**Q: Environment tools not detected**
- A: Check PATH variable
- A: Install missing tools

**Q: File repair makes wrong changes**
- A: Disable auto_fix and review suggestions
- A: Always use --backup flag
