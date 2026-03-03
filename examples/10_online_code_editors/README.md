# 10 — Online Code Editors (No Login Required)

Browser automation examples for writing and running code on free online editors.

## Tools Supported

- **CodePen** (codepen.io/pen) — HTML/CSS/JS editor with live preview
- **myCompiler** (mycompiler.io) — 27+ languages (Python, JS, C++, etc.)
- **JSFiddle** (jsfiddle.net) — Front-end code playground

## Examples

### 01 — CodePen: Write HTML/CSS/JS with live preview

```bash
# Generate code from natural language description
python3 01_codepen_live.py --code "hello world page"
python3 01_codepen_live.py --code "interactive button page"

# Use predefined presets
python3 01_codepen_live.py --preset hello
python3 01_codepen_live.py --preset animated_gradient
python3 01_codepen_live.py --preset clock
python3 01_codepen_live.py --preset todo

# Provide custom HTML/CSS/JS
python3 01_codepen_live.py --html "<h1>Test</h1>" --css "h1{color:red}" --js "console.log('ok')"
```

### 02 — myCompiler: Write and run Python/JS code

```bash
python3 02_mycompiler_run.py --lang python --code "print('Hello from NLP2CMD')"
python3 02_mycompiler_run.py --lang javascript --code "console.log(42)"
python3 02_mycompiler_run.py --lang cpp --code "#include<iostream>\nint main(){std::cout<<\"Hello\";}"
```

### 03 — Adaptive code generation with LLM routing

```bash
python3 03_adaptive_code.py --query "napisz program w Pythonie który liczy silnię"
python3 03_adaptive_code.py --query "create a JS function that reverses a string"
python3 03_adaptive_code.py --query "make a C++ program that sorts an array"
```

### 04 — JSFiddle: Frontend code playground

```bash
python3 04_jsfiddle_frontend.py --preset hello
python3 04_jsfiddle_frontend.py --preset particles
python3 04_jsfiddle_frontend.py --preset calculator
```

### 05 — Dynamic executor: Fully LLM-driven (no hardcoded presets)

```bash
# English
python3 05_dynamic_executor.py --prompt "write fibonacci in python" --verbose --headless

# Polish
python3 05_dynamic_executor.py --prompt "napisz program sortujący listę liczb" --headless

# Custom language
python3 05_dynamic_executor.py --prompt "create a factorial calculator" --lang javascript
```

The dynamic executor uses `nlp2cmd.orchestration.Orchestrator` for:
1. **LLM planning** — decomposes prompt into steps dynamically
2. **LLM code generation** — no hardcoded presets
3. **Page-schema-aware injection** — CM5/CM6/Monaco/Ace/textarea
4. **Auto-retry on error** — detects tracebacks, re-generates code
5. **LLM validation** — verifies output matches intent

## Requirements

```bash
pip install playwright
playwright install chromium
```

## Screenshots

All examples automatically save screenshots to the `screenshots/` directory:

- `codepen_*.png` — CodePen editor screenshots
- `codepen_*_preview.png` — Live preview screenshots  
- `mycompiler_*.png` — myCompiler execution screenshots
- `adaptive_code_*.png` — LLM-generated code execution screenshots

## Adaptive Learning Integration

The `LLMRouter` with `AdaptiveLearner` provides intelligent code generation:
1. **Task Classification** — Automatically detects programming language and task type
2. **Model Routing** — Chooses optimal LLM (remote → free → local fallback)
3. **Code Generation** — Generates complete, runnable code from natural language
4. **Adaptive Learning** — Learns which models work best for different tasks
5. **Health Tracking** — Monitors model performance and adapts routing decisions

### Supported Languages (via myCompiler)
- Python, JavaScript, C++, Java, C#, PHP, Ruby, Go, Rust, Swift, Kotlin
- SQL, HTML, CSS, and 15+ more languages

### LLM Model Fallback Chain
- **Remote**: Qwen2.5-Coder-32B, Grok Code Fast, Gemini 2.5 Pro
- **Free**: Arcee Trinity, Qwen2.5-Coder-7B (OpenRouter)
- **Local**: qwen2.5-coder:3b, bielik-1.5b (Ollama)
