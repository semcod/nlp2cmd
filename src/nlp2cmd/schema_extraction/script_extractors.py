"""
Script extractors for shell scripts and Makefiles.

Contains extractors for shell scripts and Makefile targets.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .extractors import CommandParameter, CommandSchema, ExtractedSchema


class ShellScriptExtractor:
    """Extract schema from a shell script file using shlex/regex heuristics."""

    _re_getopts = re.compile(r"\bgetopts\s+['\"]([^'\"]+)['\"]")
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

        # Extract functions
        functions = self._extract_functions(lines)
        
        # Extract getopts options
        getopts_match = self._re_getopts.search(source_code)
        getopts_options = getopts_match.group(1) if getopts_match else ""

        # Extract usage pattern
        usage_match = self._re_usage.search(source_code)
        usage_pattern = usage_match.group(2) if usage_match else ""

        # Parse options
        parameters = []
        if getopts_options:
            parameters = self._parse_getopts_options(getopts_options)

        # Create command schema for the script itself
        script_name = Path(source_name).stem
        commands = []

        if functions:
            for func_name, func_lines in functions.items():
                func_schema = self._create_function_schema(func_name, func_lines, source_name)
                if func_schema:
                    commands.append(func_schema)
        else:
            # Single script command
            commands.append(CommandSchema(
                name=script_name,
                description=f"Shell script: {script_name}",
                parameters=parameters,
                category="shell",
                source=source_name,
                metadata={
                    "shebang": shebang,
                    "usage_pattern": usage_pattern,
                    "getopts_options": getopts_options,
                }
            ))

        return ExtractedSchema(
            source=source_name,
            commands=commands,
            metadata={
                "script_type": "shell",
                "shebang": shebang,
                "functions_count": len(functions),
            }
        )

    def _extract_functions(self, lines: List[str]) -> Dict[str, List[str]]:
        """Extract function definitions from shell script."""
        functions = {}
        current_func = None
        current_lines = []

        func_pattern = re.compile(r'^(\w+)\s*\(\s*\)\s*\{?$')

        for line in lines:
            line = line.strip()
            
            # Check for function definition
            match = func_pattern.match(line)
            if match:
                # Save previous function if exists
                if current_func:
                    functions[current_func] = current_lines
                
                # Start new function
                current_func = match.group(1)
                current_lines = [line]
            elif current_func:
                # Add line to current function
                current_lines.append(line)
                
                # Check for function end
                if line == "}" or line.endswith("}"):
                    functions[current_func] = current_lines
                    current_func = None
                    current_lines = []

        # Save last function if exists
        if current_func:
            functions[current_func] = current_lines

        return functions

    def _parse_getopts_options(self, options_str: str) -> List[CommandParameter]:
        """Parse getopts options string."""
        parameters = []
        i = 0
        while i < len(options_str):
            opt = options_str[i]
            if opt == ":":
                i += 1
                continue
            
            param_name = opt
            param_type = "boolean"
            required = False
            
            # Check if next char indicates required argument
            if i + 1 < len(options_str) and options_str[i + 1] == ":":
                param_type = "string"
                required = True
                i += 1
            
            parameters.append(CommandParameter(
                name=param_name,
                type=param_type,
                description=f"Option -{param_name}",
                required=required,
            ))
            
            i += 1

        return parameters

    def _create_function_schema(self, func_name: str, func_lines: List[str], source_name: str) -> Optional[CommandSchema]:
        """Create command schema for a shell function."""
        func_code = "\n".join(func_lines)
        
        # Extract description from comments
        description = f"Shell function: {func_name}"
        for line in func_lines:
            if line.strip().startswith("#"):
                comment = line.strip()[1:].strip()
                if comment and not comment.startswith(func_name):
                    description = comment
                    break

        # Extract parameters from function body
        parameters = []
        for line in func_lines:
            # Look for $1, $2, etc. usage
            if re.search(r'\$\d+', line):
                # Simple heuristic: count positional parameters
                param_matches = re.findall(r'\$(\d+)', line)
                for param_num in param_matches:
                    param_name = f"arg{param_num}"
                    if not any(p.name == param_name for p in parameters):
                        parameters.append(CommandParameter(
                            name=param_name,
                            type="string",
                            description=f"Positional argument {param_num}",
                            required=True,
                        ))

        return CommandSchema(
            name=func_name,
            description=description,
            parameters=parameters,
            category="shell",
            source=f"{source_name}:{func_name}",
            metadata={
                "function_lines": len(func_lines),
            }
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

        # Try with makefile-parser library first
        try:
            return self._try_parse_with_library(file_path)
        except Exception:
            pass

        # Fallback to regex parsing
        content = file_path.read_text(encoding="utf-8", errors="replace")
        return self._parse_fallback(content, str(file_path))

    def _try_parse_with_library(self, file_path: Path) -> Optional[ExtractedSchema]:
        # Optional dependency.
        try:
            import makefile_parser  # type: ignore
        except ImportError:
            return None

        try:
            makefile = makefile_parser.Makefile(file_path)
            commands = []

            for target in makefile.targets:
                params = []
                for var_name in target.variables:
                    params.append(CommandParameter(
                        name=var_name,
                        type="string",
                        description=f"Makefile variable {var_name}",
                        required=False,
                    ))

                commands.append(CommandSchema(
                    name=target.name,
                    description=target.description or f"Makefile target: {target.name}",
                    parameters=params,
                    category="makefile",
                    source=str(file_path),
                    metadata={
                        "dependencies": list(target.dependencies),
                        "commands": target.commands,
                    }
                ))

            return ExtractedSchema(
                source=str(file_path),
                commands=commands,
                metadata={"parser": "makefile_parser"},
            )
        except Exception:
            return None

    def _parse_fallback(self, content: str, source: str) -> ExtractedSchema:
        lines = content.splitlines()
        variables: dict[str, str] = {}
        targets: dict[str, dict[str, Any]] = {}
        current_target = None
        current_commands: List[str] = []

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Variable assignment
            var_match = self._re_var.match(line)
            if var_match:
                var_name = var_match.group("name")
                var_value = var_match.group("value")
                variables[var_name] = var_value
                continue

            # Target definition
            target_match = self._re_target.match(line)
            if target_match:
                # Save previous target
                if current_target:
                    targets[current_target]["commands"] = current_commands

                # Start new target
                current_target = target_match.group("target")
                deps = target_match.group("deps").strip()
                targets[current_target] = {
                    "dependencies": [d.strip() for d in deps.split() if d.strip()],
                    "commands": [],
                }
                current_commands = []
                continue

            # Command (starts with tab)
            if current_target and line.startswith("\t"):
                current_commands.append(line[1:].strip())

        # Save last target
        if current_target:
            targets[current_target]["commands"] = current_commands

        # Create command schemas
        commands = []
        for target_name, target_data in targets.items():
            if target_name.startswith("."):
                continue  # Skip special targets

            parameters = []
            # Add variables as parameters
            for var_name in variables:
                if self._var_ref in target_data["commands"]:
                    parameters.append(CommandParameter(
                        name=var_name,
                        type="string",
                        description=f"Makefile variable {var_name}",
                        required=False,
                    ))

            description = f"Makefile target: {target_name}"
            if target_data["commands"]:
                description = f"Makefile target: {target_name} - {target_data['commands'][0]}"

            commands.append(CommandSchema(
                name=target_name,
                description=description,
                parameters=parameters,
                category="makefile",
                source=source,
                metadata={
                    "dependencies": target_data["dependencies"],
                    "commands": target_data["commands"],
                }
            ))

        return ExtractedSchema(
            source=source,
            commands=commands,
            metadata={
                "variables": list(variables.keys()),
                "targets_count": len(targets),
            }
        )
