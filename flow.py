import ast
import json
from collections import defaultdict

# -----------------------------
#  Analyzer
# -----------------------------

class FlowExtractor(ast.NodeVisitor):

    def __init__(self):
        self.cfg = defaultdict(list)
        self.node_map = {}
        self.node_id = 0

        self.current_node = None
        self.current_function = "__global__"

        # function -> entry node
        self.function_entries = {}

        # call graph: caller -> set(callee)
        self.call_graph = defaultdict(set)

        # per function CFG roots
        self.function_cfg_roots = defaultdict(list)

    # -------- basic graph --------

    def new_node(self, label):
        nid = self.node_id
        self.node_map[nid] = label
        self.node_id += 1
        return nid

    def connect(self, a, b):
        if a is not None:
            self.cfg[a].append(b)

    # -------- functions --------

    def visit_FunctionDef(self, node):
        prev_func = self.current_function
        prev_node = self.current_node

        self.current_function = node.name

        entry = self.new_node(f"FUNC:{node.name}")
        self.function_entries[node.name] = entry
        self.function_cfg_roots[node.name].append(entry)

        self.current_node = entry

        for stmt in node.body:
            self.visit(stmt)

        self.current_function = prev_func
        self.current_node = prev_node

    # -------- calls --------

    def visit_Call(self, node):
        nid = self.new_node("CALL")
        self.connect(self.current_node, nid)

        if isinstance(node.func, ast.Name):
            callee = node.func.id
            self.call_graph[self.current_function].add(callee)

        self.current_node = nid
        self.generic_visit(node)

    # -------- decisions --------

    def visit_If(self, node):
        nid = self.new_node("IF")
        self.connect(self.current_node, nid)

        parent = self.current_node
        self.current_node = nid

        for stmt in node.body:
            self.visit(stmt)

        for stmt in node.orelse:
            self.visit(stmt)

        self.current_node = parent

    # -------- generic --------

    def generic_visit(self, node):
        nid = self.new_node(type(node).__name__)
        self.connect(self.current_node, nid)

        prev = self.current_node
        self.current_node = nid
        super().generic_visit(node)
        self.current_node = prev


# -----------------------------
#  CFG paths
# -----------------------------

def enumerate_paths(cfg, start, max_depth=30):
    paths = []

    def dfs(n, path, depth):
        if depth > max_depth:
            return

        path.append(n)

        if n not in cfg or not cfg[n]:
            paths.append(path.copy())
        else:
            for nxt in cfg[n]:
                dfs(nxt, path, depth + 1)

        path.pop()

    dfs(start, [], 0)
    return paths


# -----------------------------
#  Interprocedural composition
# -----------------------------

def build_interprocedural_decision_paths(fe: FlowExtractor):

    # local decision paths per function
    local_paths = {}

    for fn, entry in fe.function_entries.items():
        all_paths = enumerate_paths(fe.cfg, entry)

        filtered = []
        for p in all_paths:
            filtered.append([
                fe.node_map[n] for n in p
                if fe.node_map[n] in ("IF", "CALL")
            ])

        local_paths[fn] = filtered

    # recursively expand CALL nodes
    def expand_path(fn, path, depth=0, max_depth=5):
        if depth > max_depth:
            return [path]

        results = [[]]

        for token in path:
            if token == "CALL":
                expanded = []

                for callee in fe.call_graph.get(fn, []):
                    for sub in local_paths.get(callee, [[]]):
                        for r in results:
                            for e in expand_path(callee, sub, depth + 1):
                                expanded.append(r + [f"CALL:{callee}"] + e)

                if expanded:
                    results = expanded
                else:
                    results = [r + ["CALL:?"] for r in results]

            else:
                results = [r + [token] for r in results]

        return results

    all_composed = []

    for fn, paths in local_paths.items():
        if fn == "__global__":
            continue
        for p in paths:
            for ep in expand_path(fn, p):
                all_composed.append({
                    "entry_function": fn,
                    "decision_path": ep
                })

    return all_composed


# -----------------------------
#  MAIN
# -----------------------------

def generate(source):

    with open(source, "r", encoding="utf8") as f:
        code = f.read()

    tree = ast.parse(code)

    fe = FlowExtractor()
    fe.visit(tree)

    # call graph
    call_graph_out = {
        k: list(v) for k, v in fe.call_graph.items()
    }

    # interprocedural decision paths
    composed_paths = build_interprocedural_decision_paths(fe)

    # raw cfg (optional, useful for debug)
    cfg_out = {
        "nodes": fe.node_map,
        "edges": fe.cfg,
        "function_entries": fe.function_entries
    }

    with open("out_call_graph.json", "w", encoding="utf8") as f:
        json.dump(call_graph_out, f, indent=2)

    with open("out_interprocedural_decision_paths.json", "w", encoding="utf8") as f:
        json.dump(composed_paths, f, indent=2)

    with open("out_cfg_full.json", "w", encoding="utf8") as f:
        json.dump(cfg_out, f, indent=2)


if __name__ == "__main__":
    generate("input.py")