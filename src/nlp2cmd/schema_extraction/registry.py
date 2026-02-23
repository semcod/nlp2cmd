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
        from .storage import PerCommandSchemaStore
        
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
