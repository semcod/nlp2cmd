---
description: Inteligentna, deklaratywna pętla zwrotna dla workflow API key na wielu SaaS
---

# Cel

Zautomatyzować pobieranie/tworzenie kluczy API bez podawania pełnych linków,
z adaptacją do różnych paneli SaaS i diagnostyką błędów w trakcie wykonania.

## 1) Zbuduj plan deklaratywny (bez twardego „kliknij X i koniec”)

Ustaw tryb generyczny (LLM-driven):

```bash
export NLP2CMD_DYNAMIC_SCHEMA_ONLY=1
export NLP2CMD_LLM_SCHEMA_MODE=llm_first
export NLP2CMD_LLM_REPLAN_ROUNDS=2
```

1. Ustal usługę (provider) i cel (`keys`/`tokens`) z zapytania.
2. Utwórz kroki wysokiego poziomu:
   - `navigate` (na `keys_url` lub `base_url`)
   - `discover_service_section` (dynamiczne odnalezienie sekcji kluczy)
   - `check_session`
   - `extract_key` / fallback `create_key`
   - `check_clipboard`
   - `prompt_secret` (tylko gdy brak klucza)
   - `save_env` + `verify_env`
3. Każdy krok musi mieć:
   - pre-condition,
   - post-condition,
   - fallback policy,
   - `store_as` (jeśli krok produkuje dane).

## 2) Uruchom pętlę zwrotną (evaluate -> diagnose -> adapt)

Dla każdego kroku:

1. Wykonaj pre-check.
2. Wykonaj akcję.
3. Wykonaj post-check.
4. Jeśli post-check nie przejdzie:
   - sklasyfikuj przyczynę:
     - `schema_definition_error` (zły selector/założenie o UI),
     - `schema_execution_error` (timeout, detach, zamknięta karta),
     - `schema_data_error` (brak danych wejściowych/niezgodny pattern).
   - uruchom fallback zależny od klasy błędu.

## 3) Dynamiczne wyszukiwanie sekcji kluczy (provider-agnostic)

1. Jeśli `keys_url` działa: użyj i zweryfikuj.
2. Jeśli redirect/ochrona/zmiana UI:
   - przeskanuj linki (`a[href]`) i oceń je po słowach-kluczach
     (`api`, `key`, `token`, `secret`, `credential`, `ustawienia`, itd.).
   - spróbuj kandydatów z heurystyk ścieżek:
     `/settings/tokens`, `/settings/keys`, `/account/api-tokens`, `/api-keys`, itd.
3. Zapisz wynik jako `resolved_keys_url` i kontynuuj plan od tej sekcji.

## 4) Zasady fallbacków

1. `navigate` mismatch -> `discover_service_section`.
2. `extract_key` fail -> `dismiss_overlay` -> `discover_service_section` -> create flow.
3. `save_env` fail przy pustym `$api_key` -> fallback do `extracted_key` / `clipboard_key`.
4. `prompt_secret` uruchamiaj tylko, gdy nie ma klucza w `variables` ani `os.environ`.

## 5) Kryteria zakończenia

Workflow jest sukcesem, jeśli:

1. klucz został znaleziony lub utworzony,
2. zapisany do `.env`,
3. `verify_env` potwierdza obecność i niepustą wartość.

## 6) Minimalny zestaw testów regresyjnych

1. Plan zawiera `discover_service_section` dla workflow API-key.
2. Fallback `navigate` wstrzykuje `discover_service_section`.
3. Fallback `extract_key` zawiera odkrywanie sekcji przed create flow.
4. `prompt_secret` jest pomijany, gdy klucz już jest dostępny.
5. `save_env` korzysta z fallback wartości (`extracted_key`/`clipboard_key`) gdy `$api_key` puste.

## 7) Uruchomienie testów

```bash
python -m pytest tests/unit/test_api_key_workflow.py tests/unit/test_schema_fallback.py -q
```

Przykład uruchomienia (generyczny workflow bez ręcznych template create-flow):

```bash
NLP2CMD_DYNAMIC_SCHEMA_ONLY=1 \
NLP2CMD_LLM_SCHEMA_MODE=llm_first \
NLP2CMD_LLM_REPLAN_ROUNDS=2 \
NLP2CMD_USE_FIREFOX_SESSIONS=1 \
nlp2cmd -r "otwórz tab w firefox wyciągnij klucz API z HuggingFace i zapisz do .env"
```
