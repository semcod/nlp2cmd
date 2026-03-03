# Config — LLM Router Configuration

Multi-model LLM routing with fallbacks, specialization, and priority for NLP2CMD.

## Files

| File | Description |
|------|-------------|
| `litellm_config.yaml` | LiteLLM Router config — model deployments, fallback chains, semantic routes |

## Architecture

```
User prompt
    ↓
classify_task()  — keyword-based PL+EN task classifier
    ↓
┌─────────────────────────────────────────────────────┐
│  LiteLLM Router (latency-based-routing)             │
│                                                     │
│  Model Group: vision / coding / text / polish / ... │
│  ┌───────────┐  ┌───────────┐  ┌──────────────┐    │
│  │ Remote    │→ │ Remote    │→ │ Local Ollama │    │
│  │ (paid)    │  │ (free)    │  │ (fallback)   │    │
│  └───────────┘  └───────────┘  └──────────────┘    │
│                                                     │
│  Fallback chains: text→fast, coding→text→fast, ...  │
└─────────────────────────────────────────────────────┘
    ↓
RouterResponse (content, model, task, latency, usage)
```

## Task Categories (8 specializations)

| Task | Purpose | Remote (paid) | Remote (free) | Local Ollama |
|------|---------|---------------|---------------|--------------|
| **vision** | Image analysis, CAPTCHA, OCR | Gemini 2.5 Pro | Qwen2.5-VL-7B | qwen2.5vl:7b → llava:7b |
| **coding** | Code/SQL/Docker/K8s generation | Qwen2.5-Coder-32B | Qwen2.5-Coder-7B | qwen2.5-coder:7b → :3b |
| **text** | General text, Q&A | Grok Code Fast | Arcee Trinity | qwen2.5:7b → :3b |
| **polish** | Polish language tasks | Grok | — | Bielik 11B → 1.5B |
| **repair** | Fix failed commands | Qwen2.5-Coder-32B | Arcee Trinity | qwen2.5-coder:7b |
| **validation** | Validate command output | — | — | qwen2.5:3b → :7b |
| **fast** | Quick lightweight tasks | — | — | qwen2.5:3b → deepseek-r1:1.5b |
| **planning** | Multi-step decomposition | Gemini 2.5 Pro | — | qwen2.5:14b → :7b |

## Fallback Strategy

**Priority order**: paid remote → free remote → local Ollama

When a model fails (timeout, 402 credits depleted, 500 error), the router automatically tries the next deployment in the group. If all deployments in a group fail, the fallback chain kicks in:

```
vision  → coding → text → fast
coding  → text → fast
text    → fast
repair  → coding → text → fast
planning → coding → text → fast
polish  → text → fast
```

This ensures that even with zero API credits, all tasks still work via local Ollama models.

## Configuration

### litellm_config.yaml

```yaml
model_list:
  - model_name: vision                          # task category
    litellm_params:
      model: openrouter/google/gemini-2.5-pro-preview  # LiteLLM model ID
      api_key: os.environ/OPENROUTER_API_KEY    # auto-resolved from .env
      api_base: https://openrouter.ai/api/v1
      max_tokens: 4096
      rpm: 10                                   # rate limits for load balancing
      tpm: 100000
    model_info:
      description: "Best vision model"
      supports_vision: true
      priority: 1                               # lower = higher priority

router_settings:
  routing_strategy: "latency-based-routing"     # or: least-busy, simple-shuffle
  num_retries: 3
  timeout: 60
  cooldown_time: 30

litellm_settings:
  fallbacks:
    - vision: ["coding", "text", "fast"]
    - text: ["fast"]
```

### Environment Variables

Set in `.env` or system environment:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | — | API key for remote models via OpenRouter |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Local Ollama endpoint |
| `NLP2CMD_ROUTER_CONFIG` | auto-detected | Path to `litellm_config.yaml` |
| `NLP2CMD_ROUTER_STRATEGY` | `latency-based-routing` | Routing strategy override |
| `NLP2CMD_ROUTER_VERBOSE` | `false` | Enable verbose router logging |

### Routing Strategies

| Strategy | Description |
|----------|-------------|
| `latency-based-routing` | Prefer the fastest responding deployment (default) |
| `least-busy` | Route to the deployment with fewest active requests |
| `simple-shuffle` | Random distribution across deployments |
| `usage-based-routing` | Balance by token usage (rpm/tpm) |

## Usage

### Python API

```python
from nlp2cmd.llm.router import LLMRouter

router = LLMRouter()

# Explicit task
resp = await router.completion("Write SQL for users", task="coding")

# Auto-classified from prompt
resp = await router.auto_completion("opisz zrzut ekranu")
# → task=vision, routes to Gemini/Qwen-VL/LLaVA

# Vision (always routes to vision models)
resp = await router.vision(image_b64, "What color is this?")

# Check health
print(router.get_stats())
print(router.get_health())
```

### Singleton

```python
from nlp2cmd.llm.router import get_router, reset_router

router = get_router()          # creates once, returns same instance
resp = await router.completion("hello", task="fast")

reset_router()                 # recreate after config change
```

### Without LiteLLM

The router works even without `litellm` installed — it falls back to direct HTTP calls to OpenRouter and Ollama:

```python
# No litellm needed — direct httpx calls
router = LLMRouter()
print(router.is_ready)  # False (no LiteLLM), but still functional
resp = await router.completion("hello", task="fast")  # → Ollama direct
```

## Semantic Auto-Routing

The config includes route definitions with example utterances. When using LiteLLM's auto-router, prompts are matched against these utterances using embedding similarity:

```yaml
routes:
  - route_name: "vision-tasks"
    utterances:
      - "describe this image"
      - "opisz zrzut ekranu"
    model: "vision"
    threshold: 0.75
```

## Adding a New Model

1. Add a deployment to `litellm_config.yaml` under the appropriate `model_name`:
   ```yaml
   - model_name: coding
     litellm_params:
       model: ollama/codellama:7b
       api_base: http://localhost:11434
       max_tokens: 4096
     model_info:
       description: "CodeLlama 7B — local coding alternative"
       priority: 5
   ```

2. Pull the model: `ollama pull codellama:7b`

3. Reset the router: `reset_router()` or restart the service.

## Required Ollama Models

Minimum set for local fallback:

```bash
ollama pull qwen2.5:3b           # fast, validation
ollama pull qwen2.5:7b           # text, planning
ollama pull qwen2.5-coder:7b     # coding, repair
ollama pull qwen2.5vl:7b         # vision (Qwen2.5-VL)
ollama pull bielik-1.5b           # polish
```

Optional larger models:

```bash
ollama pull qwen2.5:14b          # better planning
ollama pull qwen2.5-coder:14b    # better coding
ollama pull SpeakLeash/bielik-11b-v2.3-instruct:Q8_0  # better polish
ollama pull llava:13b             # better vision
```

## Tests

```bash
# Unit tests (36 tests, no network needed)
.venv/bin/python -m pytest tests/unit/test_llm_router.py -v

# Integration tests (requires Ollama running)
.venv/bin/python -m pytest tests/integration/test_llm_router_live.py -v -s
```
