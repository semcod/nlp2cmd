"""
Python code extractors for different frameworks.

Contains extractors for Click, Typer, argparse, and generic Python functions.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .extractors import CommandParameter, CommandSchema, ExtractedSchema, _ast_unparse, _python_annotation_to_param_type


class PythonCodeExtractor:
    """Extract command schemas from Python source code with decorators."""
    
    def extract_from_file(self, file_path: Union[str, Path]) -> ExtractedSchema:
        """Extract schemas from Python file."""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Python file not found: {file_path}")
        
        source_code = file_path.read_text(encoding="utf-8", errors="replace")
        
        return self.extract_from_source(source_code, str(file_path))
    
    def extract_from_source(self, source_code: str, source_name: str = "string") -> ExtractedSchema:
        """Extract schemas from Python source code string."""
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            raise ValueError(f"Invalid Python syntax in {source_name}: {e}")
        
        commands = []
        
        # Try different extraction strategies
        for node in ast.walk(tree):
            # Extract Typer commands
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                command = self._extract_typer_command(node, tree)
                if command:
                    commands.append(command)
                    continue
            
            # Extract argparse CLI
            if isinstance(node, ast.Call):
                if self._is_argparse_parser_call(node):
                    command = self._extract_argparse_cli(tree, source_name)
                    if command:
                        commands.append(command)
                        break
        
        # Fallback: extract plain functions
        if not commands:
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    command = self._extract_plain_function(node)
                    if command:
                        commands.append(command)
        
        return ExtractedSchema(
            source=source_name,
            commands=commands,
            metadata={
                "source_type": "python",
                "functions_found": len([n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]),
            }
        )
    
    def _extract_typer_command(self, node: ast.AST, tree: ast.AST) -> Optional[CommandSchema]:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return None

        # Check for Typer decorators
        typer_decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Attribute):
                if isinstance(decorator.value, ast.Name) and decorator.value.id == "typer":
                    typer_decorators.append(decorator.attr)
            elif isinstance(decorator, ast.Name):
                if decorator.id == "app":
                    typer_decorators.append("command")

        if not typer_decorators:
            return None

        # Extract parameters
        parameters = []
        for arg in node.args.args:
            if arg.arg == "self":
                continue

            param_type = "string"
            if arg.annotation:
                param_type = _python_annotation_to_param_type(arg.annotation)

            default_value = None
            required = True
            if node.args.defaults:
                # Match defaults to args (right-aligned)
                default_offset = len(node.args.args) - len(node.args.defaults)
                arg_index = node.args.args.index(arg)
                if arg_index >= default_offset:
                    default_index = arg_index - default_offset
                    default_node = node.args.defaults[default_index]
                    default_value = ast.literal_eval(default_node)
                    required = False

            description = f"Parameter {arg.arg}"
            if arg.arg in ["help", "verbose", "quiet"]:
                description = f"Flag {arg.arg}"
                param_type = "boolean"
                default_value = False

            parameters.append(CommandParameter(
                name=arg.arg,
                type=param_type,
                description=description,
                required=required,
                default=default_value,
            ))

        # Extract docstring
        description = ""
        if (node.body and isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, ast.Constant) and 
            isinstance(node.body[0].value.value, str)):
            description = node.body[0].value.value.split('\n')[0].strip()

        return CommandSchema(
            name=node.name,
            description=description,
            parameters=parameters,
            category="python",
            source=f"typer.{node.name}",
            metadata={"line_number": node.lineno},
        )

    def _is_argparse_parser_call(self, node: ast.Call) -> bool:
        """Check if node is an ArgumentParser creation call."""
        if isinstance(node.func, ast.Attribute):
            if (isinstance(node.func.value, ast.Name) and 
                node.func.value.id == "argparse" and 
                node.func.attr == "ArgumentParser"):
                return True
        return False

    def _extract_argparse_cli(self, tree: ast.AST, source_name: str) -> Optional[CommandSchema]:
        arg_calls: list[ast.Call] = []

        for n in ast.walk(tree):
            if isinstance(n, ast.Call):
                if isinstance(n.func, ast.Attribute):
                    if (isinstance(n.func.value, ast.Name) and 
                        n.func.value.id == "parser" and 
                        n.func.attr in ["add_argument", "add_parser"]):
                        arg_calls.append(n)

        if not arg_calls:
            return None

        parameters = []
        for call in arg_calls:
            if call.func.attr != "add_argument":
                continue

            # Extract argument name
            args = []
            for arg in call.args:
                if isinstance(arg, ast.Constant):
                    args.append(arg.value)
                elif isinstance(arg, ast.Str):
                    args.append(arg.s)

            if not args:
                continue

            param_name = args[0].lstrip("-").replace("-", "_")
            description = ""
            param_type = "string"
            required = not args[0].startswith("-")
            default_value = None

            # Extract kwargs
            for keyword in call.keywords:
                if keyword.arg == "help":
                    if isinstance(keyword.value, ast.Constant):
                        description = keyword.value.value
                    elif isinstance(keyword.value, ast.Str):
                        description = keyword.value.s
                elif keyword.arg == "type":
                    if isinstance(keyword.value, ast.Name):
                        type_name = keyword.value.id
                        if type_name == "int":
                            param_type = "integer"
                        elif type_name == "float":
                            param_type = "number"
                        elif type_name == "bool":
                            param_type = "boolean"
                elif keyword.arg == "default":
                    if isinstance(keyword.value, ast.Constant):
                        default_value = keyword.value.value
                    elif isinstance(keyword.value, ast.Str):
                        default_value = keyword.value.s
                    elif isinstance(keyword.value, ast.Num):
                        default_value = keyword.value.n
                    elif isinstance(keyword.value, ast.NameConstant):
                        default_value = keyword.value.value

            parameters.append(CommandParameter(
                name=param_name,
                type=param_type,
                description=description,
                required=required,
                default=default_value,
            ))

        return CommandSchema(
            name="cli",
            description="Command line interface",
            parameters=parameters,
            category="python",
            source=source_name,
            metadata={"framework": "argparse"},
        )

    def _extract_plain_function(self, node: ast.AST) -> Optional[CommandSchema]:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return None

        # Skip private/internal functions
        if node.name.startswith("_"):
            return None

        # Extract parameters
        parameters = []
        for arg in node.args.args:
            if arg.arg == "self":
                continue

            param_type = "string"
            if arg.annotation:
                param_type = _python_annotation_to_param_type(arg.annotation)

            default_value = None
            required = True
            if node.args.defaults:
                default_offset = len(node.args.args) - len(node.args.defaults)
                arg_index = node.args.args.index(arg)
                if arg_index >= default_offset:
                    default_index = arg_index - default_offset
                    default_node = node.args.defaults[default_index]
                    try:
                        default_value = ast.literal_eval(default_node)
                        required = False
                    except Exception:
                        pass

            description = f"Parameter {arg.arg}"
            parameters.append(CommandParameter(
                name=arg.arg,
                type=param_type,
                description=description,
                required=required,
                default=default_value,
            ))

        # Extract docstring
        description = ""
        if (node.body and isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, ast.Constant) and 
            isinstance(node.body[0].value.value, str)):
            description = node.body[0].value.value.split('\n')[0].strip()

        return CommandSchema(
            name=node.name,
            description=description,
            parameters=parameters,
            category="python",
            source=f"function.{node.name}",
            metadata={"line_number": node.lineno},
        )


class ClickExtractor:
    """Extract Click command schemas."""
    
    def extract_from_source(self, source_code: str, source_name: str = "string") -> ExtractedSchema:
        """Extract Click commands from Python source."""
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            raise ValueError(f"Invalid Python syntax: {e}")
        
        commands = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                command = self._extract_click_command(node)
                if command:
                    commands.append(command)
        
        return ExtractedSchema(
            source=source_name,
            commands=commands,
            metadata={"framework": "click"},
        )
    
    def _extract_click_command(self, node: ast.AST) -> Optional[CommandSchema]:
        """Extract Click command schema from function with Click decorators."""
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return None

        click_decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Attribute):
                if (isinstance(decorator.value, ast.Name) and 
                    decorator.value.id == "click" and 
                    decorator.attr in ["command", "option", "argument"]):
                    click_decorators.append(decorator.attr)

        if not click_decorators:
            return None

        # Extract parameters from function signature
        parameters = []
        for arg in node.args.args:
            if arg.arg == "self":
                continue

            param_type = "string"
            if arg.annotation:
                param_type = _python_annotation_to_param_type(arg.annotation)

            default_value = None
            required = True
            if node.args.defaults:
                default_offset = len(node.args.args) - len(node.args.defaults)
                arg_index = node.args.args.index(arg)
                if arg_index >= default_offset:
                    default_index = arg_index - default_offset
                    default_node = node.args.defaults[default_index]
                    try:
                        default_value = ast.literal_eval(default_node)
                        required = False
                    except Exception:
                        pass

            description = f"Parameter {arg.arg}"
            parameters.append(CommandParameter(
                name=arg.arg,
                type=param_type,
                description=description,
                required=required,
                default=default_value,
            ))

        # Extract docstring
        description = ""
        if (node.body and isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, ast.Constant) and 
            isinstance(node.body[0].value.value, str)):
            description = node.body[0].value.value.split('\n')[0].strip()

        return CommandSchema(
            name=node.name,
            description=description,
            parameters=parameters,
            category="python",
            source=f"click.{node.name}",
            metadata={
                "framework": "click",
                "line_number": node.lineno,
            }
        )
