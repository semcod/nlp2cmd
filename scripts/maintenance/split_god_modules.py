#!/usr/bin/env python3
"""Split god-module files into per-class submodules with re-exports."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from typing import NamedTuple


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
PKG_ROOT = SRC_ROOT / "nlp2cmd"


class ClassBlock(NamedTuple):
    name: str
    start: int
    end: int
    source: str


def class_start_line(node: ast.ClassDef) -> int:
    if node.decorator_list:
        return node.decorator_list[0].lineno - 1
    return node.lineno - 1


def node_source(source: str, lines: list[str], node: ast.AST) -> str:
    end = getattr(node, "end_lineno", None) or node.lineno
    start = node.lineno - 1
    if isinstance(node, ast.ClassDef) and node.decorator_list:
        start = class_start_line(node)
        return "".join(lines[start:end])
    segment = ast.get_source_segment(source, node)
    if segment:
        return segment
    return "".join(lines[start:end])


def extract_import_preamble(tree: ast.Module, source: str, lines: list[str]) -> str:
    parts: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            break
        parts.append(node_source(source, lines, node).rstrip())
    if not parts:
        return ""
    return "\n".join(parts) + "\n"


def find_class_blocks(source: str) -> tuple[list[ClassBlock], str, str]:
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    blocks: list[ClassBlock] = []

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            start = class_start_line(node)
            segment = node_source(source, lines, node)
            blocks.append(
                ClassBlock(
                    node.name,
                    start,
                    node.end_lineno or node.lineno,
                    segment,
                )
            )

    preamble = extract_import_preamble(tree, source, lines)

    non_class_parts: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            continue
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        part = node_source(source, lines, node)
        if part.strip():
            non_class_parts.append(part.rstrip())

    non_class_body = "\n\n".join(non_class_parts)
    non_class_body = re.sub(r"\n__all__\s*=\s*\[[\s\S]*?\]\s*\n?", "\n", non_class_body)
    return blocks, preamble, non_class_body.strip()


def camel_to_snake(name: str) -> str:
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def module_filename(class_name: str, facade_stem: str) -> str:
    stem = camel_to_snake(class_name)
    if stem == facade_stem:
        return f"{stem}_class.py"
    return f"{stem}.py"


def package_import_path(module_path: Path) -> str:
    rel = module_path.parent.relative_to(PKG_ROOT)
    return ".".join(rel.parts)


def clean_preamble(preamble: str) -> str:
    """Remove orphaned decorators left before the first class."""
    lines = preamble.splitlines(keepends=True)
    cleaned: list[str] = []
    for i, line in enumerate(lines):
        if line.strip() == "@dataclass" and i + 1 >= len(lines):
            continue
        if line.strip() == "@dataclass":
            nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
            if not nxt.startswith("class "):
                continue
        cleaned.append(line)
    return "".join(cleaned)


def split_module(
    module_path: Path,
    *,
    import_prefix: str | None = None,
    import_style: str = "package",
) -> None:
    source = module_path.read_text(encoding="utf-8")
    blocks, preamble, non_class_body = find_class_blocks(source)
    preamble = clean_preamble(preamble)

    if not blocks:
        print(f"  No classes in {module_path}")
        return

    package_dir = module_path.parent
    if import_prefix is None and import_style != "local":
        import_prefix = f"nlp2cmd.{package_import_path(module_path)}"
    facade_stem = module_path.stem
    class_files: dict[str, str] = {}

    for block in blocks:
        class_files[block.name] = module_filename(block.name, facade_stem).replace(".py", "")

    for block in blocks:
        filename = module_filename(block.name, facade_stem)
        body = block.source

        cross_imports: list[str] = []
        for other in blocks:
            if other.name == block.name:
                continue
            if re.search(rf"\b{other.name}\b", body):
                other_mod = class_files[other.name]
                if import_style == "local":
                    cross_imports.append(f"from {other_mod} import {other.name}")
                else:
                    cross_imports.append(
                        f"from {import_prefix}.{other_mod} import {other.name}"
                    )

        parts = [f"# {block.name} - extracted from {module_path.name}\n"]
        parts.append(preamble.rstrip())
        if cross_imports:
            parts.append("\n")
            parts.extend(imp + "\n" for imp in sorted(set(cross_imports)))
        parts.append("\n" + body + "\n")

        (package_dir / filename).write_text("".join(parts), encoding="utf-8")
        rel = module_path.relative_to(PROJECT_ROOT)
        print(f"  Created {package_dir / filename} (from {rel})")

    exports = [b.name for b in blocks]
    new_facade = f'"""Re-exports from split {module_path.name} module."""\n\n'
    for block in blocks:
        mod = class_files[block.name]
        if import_style == "local":
            new_facade += f"from {mod} import {block.name}\n"
        else:
            new_facade += f"from {import_prefix}.{mod} import {block.name}\n"
    new_facade += f"\n__all__ = {exports!r}\n"

    if non_class_body:
        new_facade += "\n\n" + non_class_body + "\n"

    module_path.write_text(new_facade, encoding="utf-8")
    print(f"  Rewrote {module_path.relative_to(PROJECT_ROOT)}")


def main() -> int:
    targets = [
        PKG_ROOT / "adapters" / "canvas.py",
        PKG_ROOT / "feedback" / "__init__.py",
        PKG_ROOT / "step_handlers" / "drawing.py",
    ]
    local_targets = [
        PROJECT_ROOT / "scripts" / "thermodynamic" / "termo2.py",
    ]

    for target in targets:
        if not target.exists():
            print(f"Skipping missing: {target}")
            continue
        print(f"\nSplitting {target.relative_to(PKG_ROOT)}...")
        split_module(target)

    for target in local_targets:
        if not target.exists():
            print(f"Skipping missing: {target}")
            continue
        print(f"\nSplitting {target.relative_to(PROJECT_ROOT)}...")
        split_module(target, import_style="local")

    return 0


if __name__ == "__main__":
    sys.exit(main())
