# Exploration System Guide

## Overview

The Exploration System provides automatic resource discovery across multiple domains:
- **Web**: Websites, forms, content pages
- **Disk**: File systems, directories, config files
- **Services**: API endpoints, REST/GraphQL services
- **Data Trees**: JSON, nested data structures

## Quick Start

### Universal Exploration

```python
from nlp2cmd.exploration import explore, ExplorationContext

# Explore any space - auto-detected
result = explore("https://example.com", "contact")  # Finds contact forms
result = explore("/etc", "config", search_term="nginx")  # Finds config files
result = explore({"data": [...]}, "field")  # Finds in data structures
```

### Specific Explorers

```python
from nlp2cmd.exploration import (
    SiteExplorer,      # Web exploration
    DiskExplorer,      # File system
    ServiceExplorer,   # API discovery
    DataTreeExplorer,  # Data structures
)

# Web - find contact forms
explorer = SiteExplorer()
result = explorer.find_form("https://example.com", intent="contact")

# Disk - find config files
disk = DiskExplorer()
files = disk.find_config("~", app_name="myapp")

# Service - find API endpoints
api = ServiceExplorer()
endpoint = api.explore("https://api.example.com", ExplorationContext(intent="user"))

# Data - find fields in JSON
explorer = DataTreeExplorer()
path = explorer.quick_find_in_data(data, "email")
```

## Resource Discovery Manager

The `ResourceDiscoveryManager` is integrated into the execution pipeline to automatically discover missing resources when commands fail.

### How It Works

```
Command Fails (missing file/dir)
         ↓
ResourceDiscoveryManager.analyze_error()
         ↓
should_attempt_discovery()?
         ↓
   YES → discover_missing_resource()
         ↓
   adapt_command() with new path
         ↓
   Retry command
```

### Usage in Execution

```python
from nlp2cmd.execution.runner import ExecutionRunner

runner = ExecutionRunner(use_resource_discovery=True)
result = runner.run_with_recovery("cat /etc/missing.conf", query)

# If /etc/missing.conf doesn't exist, system will:
# 1. Search for similar config files
# 2. Find alternative (e.g., ~/projects/app/config.conf)
# 3. Retry with discovered path
```

## Explorers Reference

### SiteExplorer (Web)

Finds forms, articles, products, documentation on websites.

```python
from nlp2cmd.web_schema import SiteExplorer

explorer = SiteExplorer(max_depth=2, max_pages=10)

# Find contact forms
result = explorer.find_form("https://example.com", intent="contact")
if result.success:
    print(f"Found form at: {result.form_url}")

# Find content
result = explorer.find_content(
    "https://example.com",
    content_type="article",  # or "product", "docs"
    search_term="pricing"
)

# Universal explore with intent detection
result = explorer.explore("https://example.com", "find pricing page")
```

**Supported Intents:**
- `contact` - Contact forms
- `article` - Articles, blog posts
- `product` - Products, pricing
- `docs` - Documentation pages

### DiskExplorer (File System)

Finds files, directories, configs on disk.

```python
from nlp2cmd.exploration import DiskExplorer, ExplorationContext

disk = DiskExplorer(max_depth=5)

# General file search
result = disk.explore(
    "/etc",
    ExplorationContext(intent="file", search_term="nginx")
)

# Find config files
configs = disk.find_config("~", app_name="myapp")

# Find code files
result = disk.explore(
    ".",
    ExplorationContext(intent="code", search_term="main")
)

# Find data files
data_files = disk.explore(
    "/data",
    ExplorationContext(intent="data", search_term="users")
)
```

**Supported Intents:**
- `file` - General files
- `config` - Configuration files
- `code` - Source code files
- `data` - Data files (JSON, CSV, etc.)

### ServiceExplorer (APIs)

Discovers REST/GraphQL API endpoints.

```python
from nlp2cmd.exploration import ServiceExplorer, ExplorationContext

service = ServiceExplorer(
    timeout_seconds=10,
    auth_token="Bearer xxx",
)

# Discover endpoints
result = service.explore(
    "https://api.example.com",
    ExplorationContext(intent="endpoint", search_term="user")
)

# Quick find
from nlp2cmd.exploration import quick_find_endpoint
url = quick_find_endpoint("https://api.example.com", "users")
```

**Discovery Methods:**
- OpenAPI/Swagger specs
- Common REST patterns
- GraphQL introspection

### DataTreeExplorer (Data Structures)

Navigates JSON, dicts, nested data.

```python
from nlp2cmd.exploration import DataTreeExplorer, ExplorationContext

explorer = DataTreeExplorer(max_depth=10)

data = {
    "users": [
        {"name": "Alice", "email": "alice@test.com"},
        {"name": "Bob", "email": "bob@test.com"}
    ]
}

# Find by search term
result = explorer.explore(
    data,
    ExplorationContext(intent="data", search_term="email")
)
print(result.target.path)  # "users[0].email"

# Get value at path
value = explorer.get_value(data, "users[0].email")
print(value)  # "alice@test.com"

# Quick find
from nlp2cmd.exploration import quick_find_in_data
path = quick_find_in_data(data, "bob")
print(path)  # "users[1].name"
```

## Error Patterns

ResourceDiscoveryManager recognizes these error patterns:

| Error | Resource Type | Action |
|-------|--------------|--------|
| `No such file or directory` | file | Search filesystem |
| `cd: No such file` | directory | Search directories |
| `command not found` | command | Check PATH |
| `ModuleNotFoundError` | package | Suggest install |
| `Connection refused` | endpoint | Search services |

## Configuration

### Enable/Disable Discovery

```python
from nlp2cmd.exploration import ResourceDiscoveryManager

# Disable globally
manager = ResourceDiscoveryManager(auto_discover=False)

# Or per-execution
runner = ExecutionRunner(use_resource_discovery=False)
```

### Discovery Limits

```python
from nlp2cmd.exploration import ResourceDiscoveryManager

manager = ResourceDiscoveryManager(
    max_discovery_depth=3,       # Max recursion depth
    discovery_timeout=10.0,      # Timeout per discovery
    auto_discover=True,          # Enable auto-discovery
)
```

## Integration Examples

### CLI Usage

When using `nlp2cmd -r "command"`, resource discovery is automatically enabled:

```bash
# If config file doesn't exist in expected location,
# system will search and suggest alternatives
nlp2cmd -r "edytuj konfigurację nginx"

# If form not found on page, site will be explored
nlp2cmd -r "wejdź na example.com i wypełnij formularz kontaktu"
```

### Pipeline Integration

```python
from nlp2cmd.pipeline_runner import PipelineRunner

runner = PipelineRunner(use_resource_discovery=True)

# Shell commands with auto-discovery
result = runner.run_shell("cat /etc/missing.conf")
# If file missing → search → retry with found alternative
```

### Custom Explorer Registration

```python
from nlp2cmd.exploration import ExplorerRegistry, BaseExplorer

class MyExplorer(BaseExplorer):
    def supports(self, space_type: str) -> bool:
        return space_type == "myspace"
    
    def explore(self, root, context):
        # Implementation
        pass

# Register
ExplorerRegistry.register("myspace", MyExplorer())

# Use via universal explore
result = explore("my://root", "target", space_type="myspace")
```

## API Reference

### BaseExplorer

Abstract base class for all explorers.

```python
class BaseExplorer(ABC):
    def explore(root: Any, context: ExplorationContext) -> ExplorationResult
    def supports(space_type: str) -> bool
    def reset() -> None
```

### ExplorationContext

Context for what to search for.

```python
@dataclass
class ExplorationContext:
    intent: str                    # What to find
    search_term: Optional[str]     # Specific term
    filters: dict[str, Any]      # Additional filters
    max_depth: int = 3           # Recursion limit
    max_results: int = 10        # Result limit
```

### ExplorationResult

Result of exploration.

```python
@dataclass
class ExplorationResult:
    success: bool
    target: Optional[T]          # Best match
    path: list[str]              # Path to target
    candidates: list[T]        # All matches
    metadata: dict[str, Any]   # Extra info
    error: Optional[str]        # Error message
```

## Troubleshooting

### Discovery Not Working

1. Check if `auto_discover=True` is set
2. Verify error pattern matches known patterns
3. Check discovery timeout (may need to increase)

### False Positives

If wrong resources are discovered:
- Use more specific `search_term`
- Adjust `max_depth` to limit search scope
- Use `filters` to narrow results

### Performance Issues

If discovery is slow:
- Reduce `max_depth` (default: 3)
- Reduce `max_results` (default: 10)
- Increase `discovery_timeout` (default: 10s)
- Use more specific search terms

## See Also

- `WEB_SCHEMA_GUIDE.md` - Web exploration details
- `python-api.md` - Full API reference
- `cli-reference.md` - CLI usage
