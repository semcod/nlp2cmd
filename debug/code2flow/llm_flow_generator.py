import argparse
import re
import sys
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import yaml


_FUNC_LABEL_PREFIX = "FUNC:"
_CALL_LABEL_PREFIX = "CALL "


def _strip_bom(text: str) -> str:
    return text[1:] if text.startswith("\ufeff") else text


def _safe_read_yaml(path: Path) -> Dict[str, Any]:
    raw = _strip_bom(path.read_text(encoding="utf-8"))
    loaded = yaml.safe_load(raw) or {}
    if not isinstance(loaded, dict):
        raise ValueError("analysis.yaml must be a mapping at top-level")
    return loaded


def _as_dict(d: Any) -> Dict[str, Any]:
    return d if isinstance(d, dict) else {}


def _as_list(v: Any) -> List[Any]:
    return v if isinstance(v, list) else []


def _shorten(s: str, max_len: int) -> str:
    s = (s or "").strip()
    if len(s) <= max_len:
        return s
    return s[: max(0, max_len - 1)].rstrip() + "…"


def _parse_call_label(label: str) -> Optional[str]:
    label = (label or "").strip()
    if not label.startswith(_CALL_LABEL_PREFIX):
        return None
    rest = label[len(_CALL_LABEL_PREFIX) :].strip()
    rest = rest.replace("<", "").replace(">", "")

    m = re.match(r"([A-Za-z_][A-Za-z0-9_\.]+)\s*\(", rest)
    if m:
        return m.group(1)

    m = re.match(r"([A-Za-z_][A-Za-z0-9_\.]+)$", rest)
    if m:
        return m.group(1)

    return None


def _parse_func_label(label: str) -> Optional[str]:
    label = (label or "").strip()
    if not label.startswith(_FUNC_LABEL_PREFIX):
        return None
    return label[len(_FUNC_LABEL_PREFIX) :].strip() or None


@dataclass(frozen=True)
class FuncSummary:
    name: str
    file: Optional[str]
    line: Optional[int]
    decisions: Tuple[str, ...]
    calls: Tuple[str, ...]


def _collect_nodes(analysis: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
    nodes = analysis.get("nodes")
    if not isinstance(nodes, dict):
        return {}

    parsed: Dict[int, Dict[str, Any]] = {}
    for k, v in nodes.items():
        try:
            node_id = int(k)
        except Exception:
            continue
        if isinstance(v, dict):
            parsed[node_id] = v
    return parsed


def _collect_entrypoints(nodes: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_file: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for n in nodes.values():
        f = n.get("file")
        if isinstance(f, str):
            by_file[f].append(n)

    entrypoints: List[Dict[str, Any]] = []
    for f, ns in by_file.items():
        if not (f.endswith("__main__.py") or f.endswith("cli.py")):
            continue

        main_funcs = [n for n in ns if n.get("type") == "FUNC" and isinstance(n.get("function"), str)]
        for n in main_funcs:
            entrypoints.append(
                {
                    "kind": "cli" if f.endswith("cli.py") else "module_main",
                    "file": f,
                    "function": n.get("function"),
                    "line": n.get("line"),
                }
            )

    uniq: Dict[str, Dict[str, Any]] = {}
    for ep in entrypoints:
        key = str(ep.get("function") or "")
        if key and key not in uniq:
            uniq[key] = ep

    return list(uniq.values())


def _collect_functions(nodes: Dict[int, Dict[str, Any]]) -> Set[str]:
    out: Set[str] = set()
    for n in nodes.values():
        if n.get("type") != "FUNC":
            continue
        fn = n.get("function")
        if isinstance(fn, str) and fn:
            out.add(fn)
        else:
            parsed = _parse_func_label(str(n.get("label") or ""))
            if parsed:
                out.add(parsed)
    return out


def _node_counts_by_function(nodes: Dict[int, Dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for n in nodes.values():
        fn = n.get("function")
        if isinstance(fn, str) and fn:
            counts[fn] += 1
    return counts


def _pick_relevant_functions(
    *,
    entrypoints: List[Dict[str, Any]],
    known_functions: Set[str],
    func_summaries: Dict[str, FuncSummary],
    nodes: Dict[int, Dict[str, Any]],
    max_functions: int,
) -> List[str]:
    """Pick a compact but meaningful subset of functions.

    In many real projects, the CFG "CALL" labels often point to external
    functions (e.g. click.echo), so a pure call-graph reachability may select
    almost nothing. Here we fall back to a scoring heuristic:
    - start with entrypoints
    - boost functions that have many nodes (more logic)
    - boost functions with important keywords (extract, schema, openapi, dom, cli)
    """

    roots = [str(ep.get("function") or "") for ep in entrypoints]
    roots = [r for r in roots if r in known_functions]

    counts = _node_counts_by_function(nodes)

    keyword_boosts = [
        (".cli.", 50),
        (".extract.", 80),
        ("extract_schema", 120),
        ("extract_schema_to_file", 120),
        ("extract_appspec_to_file", 120),
        ("openapi", 60),
        ("dom", 40),
        ("makefile", 40),
        ("shell", 40),
        ("python", 40),
        ("validate", 20),
        ("discover", 20),
    ]

    def score(fn: str) -> int:
        s = 0
        s += min(500, counts.get(fn, 0))  # node count baseline
        for needle, boost in keyword_boosts:
            if needle in fn:
                s += boost
        if fn in roots:
            s += 1000
        if fn in func_summaries and func_summaries[fn].decisions:
            s += min(200, 10 * len(func_summaries[fn].decisions))
        return s

    scored = [(fn, score(fn)) for fn in known_functions]
    scored.sort(key=lambda x: x[1], reverse=True)

    picked: List[str] = []
    for fn, _ in scored:
        if len(picked) >= max_functions:
            break
        picked.append(fn)

    return picked


def _summarize_functions(nodes: Dict[int, Dict[str, Any]], limit_decisions: int, limit_calls: int) -> Dict[str, FuncSummary]:
    decisions_by_func: Dict[str, List[str]] = defaultdict(list)
    calls_by_func: Dict[str, List[str]] = defaultdict(list)
    loc_by_func: Dict[str, Tuple[Optional[str], Optional[int]]] = {}

    for n in nodes.values():
        fn = n.get("function")
        if not isinstance(fn, str) or not fn:
            continue

        if fn not in loc_by_func:
            loc_by_func[fn] = (
                n.get("file") if isinstance(n.get("file"), str) else None,
                n.get("line") if isinstance(n.get("line"), int) else None,
            )

        ntype = n.get("type")
        label = str(n.get("label") or "")

        if ntype == "IF":
            decisions_by_func[fn].append(_shorten(label, 120))
        elif ntype == "CALL":
            callee = _parse_call_label(label)
            if callee:
                calls_by_func[fn].append(callee)

    summaries: Dict[str, FuncSummary] = {}
    for fn in set(list(decisions_by_func.keys()) + list(calls_by_func.keys()) + list(loc_by_func.keys())):
        file, line = loc_by_func.get(fn, (None, None))

        decision_counts = Counter(decisions_by_func.get(fn, []))
        call_counts = Counter(calls_by_func.get(fn, []))

        decisions = tuple([d for d, _ in decision_counts.most_common(limit_decisions)])
        calls = tuple([c for c, _ in call_counts.most_common(limit_calls)])

        summaries[fn] = FuncSummary(
            name=fn,
            file=file,
            line=line,
            decisions=decisions,
            calls=calls,
        )

    return summaries


def _build_call_graph(func_summaries: Dict[str, FuncSummary], known_functions: Set[str]) -> Dict[str, Set[str]]:
    g: Dict[str, Set[str]] = defaultdict(set)
    for fn, s in func_summaries.items():
        for callee in s.calls:
            if callee in known_functions:
                g[fn].add(callee)
    return g


def _reachable(g: Dict[str, Set[str]], roots: Iterable[str], max_nodes: int) -> List[str]:
    seen: Set[str] = set()
    q: deque[str] = deque([r for r in roots if r])

    while q and len(seen) < max_nodes:
        cur = q.popleft()
        if cur in seen:
            continue
        seen.add(cur)
        for nxt in sorted(g.get(cur, set())):
            if nxt not in seen:
                q.append(nxt)

    return list(seen)


def generate_llm_flow(
    analysis: Dict[str, Any],
    max_functions: int,
    limit_decisions: int,
    limit_calls: int,
) -> Dict[str, Any]:
    nodes = _collect_nodes(analysis)
    entrypoints = _collect_entrypoints(nodes)

    known_functions = _collect_functions(nodes)
    func_summaries = _summarize_functions(nodes, limit_decisions=limit_decisions, limit_calls=limit_calls)

    reachable = _pick_relevant_functions(
        entrypoints=entrypoints,
        known_functions=known_functions,
        func_summaries=func_summaries,
        nodes=nodes,
        max_functions=max_functions,
    )

    functions_out: List[Dict[str, Any]] = []
    for fn in sorted(reachable):
        s = func_summaries.get(fn)
        if not s:
            continue
        functions_out.append(
            {
                "name": s.name,
                "file": s.file,
                "line": s.line,
                "decisions": list(s.decisions),
                "calls": list(s.calls),
            }
        )

    package_names = sorted({fn.split(".")[0] for fn in known_functions if "." in fn})

    return {
        "format": "llm_flow.v1",
        "app": {
            "packages": package_names,
            "entrypoints": entrypoints,
        },
        "flow": {
            "selected_functions": functions_out,
        },
    }


def render_llm_flow_md(flow: Dict[str, Any]) -> str:
    app = _as_dict(flow.get("app"))
    entrypoints = _as_list(app.get("entrypoints"))
    selected = _as_list(_as_dict(flow.get("flow")).get("selected_functions"))

    lines: List[str] = []
    lines.append("# LLM Flow Summary")
    lines.append("")

    pkgs = _as_list(app.get("packages"))
    if pkgs:
        lines.append("## Packages")
        for p in pkgs:
            lines.append(f"- {p}")
        lines.append("")

    if entrypoints:
        lines.append("## Entrypoints")
        for ep in entrypoints:
            epd = _as_dict(ep)
            fn = epd.get("function")
            f = epd.get("file")
            ln = epd.get("line")
            lines.append(f"- {fn} ({f}:{ln})")
        lines.append("")

    lines.append("## Selected functions")
    for f in selected:
        fd = _as_dict(f)
        name = fd.get("name")
        file = fd.get("file")
        line = fd.get("line")
        lines.append(f"### {name}")
        lines.append(f"- Location: {file}:{line}")

        decisions = _as_list(fd.get("decisions"))
        if decisions:
            lines.append("- Decisions:")
            for d in decisions:
                lines.append(f"  - {_shorten(str(d), 180)}")

        calls = _as_list(fd.get("calls"))
        if calls:
            lines.append("- Calls:")
            for c in calls:
                lines.append(f"  - {c}")

        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


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
        prog="llm-flow-generator",
        description="Generate compact LLM-friendly app flow summary from code2flow analysis.yaml",
    )
    p.add_argument(
        "-i",
        "--input",
        default="./output/analysis.yaml",
        help="Path to analysis.yaml (default: ./output/analysis.yaml)",
    )
    p.add_argument(
        "-o",
        "--output",
        default="./output/llm_flow.yaml",
        help="Output llm_flow.yaml path (default: ./output/llm_flow.yaml)",
    )
    p.add_argument(
        "--md",
        default=None,
        help="Optional output Markdown summary path (e.g. ./output/llm_flow.md)",
    )
    p.add_argument("--max-functions", type=int, default=40)
    p.add_argument("--limit-decisions", type=int, default=8)
    p.add_argument("--limit-calls", type=int, default=12)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = create_parser().parse_args(argv)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        return 2

    analysis = _safe_read_yaml(input_path)
    flow = generate_llm_flow(
        analysis,
        max_functions=max(1, args.max_functions),
        limit_decisions=max(0, args.limit_decisions),
        limit_calls=max(0, args.limit_calls),
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(dump_yaml(flow), encoding="utf-8")

    if args.md:
        md_path = Path(args.md)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(render_llm_flow_md(flow), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
