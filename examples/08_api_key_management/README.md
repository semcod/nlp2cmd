# 08 — API Key Management Examples

Przykłady automatycznego zarządzania kluczami API dla różnych providerów.

## Wymagania

```bash
pip install nlp2cmd[browser]
nlp2cmd cache auto-setup  # Playwright browsers
```

## Przykłady

| Przykład | Provider | Co robi |
|----------|----------|---------|
| `01_diagnose_credentials/` | Wszystkie | Sprawdza dostępność haseł i kluczy |
| `02_openrouter_key/` | OpenRouter | Pobiera klucz API z OpenRouter |
| `03_github_token/` | GitHub | Tworzy Personal Access Token |
| `04_huggingface_token/` | HuggingFace | Pobiera HF Token |
| `05_openai_key/` | OpenAI | Pobiera klucz OpenAI |
| `06_multi_provider/` | Wiele | Batch setup wielu providerów naraz |

## Konfiguracja Password Store

```bash
# Automatycznie (domyślne) — czyta hasła z Firefox
NLP2CMD_PASSWORD_BACKEND=auto

# Tylko Firefox
NLP2CMD_PASSWORD_BACKEND=firefox

# KeePassXC
NLP2CMD_PASSWORD_BACKEND=keepassxc
NLP2CMD_KEEPASSXC_DB=/path/to/passwords.kdbx

# Bitwarden
NLP2CMD_PASSWORD_BACKEND=bitwarden
NLP2CMD_BITWARDEN_SESSION=$(bw unlock --raw)

# Env vars (zawsze dostępne jako fallback)
OPENROUTER_EMAIL=user@example.com
OPENROUTER_PASSWORD=secret
```
