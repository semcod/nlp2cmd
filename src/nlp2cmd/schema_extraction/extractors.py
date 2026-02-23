"""
Schema extractors for different source types.

Contains specialized extractors for OpenAPI, shell help, Python code, etc.
"""

from __future__ import annotations

import ast
import json
import re
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None  # type: ignore

from nlp2cmd.utils.yaml_compat import yaml


def _ast_unparse(node: Optional[ast.AST]) -> str:
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except Exception:
        return node.__class__.__name__


def _python_annotation_to_param_type(annotation: Optional[ast.AST]) -> str:
    if annotation is None:
        return "string"

    txt = _ast_unparse(annotation)
    txt_lower = txt.lower()

    if txt_lower in {"int", "integer"}:
        return "integer"
    if txt_lower in {"float", "double", "number"}:
        return "number"
    if txt_lower in {"bool", "boolean"}:
        return "boolean"
    if "path" in txt_lower:
        return "path"
    if txt_lower.startswith("list[") or txt_lower.startswith("set[") or txt_lower.startswith("tuple["):
        return "array"
    if txt_lower.startswith("dict["):
        return "object"

    return "string"


def _shell_opt_to_param_name(opt: str) -> str:
    return opt.lstrip("-").replace("-", "_")


def _dedupe_params(params: list["CommandParameter"]) -> list["CommandParameter"]:
    seen: set[str] = set()
    out: list[CommandParameter] = []
    for p in params:
        if p.name in seen:
            continue
        seen.add(p.name)
        out.append(p)
    return out


@dataclass
class CommandParameter:
    """Represents a command parameter extracted from schema."""
    
    name: str
    type: str
    description: str = ""
    required: bool = False
    default: Any = None
    choices: Optional[List[str]] = None
    pattern: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None


@dataclass
class CommandSchema:
    """Represents a command schema."""
    
    name: str
    description: str
    parameters: List[CommandParameter] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    category: str = "general"
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedSchema:
    """Container for extracted schema information."""
    
    source: str
    commands: List[CommandSchema] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class OpenAPISchemaExtractor:
    """Extract command schemas from OpenAPI/Swagger specifications."""
    
    def __init__(self, http_client: Optional[httpx.Client] = None):
        if httpx is None:
            raise ImportError("httpx is required for OpenAPI schema extraction")
        self.client = http_client or httpx.Client()
    
    def extract_from_url(self, url: str) -> ExtractedSchema:
        """Extract schema from OpenAPI spec URL."""
        try:
            response = self.client.get(url)
            response.raise_for_status()
            spec = response.json()
        except Exception as e:
            raise ValueError(f"Failed to fetch OpenAPI spec from {url}: {e}")
        
        return self._parse_openapi_spec(spec, url)
    
    def extract_from_file(self, file_path: Union[str, Path]) -> ExtractedSchema:
        """Extract schema from OpenAPI spec file."""
        file_path = Path(file_path)
        
        if file_path.suffix.lower() in ['.yaml', '.yml']:
            with open(file_path, 'r', encoding='utf-8') as f:
                spec = yaml.safe_load(f)
        elif file_path.suffix.lower() == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                spec = json.load(f)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")
        
        return self._parse_openapi_spec(spec, str(file_path))
    
    def _parse_openapi_spec(self, spec: Dict[str, Any], source: str) -> ExtractedSchema:
        """Parse OpenAPI specification and extract command schemas."""
        commands = []
        
        paths = spec.get('paths', {})
        info = spec.get('info', {})
        api_name = info.get('title', 'API')
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                    command = self._extract_operation_command(path, method, operation, api_name)
                    if command:
                        commands.append(command)
        
        return ExtractedSchema(
            source=source,
            commands=commands,
            metadata={
                "api_title": info.get('title'),
                "api_version": info.get('version'),
                "base_url": spec.get('servers', [{}])[0].get('url', ''),
            }
        )
    
    def _extract_operation_command(self, path: str, method: str, operation: Dict[str, Any], api_name: str) -> Optional[CommandSchema]:
        """Extract a single command from OpenAPI operation."""
        operation_id = operation.get('operationId') or f"{method}_{path.replace('/', '_').replace('{', '').replace('}', '')}"
        summary = operation.get('summary', '')
        description = operation.get('description', '') or summary
        
        parameters = []
        
        # Extract path parameters
        for param in operation.get('parameters', []):
            if param.get('in') == 'path':
                param_name = param['name']
                param_type = self._openapi_type_to_param_type(param.get('schema', {}))
                parameters.append(CommandParameter(
                    name=param_name,
                    type=param_type,
                    description=param.get('description', ''),
                    required=param.get('required', False),
                ))
        
        # Extract query parameters
        for param in operation.get('parameters', []):
            if param.get('in') == 'query':
                param_name = param['name']
                param_type = self._openapi_type_to_param_type(param.get('schema', {}))
                parameters.append(CommandParameter(
                    name=param_name,
                    type=param_type,
                    description=param.get('description', ''),
                    required=param.get('required', False),
                ))
        
        # Extract request body parameters
        request_body = operation.get('requestBody')
        if request_body:
            content = request_body.get('content', {})
            for media_type, media_obj in content.items():
                schema = media_obj.get('schema', {})
                if schema.get('type') == 'object':
                    for prop_name, prop_schema in schema.get('properties', {}).items():
                        param_type = self._openapi_type_to_param_type(prop_schema)
                        parameters.append(CommandParameter(
                            name=prop_name,
                            type=param_type,
                            description=prop_schema.get('description', ''),
                            required=prop_name in schema.get('required', []),
                        ))
        
        return CommandSchema(
            name=operation_id,
            description=description,
            parameters=parameters,
            category="api",
            source=f"{api_name} {method.upper()} {path}",
            metadata={
                "method": method.upper(),
                "path": path,
                "operation_id": operation.get('operationId'),
            }
        )
    
    def _openapi_type_to_param_type(self, schema: Dict[str, Any]) -> str:
        """Convert OpenAPI schema type to parameter type."""
        schema_type = schema.get('type', 'string')
        format_type = schema.get('format', '')
        
        if schema_type == 'string':
            if format_type in ['date', 'date-time']:
                return 'date'
            elif format_type == 'email':
                return 'email'
            elif format_type == 'uri':
                return 'url'
            return 'string'
        elif schema_type == 'integer':
            return 'integer'
        elif schema_type == 'number':
            return 'number'
        elif schema_type == 'boolean':
            return 'boolean'
        elif schema_type == 'array':
            return 'array'
        elif schema_type == 'object':
            return 'object'
        
        return 'string'


class ShellHelpExtractor:
    """Extract command schemas from shell help output."""
    
    def __init__(self):
        pass
    
    def extract_from_command(self, command: str) -> ExtractedSchema:
        try:
            # Try different help flags
            help_flags = ['--help', '-h', '-help', 'help']
            help_text = None
            
            for flag in help_flags:
                try:
                    result = subprocess.run(
                        [command, flag],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    if result.returncode == 0:
                        help_text = result.stdout
                        break
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    continue
            
            if not help_text:
                raise ValueError(f"Could not get help for command: {command}")
            
            return self._parse_help_output(help_text, command)
        except Exception as e:
            raise ValueError(f"Failed to extract help for {command}: {e}")
    
    def extract_from_multiple_commands(self, commands: List[str]) -> List[ExtractedSchema]:
        """Extract schemas from multiple commands."""
        schemas = []
        for command in commands:
            try:
                schema = self.extract_from_command(command)
                schemas.append(schema)
            except Exception:
                continue
        return schemas
    
    def _parse_help_output(self, help_text: str, command_name: str) -> ExtractedSchema:
        """Parse help output and extract command schema."""
        lines = help_text.split('\n')
        
        # Extract description (first non-empty lines)
        description = ""
        for line in lines:
            if line.strip() and not line.startswith('Usage:') and not line.startswith('Options:'):
                description = line.strip()
                break
        
        # Extract usage pattern
        usage_pattern = ""
        for line in lines:
            if line.startswith('Usage:') or line.startswith('usage:'):
                usage_pattern = line.split(':', 1)[1].strip()
                break
        
        # Extract options
        parameters = []
        in_options = False
        
        for line in lines:
            line = line.rstrip()
            if line.startswith('Options:') or line.startswith('options:'):
                in_options = True
                continue
            
            if in_options and line.strip() == '':
                continue
            
            if in_options and line and not line.startswith(' '):
                # End of options section
                break
            
            if in_options and line.startswith('  '):
                # Option line
                option_match = re.match(r'\s*(-\w|--\w+(?:-\w+)*)\s+(.*)', line)
                if option_match:
                    option = option_match.group(1)
                    desc = option_match.group(2)
                    param_name = _shell_opt_to_param_name(option)
                    
                    param_type = 'string'
                    if 'FILE' in desc.upper():
                        param_type = 'path'
                    elif 'DIR' in desc.upper():
                        param_type = 'path'
                    elif 'NUM' in desc.upper() or 'COUNT' in desc.upper():
                        param_type = 'integer'
                    elif 'BOOL' in desc.upper() or option.startswith('--no-'):
                        param_type = 'boolean'
                    
                    parameters.append(CommandParameter(
                        name=param_name,
                        type=param_type,
                        description=desc,
                        required=False,
                    ))
        
        return ExtractedSchema(
            source=command_name,
            commands=[CommandSchema(
                name=command_name,
                description=description,
                parameters=parameters,
                category="shell",
                source=command_name,
                metadata={
                    "usage_pattern": usage_pattern,
                }
            )],
            metadata={
                "help_text_length": len(help_text),
            }
        )
