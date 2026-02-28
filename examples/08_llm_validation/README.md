# LLM Validation & Repair

Automatic output validation and self-repair for nlp2cmd using local and cloud LLMs.

## Architecture

```
User query → nlp2cmd → Command → Execute → stdout/stderr
                                               ↓
                                    LLM_VALIDATOR (local)
                                    qwen2.5:3b / Ollama
                                    Input: query + command + output
                                    Output: pass/fail + score + reason
                                               ↓
                                        verdict == fail?
                                           ↓ yes
                                    LLM_REPAIR (cloud)
                                    OpenRouter (qwen-2.5-coder-32b)
                                    Input: full context + stdout
                                    Output: improved_command + JSON patches
                                               ↓
                                    Retry with improved command
                                    + patch patterns.json/templates.json
```

## Configuration

```bash
# .env — validator (local, runs after every command)
LLM_VALIDATOR_ENABLED=true
LLM_VALIDATOR_MODEL=qwen2.5:3b
LLM_VALIDATOR_BASE_URL=http://localhost:11434
LLM_VALIDATOR_TIMEOUT=30
LLM_VALIDATOR_TEMPERATURE=0.1

# .env — repair (cloud, runs only on validator FAIL)
LLM_REPAIR_ENABLED=true
LLM_REPAIR_MODEL=qwen/qwen-2.5-coder-32b-instruct
LLM_REPAIR_API_KEY=          # or OPENROUTER_API_KEY
LLM_REPAIR_TIMEOUT=60
```

## Test Suite

```bash
# Run 15 test cases covering pass/fail/edge cases
python3 examples/08_llm_validation/test_validator.py

# Full demo (live nlp2cmd + test suite)
bash examples/08_llm_validation/demo_validation.sh
```

### Test Results (qwen2.5:3b)

| Category | Tests | Pass Rate |
|----------|-------|-----------|
| Correct output → pass | 8 | 100% |
| Error output → fail | 5 | 100% |
| Edge cases (partial, multi) | 2 | 100% |
| **Total** | **15** | **100%** |

## Files

| File | Description |
|------|-------------|
| `test_validator.py` | 15 test cases with automated scoring |
| `demo_validation.sh` | Live demo script |
| `test_results.json` | Last test run results (auto-generated) |
| `README.md` | This file |
