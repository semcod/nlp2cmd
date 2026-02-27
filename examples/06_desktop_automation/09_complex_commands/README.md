# 09 — Complex Commands: Multi-Step Automation

Decompose complex natural language commands into multi-step execution plans.

## What it does

1. Parses complex NL command (Polish or English)
2. Matches against template patterns or uses LLM decomposition
3. Generates ordered action steps
4. Executes steps sequentially with Playwright

## Example commands

```bash
# Drawing
nlp2cmd -r "wejdź na jspaint.app i narysuj biedronkę"

# Multi-tab workflow
nlp2cmd -r "otwórz 3 taby: GitHub, Stack Overflow i ChatGPT"

# API key extraction
nlp2cmd -r "wyciągnij klucz API z OpenRouter i zapisz do .env"

# Email automation
nlp2cmd -r "w Thunderbird odpowiedz na ostatniego maila"

# Desktop + browser combo
nlp2cmd -r "otwórz Chrome, wejdź na openrouter.ai, skopiuj API key"
```

## Run

```bash
cd examples/06_desktop_automation/09_complex_commands
python3 run.py --query "wejdź na jspaint.app i narysuj biedronkę"
python3 run.py --query "otwórz przeglądarkę i sprawdź pocztę"
python3 run.py --plan-only --query "narysuj czerwone koło na jspaint.app"
```

## Architecture

```
NL Query → ComplexCommandPlanner → [ActionStep, ActionStep, ...]
                                         ↓
                                   PipelineRunner
                                   (Playwright + xdotool)
```
