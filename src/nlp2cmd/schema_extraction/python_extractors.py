"""Python code extractors for dynamic schema extraction."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .extractors import CommandParameter, CommandSchema, ExtractedSchema


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
        # Extract name from decorator if provided
        for keyword in decorator_call.keywords:
            if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
                cmd_name = str(keyword.value.value)
                break

        docstring = ast.get_docstring(node)
        description = docstring or f"Typer command: {cmd_name}"

        parameters = []
        for arg in node.args.args:
            arg_name = arg.arg
            if arg_name in ("self", "cls"):
                continue

            param_type = "string"
            if arg.annotation:
                param_type = _python_annotation_to_param_type(arg.annotation)

            required = arg_name not in [a.arg for a in node.args.defaults]
            
            parameters.append(CommandParameter(
                name=arg_name,
                type=param_type,
                description=f"Parameter {arg_name}",
                required=required,
                location="argument"
            ))

        return CommandSchema(
            name=cmd_name,
            description=description,
            category="python",
            parameters=parameters,
            examples=[f"python script.py {cmd_name}"],
            patterns=[cmd_name],
            source_type="typer",
            metadata={"function_name": node.name}
        )
    
    def _extract_click_command(self, node: ast.AST) -> Optional[CommandSchema]:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return None

        # Check for @click.command or @click.option decorators
        has_click_decorator = False
        for dec in node.decorator_list:
            if isinstance(dec, ast.Attribute):
                if isinstance(dec.value, ast.Name) and dec.value.id == "click":
                    has_click_decorator = True
                    break
            elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                if isinstance(dec.func.value, ast.Name) and dec.func.value.id == "click":
                    has_click_decorator = True
                    break

        if not has_click_decorator:
            return None

        cmd_name = node.name
        docstring = ast.get_docstring(node)
        description = docstring or f"Click command: {cmd_name}"

        parameters = []
        for arg in node.args.args:
            arg_name = arg.arg
            if arg_name in ("self", "cls"):
                continue

            param_type = "string"
            if arg.annotation:
                param_type = _python_annotation_to_param_type(arg.annotation)

            required = arg_name not in [a.arg for a in node.args.defaults]
            
            parameters.append(CommandParameter(
                name=arg_name,
                type=param_type,
                description=f"Parameter {arg_name}",
                required=required,
                location="argument"
            ))

        return CommandSchema(
            name=cmd_name,
            description=description,
            category="python",
            parameters=parameters,
            examples=[f"python script.py {cmd_name}"],
            patterns=[cmd_name],
            source_type="click",
            metadata={"function_name": node.name}
        )
    
    def _extract_generic_command(self, node: ast.AST) -> Optional[CommandSchema]:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return None

        # Check for generic command decorators
        command_decorators = ["command", "cli_command", "cmd"]
        has_command_decorator = False
        
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name) and dec.id in command_decorators:
                has_command_decorator = True
                break
            elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name):
                if dec.func.id in command_decorators:
                    has_command_decorator = True
                    break

        if not has_command_decorator:
            return None

        cmd_name = node.name
        docstring = ast.get_docstring(node)
        description = docstring or f"Command: {cmd_name}"

        parameters = []
        for arg in node.args.args:
            arg_name = arg.arg
            if arg_name in ("self", "cls"):
                continue

            param_type = "string"
            if arg.annotation:
                param_type = _python_annotation_to_param_type(arg.annotation)

            required = arg_name not in [a.arg for a in node.args.defaults]
            
            parameters.append(CommandParameter(
                name=arg_name,
                type=param_type,
                description=f"Parameter {arg_name}",
                required=required,
                location="argument"
            ))

        return CommandSchema(
            name=cmd_name,
            description=description,
            category="python",
            parameters=parameters,
            examples=[f"python script.py {cmd_name}"],
            patterns=[cmd_name],
            source_type="generic",
            metadata={"function_name": node.name}
        )
    
    def _extract_plain_function(self, node: ast.AST) -> Optional[CommandSchema]:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return None

        # Only extract functions that look like they could be commands
        # (public functions with simple names)
        if node.name.startswith("_"):
            return None
        
        # Skip functions that are clearly not commands
        if node.name in ["main", "run", "setup", "init"]:
            return None

        cmd_name = node.name
        docstring = ast.get_docstring(node)
        
        # Skip functions without docstrings that describe what they do
        if not docstring:
            return None

        description = docstring.split('\n')[0].strip()

        parameters = []
        for arg in node.args.args:
            arg_name = arg.arg
            if arg_name in ("self", "cls"):
                continue

            param_type = "string"
            if arg.annotation:
                param_type = _python_annotation_to_param_type(arg.annotation)

            required = arg_name not in [a.arg for a in node.args.defaults]
            
            parameters.append(CommandParameter(
                name=arg_name,
                type=param_type,
                description=f"Parameter {arg_name}",
                required=required,
                location="argument"
            ))

        return CommandSchema(
            name=cmd_name,
            description=description,
            category="python",
            parameters=parameters,
            examples=[f"python script.py {cmd_name}"],
            patterns=[cmd_name],
            source_type="function",
            metadata={"function_name": node.name}
        )
    
    def _extract_argparse_cli(self, tree: ast.AST, source_name: str) -> Optional[CommandSchema]:
        """Extract argparse-based CLI commands."""
        has_argparse = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "argparse":
                        has_argparse = True
                        break
            elif isinstance(node, ast.ImportFrom):
                if node.module == "argparse":
                    has_argparse = True
                    break
        
        if not has_argparse:
            return None

        # Look for ArgumentParser usage
        parser_name = None
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if isinstance(node.value, ast.Call):
                            func = node.value.func
                            if isinstance(func, ast.Name) and func.id == "ArgumentParser":
                                parser_name = target.id
                                break
                            elif isinstance(func, ast.Attribute) and func.attr == "ArgumentParser":
                                parser_name = target.id
                                break
            if parser_name:
                break

        if not parser_name:
            return None

        cmd_name = Path(source_name).stem if source_name != "string" else "cli"
        description = f"Argparse CLI: {cmd_name}"

        return CommandSchema(
            name=cmd_name,
            description=description,
            category="python",
            parameters=[],
            examples=[f"python {cmd_name}.py"],
            patterns=[cmd_name],
            source_type="argparse",
            metadata={"parser_name": parser_name}
        )


class ClickExtractor:
    """Specialized extractor for Click applications."""
    
    def __init__(self):
        self.python_extractor = PythonCodeExtractor()
    
    def extract_from_file(self, file_path: Union[str, Path]) -> ExtractedSchema:
        """Extract Click schemas from Python file."""
        schema = self.python_extractor.extract_from_file(file_path)
        
        # Filter only Click commands
        click_commands = [
            cmd for cmd in schema.commands 
            if cmd.source_type == "click"
        ]
        
        return ExtractedSchema(
            source=schema.source,
            source_type="click",
            commands=click_commands,
            metadata={**schema.metadata, "extractor": "click"}
        )
