"""
Dynamic schema extraction and analysis for NLP2CMD.

This module provides dynamic schema parsing capabilities for:
- OpenAPI/Swagger specifications
- Shell command help output
- Python source code with decorators
- Click applications
- And other command sources

Instead of hardcoded keywords, this module dynamically extracts
command patterns, parameters, and metadata from various sources.
"""

from __future__ import annotations

import ast
import inspect
import json
import re
import shlex
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None  # type: ignore
from nlp2cmd.utils.yaml_compat import yaml
try:
    from pydantic import BaseModel, Field
except ImportError:  # pragma: no cover
    BaseModel = object  # type: ignore

    def Field(*args: Any, **kwargs: Any):  # noqa: N802
        return None

# Import per-command storage
from ..storage.per_command_store import PerCommandSchemaStore


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


class OpenAPISchemaExtractor:
    """Extract command schemas from OpenAPI/Swagger specifications."""
    
    def __init__(self, http_client: Optional[httpx.Client] = None):
        if httpx is None and http_client is None:
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
                "total_paths": len(paths),
            }
        )
    
    def _extract_operation_command(self, path: str, method: str, operation: Dict[str, Any], api_name: str) -> Optional[CommandSchema]:
        """Extract a single command from OpenAPI operation."""
        operation_id = operation.get('operationId') or f"{method}_{path.replace('/', '_').replace('{', '').replace('}', '')}"
        summary = operation.get('summary', '')
        description = operation.get('description', summary)
        
        # Extract parameters
        parameters = []
        
        # Path parameters
        for param in operation.get('parameters', []):
            if param.get('in') == 'path':
                param_schema = param.get('schema', {})
                command_param = CommandParameter(
                    name=param['name'],
                    type=param_schema.get('type', 'string'),
                    description=param.get('description', ''),
                    required=param.get('required', False),
                    example=param.get('example'),
                    location='path',
                )
                parameters.append(command_param)
        
        # Query parameters
        for param in operation.get('parameters', []):
            if param.get('in') == 'query':
                param_schema = param.get('schema', {})
                command_param = CommandParameter(
                    name=param['name'],
                    type=param_schema.get('type', 'string'),
                    description=param.get('description', ''),
                    required=param.get('required', False),
                    default=param_schema.get('default'),
                    choices=param_schema.get('enum', []),
                    example=param.get('example'),
                    location='query',
                )
                parameters.append(command_param)
        
        # Request body parameters
        request_body = operation.get('requestBody')
        if request_body:
            content = request_body.get('content', {})
            for media_type, media_obj in content.items():
                schema = media_obj.get('schema', {})
                if schema.get('type') == 'object':
                    properties = schema.get('properties', {})
                    required_fields = schema.get('required', [])
                    
                    for prop_name, prop_schema in properties.items():
                        command_param = CommandParameter(
                            name=prop_name,
                            type=prop_schema.get('type', 'string'),
                            description=prop_schema.get('description', ''),
                            required=prop_name in required_fields,
                            default=prop_schema.get('default'),
                            choices=prop_schema.get('enum', []),
                            example=prop_schema.get('example'),
                            location='body',
                        )
                        parameters.append(command_param)
        
        # Generate patterns from operation
        patterns = [
            f"{method.lower()} {path}",
            f"{operation_id}",
        ]
        
        if summary:
            patterns.append(summary.lower())
        
        # Generate examples
        examples = []
        for example_key, example_obj in operation.get('examples', {}).items():
            if isinstance(example_obj, dict) and 'value' in example_obj:
                examples.append(str(example_obj['value']))
        
        return CommandSchema(
            name=operation_id,
            description=description,
            category=api_name,
            parameters=parameters,
            examples=examples,
            patterns=patterns,
            source_type="openapi",
            metadata={
                "method": method,
                "path": path,
                "tags": operation.get('tags', []),
            }
        )


class ShellHelpExtractor:
    """Extract command schemas from shell help output."""
    
    def __init__(self):
        self.common_commands = {
            'find', 'grep', 'sed', 'awk', 'ls', 'cd', 'mkdir', 'rm', 'cp', 'mv',
            'ps', 'top', 'htop', 'kill', 'killall', 'systemctl', 'service',
            'docker', 'kubectl', 'git', 'curl', 'wget', 'ping', 'netstat',
            'tar', 'zip', 'unzip', 'chmod', 'chown', 'ssh', 'scp', 'rsync'
        }
    
    def _generate_template_from_examples(self, command_name: str, examples: List[str]) -> Optional[str]:
        """Generate a template from example commands."""
        if not examples:
            return None
        
        # Predefined templates for common commands based on their typical usage
        common_templates = {
            'find': 'find {path} -type f -size {size} -mtime -{days}',
            'grep': 'grep -r {pattern} {path}',
            'ps': 'ps aux | head -{limit}',
            'df': 'df -h',
            'du': 'du -sh {path}',
            'tar': 'tar -czf {archive}.tar.gz {source}',
            'git': 'git {subcommand} {options}',
            'docker': 'docker {subcommand} {options}',
            'kubectl': 'kubectl {subcommand} {options}',
            'ls': 'ls -{flags} {path}',
            'mkdir': 'mkdir {path}',
            'rm': 'rm -{flags} {path}',
            'cp': 'cp -{flags} {source} {dest}',
            'mv': 'mv -{flags} {source} {dest}',
        }
        
        # Use predefined template if available
        if command_name in common_templates:
            return common_templates[command_name]
        
        # Try to generate from examples
        base_example = examples[0]
        
        # Replace specific values with placeholders
        template = base_example
        
        # Common replacements
        replacements = {
            # File paths
            r'\b[\w/.-]+\.(py|js|txt|log|json|yaml|yml)\b': '{file}',
            r'\b[\w/.-]+\b': '{path}',
            
            # Numbers
            r'\b\d+\b': '{number}',
            
            # Sizes
            r'\b\d+[KMGT]?B?\b': '{size}',
            
            # Dates
            r'\b\d{4}-\d{2}-\d{2}\b': '{date}',
            r'\b(last|recent|yesterday|today)\b': '{time}',
            
            # Common options
            r'--\w+(?:=\S+)?': '{option}',
            r'-\w': '{flag}',
            
            # Docker specifics
            r'\b[a-f0-9]{12,}\b': '{container_id}',
            r'\b\w+/\w+:\w+\b': '{image}',
            
            # Git specifics
            r'\b[a-f0-9]{7,}\b': '{commit}',
            r'\b[\w/-]+\b': '{branch}',
        }
        
        for pattern, replacement in replacements.items():
            template = re.sub(pattern, replacement, template)
        
        # If template is too generic (just placeholders), return None
        if template.count('{') > len(template.split()) / 2:
            return None
        
        return template
    
    def extract_from_command(self, command: str) -> ExtractedSchema:
        try:
            # Try different help flags
            help_flags = ['--help', '-h', '-help', 'help']
            help_output = None
            
            for flag in help_flags:
                try:
                    result = subprocess.run(
                        [command, flag],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode == 0:
                        help_output = result.stdout
                        break
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    continue
            
            if not help_output:
                # Try man page
                try:
                    result = subprocess.run(
                        ['man', command],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode == 0:
                        help_output = result.stdout
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    pass
            
            if not help_output:
                raise ValueError(f"Could not get help for command: {command}")
            
            return self._parse_help_output(help_output, command)
        
        except Exception as e:
            raise ValueError(f"Failed to extract help for {command}: {e}")
    
    def extract_from_multiple_commands(self, commands: List[str]) -> List[ExtractedSchema]:
        """Extract schemas from multiple commands."""
        schemas = []
        for command in commands:
            try:
                schema = self.extract_from_command(command)
                schemas.append(schema)
            except ValueError:
                # Skip commands that don't have help available
                continue
        return schemas
    
    def _parse_help_output(self, help_text: str, command_name: str) -> ExtractedSchema:
        """Parse help output and extract command schema."""
        lines = help_text.split('\n')
        
        # Extract description (first non-empty lines)
        description = ""
        description_lines = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('-') and not line.startswith('Usage:'):
                description_lines.append(line)
            elif description_lines:
                break
        
        description = ' '.join(description_lines[:3])  # First 3 lines as description
        
        # Extract usage patterns
        usage_patterns = []
        in_usage = False
        for line in lines:
            line = line.strip()
            if line.startswith('Usage:') or line.startswith('usage:'):
                in_usage = True
                usage_part = line.split(':', 1)[1].strip()
                usage_patterns.append(usage_part)
            elif in_usage and line:
                if line.startswith(' ') or line.startswith('\t'):
                    usage_patterns.append(line.strip())
                else:
                    in_usage = False
        
        # Extract options/parameters
        parameters = []
        current_param = None
        
        for line in lines:
            line = line.strip()
            
            # Match option patterns like -h, --help, -f FILE, --file=FILE
            option_match = re.match(r'^(-[a-zA-Z]|--[a-zA-Z0-9-]+)(?:\s+|=)(.+)?$', line)
            if option_match:
                option = option_match.group(1)
                rest = option_match.group(2) or ''
                
                # Extract parameter name and description
                param_name = option.lstrip('-').replace('-', '_')
                param_desc = rest
                
                # Check if it's a flag (boolean) or takes a value
                param_type = 'boolean'
                if '=' in rest or '<' in rest or '[' in rest:
                    param_type = 'string'
                    # Try to extract type from description
                    if 'file' in rest.lower():
                        param_type = 'file'
                    elif 'number' in rest.lower() or 'int' in rest.lower():
                        param_type = 'integer'
                
                parameters.append(CommandParameter(
                    name=param_name,
                    type=param_type,
                    description=param_desc,
                    required=False,  # Most options are optional
                    location="option",
                ))
        
        # Generate patterns from usage and description
        patterns = usage_patterns.copy()
        if description:
            patterns.append(description.lower())
        
        # Generate template from examples
        template = self._generate_template_from_examples(command_name, usage_patterns)
        
        return ExtractedSchema(
            source=command_name,
            source_type="shell_help",
            commands=[CommandSchema(
                name=command_name,
                description=description,
                category="shell",
                parameters=parameters,
                examples=usage_patterns,
                patterns=patterns,
                source_type="shell_help",
                metadata={
                    "command": command_name,
                    "help_lines": len(lines),
                },
                template=template,  # Add generated template
            )]
        )


class PythonCodeExtractor:
    """Extract command schemas from Python source code with decorators."""
    
    def extract_from_file(self, file_path: Union[str, Path]) -> ExtractedSchema:
        """Extract schemas from Python file."""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Python file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        return self.extract_from_source(source_code, str(file_path))
    
    def extract_from_source(self, source_code: str, source_name: str = "string") -> ExtractedSchema:
        """Extract schemas from Python source code string."""
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            raise ValueError(f"Invalid Python syntax in {source_name}: {e}")
        
        commands: list[CommandSchema] = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Check for Click decorators
                click_command = self._extract_click_command(node)
                if click_command:
                    commands.append(click_command)
                    continue

                # Check for Typer CLI commands
                typer_command = self._extract_typer_command(node, tree)
                if typer_command:
                    commands.append(typer_command)
                    continue
                
                # Check for other command decorators
                generic_command = self._extract_generic_command(node)
                if generic_command:
                    commands.append(generic_command)
                    continue

                plain_command = self._extract_plain_function(node)
                if plain_command:
                    commands.append(plain_command)

        # Detect argparse-based scripts (single-command CLI)
        argparse_command = self._extract_argparse_cli(tree, source_name)
        if argparse_command:
            commands.append(argparse_command)
        
        return ExtractedSchema(
            source=source_name,
            source_type="python_code",
            commands=commands,
            metadata={
                "functions_count": len([n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]),
                "classes_count": len([n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]),
            }
        )

    def _extract_typer_command(self, node: ast.AST, tree: ast.AST) -> Optional[CommandSchema]:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return None

        typer_apps: set[str] = set()
        for n in getattr(tree, "body", []) or []:
            if not isinstance(n, ast.Assign):
                continue
            if not n.targets:
                continue
            t0 = n.targets[0]
            if not isinstance(t0, ast.Name):
                continue
            if not isinstance(n.value, ast.Call):
                continue
            fn = n.value.func
            if isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name):
                if fn.value.id == "typer" and fn.attr == "Typer":
                    typer_apps.add(t0.id)
            elif isinstance(fn, ast.Name) and fn.id == "Typer":
                typer_apps.add(t0.id)

        if not typer_apps:
            return None

        decorator_call: Optional[ast.Call] = None
        for dec in node.decorator_list:
            if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                if isinstance(dec.func.value, ast.Name) and dec.func.value.id in typer_apps:
                    if dec.func.attr == "command":
                        decorator_call = dec
                        break

        if decorator_call is None:
            return None

        cmd_name = node.name
        for kw in decorator_call.keywords:
            if kw.arg == "name" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                cmd_name = kw.value.value

        description = ast.get_docstring(node) or ""
        parameters: list[CommandParameter] = []

        defaults = list(node.args.defaults or [])
        default_by_arg: dict[str, ast.AST] = {}
        if defaults:
            for a, d in zip(node.args.args[-len(defaults):], defaults):
                default_by_arg[a.arg] = d

        for a in node.args.args:
            if a.arg in {"self", "cls", "ctx"}:
                continue

            default_node = default_by_arg.get(a.arg)
            required = default_node is None
            param_type = _python_annotation_to_param_type(a.annotation)
            location = "option"
            default_val: Any = None

            if isinstance(default_node, ast.Call) and isinstance(default_node.func, ast.Attribute):
                if isinstance(default_node.func.value, ast.Name) and default_node.func.value.id == "typer":
                    if default_node.func.attr in {"Option", "Argument"}:
                        location = "argument" if default_node.func.attr == "Argument" else "option"
                        if default_node.args:
                            first = default_node.args[0]
                            if isinstance(first, ast.Constant) and first.value is Ellipsis:
                                required = True
                            else:
                                required = False
                                try:
                                    default_val = ast.literal_eval(first)
                                except Exception:
                                    default_val = _ast_unparse(first)
                        for kw in default_node.keywords:
                            if kw.arg == "default":
                                required = False
                                try:
                                    default_val = ast.literal_eval(kw.value)
                                except Exception:
                                    default_val = _ast_unparse(kw.value)

            parameters.append(
                CommandParameter(
                    name=a.arg,
                    type=param_type,
                    description="",
                    required=required,
                    default=default_val,
                    location=location,
                )
            )

        patterns = [cmd_name]
        if description:
            patterns.extend([word.lower() for word in description.split()[:3]])

        return CommandSchema(
            name=cmd_name,
            description=description,
            category="typer",
            parameters=_dedupe_params(parameters),
            examples=[f"{cmd_name} --help"],
            patterns=patterns,
            source_type="python_typer",
            metadata={"line_number": node.lineno},
        )

    def _extract_argparse_cli(self, tree: ast.AST, source_name: str) -> Optional[CommandSchema]:
        arg_calls: list[ast.Call] = []

        for n in ast.walk(tree):
            if not isinstance(n, ast.Call):
                continue
            if isinstance(n.func, ast.Attribute) and n.func.attr == "add_argument":
                arg_calls.append(n)

        if not arg_calls:
            return None

        params: list[CommandParameter] = []
        for call in arg_calls:
            opt_strings: list[str] = []
            for a in call.args:
                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                    opt_strings.append(a.value)

            dest: Optional[str] = None
            required = False
            default_val: Any = None
            choices: list[str] = []
            param_type = "string"
            action = None
            nargs = None

            for kw in call.keywords:
                if kw.arg == "dest" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                    dest = kw.value.value
                elif kw.arg == "required" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, bool):
                    required = kw.value.value
                elif kw.arg == "default":
                    try:
                        default_val = ast.literal_eval(kw.value)
                    except Exception:
                        default_val = _ast_unparse(kw.value)
                elif kw.arg == "choices":
                    if isinstance(kw.value, (ast.List, ast.Tuple)):
                        for elt in kw.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                choices.append(elt.value)
                elif kw.arg == "action" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                    action = kw.value.value
                elif kw.arg == "nargs":
                    nargs = _ast_unparse(kw.value)
                elif kw.arg == "type":
                    txt = _ast_unparse(kw.value).lower()
                    if "int" in txt:
                        param_type = "integer"
                    elif "float" in txt:
                        param_type = "number"

            if action in {"store_true", "store_false"}:
                param_type = "boolean"

            is_positional = not any(s.startswith("-") for s in opt_strings)
            location = "argument" if is_positional else "option"

            name = dest
            if not name:
                long_opts = [s for s in opt_strings if s.startswith("--")]
                if long_opts:
                    name = _shell_opt_to_param_name(long_opts[0])
                elif opt_strings:
                    name = _shell_opt_to_param_name(opt_strings[0])
                else:
                    continue

            if default_val is not None and not required:
                required = False
            if location == "argument" and default_val is None and not required:
                if nargs in {"?", "*"}:
                    required = False
                else:
                    required = True

            params.append(
                CommandParameter(
                    name=name,
                    type=param_type,
                    description="",
                    required=required,
                    default=default_val,
                    choices=choices,
                    location=location,
                )
            )

        cmd_name = Path(str(source_name)).stem
        patterns = [cmd_name, "argparse"]
        return CommandSchema(
            name=cmd_name,
            description="",
            category="argparse",
            parameters=_dedupe_params(params),
            examples=[f"python {Path(str(source_name)).name} --help"],
            patterns=patterns,
            source_type="python_argparse",
            metadata={},
        )
    
    def _extract_plain_function(self, node: ast.AST) -> Optional[CommandSchema]:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return None

        if node.name.startswith("_"):
            return None

        description = ast.get_docstring(node) or ""

        args = node.args
        parameters: list[CommandParameter] = []

        pos_args = list(args.args)
        defaults = list(args.defaults)
        default_by_arg: dict[str, Any] = {}
        if defaults:
            for a, d in zip(pos_args[-len(defaults):], defaults):
                try:
                    default_by_arg[a.arg] = ast.literal_eval(d)
                except Exception:
                    default_by_arg[a.arg] = _ast_unparse(d)

        for a in pos_args:
            if a.arg in {"self", "cls", "ctx"}:
                continue
            parameters.append(
                CommandParameter(
                    name=a.arg,
                    type=_python_annotation_to_param_type(a.annotation),
                    description="",
                    required=a.arg not in default_by_arg,
                    default=default_by_arg.get(a.arg),
                )
            )

        for a, d in zip(args.kwonlyargs, args.kw_defaults):
            if a.arg in {"self", "cls", "ctx"}:
                continue

            required = d is None
            default_val = None
            if d is not None:
                try:
                    default_val = ast.literal_eval(d)
                except Exception:
                    default_val = _ast_unparse(d)

            parameters.append(
                CommandParameter(
                    name=a.arg,
                    type=_python_annotation_to_param_type(a.annotation),
                    description="",
                    required=required,
                    default=default_val,
                )
            )

        if args.vararg:
            parameters.append(
                CommandParameter(
                    name=args.vararg.arg,
                    type="array",
                    description="",
                    required=False,
                )
            )

        if args.kwarg:
            parameters.append(
                CommandParameter(
                    name=args.kwarg.arg,
                    type="object",
                    description="",
                    required=False,
                )
            )

        patterns = [node.name]
        if description:
            patterns.extend([word.lower() for word in description.split()[:3]])

        return CommandSchema(
            name=node.name,
            description=description,
            category="python",
            parameters=_dedupe_params(parameters),
            examples=[],
            patterns=patterns,
            source_type="python_ast",
            metadata={
                "line_number": node.lineno,
            },
        )

    def _extract_click_command(self, node: ast.AST) -> Optional[CommandSchema]:
        """Extract Click command schema from function with Click decorators."""
        click_decorators = []

        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return None
        
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == 'command':
                click_decorators.append('command')
            elif isinstance(decorator, ast.Attribute):
                if (isinstance(decorator.value, ast.Name) and 
                    decorator.value.id == 'click' and 
                    decorator.attr in ['command', 'option', 'argument']):
                    click_decorators.append(decorator.attr)
        
        if not click_decorators:
            return None
        
        # Extract docstring
        description = ""
        if (node.body and isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, ast.Constant) and 
            isinstance(node.body[0].value.value, str)):
            description = node.body[0].value.value.strip()
        
        # Extract parameters from function arguments and Click decorators
        parameters = []
        
        # Extract from function signature
        args = node.args
        for arg in args.args:
            if arg.arg in ('ctx',):  # Skip Click context
                continue
            
            param_type = 'string'
            if arg.annotation:
                if isinstance(arg.annotation, ast.Name):
                    param_type = arg.annotation.id
                elif isinstance(arg.annotation, ast.Constant):
                    param_type = str(arg.annotation.value)
            
            parameters.append(CommandParameter(
                name=arg.arg,
                type=param_type,
                description=f"Parameter {arg.arg}",
                required=arg.arg not in (args.defaults or []),
            ))
        
        # Extract from Click option decorators
        for decorator in node.decorator_list:
            if (isinstance(decorator, ast.Call) and
                isinstance(decorator.func, ast.Attribute) and
                decorator.func.attr == 'option'):
                
                # Extract option name(s)
                option_names = []
                if isinstance(decorator.args[0], ast.Constant):
                    option_names = [decorator.args[0].value]
                elif isinstance(decorator.args[0], (ast.List, ast.Tuple)):
                    for elt in decorator.args[0].elts:
                        if isinstance(elt, ast.Constant):
                            option_names.append(elt.value)
                
                # Extract other properties
                param_name = option_names[0].lstrip('-').replace('-', '_') if option_names else "option"
                param_type = 'string'
                param_help = ""
                required = False
                
                for keyword in decorator.keywords:
                    if keyword.arg == 'type':
                        param_type = 'string'  # Could be enhanced to parse Click types
                    elif keyword.arg == 'help':
                        param_help = keyword.value.value if isinstance(keyword.value, ast.Constant) else ""
                    elif keyword.arg == 'required':
                        required = keyword.value.value if isinstance(keyword.value, ast.Constant) else False
                
                parameters.append(CommandParameter(
                    name=param_name,
                    type=param_type,
                    description=param_help,
                    required=required,
                ))
        
        # Generate patterns
        patterns = [node.name, f"run {node.name}"]
        if description:
            patterns.extend([word.lower() for word in description.split()[:3]])
        
        return CommandSchema(
            name=node.name,
            description=description,
            category="click",
            parameters=parameters,
            examples=[f"{node.name} --help"],
            patterns=patterns,
            source_type="python_click",
            metadata={
                "decorators": click_decorators,
                "line_number": node.lineno,
            }
        )
    
    def _extract_generic_command(self, node: ast.AST) -> Optional[CommandSchema]:
        """Extract generic command schema from function with command-like decorators."""
        command_decorators = []

        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return None
        
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                if decorator.id.lower() in ['command', 'cmd', 'task']:
                    command_decorators.append(decorator.id)
            elif isinstance(decorator, ast.Attribute):
                if decorator.attr.lower() in ['command', 'cmd', 'task']:
                    command_decorators.append(decorator.attr)
        
        if not command_decorators:
            return None
        
        # Extract docstring
        description = ""
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            description = node.body[0].value.value.strip()

        # Extract parameters from function signature
        parameters = []
        args = node.args

        for arg in args.args:
            param_type = 'string'
            if arg.annotation:
                if isinstance(arg.annotation, ast.Name):
                    param_type = arg.annotation.id
                elif isinstance(arg.annotation, ast.Constant):
                    param_type = str(arg.annotation.value)

            parameters.append(CommandParameter(
                name=arg.arg,
                type=param_type,
                description=f"Parameter {arg.arg}",
                required=arg.arg not in (args.defaults or []),
            ))

        # Generate patterns
        patterns = [node.name, f"execute {node.name}"]
        if description:
            patterns.extend([word.lower() for word in description.split()[:3]])

        return CommandSchema(
            name=node.name,
            description=description,
            category="python",
            parameters=parameters,
            examples=[f"python -c \"import {node.__module__}; {node.name}()\""],
            patterns=patterns,
            source_type="python_generic",
            metadata={
                "decorators": command_decorators,
                "line_number": node.lineno,
            }
        )


class ShellScriptExtractor:
    """Extract schema from a shell script file using shlex/regex heuristics."""

    _re_getopts = re.compile(r"\bgetopts\s+['\"]([^'\"]+)['\"]")
    _re_long_opt = re.compile(r"--[A-Za-z0-9][A-Za-z0-9_-]*")
    _re_long_opt_value = re.compile(
        r"(--[A-Za-z0-9][A-Za-z0-9_-]*)(?:=|\s+)(?P<value><[^>]+>|\[[^\]]+\]|[A-Za-z0-9_]+)"
    )
    _re_short_opt = re.compile(r"(?:^|\s)-(?P<flag>[A-Za-z0-9])\b")
    _re_usage = re.compile(r"\b(usage:|Usage:)\s*(.*)")

    def extract_from_file(self, file_path: Union[str, Path]) -> ExtractedSchema:
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Shell script not found: {file_path}")

        source_code = file_path.read_text(encoding="utf-8", errors="replace")
        return self.extract_from_source(source_code, str(file_path))

    def extract_from_source(self, source_code: str, source_name: str) -> ExtractedSchema:
        lines = source_code.splitlines()
        shebang = lines[0].strip() if lines and lines[0].startswith("#!") else ""

        description_lines: list[str] = []
        for line in lines[:30]:
            s = line.strip()
            if s.startswith("#"):
                txt = s.lstrip("#").strip()
                if txt:
                    description_lines.append(txt)
            elif s:
                break

        description = " ".join(description_lines[:3])

        usage_lines: list[str] = []
        for line in lines:
            m = self._re_usage.search(line)
            if m:
                usage_lines.append(m.group(2).strip())

        params: list[CommandParameter] = []

        # getopts: "ab:c" => -a, -b <val>, -c
        for m in self._re_getopts.finditer(source_code):
            spec = m.group(1)
            i = 0
            while i < len(spec):
                ch = spec[i]
                if ch in {":", "?"}:
                    i += 1
                    continue
                takes_value = i + 1 < len(spec) and spec[i + 1] == ":"
                params.append(
                    CommandParameter(
                        name=ch,
                        type="string" if takes_value else "boolean",
                        description="",
                        required=False,
                        location="option",
                    )
                )
                i += 2 if takes_value else 1

        long_opts_with_value: set[str] = set()
        for m in self._re_long_opt_value.finditer(source_code):
            long_opts_with_value.add(m.group(1))

        for opt in sorted(set(self._re_long_opt.findall(source_code))):
            params.append(
                CommandParameter(
                    name=_shell_opt_to_param_name(opt),
                    type="string" if opt in long_opts_with_value else "boolean",
                    description="",
                    required=False,
                    location="option",
                )
            )

        for m in self._re_short_opt.finditer(source_code):
            params.append(
                CommandParameter(
                    name=m.group("flag"),
                    type="boolean",
                    description="",
                    required=False,
                    location="option",
                )
            )

        # Heuristic: parse usage tokens for positional args
        for u in usage_lines[:3]:
            try:
                toks = shlex.split(u)
            except Exception:
                toks = u.split()

            for t in toks:
                if t.startswith("--") or t.startswith("-"):
                    continue
                cleaned = t.strip("[]<>")
                if cleaned and cleaned.isidentifier():
                    params.append(
                        CommandParameter(
                            name=cleaned,
                            type="string",
                            description="",
                            required=False,
                            location="argument",
                        )
                    )

        script_name = Path(source_name).stem
        command = CommandSchema(
            name=script_name,
            description=description,
            category="shell_script",
            parameters=_dedupe_params(params),
            examples=[f"./{Path(source_name).name}"],
            patterns=[script_name] + ([description.lower()] if description else []),
            source_type="shell_script",
            metadata={"shebang": shebang, "usages": usage_lines},
        )

        return ExtractedSchema(
            source=source_name,
            source_type="shell_script",
            commands=[command],
            metadata={"shebang": shebang},
        )


class MakefileExtractor:
    """Extract schema from Makefile targets and variables."""

    _re_var = re.compile(r"^(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*(?P<op>[:+?]?=)\s*(?P<value>.*)$")
    _re_target = re.compile(r"^(?P<target>[A-Za-z0-9][A-Za-z0-9_.\-/]*)\s*:(?P<deps>.*)$")
    _re_var_ref = re.compile(r"\$\((?P<name>[A-Za-z_][A-Za-z0-9_]*)\)")

    def extract_from_file(self, file_path: Union[str, Path]) -> ExtractedSchema:
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Makefile not found: {file_path}")

        parsed = self._try_parse_with_library(file_path)
        if parsed is not None:
            return parsed

        content = file_path.read_text(encoding="utf-8", errors="replace")
        return self._parse_fallback(content, str(file_path))

    def _try_parse_with_library(self, file_path: Path) -> Optional[ExtractedSchema]:
        # Optional dependency.
        try:
            import makefile_parser  # type: ignore
        except Exception:
            return None

        parser_cls = getattr(makefile_parser, "MakefileParser", None)
        if parser_cls is None:
            return None

        try:
            parser = parser_cls()
            data = parser.parse(str(file_path))
        except Exception:
            return None

        if not isinstance(data, dict):
            return None

        targets = data.get("targets") if isinstance(data.get("targets"), dict) else {}
        variables = data.get("variables") if isinstance(data.get("variables"), dict) else {}

        commands: list[CommandSchema] = []
        for tname, tinfo in targets.items():
            deps: list[str] = []
            if isinstance(tinfo, dict):
                deps = list(tinfo.get("deps", tinfo.get("prereqs", [])) or [])

            commands.append(
                CommandSchema(
                    name=str(tname),
                    description="",
                    category="make",
                    parameters=[],
                    examples=[f"make {tname}"],
                    patterns=[str(tname), f"make {tname}"],
                    source_type="makefile",
                    metadata={"deps": deps},
                )
            )

        return ExtractedSchema(
            source=str(file_path),
            source_type="makefile",
            commands=commands,
            metadata={"variables": list(variables.keys())},
        )

    def _parse_fallback(self, content: str, source: str) -> ExtractedSchema:
        lines = content.splitlines()
        variables: dict[str, str] = {}
        targets: dict[str, dict[str, Any]] = {}
        target_comments: dict[str, str] = {}

        last_comment: Optional[str] = None
        current_target: Optional[str] = None
        current_recipe: list[str] = []

        def flush_recipe() -> None:
            nonlocal current_target, current_recipe
            if current_target is not None:
                targets[current_target]["recipe"] = list(current_recipe)
            current_recipe = []
            current_target = None

        for raw in lines:
            line = raw.rstrip("\n")
            if not line.strip():
                last_comment = None
                continue
            if line.lstrip().startswith("#"):
                txt = line.lstrip()[1:].strip()
                if txt:
                    last_comment = txt
                continue

            # Recipe lines begin with a tab
            if line.startswith("\t") and current_target is not None:
                current_recipe.append(line.strip())
                continue

            mv = self._re_var.match(line)
            if mv:
                variables[mv.group("name")] = mv.group("value").strip()
                continue

            mt = self._re_target.match(line)
            if mt:
                flush_recipe()
                tname = mt.group("target").strip()
                deps = [d for d in mt.group("deps").strip().split() if d]
                targets[tname] = {"deps": deps, "recipe": []}
                if last_comment:
                    target_comments[tname] = last_comment
                current_target = tname
                last_comment = None
                continue

            flush_recipe()

        flush_recipe()

        commands: list[CommandSchema] = []
        for tname, tinfo in targets.items():
            used_vars: set[str] = set()
            for r in tinfo.get("recipe", []):
                for m in self._re_var_ref.finditer(r):
                    used_vars.add(m.group("name"))

            params = [
                CommandParameter(name=v, type="string", description="", required=False)
                for v in sorted(used_vars)
            ]

            commands.append(
                CommandSchema(
                    name=tname,
                    description=target_comments.get(tname, ""),
                    category="make",
                    parameters=params,
                    examples=[f"make {tname}"],
                    patterns=[tname, f"make {tname}"],
                    source_type="makefile",
                    metadata={"deps": tinfo.get("deps", [])},
                )
            )

        return ExtractedSchema(
            source=source,
            source_type="makefile",
            commands=commands,
            metadata={"variables": variables, "targets": list(targets.keys())},
        )


class DynamicSchemaRegistry:
    """Registry for managing dynamically extracted schemas."""
    
    def __init__(
        self,
        auto_save_path: Optional[Union[str, Path]] = None,
        use_llm: bool = False,
        llm_config: Optional[Dict] = None,
        use_per_command_storage: bool = True,
        storage_dir: Optional[str] = "./command_schemas",
    ):
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
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Dynamic export file not found: {file_path}")

        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception as e:
            raise ValueError(f"Failed to parse dynamic export from {file_path}: {e}")

        if not isinstance(payload, dict) or payload.get("format") != "nlp2cmd.dynamic_schema_export":
            raise ValueError(f"Invalid dynamic export format: {file_path}")

        sources = payload.get("sources")
        if not isinstance(sources, dict):
            raise ValueError(f"Invalid dynamic export sources: {file_path}")

        extracted_schemas: list[ExtractedSchema] = []

        for source_name, src in sources.items():
            if not isinstance(source_name, str) or not source_name:
                continue
            if not isinstance(src, dict):
                continue

            src_type = str(src.get("source_type") or "unknown")
            src_meta = src.get("metadata") if isinstance(src.get("metadata"), dict) else {}

            commands: list[CommandSchema] = []
            for c in src.get("commands", []) or []:
                if not isinstance(c, dict):
                    continue

                params: list[CommandParameter] = []
                for p in c.get("parameters", []) or []:
                    if not isinstance(p, dict):
                        continue
                    params.append(
                        CommandParameter(
                            name=str(p.get("name") or ""),
                            type=str(p.get("type") or "string"),
                            description=str(p.get("description") or ""),
                            required=bool(p.get("required", False)),
                            default=p.get("default"),
                            choices=list(p.get("choices", []) or []),
                            pattern=p.get("pattern"),
                            example=p.get("example"),
                            location=str(p.get("location") or "unknown"),
                        )
                    )

                metadata = c.get("metadata") if isinstance(c.get("metadata"), dict) else {}
                template = metadata.get("template") if isinstance(metadata.get("template"), str) else None

                commands.append(
                    CommandSchema(
                        name=str(c.get("name") or "unknown"),
                        description=str(c.get("description") or ""),
                        category=str(c.get("category") or "general"),
                        parameters=params,
                        examples=list(c.get("examples", []) or []),
                        patterns=list(c.get("patterns", []) or []),
                        source_type=str(c.get("source_type") or src_type),
                        metadata=dict(metadata),
                        template=template,
                    )
                )

            extracted = ExtractedSchema(
                source=source_name,
                source_type=src_type,
                commands=commands,
                metadata=dict(src_meta),
            )

            self.schemas[extracted.source] = extracted
            extracted_schemas.append(extracted)

        self._auto_save()
        return extracted_schemas
    
    def register_appspec_export(self, file_path: Union[str, Path]) -> ExtractedSchema:
        """Register an app2schema.appspec export file and convert to ExtractedSchema."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"AppSpec export file not found: {file_path}")

        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception as e:
            raise ValueError(f"Failed to parse AppSpec export from {file_path}: {e}")

        if not isinstance(payload, dict) or payload.get("format") != "app2schema.appspec":
            raise ValueError(f"Invalid AppSpec export format: {file_path}")

        commands: list[CommandSchema] = []
        for action in payload.get("actions", []):
            if not isinstance(action, dict):
                continue

            # Convert parameters
            params: list[CommandParameter] = []
            for name, pinfo in (action.get("params") or {}).items():
                if not isinstance(pinfo, dict):
                    continue
                params.append(
                    CommandParameter(
                        name=str(name),
                        type=str(pinfo.get("type") or "string"),
                        description=str(pinfo.get("description") or ""),
                        required=bool(pinfo.get("required", False)),
                        default=pinfo.get("default"),
                        choices=list(pinfo.get("choices", []) or []),
                        location="option",  # Assume options for appspec
                    )
                )

            # Extract patterns and examples from match section
            patterns = []
            examples = []
            if isinstance(action.get("match"), dict):
                patterns = list(action["match"].get("patterns", []))
                examples = list(action["match"].get("examples", []))

            # Determine source_type from metadata or default to shell_help
            source_type = "shell_help"
            metadata = action.get("metadata", {})
            if isinstance(metadata, dict):
                source_type = str(metadata.get("source_type") or "shell_help")

            commands.append(
                CommandSchema(
                    name=str(action.get("id", "").split(".")[-1] or "unknown"),
                    description=str(action.get("description") or ""),
                    category=str(action.get("type") or "general"),
                    parameters=params,
                    examples=examples,
                    patterns=patterns,
                    source_type=source_type,
                    metadata=dict(action.get("metadata", {}) or {}),
                    template=action.get("dsl", {}).get("template"),  # Add template from DSL
                )
            )

        # Use the app name as source, fallback to filename
        app_info = payload.get("app", {})
        source_name = str(app_info.get("name") or file_path.stem)

        extracted_schema = ExtractedSchema(
            source=source_name,
            source_type="appspec_export",
            commands=commands,
            metadata=dict(payload.get("metadata", {}) or {}),
        )
        self.schemas[extracted_schema.source] = extracted_schema
        self._auto_save()  # Auto-save after registration
        return extracted_schema
    
    def save_cache(self, cache_path: Union[str, Path]) -> None:
        """Save all schemas to cache file."""
        cache_path = Path(cache_path)
        cache_data = {
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "schemas": {}
        }
        
        for source, schema in self.schemas.items():
            cache_data["schemas"][source] = {
                "source_type": schema.source_type,
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
                                "location": p.location,
                            }
                            for p in cmd.parameters
                        ],
                        "examples": cmd.examples,
                        "patterns": cmd.patterns,
                        "source_type": cmd.source_type,
                        "metadata": cmd.metadata,
                        "template": cmd.template,  # Include template
                    }
                    for cmd in schema.commands
                ],
                "metadata": schema.metadata,
            }
        
        cache_path.write_text(json.dumps(cache_data, indent=2), encoding='utf-8')
    
    def load_cache(self, cache_path: Union[str, Path]) -> int:
        """Load schemas from cache file. Returns number of loaded schemas."""
        cache_path = Path(cache_path)
        if not cache_path.exists():
            return 0
        
        try:
            cache_data = json.loads(cache_path.read_text(encoding='utf-8'))
            loaded = 0
            
            for source, data in cache_data.get("schemas", {}).items():
                commands = []
                for cmd_data in data["commands"]:
                    parameters = [
                        CommandParameter(
                            name=p["name"],
                            type=p["type"],
                            description=p.get("description", ""),
                            required=p.get("required", False),
                            default=p.get("default"),
                            choices=p.get("choices", []),
                            pattern=p.get("pattern"),
                            location=p.get("location", "unknown"),
                        )
                        for p in cmd_data.get("parameters", [])
                    ]
                    
                    command = CommandSchema(
                        name=cmd_data["name"],
                        description=cmd_data.get("description", ""),
                        category=cmd_data.get("category", "general"),
                        parameters=parameters,
                        examples=cmd_data.get("examples", []),
                        patterns=cmd_data.get("patterns", []),
                        source_type=cmd_data.get("source_type", "unknown"),
                        metadata=cmd_data.get("metadata", {}),
                        template=cmd_data.get("template"),
                    )
                    commands.append(command)
                
                schema = ExtractedSchema(
                    source=source,
                    source_type=data["source_type"],
                    commands=commands,
                    metadata=data.get("metadata", {}),
                )
                self.schemas[source] = schema
                loaded += 1
            
            return loaded
        except Exception as e:
            print(f"Failed to load cache: {e}")
            return 0
    
    def get_all_commands(self) -> List[CommandSchema]:
        all_commands = []
        for schema in self.schemas.values():
            all_commands.extend(schema.commands)
        return all_commands
    
    def search_commands(self, query: str, limit: int = 10) -> List[CommandSchema]:
        """Search commands by name, description, patterns and token overlap."""

        def tokenize(text: str) -> set[str]:
            return {t for t in re.split(r"\W+", (text or "").lower()) if t}

        query_lower = (query or "").lower()
        q_tokens = tokenize(query)
        matches: list[tuple[CommandSchema, float]] = []

        for command in self.get_all_commands():
            score = 0.0

            name_l = (command.name or "").lower()
            desc_l = (command.description or "").lower()

            # Strong name matches - exact match gets highest score
            if query_lower == name_l:
                score += 100
            if name_l and name_l in query_lower:
                score += 50
            if query_lower and query_lower in name_l:
                score += 20

            # Token overlap with name (but penalize generic names like 'awk')
            name_tokens = tokenize(command.name)
            overlap = len(q_tokens & name_tokens)
            if command.name in {"awk", "sed", "cat", "ls"}:
                overlap *= 0.1  # Penalize generic tools
            score += min(overlap, 3) * 10

            # Description overlap
            desc_tokens = tokenize(command.description)
            desc_overlap = len(q_tokens & desc_tokens)
            score += min(desc_overlap, 6) * 2
            if query_lower and query_lower in desc_l:
                score += 10

            # Pattern match (both directions + token overlap)
            for pattern in command.patterns:
                p_l = (pattern or "").lower()
                if not p_l:
                    continue
                if p_l in query_lower:
                    score += 15
                    break
                if query_lower and query_lower in p_l:
                    score += 5
                    break
                p_tokens = tokenize(pattern)
                p_overlap = len(q_tokens & p_tokens)
                if p_overlap:
                    score += min(p_overlap, 3) * 3

            # Parameter name match
            for param in command.parameters:
                pnm = (param.name or "").lower()
                if not pnm:
                    continue
                if pnm in query_lower:
                    score += 2

            # Bonus for specific tools based on keywords
            if "docker" in query_lower and command.name == "docker":
                score += 30
            if "git" in query_lower and command.name == "git":
                score += 30
            if "kubectl" in query_lower and command.name == "kubectl":
                score += 30
            if "find" in query_lower and command.name == "find":
                score += 30
            if "grep" in query_lower and command.name == "grep":
                score += 30
            if ("todo" in query_lower or "comment" in query_lower) and command.name == "grep":
                score += 100  # Very strong bonus to beat 'find'
            if ("python" in query_lower or "count" in query_lower) and command.name == "grep":
                score += 60  # Bonus for grep with Python/count
            if "process" in query_lower and command.name == "ps":
                score += 60  # Increased from 40
            if ("memory" in query_lower or "cpu" in query_lower) and command.name == "ps":
                score += 50  # Bonus for ps with memory/cpu
            if "disk" in query_lower and command.name == "df":
                score += 40
            if "usage" in query_lower and command.name == "du":
                score += 40
            if ("compress" in query_lower or "archive" in query_lower or "zip" in query_lower) and command.name == "tar":
                score += 80  # Strong bonus for compression

            if score > 0:
                matches.append((command, score))

        matches.sort(key=lambda x: x[1], reverse=True)
        return [cmd for cmd, _ in matches[:limit]]
    
    def get_command_by_name(self, name: str) -> Optional[CommandSchema]:
        """Get command by exact name."""
        for command in self.get_all_commands():
            if command.name == name:
                return command
        return None
    
    def get_commands_by_category(self, category: str) -> List[CommandSchema]:
        """Get all commands in a category."""
        return [cmd for cmd in self.get_all_commands() if cmd.category == category]
    
    def export_schemas(self, format: str = "json") -> str:
        fmt = (format or "json").lower()

        if fmt in {"json_schema", "schema"}:
            return json.dumps(self._export_registry_json_schema(), indent=2, ensure_ascii=False)

        if fmt not in {"json", "dynamic", "dynamic_export"}:
            raise ValueError(f"Unsupported export format: {format}")

        sources: dict[str, Any] = {}
        for source, schema in self.schemas.items():
            sources[source] = {
                "source_type": schema.source_type,
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
                    }
                    for cmd in schema.commands
                ],
                "metadata": schema.metadata,
            }

        payload = {
            "format": "nlp2cmd.dynamic_schema_export",
            "version": 1,
            "detected_type": "mixed",
            "sources": sources,
            "metadata": {"exported_at": datetime.now().isoformat()},
        }
        return json.dumps(payload, indent=2, ensure_ascii=False)

    def _export_registry_json_schema(self) -> dict[str, Any]:
        commands = self.get_all_commands()
        command_defs: dict[str, Any] = {}

        type_map = {
            "string": "string",
            "path": "string",
            "file": "string",
            "integer": "integer",
            "number": "number",
            "boolean": "boolean",
            "array": "array",
            "object": "object",
        }

        for cmd in commands:
            props: dict[str, Any] = {}
            required: list[str] = []
            for p in cmd.parameters:
                props[p.name] = {
                    "type": type_map.get(p.type, "string"),
                    "description": p.description or "",
                }
                if p.default is not None:
                    props[p.name]["default"] = p.default
                if p.choices:
                    props[p.name]["enum"] = list(p.choices)
                if p.required:
                    required.append(p.name)

            command_defs[cmd.name] = {
                "type": "object",
                "description": cmd.description or "",
                "properties": props,
                "required": required,
                "additionalProperties": False,
            }

        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "NLP2CMD Dynamic Registry",
            "type": "object",
            "properties": {
                "intent": {"type": "string", "enum": sorted(list(command_defs.keys()))},
                "entities": {"type": "object"},
                "commands": {"type": "object", "additionalProperties": False, "properties": command_defs},
            },
            "required": ["intent"],
            "additionalProperties": True,
        }


# Import LLM extractor if available
try:
    from nlp2cmd.schema_extraction.llm_extractor import LLMSchemaExtractor
except ImportError:
    LLMSchemaExtractor = None
