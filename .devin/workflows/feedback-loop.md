---
description: Declarative schema-driven feedback loop for browser automation with LLM validation and repair escalation
---

# Feedback Loop Workflow

## Architecture

The feedback loop wraps every browser automation step with validation → diagnosis → repair:

```
Step Schema (declarative)
    ↓
Execute step
    ↓
Validate result (pre/post conditions)
    ↓ failed?
Classify failure:
  - schema_error    → wrong selector/URL in service config
  - handling_error   → code bug, timeout, unexpected state
  - data_error       → user not logged in, no key exists
  - page_state_error → redirect, modal, CAPTCHA
    ↓
Repair escalation chain:
  1. Rule-based (selector alternatives, URL fixes)      ~0ms
  2. Page analysis (DOM scan for correct elements)       ~50ms
  3. Local LLM diagnosis (qwen2.5:3b via Ollama)        ~500ms
  4. Cloud LLM repair (OpenRouter, 32B model)            ~2s
    ↓
Retry with repaired params (max 5 attempts)
```

## Key Principle

**A solution is always found — it's a matter of time, not algorithm limits.**
If local LLM can't diagnose the problem, escalate to a larger cloud model.

## Components

### 1. FeedbackLoop (`src/nlp2cmd/automation/feedback_loop.py`)
- `classify_failure()` — categorizes WHY a step failed
- `diagnose_with_llm()` — uses local/cloud LLM for complex diagnosis
- `generate_repair_params()` — produces fixed parameters

### 2. PageAnalyzer (`src/nlp2cmd/automation/feedback_loop.py`)
- `extract_page_context()` — minimal DOM snapshot for LLM
- `find_api_keys_section()` — generic navigation link scanner
- `find_clickable_for_text()` — DOM-based selector finder

### 3. SchemaFallback (`src/nlp2cmd/automation/schema_fallback.py`)
6-strategy escalation:
1. Rule-based heuristics
2. DOM extraction (key patterns)
3. Page analysis (navigation + selectors)
4. Clipboard check
5. Local LLM re-planning
6. Cloud LLM escalation

### 4. StepValidator (`src/nlp2cmd/automation/step_validator.py`)
Pre/post validation for each step (URL check, clipboard, DOM state).

## Testing

```bash
# Run feedback loop tests (19 cases, 100% accuracy)
// turbo
python3 examples/08_llm_validation/test_feedback_loop.py

# Run validator tests (15 cases, 100% accuracy)
// turbo
python3 examples/08_llm_validation/test_validator.py
```

## Configuration

```bash
# .env
LLM_VALIDATOR_ENABLED=true
LLM_VALIDATOR_MODEL=qwen2.5:3b
LLM_REPAIR_ENABLED=true
LLM_REPAIR_MODEL=qwen/qwen-2.5-coder-32b-instruct
FEEDBACK_LOOP_MAX_RETRIES=5
OPENROUTER_API_KEY=sk-or-...
```

## Adding a New Provider

1. Add service config to `src/nlp2cmd/automation/service_configs.py`
2. Add test case to `test_feedback_loop.py` → `test_multi_provider_classification()`
3. Run tests to verify classification accuracy
