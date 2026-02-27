# 06 — API Key Extraction: Browser → .env

Extract API keys from authenticated browser sessions and save to .env files.

## What it does

1. Opens browser with persistent context (preserves login)
2. Navigates to OpenRouter API keys page
3. Extracts API key via DOM selectors / regex / LLM OCR
4. Saves to `.env` file with correct variable name

## Supported services

- OpenRouter (`OPENROUTER_API_KEY`)
- Anthropic (`ANTHROPIC_API_KEY`)
- OpenAI (`OPENAI_API_KEY`)
- GitHub (`GITHUB_TOKEN`)
- Hugging Face (`HF_TOKEN`)

## Run

```bash
# Interactive — opens browser for login if needed
cd examples/06_desktop_automation/06_env_extract
python3 run.py --service openrouter --env-path .env

# Or via nlp2cmd CLI
nlp2cmd -r "wyciągnij klucz API z OpenRouter i zapisz do .env"
```

## Notes

- First run requires manual login in the browser window
- Subsequent runs reuse the saved session from `~/.nlp2cmd/browser_profile/`
- Keys are saved with file permissions 600 (owner-only)
- Existing keys in .env are updated, not duplicated
