"""Base extractor classes for dynamic schema extraction."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None  # type: ignore

from nlp2cmd.utils.yaml_compat import yaml


@dataclass
class CommandParameter:
    """Represents a command parameter extracted from schema."""
    
    name: str
    type: str
    description: str = ""
    required: bool = False
    default: Any = None
    choices: List[str] = field(default_factory=list)
    pattern: Optional[str] = None
    example: Optional[str] = None
    location: str = "unknown"


@dataclass
class CommandSchema:
    """Dynamic command schema extracted from various sources."""
    
    name: str
    description: str
    category: str = "general"
    parameters: List[CommandParameter] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)
    source_type: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)
    template: Optional[str] = None  # Template string for command generation


@dataclass
class ExtractedSchema:
    """Container for extracted schemas from a source."""
    
    source: str
    source_type: str
    commands: List[CommandSchema] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "source": self.source,
            "source_type": self.source_type,
            "commands": [
                {
                    "name": cmd.name,
                    "description": cmd.description,
                    "category": cmd.category,
                    "parameters": [
                        {
                            "name": p.name,
                            "type": p.type,
                            "description": p.description,
                            "required": p.required,
                            "default": p.default,
                            "choices": p.choices,
                            "pattern": p.pattern,
                            "example": p.example,
                            "location": p.location,
                        }
                        for p in cmd.parameters
                    ],
                    "examples": cmd.examples,
                    "patterns": cmd.patterns,
                    "source_type": cmd.source_type,
                    "metadata": cmd.metadata,
                    "template": cmd.template,
                }
                for cmd in self.commands
            ],
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExtractedSchema":
        """Create from dictionary."""
        commands = []
        for cmd_data in data.get("commands", []):
            parameters = []
            for p_data in cmd_data.get("parameters", []):
                param = CommandParameter(
                    name=p_data["name"],
                    type=p_data["type"],
                    description=p_data.get("description", ""),
                    required=p_data.get("required", False),
                    default=p_data.get("default"),
                    choices=p_data.get("choices", []),
                    pattern=p_data.get("pattern"),
                    example=p_data.get("example"),
                    location=p_data.get("location", "unknown"),
                )
                parameters.append(param)
            
            command = CommandSchema(
                name=cmd_data["name"],
                description=cmd_data["description"],
                category=cmd_data.get("category", "general"),
                parameters=parameters,
                examples=cmd_data.get("examples", []),
                patterns=cmd_data.get("patterns", []),
                source_type=cmd_data.get("source_type", "unknown"),
                metadata=cmd_data.get("metadata", {}),
                template=cmd_data.get("template"),
            )
            commands.append(command)
        
        return cls(
            source=data["source"],
            source_type=data["source_type"],
            commands=commands,
            metadata=data.get("metadata", {}),
        )


class OpenAPISchemaExtractor:
    """Extract command schemas from OpenAPI/Swagger specifications."""
    
    def __init__(self, http_client: Optional[httpx.Client] = None):
        if httpx is None and httpx is None:
            raise ImportError("httpx is required for OpenAPI schema extraction")
        self.client = http_client or httpx.Client()
    
    def extract_from_url(self, url: str) -> ExtractedSchema:
        """Extract schema from OpenAPI spec URL."""
        try:
            response = self.client.get(url)
            response.raise_for_status()
            
            if url.endswith('.yaml') or url.endswith('.yml'):
                spec = yaml.safe_load(response.text)
            else:
                spec = response.json()
            
            return self._parse_openapi_spec(spec, url)
        except Exception as e:
            raise ValueError(f"Failed to fetch OpenAPI spec from {url}: {e}")
    
    def extract_from_file(self, file_path: Union[str, Path]) -> ExtractedSchema:
        """Extract schema from OpenAPI spec file."""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"OpenAPI spec file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix in ['.yaml', '.yml']:
                    spec = yaml.safe_load(f)
                else:
                    spec = json.load(f)
            
            return self._parse_openapi_spec(spec, str(file_path))
        except Exception as e:
            raise ValueError(f"Failed to parse OpenAPI spec from {file_path}: {e}")
    
    def _parse_openapi_spec(self, spec: Dict[str, Any], source: str) -> ExtractedSchema:
        """Parse OpenAPI specification and extract command schemas."""
        commands = []
        
        # Extract basic info
        info = spec.get('info', {})
        title = info.get('title', 'API')
        version = info.get('version', '1.0.0')

        base_url = ""
        servers = spec.get('servers')
        if isinstance(servers, list) and servers:
            first_server = servers[0]
            if isinstance(first_server, dict):
                base_url = str(first_server.get('url', '') or '')
        
        # Extract paths as commands
        paths = spec.get('paths', {})
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.lower() not in ['get', 'post', 'put', 'delete', 'patch']:
                    continue
                
                command = self._extract_operation_command(
                    path, method, operation, f"{title} v{version}"
                )
                if command:
                    command.metadata["base_url"] = base_url
                    commands.append(command)
        
        return ExtractedSchema(
            source=source,
            source_type="openapi",
            commands=commands,
            metadata={
                "title": title,
                "version": version,
                "base_url": base_url,
            }
        )
    
    def _extract_operation_command(self, path: str, method: str, operation: Dict[str, Any], api_name: str) -> Optional[CommandSchema]:
        """Extract command schema from OpenAPI operation."""
        operation_id = operation.get('operationId', f"{method}_{path.replace('/', '_').replace('{', '').replace('}', '')}")
        summary = operation.get('summary', '')
        description = operation.get('description', summary)
        
        if not description:
            description = f"{method.upper()} {path}"
        
        parameters = []
        
        # Extract path parameters
        for param in operation.get('parameters', []):
            if param.get('in') == 'path':
                parameters.append(CommandParameter(
                    name=param['name'],
                    type=param.get('schema', {}).get('type', 'string'),
                    description=param.get('description', ''),
                    required=param.get('required', False),
                    location='path'
                ))
        
        # Extract query parameters
        for param in operation.get('parameters', []):
            if param.get('in') == 'query':
                parameters.append(CommandParameter(
                    name=param['name'],
                    type=param.get('schema', {}).get('type', 'string'),
                    description=param.get('description', ''),
                    required=param.get('required', False),
                    location='query'
                ))
        
        # Extract request body parameters
        request_body = operation.get('requestBody')
        if request_body:
            content = request_body.get('content', {})
            for media_type, media_obj in content.items():
                schema = media_obj.get('schema', {})
                if schema.get('type') == 'object':
                    properties = schema.get('properties', {})
                    for prop_name, prop_schema in properties.items():
                        parameters.append(CommandParameter(
                            name=prop_name,
                            type=prop_schema.get('type', 'string'),
                            description=prop_schema.get('description', ''),
                            required=prop_name in schema.get('required', []),
                            location='body'
                        ))
        
        return CommandSchema(
            name=operation_id,
            description=description,
            category="api",
            parameters=parameters,
            examples=[f"{method.upper()} {path}"],
            patterns=[f"{method.lower()} {path}"],
            source_type="openapi",
            metadata={
                "method": method,
                "path": path,
                "api_name": api_name,
            }
        )


class ShellHelpExtractor:
    """Extract command schemas from shell help output."""
    
    def __init__(self):
        pass
    
    def extract_from_command(self, command: str) -> ExtractedSchema:
        """Extract schema from shell command help."""
        try:
            # Try different help flags
            help_flags = ['--help', '-h', '--usage', '-?']
            help_output = None
            
            for flag in help_flags:
                try:
                    result = subprocess.run(
                        f"{command} {flag}",
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode == 0:
                        help_output = result.stdout
                        break
                except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                    continue
            
            if not help_output:
                # Fallback to basic command info
                help_output = f"Command: {command}\nNo help available."
            
            return self._parse_help_output(command, help_output)
        except Exception as e:
            # Return minimal schema on error
            return ExtractedSchema(
                source=command,
                source_type="shell",
                commands=[
                    CommandSchema(
                        name=command,
                        description=f"Shell command: {command}",
                        category="shell",
                        source_type="shell"
                    )
                ],
                metadata={"error": str(e)}
            )
    
    def _parse_help_output(self, command: str, help_output: str) -> ExtractedSchema:
        """Parse shell help output to extract command schema."""
        lines = help_output.split('\n')
        
        # Extract description (first non-empty line that looks like a description)
        description = f"Shell command: {command}"
        for line in lines:
            line = line.strip()
            if line and not line.startswith('-') and not line.startswith('Usage:'):
                description = line
                break
        
        # Extract options using regex
        option_pattern = re.compile(r'^\s*(-{1,2}[\w-]+)(?:\s*<([^>]+)>)?(?:\s*=\s*([^\s]+))?\s*(.*)$')
        parameters = []
        
        for line in lines:
            match = option_pattern.match(line)
            if match:
                option = match.group(1)
                arg_type = match.group(2) or "string"
                default_value = match.group(3)
                param_desc = match.group(4).strip()
                
                param_name = option.lstrip('-').replace('-', '_')
                
                # Determine parameter type
                param_type = "string"
                if arg_type:
                    if arg_type.lower() in ['int', 'integer', 'num']:
                        param_type = "integer"
                    elif arg_type.lower() in ['float', 'double']:
                        param_type = "number"
                    elif arg_type.lower() in ['bool', 'boolean', 'flag']:
                        param_type = "boolean"
                    elif 'file' in arg_type.lower() or 'path' in arg_type.lower():
                        param_type = "path"
                
                parameters.append(CommandParameter(
                    name=param_name,
                    type=param_type,
                    description=param_desc,
                    default=default_value,
                    location="option"
                ))
        
        # Extract usage examples
        examples = []
        usage_pattern = re.compile(r'Usage:\s*(.+)$', re.IGNORECASE)
        for line in lines:
            match = usage_pattern.match(line)
            if match:
                examples.append(match.group(1).strip())
        
        return ExtractedSchema(
            source=command,
            source_type="shell",
            commands=[
                CommandSchema(
                    name=command,
                    description=description,
                    category="shell",
                    parameters=parameters,
                    examples=examples,
                    patterns=[command],
                    source_type="shell"
                )
            ]
        )
