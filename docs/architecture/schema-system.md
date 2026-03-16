# Schema System Architecture

## Overview

System schematów w NLP2CMD pozwala na ekstrakcję, przechowywanie i wykorzystanie metadanych poleceń do generowania precyzyjnych komend z naturalnego języka.

## Core Concepts

### Schema

Schema opisuje strukturę polecenia:
- Nazwa komendy
- Parametry (wymagane/opcjonalne)
- Szablony użycia
- Przykłady

```json
{
  "command": "docker",
  "version": "1.0",
  "description": "Docker container management",
  "category": "container",
  "parameters": [
    {
      "name": "image",
      "type": "string",
      "required": true,
      "description": "Container image"
    }
  ],
  "templates": [
    "docker run {image}",
    "docker run -d {image}"
  ]
}
```

## Components

### 1. Schema Extraction (`src/nlp2cmd/schema_extraction/`)

Ekstrakcja schematów z różnych źródeł:
- `man` pages
- `--help` output
- AppSpec files
- Istniejące komendy

**Key Classes:**
```python
from nlp2cmd.schema_extraction import DynamicSchemaRegistry

registry = DynamicSchemaRegistry(
    use_per_command_storage=True,
    storage_dir="./command_schemas"
)

# Extract from command help
schema = registry.register_shell_help("docker")

# Extract from AppSpec
schema = registry.register_appspec("path/to/appspec.json")
```

### 2. Schema Storage (`src/nlp2cmd/storage/`)

Przechowywanie schematów w `command_schemas/`:
- Per-command storage: każdy schemat w osobnym pliku JSON
- Kategoryzacja w `categories/`
- Index w `index.json`

**Structure:**
```
command_schemas/
├── categories/          # Schema categories
├── commands/            # Individual command schemas  
├── docker.appspec.json
├── docker.json
├── index.json
└── nginx.json
```

### 3. Schema-Based Generation (`src/nlp2cmd/generation/schema/`)

**Note:** Module przeniesiony z `schema_based/` do `generation/schema/` jako shims.

Generowanie komend na podstawie schematów:
- Pattern matching
- Context-aware generation
- Learning from feedback

```python
# Historical API (deprecated shim)
from nlp2cmd.generation.schema import SchemaBasedGenerator

generator = SchemaBasedGenerator(llm_config)
command = generator.generate_command('find', {'path': '/home', 'pattern': '*.py'})
```

## Usage Flow

```
1. User Input (NL)
      ↓
2. Schema Registry Lookup
      ↓
3. Schema-Based Generation
      ↓
4. Command Output
```

## Versioning

Schematy wspierają wersjonowanie:
- Major: breaking changes
- Minor: new features
- Patch: bug fixes

```json
{
  "command": "docker",
  "version": "2.1.0",
  "migration_notes": "v1→v2: --rm moved to run options"
}
```

## Integration with Pipeline

Schematy są używane w pipeline NLP2CMD jako pierwszy poziom generacji:

1. **Schema Match** - sprawdź czy istnieje schema
2. **Template Match** - użyj zapisanych szablonów
3. **LLM Fallback** - generuj przez LLM jeśli brak schema

## Best Practices

1. **Start with good schemas** - Provide quality initial schemas
2. **Use per-command storage** - Lepsza organizacja
3. **Collect feedback** - Enable user feedback for improvement
4. **Validate generations** - Check generated commands
5. **Version schemas** - Track schema evolution

## Configuration

```python
# Schema extraction config
llm_config = {
    "model": "ollama/qwen2.5-coder:7b",
    "api_base": "http://localhost:11434",
    "temperature": 0.1,
    "max_tokens": 512,
}

# Registry config
registry_config = {
    "use_per_command_storage": True,
    "storage_dir": "./command_schemas",
    "auto_version": True
}
```

## Migration History

- **v0.2.0**: Schema extraction introduced
- **v0.3.0**: Per-command storage added
- **v0.4.0**: `schema_based/` → `generation/schema/` (shims)

## Related Documentation

- [API Reference](api/README.md) - Detailed API
- [Examples Guide](reference/examples-guide.md) - Practical examples
- [Versioned Schemas](#versioning) - Schema versioning
