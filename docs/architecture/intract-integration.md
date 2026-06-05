# Intract × nlp2dsl × nlp2cmd

Warstwa kontraktów [Intract](https://github.com/semcod/intract) egzekwuje **policy przed wykonaniem** (zakazane efekty, wymagane inputy, zgodność z manifestem). Nie weryfikuje stdout ani semantyki wyniku w shellu.

## Architektura (przegląd)

```mermaid
flowchart TB
    subgraph input [Wejście NL]
        Q[Zapytanie użytkownika]
    end

    subgraph nlp2dsl_pkgs [Pakiety nlp2dsl]
        Intent[IntentPipeline → IntentIR]
        Clarify{needs_clarification?}
        Plan[PlanningPipeline → ExecutionPlanIR]
    end

    subgraph intract [Intract — opcjonalnie]
        Bindings[intract-bindings.json]
        Manifest[intract.yaml]
        Bridge[RuntimeBridge]
        PGate[PlanStepGate]
        TVal[IntractValidator]
        PRGate[PipelineRunnerGate]
        SGate[IntractStepGate]
    end

    subgraph paths [Ścieżki wykonania]
        Show[nlp2dsl show --plan]
        PlanCmd[nlp2cmd plan]
        Legacy[nlp2cmd -q -r]
        Propact[Propact / subprocess]
        Runner[PipelineRunner]
    end

    Q --> Intent --> Clarify
    Clarify -->|plan: zawsze blokuj| Plan
    Clarify -->|show: tylko z ENFORCE| Plan
    Plan --> PGate
    PGate --> Bridge
    Bridge --> Bindings
    Bridge --> Manifest

    Plan --> Show
    Plan --> PlanCmd --> Propact
    Q --> Legacy
    Legacy --> TVal --> Bridge
    Legacy --> PRGate --> Bridge
    Legacy --> Runner
    Runner --> PRGate
    Runner --> SGate --> Bridge
```

## Dwie ścieżki wykonania

### Ścieżka integracji (`show` / `plan`)

Struktura i planowanie — **bez** legacy `ActionRegistry`. Walidacja = Pydantic IR + (opcjonalnie) Intract na `PlanStep`.

```mermaid
sequenceDiagram
    participant U as Użytkownik
    participant S as nlp2dsl show / nlp2cmd plan
    participant I as IntentPipeline
    participant P as PlanningPipeline
    participant G as PlanStepGate
    participant B as RuntimeBridge

    U->>S: NL query
    S->>I: run(query)
    I-->>S: IntentIR
    Note over S: plan: ensure_intent_clear (zawsze)<br/>show: tylko z NLP2CMD_ENFORCE_CLARIFICATION
    S->>P: run(query)
    P-->>S: ExecutionPlanIR
    alt NLP2CMD_INTRACT_GATE=1
        S->>G: check_plan(steps)
        G->>B: resolve contract + check_policy
        B-->>G: GateResult
        G-->>S: contract_check / lub PlanContractViolation
    end
    S-->>U: JSON / Propact markdown
```

### Ścieżka legacy (`-q -r`)

Pełny runtime: generacja → transform → pre-execute gate → wykonanie.

```mermaid
sequenceDiagram
    participant U as Użytkownik
    participant N as NLP2CMD.transform
    participant V as TransformValidator
    participant SV as ShellValidator
    participant IV as IntractValidator
    participant R as PipelineRunner
    participant G as PipelineRunnerGate

    U->>N: NL query
    N->>N: generate_plan + adapter
    alt validator podpięty
        N->>V: validate(command, plan)
        V->>SV: składnia / dangerous patterns
        opt NLP2CMD_INTRACT_GATE=1
            V->>IV: kontrakt intent → DSL
        end
    end
    N->>R: ActionIR
    opt NLP2CMD_INTRACT_GATE=1
        R->>G: check(ActionIR)
        G-->>R: pass / block
    end
    R-->>U: wykonanie shell / DOM
```

## Warstwy walidacji

| Warstwa | Gdzie | Co sprawdza | Czego nie sprawdza |
|---------|-------|-------------|-------------------|
| **Pydantic IR** | `pact-ir` | Struktura `IntentIR` / `ExecutionPlanIR` | Poprawność komendy |
| **Keyword detector** | `nlp2cmd-intent` | `confidence`, `ambiguities` | Wynik w shellu |
| **needs_clarification** | `nlp2cmd plan` | Blokada przy `confidence < 0.5` | — |
| **PlanStepGate** | `plan`, `show --plan` | Kontrakt na `PlanStep.dsl` | stdout |
| **TransformValidator** | `nlp2cmd -q` | ShellValidator + IntractValidator | stdout |
| **PipelineRunnerGate** | legacy execute | `ActionIR` przed shell/DOM | stdout |
| **IntractStepGate** | browser plan | pre/post kroków canvas/DOM | treść strony |

## Bramki Intract (nlp2cmd)

| Klasa | Plik | Hook | Wejście |
|-------|------|------|---------|
| `PlanStepGate` | `intract/plan_gate.py` | `plan_query_via_integration`, `nlp2dsl show --plan` | `PlanStep` + `IntentIR` |
| `IntractValidator` | `intract/validator.py` | `NLP2CMD.transform` via `build_transform_validator` | DSL + plan.intent |
| `PipelineRunnerGate` | `intract/pipeline_gate.py` | `PipelineRunner.run` | `ActionIR` |
| `IntractStepGate` | `intract/step_gate.py` | `plan_executor` browser steps | krok DOM/canvas |

Mapowanie kontraktów: `src/nlp2cmd/data/intract-bindings.json` (generowany z `scripts/generate_intract_manifest.py`).

### Źródła kontraktów

```mermaid
flowchart LR
    AR[ActionRegistry]
    RC[router_config.json]
    DOM[DomActionRegistry]
    HR[HandlerRegistry]
    PIR[pact-ir plan_action<br/>shell_list …]

    GEN[generate_intract_manifest.py]
    YAML[intract.yaml]
    BIND[intract-bindings.json]

    AR --> GEN
    RC --> GEN
    DOM --> GEN
    HR --> GEN
    PIR --> GEN
    GEN --> YAML
    GEN --> BIND
```

Akcje plannera spoza `ActionRegistry` (np. `shell_list`) mają `scope: plan_action` i `registry: pact_ir`.

### Aliasy intencji (keyword → kontrakt)

| Alias detektora | Kontrakt kanoniczny |
|-----------------|---------------------|
| `find`, `search` | `intent.file_search` |
| `ls`, `dir` | `intent.list` |

## Zmienne środowiskowe

| Zmienna | Domyślnie | Efekt |
|---------|-----------|-------|
| `NLP2CMD_INTEGRATION` | `0` | Włącza `nlp2cmd plan` |
| `NLP2CMD_INTRACT_GATE` | `0` | PlanStepGate + TransformValidator + PipelineRunnerGate + IntractStepGate |
| `NLP2CMD_ENFORCE_CLARIFICATION` | `0` | `nlp2dsl show` blokuje niską pewność (`nlp2cmd plan` — zawsze) |
| `NLP2CMD_QUERY_INPUT` | `1` | IntentIR na wejściu `-q` / `-r` / `plan` |

## Przykłady

```bash
export NLP2CMD_INTEGRATION=1
export NLP2CMD_INTRACT_GATE=1

# Plan z contract_check w JSON
nlp2cmd plan "znajdź pliki *.py w src" --json

# Show — contract_check w output (exit 1 przy violations)
nlp2dsl show "znajdź pliki *.py w src" --plan

# Legacy — Intract na transform + pre-execute
nlp2cmd -q "znajdź pliki *.py" -r

# Blokada niejednoznacznego zapytania (show)
export NLP2CMD_ENFORCE_CLARIFICATION=1
nlp2dsl show "xyz"   # exit 2
```

### Przykładowy `contract_check` w JSON

```json
{
  "contract_check": {
    "enabled": true,
    "passed": true,
    "steps": [{
      "step_id": "s1",
      "action": "shell_find",
      "contract_id": "action.shell_find",
      "passed": true,
      "violations": []
    }]
  }
}
```

## Czego Intract nie robi

- Nie porównuje stdout z oczekiwaniem użytkownika.
- Nie zastępuje `ActionRegistry.validate_action()` w ścieżce integracji (plan buduje params z regexów).
- Przy braku mapowania kontraktu gate **pomija** krok (`passed: true`, `skipped: true`) — nie blokuje po cichu destrukcyjnych komend bez kontraktu.

Post-execution validation (stdout vs oczekiwanie) to **osobna warstwa** — zob. [`post-execution-validation.md`](post-execution-validation.md). Włączanie: `NLP2CMD_POST_CHECK=1` po `plan --execute`.

## Regeneracja manifestu

```bash
cd nlp2cmd
python scripts/generate_intract_manifest.py
# → intract.yaml, src/nlp2cmd/data/intract-bindings.json, intract-policy.json
```

## Powiązane repozytoria

| Repo | Rola |
|------|------|
| [nlp2dsl](https://github.com/wronai/nlp2dsl) | `IntentIR`, `ExecutionPlanIR`, `nlp2dsl show` |
| [nlp2cmd](https://github.com/wronai/nlp2cmd) | Runtime, gates, `intract-bindings.json` |
| [intract](https://github.com/semcod/intract) | Silnik kontraktów (`validate_contract_against_source`) |
