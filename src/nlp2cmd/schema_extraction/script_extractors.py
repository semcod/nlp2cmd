"""Script extractors for shell scripts and makefiles."""

from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .extractors import CommandParameter, CommandSchema, ExtractedSchema


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
                if t.startswith("<") and t.endswith(">"):
                    arg_name = t.strip("<>")
                    params.append(
                        CommandParameter(
                            name=arg_name,
                            type="string",
                            description=f"Positional argument {arg_name}",
                            required=True,
                            location="positional",
                        )
                    )
                elif t.startswith("[") and t.endswith("]"):
                    arg_name = t.strip("[]")
                    params.append(
                        CommandParameter(
                            name=arg_name,
                            type="string",
                            description=f"Optional argument {arg_name}",
                            required=False,
                            location="positional",
                        )
                    )

        params = _dedupe_params(params)

        script_name = Path(source_name).stem if source_name != "string" else "script"
        command = CommandSchema(
            name=script_name,
            description=description or f"Shell script: {script_name}",
            category="shell_script",
            parameters=params,
            examples=usage_lines[:3],
            patterns=[script_name],
            source_type="shell_script",
            metadata={"shebang": shebang},
        )

        return ExtractedSchema(
            source=source_name,
            source_type="shell_script",
            commands=[command],
            metadata={"shebang": shebang, "usage_lines": usage_lines},
        )


class MakefileExtractor:
    """Extract schema from Makefile targets and variables."""

    _re_var = re.compile(r"^(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*(?P<op>[:+?]?=)\s*(?P<value>.*)$")
    _re_target = re.compile(r"^(?P<target>[^:#\s]+)\s*:\s*(?P<deps>.*)$")
    _re_phony = re.compile(r"^.PHONY\s*:\s*(.*)")

    def extract_from_file(self, file_path: Union[str, Path]) -> ExtractedSchema:
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Makefile not found: {file_path}")

        source_code = file_path.read_text(encoding="utf-8", errors="replace")
        return self.extract_from_source(source_code, str(file_path))

    def extract_from_source(self, source_code: str, source_name: str) -> ExtractedSchema:
        lines = source_code.splitlines()
        
        # Extract description from comments at the top
        description_lines: list[str] = []
        for line in lines[:20]:
            s = line.strip()
            if s.startswith("#"):
                txt = s.lstrip("#").strip()
                if txt:
                    description_lines.append(txt)
            elif s:
                break

        description = " ".join(description_lines[:3])

        # Extract variables
        variables: Dict[str, str] = {}
        for line in lines:
            m = self._re_var.match(line)
            if m:
                variables[m.group("name")] = m.group("value").strip()

        # Extract phony targets
        phony_targets: set[str] = set()
        for line in lines:
            m = self._re_phony.match(line)
            if m:
                phony_targets.update(t.strip() for t in m.group(1).split())

        # Extract targets
        commands: list[CommandSchema] = []
        for line in lines:
            m = self._re_target.match(line)
            if m:
                target = m.group("target").strip()
                deps = m.group("deps").strip()
                
                # Skip internal targets
                if target.startswith(".") or target.endswith("_"):
                    continue

                # Extract description from preceding comment
                target_desc = f"Makefile target: {target}"
                for i in range(max(0, lines.index(line) - 5), lines.index(line)):
                    prev_line = lines[i].strip()
                    if prev_line.startswith("#"):
                        target_desc = prev_line.lstrip("#").strip()
                        break

                parameters: list[CommandParameter] = []
                
                # Add dependencies as parameters if they look like variables
                for dep in deps.split():
                    dep = dep.strip()
                    if dep in variables:
                        parameters.append(
                            CommandParameter(
                                name=dep,
                                type="string",
                                description=f"Dependency variable: {dep}",
                                required=False,
                                default=variables[dep],
                                location="variable",
                            )
                        )

                command = CommandSchema(
                    name=target,
                    description=target_desc,
                    category="makefile",
                    parameters=parameters,
                    examples=[f"make {target}"],
                    patterns=[f"make {target}", target],
                    source_type="makefile",
                    metadata={
                        "dependencies": deps.split(),
                        "is_phony": target in phony_targets,
                    },
                )
                commands.append(command)

        return ExtractedSchema(
            source=source_name,
            source_type="makefile",
            commands=commands,
            metadata={
                "variables": variables,
                "phony_targets": list(phony_targets),
                "description": description,
            },
        )
