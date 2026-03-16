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
from nlp2cmd.schema_extraction import SchemaRegistry

registry = SchemaRegistry(
    use_per_command_storage=True,
    storage_dir="./command_schemas"
)

# Extract from command help
schema = registry.register_shell_help("docker")

# Extract from OpenAPI
schema = registry.register_openapi_schema("https://api.example.com/openapi.json")
```

### 2. Schema Storage (`src/nlp2cmd/storage/`)

Przechowywanie schematów w `command_schemas/`:
- Per-command storage: każdy schemat w osobnym pliku JSON
- Kategoryzacja w `categories/`
- Index w `index.json`

**Structure:**
```
command_schemas/
├── browser/            # Browser-specific schemas
├── categories/         # Schema categories
├── commands/           # Individual command schemas  
├── exports/            # Exported schemas
├── keyboard/           # Keyboard command schemas
├── sites/              # Site-specific schemas
├── docker.appspec.json
├── docker.json
├── nginx.json
└── index.json
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

**Note:** Wersjonowanie schematów jest obecnie ograniczone do wersji "1.0".

Planowane wsparcie dla wersjonowania:
- Major: breaking changes
- Minor: new features
- Patch: bug fixes

```json
{
  "command": "docker",
  "version": "1.0",
  "migration_notes": "v1→v2: --rm moved to run options (planned)"
}
```

## Integration with Pipeline

**Current State:** Schematy są częściowo zintegrowane z pipeline NLP2CMD:

1. **Schema Extraction** - `SchemaRegistry` ekstrahuje schematy z różnych źródeł
2. **Schema Storage** - `PerCommandSchemaStore` przechowuje schematy
3. **Limited Integration** - `SchemaBasedGenerator` używany w nielicznych miejscach

**Planned Integration:**
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
    "use_llm": False  # Optional LLM extraction
}
```

## Migration History

- **v0.2.0**: Schema extraction introduced
- **v0.3.0**: Per-command storage added
- **v0.4.0**: `schema_based/` → `generation/schema/` (shims)
- **v0.5.0**: `DynamicSchemaRegistry` → `SchemaRegistry` (rename)
- **v0.5.0**: Added support for OpenAPI, AppSpec exports, dynamic schemas

## Related Documentation

- [API Reference](api/README.md) - Detailed API
- [Examples Guide](reference/examples-guide.md) - Practical examples
- [Versioned Schemas](#versioning) - Schema versioning
