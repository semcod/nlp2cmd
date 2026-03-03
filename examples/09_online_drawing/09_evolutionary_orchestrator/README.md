# 09_evolutionary_orchestrator - "Never Give Up" Engine

Demonstracja autonomicznego silnika ewolucyjnego, który nigdy nie poddaje się bez próby naprawy błędów.

## Architektura

```
┌─────────────────────────────────────────────────────────────┐
│              EvolutionaryOrchestrator                        │
├─────────────────────────────────────────────────────────────┤
│  1. Detect Error → Classify → Select Recovery Strategy       │
│  2. Consult LLM → Get Strategy Recommendation              │
│  3. Execute Recovery → Retry Execution                     │
│  4. Learn → Store Success/Failure Pattern                  │
│  5. Escalate → Cloud LLM for Complex Cases                   │
└─────────────────────────────────────────────────────────────┘
```

## Strategie Naprawy (RecoveryStrategy)

| Strategia | Kiedy używana |
|-----------|---------------|
| `INSTALL_DEPENDENCY` | Brakujące moduły (playwright, itp.) |
| `SWITCH_FALLBACK` | Problemy z HF_TOKEN, rate limits |
| `CONFIGURE_ENV` | Brakujące zmienne środowiskowe |
| `RETRY_WITH_DELAY` | Timeouty, problemy sieciowe |
| `MODIFY_ARGS` | Nieprawidłowe argumenty CLI |
| `CONSULT_LLM` | Głęboka konsultacja z LLM |
| `FALLBACK_LOCAL_MODEL` | Rate limits na API |
| `USE_ALTERNATIVE_SITE` | Problemy z konkretnym site'em |
| `ESCALATE_TO_CLOUD` | Po wielu nieudanych próbach |

## Użycie

```bash
# Lista scenariuszy
python3 run.py --list

# Normalne wykonanie
python3 run.py --scenario success

# Symulacja braku zależności (pokaże recovery)
python3 run.py --scenario dependency_error

# Symulacja timeoutu
python3 run.py --scenario timeout

# Symulacja braku HF_TOKEN
python3 run.py --scenario hf_token_error

# Porównanie: z vs bez orchestratora
python3 run.py --scenario dependency_error --compare

# Wyłączenie orchestratora (pokaże jak wygląda błąd bez recovery)
python3 run.py --scenario dependency_error --no-orchestrator
```

## Przykładowe Wyjście

```
[italic]Scenariusz: dependency_error[/italic]
[dim]Symuluje brak zależności (ModuleNotFoundError)[/dim]

[yellow]Używam EvolutionaryOrchestrator...[/yellow]

🚀 Attempt 1/3
   ✗ Error: RuntimeError: ModuleNotFoundError: No module named 'playwright'
🤖 Consulting LLM for recovery strategy...
   LLM suggests: install_dependency
   Reasoning: Missing dependency should be installed
🔧 Executing recovery: install_dependency
   Installing missing dependencies...
   ✓ Dependencies installed
   ✓ Recovery successful, retrying...

🚀 Attempt 2/3
   → Wykonanie zakończone sukcesem

Execution Report
┌──────────────────┬────────┐
│ Metric           │ Value  │
├──────────────────┼────────┤
│ Success          │ ✅ Yes │
│ Attempts         │ 2      │
│ Recovery Count   │ 1      │
│ Duration         │ 3450ms │
└──────────────────┴────────┘
```

## Baza Wiedzy

Orchestrator uczy się z każdego wykonania i zapisuje wiedzę do:
```
~/.nlp2cmd/evolutionary_learning.json
```

Struktura:
```json
{
  "error_patterns": {
    "RuntimeError": {
      "install_dependency": {"attempts": 5, "successes": 5},
      "retry_with_delay": {"attempts": 2, "successes": 1}
    }
  },
  "execution_history": [...],
  "llm_insights": [...]
}
```

## Klasy Główne

### EvolutionaryRecoveryEngine
```python
engine = EvolutionaryRecoveryEngine(console=console)

success, result, metrics = await engine.execute_with_evolutionary_recovery(
    func=your_async_function,
    context={"key": "value"},
    max_attempts=5,
)
```

### AutonomousExampleRunner
```python
runner = AutonomousExampleRunner(console=console)

success, metrics = await runner.run_example(
    scenario_id="drawing_test",
    script_path=Path("03_adaptive/run.py"),
    args=["--query", "blue circle", "--headless"],
    env_setup={"OLLAMA_BASE_URL": "http://localhost:11434"},
)
```

## Integracja z Istniejącymi Przykładami

Zamiast bezpośredniego wykonywania:
```bash
python3 03_adaptive/run.py --query "blue circle"
```

Użyj orchestratora:
```python
runner = AutonomousExampleRunner()
success, metrics = await runner.run_example(
    scenario_id="adaptive_blue_circle",
    script_path=Path("03_adaptive/run.py"),
    args=["--query", "blue circle", "--headless"],
    env_setup={},
)
```

Orchestrator automatycznie obsłuży:
- Brakujące zależności (zainstaluje playwright)
- Timeouty (z retry i exponential backoff)
- Brak HF_TOKEN (przełączy na lokalne modele)
- Rate limiting (fallback do darmowych modeli)

## Metryki

Po każdym wykonaniu dostępne są metryki:
- `metrics.success` — czy udało się ostatecznie
- `metrics.attempts` — liczba prób
- `metrics.recovery_count` — liczba operacji naprawy
- `metrics.duration_ms` — całkowity czas
- `metrics.recovery_attempts` — szczegóły każdej próby recovery
