#!/usr/bin/env python3
"""Split nlp2cmd_web_controller.py into local submodules."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from typing import NamedTuple


class ClassBlock(NamedTuple):
    name: str
    source: str


def camel_to_snake(name: str) -> str:
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def module_filename(class_name: str, facade_stem: str) -> str:
    stem = camel_to_snake(class_name)
    if stem == facade_stem:
        return f"{stem}_class.py"
    return f"{stem}.py"


def split_local_module(module_path: Path) -> None:
    source = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)

    blocks: list[ClassBlock] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            segment = ast.get_source_segment(source, node) or "".join(
                lines[node.lineno - 1 : node.end_lineno]
            )
            blocks.append(ClassBlock(node.name, segment))

    if not blocks:
        return

    preamble_end = tree.body[0].lineno - 1 if tree.body else 0
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            preamble_end = node.lineno - 1
            break
    preamble = "".join(lines[:preamble_end])

    package_dir = module_path.parent
    facade_stem = module_path.stem
    class_files = {
        b.name: module_filename(b.name, facade_stem).replace(".py", "") for b in blocks
    }

    for block in blocks:
        filename = module_filename(block.name, facade_stem)
        cross = []
        for other in blocks:
            if other.name != block.name and re.search(rf"\b{other.name}\b", block.source):
                cross.append(f"from {class_files[other.name]} import {other.name}")

        content = f"# {block.name} - extracted from {module_path.name}\n"
        content += preamble.rstrip() + "\n"
        if cross:
            content += "\n" + "\n".join(sorted(set(cross))) + "\n"
        content += "\n" + block.source + "\n"
        (package_dir / filename).write_text(content, encoding="utf-8")
        print(f"  Created {filename}")

    facade = f'"""Re-exports from split {module_path.name}."""\n\n'
    for block in blocks:
        facade += f"from {class_files[block.name]} import {block.name}\n"
    facade += f"\n__all__ = {[b.name for b in blocks]!r}\n"
    module_path.write_text(facade, encoding="utf-8")
    print(f"  Rewrote {module_path.name}")


def main() -> int:
    controller = (
        Path(__file__).resolve().parents[2]
        / "examples"
        / "03_integrations"
        / "web_development"
        / "nlp2cmd_web_controller.py"
    )
    print(f"Splitting {controller}...")
    split_local_module(controller)
    return 0


if __name__ == "__main__":
    sys.exit(main())
