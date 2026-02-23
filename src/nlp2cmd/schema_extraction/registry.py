"""
Schema registry for managing extracted schemas.

Provides registration, storage, and retrieval of command schemas.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .extractors import ExtractedSchema
from .python_extractors import PythonCodeExtractor, ClickExtractor
from .script_extractors import ShellScriptExtractor, MakefileExtractor


# Import per-command storage
from ..storage.per_command_store import PerCommandSchemaStore


class SchemaRegistry:
    """Registry for managing command schemas from various sources."""
    
    def __init__(
        self,
        storage_path: Optional[Path] = None,
        use_llm: bool = False,
        llm_extractor: Optional[Any] = None,
    ):
        self.storage_path = storage_path or Path.home() / ".nlp2cmd" / "schemas"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.schemas: Dict[str, ExtractedSchema] = {}
        self.use_llm = use_llm
        self.llm_extractor = llm_extractor
        
        # Initialize extractors
        self.openapi_extractor = None
        try:
            from .extractors import OpenAPISchemaExtractor
            self.openapi_extractor = OpenAPISchemaExtractor()
        except ImportError:
            pass
        
        from .extractors import ShellHelpExtractor
        self.shell_help_extractor = ShellHelpExtractor()
        self.python_extractor = PythonCodeExtractor()
        self.click_extractor = ClickExtractor()
        self.shell_script_extractor = ShellScriptExtractor()
        self.makefile_extractor = MakefileExtractor()
        
        # Initialize storage
        self.store = PerCommandSchemaStore()
        
        # Load existing schemas
        self._load_schemas()
    
    def _load_schemas(self):
        """Load schemas from storage."""
        try:
            self.schemas = self.store.load_all_schemas()
        except Exception:
            self.schemas = {}
    
    def _auto_save(self):
        """Auto-save schemas to storage."""
        try:
            saved = self.store.save_schemas(self.schemas)
            if saved > 0:
                print(f"[Registry] Saved {saved} schemas to per-command storage")
        except Exception:
            pass
    
    def register_openapi_schema(self, source: Union[str, Path]) -> ExtractedSchema:
        """Register OpenAPI schema from URL or file."""
        if not self.openapi_extractor:
            raise ImportError("httpx is required for OpenAPI schema extraction")
        
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
                schema = self.llm_extractor.extract_from_command_help(command)
                self.schemas[schema.source] = schema
                self._auto_save()
                return schema
            except Exception:
                pass
        
        # Fallback to shell help extractor
        schema = self.shell_help_extractor.extract_from_command(command)
        self.schemas[schema.source] = schema
        self._auto_save()  # Auto-save after registration
        return schema
    
    def register_python_code(self, source: Union[str, Path]) -> ExtractedSchema:
        """Register Python code schema."""
        if isinstance(source, str) and '\n' in source:
            schema = self.python_extractor.extract_from_source(source)
        else:
            schema = self.python_extractor.extract_from_file(source)
        
        self.schemas[schema.source] = schema
        self._auto_save()  # Auto-save after registration
        return schema
    
    def register_shell_script(self, source: Union[str, Path]) -> ExtractedSchema:
        """Register schema from a shell script file (.sh)."""
        schema = self.shell_script_extractor.extract_from_file(source)
        self.schemas[schema.source] = schema
        self._auto_save()  # Auto-save after registration
        return schema
    
    def register_makefile(self, source: Union[str, Path]) -> ExtractedSchema:
        """Register schema from a Makefile."""
        schema = self.makefile_extractor.extract_from_file(source)
        self.schemas[schema.source] = schema
        self._auto_save()  # Auto-save after registration
        return schema
    
    def register_dynamic_export(self, file_path: Union[str, Path]) -> list[ExtractedSchema]:
        """Register schemas from dynamic export file."""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Export file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        schemas = []
        
        for item in data.get('schemas', []):
            schema = ExtractedSchema(
                source=item.get('source', ''),
                commands=item.get('commands', []),
                metadata=item.get('metadata', {}),
            )
            self.schemas[schema.source] = schema
            schemas.append(schema)
        
        self._auto_save()
        return schemas
    
    def get_schema(self, source: str) -> Optional[ExtractedSchema]:
        """Get schema by source."""
        return self.schemas.get(source)
    
    def list_schemas(self) -> List[str]:
        """List all registered schema sources."""
        return list(self.schemas.keys())
    
    def search_commands(self, query: str) -> List[Any]:
        """Search for commands matching query."""
        results = []
        query_lower = query.lower()
        
        for schema in self.schemas.values():
            for command in schema.commands:
                if (query_lower in command.name.lower() or 
                    query_lower in command.description.lower()):
                    results.append(command)
        
        return results
    
    def validate(self, content: str, schema_type: str) -> Dict[str, Any]:
        """Validate content against schema type."""
        errors = []
        warnings = []
        
        try:
            if schema_type == "openapi":
                import json
                try:
                    data = json.loads(content)
                    if not isinstance(data, dict):
                        errors.append("OpenAPI spec must be a JSON object")
                    elif "paths" not in data:
                        warnings.append("OpenAPI spec missing 'paths' field")
                except json.JSONDecodeError:
                    errors.append("Invalid JSON format")
            
            elif schema_type == "python":
                import ast
                try:
                    ast.parse(content)
                except SyntaxError as e:
                    errors.append(f"Python syntax error: {e}")
            
            elif schema_type == "shell":
                # Basic shell script validation
                if not content.strip():
                    errors.append("Empty shell script")
                elif not any(line.strip().startswith("#") for line in content.split('\n')):
                    warnings.append("Shell script missing shebang or comments")
            
        except Exception as e:
            errors.append(f"Validation error: {e}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
    
    def repair(self, content: str, schema_type: str, auto_fix: bool = True) -> Dict[str, Any]:
        """Repair content based on schema type."""
        changes = []
        repaired_content = content
        
        try:
            if schema_type == "python":
                # Fix common Python issues
                lines = content.split('\n')
                fixed_lines = []
                
                for line in lines:
                    # Add missing imports
                    if "click.command" in line and "import click" not in content:
                        fixed_lines.append("import click")
                        changes.append("Added missing click import")
                    
                    fixed_lines.append(line)
                
                repaired_content = '\n'.join(fixed_lines)
            
            elif schema_type == "shell":
                # Fix common shell script issues
                if not content.strip().startswith("#!"):
                    repaired_content = "#!/bin/bash\n" + content
                    changes.append("Added shebang")
                
                if "function" in content and "{" not in content:
                    repaired_content = repaired_content.replace("function", "function {")
                    changes.append("Added function braces")
            
            elif schema_type == "openapi":
                # Fix common OpenAPI issues
                try:
                    data = json.loads(content)
                    if "openapi" not in data and "swagger" not in data:
                        data["openapi"] = "3.0.0"
                        changes.append("Added OpenAPI version")
                    
                    if "info" not in data:
                        data["info"] = {"title": "API", "version": "1.0.0"}
                        changes.append("Added info section")
                    
                    repaired_content = json.dumps(data, indent=2)
                except json.JSONDecodeError:
                    pass
        
        except Exception as e:
            changes.append(f"Repair error: {e}")
        
        return {
            "content": repaired_content,
            "changes": changes,
            "repaired": len(changes) > 0 and auto_fix,
        }
    
    def detect_format(self, file_path: Path) -> Optional[str]:
        """Detect schema format from file path and content."""
        file_path = Path(file_path)
        
        # Check file extension
        suffix = file_path.suffix.lower()
        
        if suffix in ['.yaml', '.yml']:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    if 'openapi' in content.lower() or 'swagger' in content.lower():
                        return 'openapi'
            except Exception:
                pass
        
        elif suffix == '.json':
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, dict) and ('openapi' in data or 'swagger' in data):
                        return 'openapi'
            except Exception:
                pass
        
        elif suffix == '.py':
            return 'python'
        
        elif suffix == '.sh':
            return 'shell'
        
        elif file_path.name.lower() in ['makefile', 'makefile.am', 'makefile.in']:
            return 'makefile'
        
        # Try to detect from content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read(1000)  # Read first 1000 chars
                
                if 'openapi:' in content.lower() or 'swagger:' in content.lower():
                    return 'openapi'
                elif content.strip().startswith('#!/bin/bash') or content.strip().startswith('#!/bin/sh'):
                    return 'shell'
                elif 'def ' in content and 'import ' in content:
                    return 'python'
                elif content.strip().startswith('# Makefile') or ':' in content:
                    return 'makefile'
        except Exception:
            pass
        
        return None
