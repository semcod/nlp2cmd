"""Schema registry for managing dynamically extracted schemas."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Union

from .extractors import ExtractedSchema
from .python_extractors import PythonCodeExtractor
from .script_extractors import MakefileExtractor, ShellScriptExtractor


class SchemaRegistry:
    """Registry for managing dynamically extracted schemas."""
    
    def __init__(
        self,
        auto_save_path: Optional[Union[str, Path]] = None,
        use_llm: bool = False,
        llm_config: Optional[Dict] = None,
        use_per_command_storage: bool = True,
        storage_dir: Optional[str] = "./command_schemas",
    ):
        from .extractors import OpenAPISchemaExtractor, ShellHelpExtractor
        from .llm_extractor import LLMSchemaExtractor
        from nlp2cmd.storage.per_command_store import PerCommandSchemaStore
        
        self.schemas: Dict[str, ExtractedSchema] = {}
        self.openapi_extractor = OpenAPISchemaExtractor()
        self.shell_extractor = ShellHelpExtractor()
        self.python_extractor = PythonCodeExtractor()
        self.shell_script_extractor = ShellScriptExtractor()
        self.makefile_extractor = MakefileExtractor()
        self.auto_save_path = Path(auto_save_path) if auto_save_path else None
        
        # Initialize per-command storage
        self.use_per_command_storage = use_per_command_storage
        self.per_command_store = None
        if use_per_command_storage:
            storage_path = storage_dir or "./command_schemas"
            self.per_command_store = PerCommandSchemaStore(storage_path)
            # Load existing schemas from storage
            self._load_from_storage()
        
        # Initialize LLM extractor if requested
        self.use_llm = use_llm
        self.llm_extractor = None
        if use_llm and LLMSchemaExtractor:
            self.llm_extractor = LLMSchemaExtractor(llm_config or {})
    
    def _auto_save(self) -> None:
        """Auto-save schemas to file if path is configured."""
        if self.auto_save_path:
            self.save_cache(self.auto_save_path)
        # Also save to per-command storage if enabled
        if self.use_per_command_storage and self.per_command_store:
            self._save_to_storage()
    
    def _load_from_storage(self):
        """Load schemas from per-command storage."""
        if not self.per_command_store:
            return
        
        print(f"[Registry] Loading schemas from {self.per_command_store.base_dir}")
        commands = self.per_command_store.list_commands()
        loaded = 0
        
        for command in commands:
            schema = self.per_command_store.load_schema(command)
            if schema:
                self.schemas[schema.source] = schema
                loaded += 1
        
        print(f"[Registry] Loaded {loaded} schemas from storage")
    
    def _save_to_storage(self):
        """Save all schemas to per-command storage."""
        if not self.per_command_store:
            return
        
        saved = 0
        for source, schema in self.schemas.items():
            if self.per_command_store.store_schema(schema):
                saved += 1
        
        if saved > 0:
            print(f"[Registry] Saved {saved} schemas to per-command storage")
    
    def register_openapi_schema(self, source: Union[str, Path]) -> ExtractedSchema:
        """Register OpenAPI schema from URL or file."""
        if isinstance(source, str) and source.startswith(('http://', 'https://')):
            schema = self.openapi_extractor.extract_from_url(source)
        else:
            schema = self.openapi_extractor.extract_from_file(source)
        
        self.schemas[schema.source] = schema
        self._auto_save()  # Auto-save after registration
        return schema
    
    def register_shell_help(self, command: str) -> ExtractedSchema:
        """Register shell command help schema."""
        # Try LLM extractor first if enabled
        if self.use_llm and self.llm_extractor:
            try:
                schema = self.llm_extractor.extract_from_command(command)
            except Exception as e:
                print(f"[Registry] LLM extraction failed for {command}: {e}")
                schema = self.shell_extractor.extract_from_command(command)
        else:
            schema = self.shell_extractor.extract_from_command(command)
        
        self.schemas[schema.source] = schema
        self._auto_save()  # Auto-save after registration
        return schema
    
    def save_cache(self, path: Union[str, Path]) -> None:
        """Save registry cache to file."""
        import json
        
        path = Path(path)
        cache_data = {
            "schemas": {
                source: schema.to_dict() for source, schema in self.schemas.items()
            }
        }
        
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(cache_data, f, indent=2)
    
    def load_cache(self, path: Union[str, Path]) -> None:
        """Load registry cache from file."""
        import json
        
        path = Path(path)
        if not path.exists():
            return
        
        with open(path, 'r') as f:
            cache_data = json.load(f)
        
        # Convert dictionaries back to ExtractedSchema objects
        for source, schema_dict in cache_data.get("schemas", {}).items():
            schema = ExtractedSchema.from_dict(schema_dict)
            self.schemas[source] = schema
    
    def get_schema(self, source: str) -> Optional[ExtractedSchema]:
        """Get schema by source identifier."""
        return self.schemas.get(source)
    
    def list_schemas(self) -> list[str]:
        """List all registered schema sources."""
        return list(self.schemas.keys())
    
    def clear(self) -> None:
        """Clear all registered schemas."""
        self.schemas.clear()


class DynamicSchemaRegistry(SchemaRegistry):
    """Extended schema registry with command-level operations for DynamicAdapter."""

    def register_python_code(self, source: Union[str, Path]) -> ExtractedSchema:
        """Register Python code schema from file."""
        schema = self.python_extractor.extract_from_file(source)
        self.schemas[schema.source] = schema
        self._auto_save()
        return schema

    def register_shell_script(self, source: Union[str, Path]) -> ExtractedSchema:
        """Register shell script schema from file."""
        schema = self.shell_script_extractor.extract_from_file(source)
        self.schemas[schema.source] = schema
        self._auto_save()
        return schema

    def register_makefile(self, source: Union[str, Path]) -> ExtractedSchema:
        """Register Makefile schema from file."""
        schema = self.makefile_extractor.extract_from_file(source)
        self.schemas[schema.source] = schema
        self._auto_save()
        return schema

    def register_appspec_export(self, source: Union[str, Path]) -> ExtractedSchema:
        """Register AppSpec export JSON."""
        from .extractors import CommandSchema, CommandParameter
        path = Path(source)
        data = json.loads(path.read_text(encoding="utf-8"))
        commands = []
        for cmd in data.get("commands", []):
            params = [
                CommandParameter(
                    name=p["name"],
                    type=p.get("type", "string"),
                    description=p.get("description", ""),
                    required=p.get("required", False),
                )
                for p in cmd.get("parameters", [])
            ]
            commands.append(
                CommandSchema(
                    name=cmd["name"],
                    description=cmd.get("description", ""),
                    category=cmd.get("category", "general"),
                    parameters=params,
                    examples=cmd.get("examples", []),
                    patterns=cmd.get("patterns", []),
                    source_type="appspec",
                    metadata=cmd.get("metadata", {}),
                )
            )
        schema = ExtractedSchema(
            source=str(source),
            source_type="appspec",
            commands=commands,
            metadata={"format": "app2schema.appspec"},
        )
        self.schemas[schema.source] = schema
        self._auto_save()
        return schema

    def register_dynamic_export(self, source: Union[str, Path]) -> list[ExtractedSchema]:
        """Register dynamic schema export JSON."""
        from .extractors import CommandSchema, CommandParameter
        path = Path(source)
        data = json.loads(path.read_text(encoding="utf-8"))
        schemas: list[ExtractedSchema] = []
        for entry in data.get("schemas", []):
            commands = []
            for cmd in entry.get("commands", []):
                params = [
                    CommandParameter(
                        name=p["name"],
                        type=p.get("type", "string"),
                        description=p.get("description", ""),
                        required=p.get("required", False),
                    )
                    for p in cmd.get("parameters", [])
                ]
                commands.append(
                    CommandSchema(
                        name=cmd["name"],
                        description=cmd.get("description", ""),
                        category=cmd.get("category", "general"),
                        parameters=params,
                        examples=cmd.get("examples", []),
                        patterns=cmd.get("patterns", []),
                        source_type="dynamic_export",
                        metadata=cmd.get("metadata", {}),
                    )
                )
            extracted = ExtractedSchema(
                source=entry.get("source", str(source)),
                source_type="dynamic_export",
                commands=commands,
                metadata=entry.get("metadata", {}),
            )
            self.schemas[extracted.source] = extracted
            schemas.append(extracted)
        self._auto_save()
        return schemas

    def get_command_by_name(self, name: str) -> Optional[CommandSchema]:
        """Get a single command schema by name across all sources."""
        for extracted in self.schemas.values():
            for cmd in extracted.commands:
                if cmd.name == name:
                    return cmd
        return None

    def get_all_commands(self) -> list[CommandSchema]:
        """Get all command schemas from all sources."""
        commands: list[CommandSchema] = []
        for extracted in self.schemas.values():
            commands.extend(extracted.commands)
        return commands

    def search_commands(self, query: str, limit: int = 10) -> list[CommandSchema]:
        """Search commands by name or patterns."""
        query_lower = query.lower()
        matches: list[tuple[CommandSchema, int]] = []
        for extracted in self.schemas.values():
            for cmd in extracted.commands:
                score = 0
                if query_lower in cmd.name.lower():
                    score += 10
                for pattern in cmd.patterns:
                    if query_lower in pattern.lower():
                        score += 5
                if query_lower in cmd.description.lower():
                    score += 3
                if score > 0:
                    matches.append((cmd, score))
        matches.sort(key=lambda x: x[1], reverse=True)
        return [cmd for cmd, _ in matches[:limit]]

    def register_command(self, schema: CommandSchema) -> None:
        """Register a single command schema."""
        extracted = self.schemas.get(schema.name)
        if extracted is None:
            extracted = ExtractedSchema(
                source=schema.name,
                source_type=schema.source_type,
                commands=[schema],
            )
        else:
            extracted.commands.append(schema)
        self.schemas[schema.name] = extracted
        self._auto_save()
