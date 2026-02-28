import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


def _strip_bom(text: str) -> str:
    return text[1:] if text.startswith("\ufeff") else text


def _ensure_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _deep_get(d: Dict[str, Any], path: Tuple[str, ...]) -> Any:
    cur: Any = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def normalize_llm_task(data: Dict[str, Any]) -> Dict[str, Any]:
    task = data.get("task") or {}
    context = data.get("context") or {}
    deliverables = data.get("deliverables") or {}
    interfaces = data.get("interfaces") or {}
    rules = data.get("rules") or {}
    acceptance = data.get("acceptance") or {}
    examples = data.get("examples")
    notes = data.get("notes_for_llm") or {}

    normalized: Dict[str, Any] = {
        "task": {
            "title": task.get("title") or "",
            "one_line_goal": task.get("one_line_goal") or "",
        },
        "context": {
            "product_area": context.get("product_area") or "",
            "current_behavior": context.get("current_behavior") or "",
            "desired_behavior": context.get("desired_behavior") or "",
        },
        "deliverables": {
            "language": deliverables.get("language") or "any",
            "must_generate": _ensure_list(deliverables.get("must_generate")),
            "files_to_create_or_edit": _ensure_list(deliverables.get("files_to_create_or_edit")),
        },
        "interfaces": {
            "inputs": _ensure_list(interfaces.get("inputs")),
            "outputs": _ensure_list(interfaces.get("outputs")),
        },
        "rules": {
            "must": _ensure_list(rules.get("must")),
            "must_not": _ensure_list(rules.get("must_not")),
            "assumptions": _ensure_list(rules.get("assumptions")),
            "edge_cases": _ensure_list(rules.get("edge_cases")),
            "performance": _ensure_list(rules.get("performance")),
        },
        "acceptance": {
            "tests": _ensure_list(acceptance.get("tests")),
            "done_definition": _ensure_list(acceptance.get("done_definition")),
        },
        "examples": _ensure_list(examples),
        "notes_for_llm": {
            "constraints": _ensure_list(notes.get("constraints")),
            "style": _ensure_list(notes.get("style")),
            "language_specific_hints": _ensure_list(notes.get("language_specific_hints")),
        },
    }

    return normalized


_SECTION_KEYS = {
    "TITLE": ("task", "title"),
    "GOAL": ("task", "one_line_goal"),
    "PRODUCT_AREA": ("context", "product_area"),
    "CURRENT": ("context", "current_behavior"),
    "DESIRED": ("context", "desired_behavior"),
}


def _parse_bullets(lines: List[str]) -> List[str]:
    items: List[str] = []
    for raw in lines:
        s = raw.strip()
        if not s:
            continue
        if s.startswith("-"):
            items.append(s[1:].strip())
        else:
            items.append(s)
    return items


def parse_llm_task_text(text: str) -> Dict[str, Any]:
    text = _strip_bom(text)
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    sections: Dict[str, List[str]] = {}
    current: Optional[str] = None

    def start_section(name: str) -> None:
        nonlocal current
        current = name
        sections.setdefault(name, [])

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current is not None:
                sections[current].append("")
            continue

        upper = stripped.upper()
        if upper.endswith(":"):
            key = upper[:-1].strip()
            if key in {
                "TITLE",
                "GOAL",
                "CURRENT",
                "DESIRED",
                "INPUTS",
                "OUTPUTS",
                "RULES (MUST)",
                "RULES (MUST NOT)",
                "EDGE CASES",
                "ACCEPTANCE TESTS",
                "DELIVERABLES",
            }:
                start_section(key)
                continue

        if current is None:
            continue
        sections[current].append(line)

    data: Dict[str, Any] = {
        "task": {"title": "", "one_line_goal": ""},
        "context": {"product_area": "", "current_behavior": "", "desired_behavior": ""},
        "deliverables": {"language": "any", "must_generate": [], "files_to_create_or_edit": []},
        "interfaces": {"inputs": [], "outputs": []},
        "rules": {"must": [], "must_not": [], "assumptions": [], "edge_cases": [], "performance": []},
        "acceptance": {"tests": [], "done_definition": []},
        "examples": [],
        "notes_for_llm": {"constraints": [], "style": [], "language_specific_hints": []},
    }

    for section_name, path in _SECTION_KEYS.items():
        content_lines = sections.get(section_name)
        if not content_lines:
            continue
        value = "\n".join(content_lines).strip()
        if value:
            parent = data
            for key in path[:-1]:
                parent = parent[key]
            parent[path[-1]] = value

    if sections.get("INPUTS"):
        data["interfaces"]["inputs"] = _parse_bullets(sections["INPUTS"])
    if sections.get("OUTPUTS"):
        data["interfaces"]["outputs"] = _parse_bullets(sections["OUTPUTS"])
    if sections.get("RULES (MUST)"):
        data["rules"]["must"] = _parse_bullets(sections["RULES (MUST)"])
    if sections.get("RULES (MUST NOT)"):
        data["rules"]["must_not"] = _parse_bullets(sections["RULES (MUST NOT)"])
    if sections.get("EDGE CASES"):
        data["rules"]["edge_cases"] = _parse_bullets(sections["EDGE CASES"])

    if sections.get("ACCEPTANCE TESTS"):
        tests: List[Dict[str, str]] = []
        raw_items = _parse_bullets(sections["ACCEPTANCE TESTS"])
        for idx, item in enumerate(raw_items, 1):
            tests.append({"name": f"test_{idx}", "given": "", "when": "", "then": item})
        data["acceptance"]["tests"] = tests

    if sections.get("DELIVERABLES"):
        data["deliverables"]["must_generate"] = _parse_bullets(sections["DELIVERABLES"])

    return data


def load_input(path: Path) -> Dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    raw = _strip_bom(raw)

    if path.suffix.lower() in {".yaml", ".yml"}:
        loaded = yaml.safe_load(raw) or {}
        if not isinstance(loaded, dict):
            raise ValueError("YAML input must be a mapping/object at top level")
        return loaded

    if path.suffix.lower() == ".json":
        import json

        loaded = json.loads(raw)
        if not isinstance(loaded, dict):
            raise ValueError("JSON input must be an object at top level")
        return loaded

    return parse_llm_task_text(raw)


def dump_yaml(data: Dict[str, Any]) -> str:
    return yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        width=100,
        default_flow_style=False,
    )


def create_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="llm-task-generator",
        description="Generate normalized llm_task.yaml from simplified task spec (text/YAML/JSON).",
    )
    p.add_argument("-i", "--input", required=True, help="Input file: .txt/.md/.yaml/.yml/.json")
    p.add_argument("-o", "--output", required=True, help="Output YAML file path")
    p.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate/normalize input; do not write output file",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = create_parser().parse_args(argv)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        return 2

    data = load_input(input_path)

    if "task" not in data:
        data = {"task": data}

    normalized = normalize_llm_task(data)

    if args.validate_only:
        sys.stdout.write(dump_yaml(normalized))
        return 0

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(dump_yaml(normalized), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
