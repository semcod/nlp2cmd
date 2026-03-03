# Dynamic Orchestration Engine

## Overview

The `nlp2cmd.orchestration` module replaces hardcoded template/pattern matching
with LLM-driven task planning, execution, reflection, and repair.

```
User prompt → DecisionRouter
                ↓ (DYNAMIC_ORCHESTRATOR)
              Orchestrator.plan() → TaskSchema (LLM)
                ↓
              Step execution (with retry)
                ↓ on failure → LLM repair
              ResultAnalyzer.analyze() (LLM reflection)
                ↓ invalid → re-generate + re-run
              TaskResult
```

## Architecture

### Core Components

| Module | Class | Purpose |
|--------|-------|---------|
| `orchestration/engine.py` | `Orchestrator` | Main engine: plan → execute → reflect |
| `orchestration/reflection.py` | `ResultAnalyzer` | LLM-driven output validation + error classification |
| `orchestration/handlers.py` | `register_default_handlers()` | 11 step handlers bridging to execution capabilities |
| `router/__init__.py` | `DecisionRouter` | Routes to `DYNAMIC_ORCHESTRATOR` for complex tasks |

### Step Handlers

| Handler | Action | Description |
|---------|--------|-------------|
| `handle_shell_exec` | `shell_exec` | Execute shell commands |
| `handle_generate_code` | `generate_code` | Generate code via LLM (coding/repair tasks) |
| `handle_inject_code` | `inject_code` | Inject code into web editors (CM5/CM6/Monaco/Ace/textarea) |
| `handle_navigate` | `navigate` | Navigate browser to URL |
| `handle_dismiss_popups` | `dismiss_popups` | Close cookie/consent dialogs |
| `handle_inspect` | `inspect` | Extract page DOM schema |
| `handle_find_and_click` | `find_and_click` | Click buttons by purpose (run, submit) |
| `handle_wait` | `wait` | Wait for specified duration |
| `handle_capture_output` | `capture_output` | Read program output from page |
| `handle_screenshot` | `screenshot` | Take page screenshot |
| `handle_validate` | `validate` | Validate output via ResultAnalyzer |

### Reflection System

The `ResultAnalyzer` provides intelligent output analysis:

1. **Fast path** — `has_error_signals()` detects tracebacks, SyntaxError, exit codes without LLM
2. **Error classification** — `classify_error()` categorizes: syntax_error, runtime_error, crash, etc.
3. **LLM validation** — Sends output + goal to validation model for semantic checking
4. **Repair suggestions** — `suggest_repair()` asks LLM for specific fix strategy
5. **Double-check** — On false negatives, re-validates with simpler prompt

### Routing Integration

The `DecisionRouter` now includes `DYNAMIC_ORCHESTRATOR` as a routing decision:

```python
class RoutingDecision(Enum):
    DIRECT = "direct"                        # Simple single-action
    LLM_PLANNER = "llm_planner"             # Multi-step LLM planning
    DYNAMIC_ORCHESTRATOR = "dynamic_orchestrator"  # Full orchestration + reflection
    CLARIFICATION = "clarification"          # Needs user input
    REJECT = "reject"                        # Cannot process
```

For unknown/complex intents, the router checks if the orchestration module is
available and routes to `DYNAMIC_ORCHESTRATOR` by default.

## Usage

### Programmatic

```python
from nlp2cmd.orchestration import Orchestrator, register_default_handlers

orch = Orchestrator()
register_default_handlers(orch)

result = await orch.run(
    "write a python program that sorts numbers",
    context={"page": playwright_page},
)
print(result.success, result.output)
```

### Custom Handlers

```python
async def my_custom_handler(step, ctx):
    from nlp2cmd.orchestration.engine import StepResult, StepStatus
    # ... custom logic ...
    return StepResult(StepStatus.SUCCESS, {"key": "value"})

orch.register_handler("my_action", my_custom_handler)
```

### CLI (via examples)

```bash
python3 examples/10_online_code_editors/05_dynamic_executor.py \
    --prompt "write fibonacci in python" --verbose --headless
```

## Deprecation of Hardcoded Systems

The following systems are **deprecated** in favor of dynamic orchestration:

| System | Status | Migration Path |
|--------|--------|----------------|
| `ComplexCommandPlanner.DRAWING_PATTERNS` | Deprecated fallback | `Orchestrator.plan()` called first |
| `ComplexCommandPlanner.BROWSER_PATTERNS` | Deprecated fallback | `Orchestrator.plan()` called first |
| `ComplexCommandPlanner.DESKTOP_PATTERNS` | Deprecated fallback | `Orchestrator.plan()` called first |
| `TemplateGenerator` (16 static dicts) | Active (shell/SQL) | Gradual migration to `DynamicSchemaGenerator` |
| `CommandDetector` (static regex) | Active | Gradual migration to LLM detection |
| `PlanExecutionMixin` (CC=344 god module) | Active | Split into orchestration handlers |

The hardcoded patterns are kept as fallbacks and will be removed once the
dynamic orchestrator has been validated in production use.

## Tests

63 unit tests in `tests/unit/test_orchestration.py`:

- **Reflection**: `has_error_signals` (8), `classify_error` (11), `ResultAnalyzer` (4)
- **Engine**: `Orchestrator` plan/execute/repair (8), `_parse_json` (5)
- **Handlers**: All 11 handlers (16), `_normalize_purpose` (1), `_strip_code_fences` (1)
- **Router integration**: `DYNAMIC_ORCHESTRATOR` routing (3)
- **ComplexPlanner integration**: Orchestrator delegation (2)
- **Data classes**: `StepDef`, `TaskSchema`, `_parse_json_safe` (7)

Run: `python3 -m pytest tests/unit/test_orchestration.py -v`
