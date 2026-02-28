import ast
import os
import json
from collections import defaultdict

# =====================================================
# helpers
# =====================================================

def module_name_from_path(root, path):
    rel = os.path.relpath(path, root)
    rel = rel.replace(os.sep, ".")
    if rel.endswith(".py"):
        rel = rel[:-3]
    if rel.endswith(".__init__"):
        rel = rel[:-9]
    return rel


# =====================================================
# main extractor
# =====================================================

class FlowExtractor(ast.NodeVisitor):

    def __init__(self, module_name):
        self.module = module_name

        self.cfg = defaultdict(list)
        self.node_map = {}
        self.node_function = {}

        self.node_id = 0
        self.current_node = None

        self.class_stack = []
        self.current_function = None

        # fq_function -> entry node
        self.function_entries = {}

        # fq_caller -> set(fq_callee)
        self.call_graph = defaultdict(set)

        # local name -> fully qualified name (imports)
        self.imports = {}

    # -------------------------------------------------

    def fq_name(self, name):
        parts = []
        if self.class_stack:
            parts.append(self.class_stack[-1])
        parts.append(name)
        return f"{self.module}." + ".".join(parts)

    # -------------------------------------------------

    def new_node(self, label):
        nid = self.node_id
        self.node_id += 1
        self.node_map[nid] = label
        self.node_function[nid] = self.current_function
        return nid

    def connect(self, a, b):
        if a is not None:
            self.cfg[a].append(b)

    # =================================================
    # imports
    # =================================================

    def visit_Import(self, node):
        for n in node.names:
            asname = n.asname or n.name
            self.imports[asname] = n.name

    def visit_ImportFrom(self, node):
        if node.module:
            for n in node.names:
                asname = n.asname or n.name
                self.imports[asname] = node.module + "." + n.name

    # =================================================
    # class / function
    # =================================================

    def visit_ClassDef(self, node):
        self.class_stack.append(node.name)
        for stmt in node.body:
            self.visit(stmt)
        self.class_stack.pop()

    def visit_FunctionDef(self, node):

        prev_fn = self.current_function
        prev_node = self.current_node

        fq = self.fq_name(node.name)
        self.current_function = fq

        entry = self.new_node(f"FUNC:{fq}")
        self.function_entries[fq] = entry
        self.current_node = entry

        for stmt in node.body:
            self.visit(stmt)

        self.current_function = prev_fn
        self.current_node = prev_node

    # =================================================
    # calls
    # =================================================

    def resolve_call_name(self, node):

        # foo()
        if isinstance(node, ast.Name):
            name = node.id
            if name in self.imports:
                return self.imports[name]
            return self.module + "." + name

        # a.b.c()
        if isinstance(node, ast.Attribute):
            parts = []
            cur = node
            while isinstance(cur, ast.Attribute):
                parts.append(cur.attr)
                cur = cur.value

            if isinstance(cur, ast.Name):
                parts.append(cur.id)
                parts.reverse()

                root = parts[0]
                rest = parts[1:]

                if root in self.imports:
                    return self.imports[root] + "." + ".".join(rest)

                return self.module + "." + ".".join(parts)

        return None

    def visit_Call(self, node):

        nid = self.new_node("CALL")
        self.connect(self.current_node, nid)

        if self.current_function:
            callee = self.resolve_call_name(node.func)
            if callee:
                self.call_graph[self.current_function].add(callee)

        prev = self.current_node
        self.current_node = nid
        self.generic_visit(node)
        self.current_node = prev

    # =================================================
    # decisions
    # =================================================

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

    # =================================================
    # generic
    # =================================================

    def generic_visit(self, node):

        if isinstance(node, (ast.If, ast.Call, ast.FunctionDef, ast.ClassDef)):
            return super().generic_visit(node)

        nid = self.new_node(type(node).__name__)
        self.connect(self.current_node, nid)

        prev = self.current_node
        self.current_node = nid
        super().generic_visit(node)
        self.current_node = prev


# =====================================================
# project-level merge
# =====================================================

class ProjectModel:

    def __init__(self):
        self.cfg = defaultdict(list)
        self.node_map = {}
        self.node_function = {}

        self.function_entries = {}
        self.call_graph = defaultdict(set)

        self._node_offset = 0

    def merge(self, fe: FlowExtractor):

        mapping = {}

        for old_id in fe.node_map:
            new_id = old_id + self._node_offset
            mapping[old_id] = new_id
            self.node_map[new_id] = fe.node_map[old_id]
            self.node_function[new_id] = fe.node_function[old_id]

        for a, bs in fe.cfg.items():
            for b in bs:
                self.cfg[mapping[a]].append(mapping[b])

        for fn, entry in fe.function_entries.items():
            self.function_entries[fn] = mapping[entry]

        for k, v in fe.call_graph.items():
            self.call_graph[k].update(v)

        self._node_offset += len(fe.node_map)


# =====================================================
# paths
# =====================================================

def enumerate_paths(cfg, start, max_depth=40):

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


def build_interprocedural_decision_paths(model: ProjectModel):

    local_paths = {}

    for fn, entry in model.function_entries.items():
        all_paths = enumerate_paths(model.cfg, entry)

        filtered = []
        for p in all_paths:
            seq = []
            for n in p:
                lbl = model.node_map[n]
                if lbl == "IF":
                    seq.append("IF")
                elif lbl == "CALL":
                    seq.append("CALL")
            filtered.append(seq)

        local_paths[fn] = filtered

    def expand(fn, path, depth=0, max_depth=4):

        if depth > max_depth:
            return [path]

        results = [[]]

        for token in path:
            if token == "CALL":

                expanded = []
                callees = list(model.call_graph.get(fn, []))

                if not callees:
                    for r in results:
                        expanded.append(r + ["CALL:?"])
                else:
                    for callee in callees:
                        sub = local_paths.get(callee, [[]])
                        for sp in sub:
                            for r in results:
                                for e in expand(callee, sp, depth + 1):
                                    expanded.append(
                                        r + [f"CALL:{callee}"] + e
                                    )
                results = expanded
            else:
                results = [r + ["IF"] for r in results]

        return results

    composed = []

    for fn, paths in local_paths.items():
        for p in paths:
            for ep in expand(fn, p):
                composed.append({
                    "entry_function": fn,
                    "decision_path": ep
                })

    return composed


# =====================================================
# main
# =====================================================

def analyze_project(src_root):

    project = ProjectModel()

    for root, _, files in os.walk(src_root):
        for f in files:
            if not f.endswith(".py"):
                continue

            path = os.path.join(root, f)
            module = module_name_from_path(src_root, path)

            try:
                with open(path, "r", encoding="utf8") as fh:
                    code = fh.read()

                tree = ast.parse(code, filename=path)
                fe = FlowExtractor(module)
                fe.visit(tree)
                project.merge(fe)

            except Exception as e:
                print("[WARN]", path, e)

    with open("out_call_graph.json", "w", encoding="utf8") as f:
        json.dump(
            {k: sorted(v) for k, v in project.call_graph.items()},
            f, indent=2
        )

    with open("out_interprocedural_decision_paths.json", "w", encoding="utf8") as f:
        json.dump(
            build_interprocedural_decision_paths(project),
            f, indent=2
        )

    with open("out_function_entries.json", "w", encoding="utf8") as f:
        json.dump(project.function_entries, f, indent=2)

    print("Done.")


if __name__ == "__main__":
    analyze_project("src/app2schema")