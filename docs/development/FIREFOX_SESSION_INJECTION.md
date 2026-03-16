# Firefox Session Injection do Playwright

## Problem

Playwright uruchamia **izolowaną przeglądarkę** (Chromium/Firefox) z czystym profilem.
To oznacza, że automatyzacja nie ma dostępu do zalogowanych portali użytkownika —
każde zadanie wymaga złożonego logowania (login + hasło + 2FA + email verification).

Dla zadań takich jak:

- Wyciągnij klucz API z OpenRouter i zapisz do `.env`
- Sprawdź status konta na Anthropic
- Pobierz tokeny z GitHub Settings

...jest to blokujące. Użytkownik jest już zalogowany w lokalnym Firefox,
ale Playwright tego nie widzi.

## Rozwiązanie

**Kopiujemy sesje z lokalnego Firefox do izolowanej przeglądarki Playwright.**

Moduł `FirefoxSessionImporter` (`src/nlp2cmd/automation/firefox_sessions.py`):

1. **Wykrywa profil Firefox** automatycznie (Ubuntu: standard, Snap, Flatpak)
2. **Kopiuje pliki sesji** (cookies, localStorage, certyfikaty, loginy)
3. **Obsługuje zablokowane bazy danych** (WAL-safe read gdy Firefox działa)
4. **Uruchamia Playwright** z skopiowanym profilem lub wstrzykuje ciasteczka

```text
┌──────────────────┐     copy session files     ┌────────────────────────┐
│  Firefox (Snap)  │ ─────────────────────────→  │  Playwright Firefox    │
│  zalogowany na:  │   cookies.sqlite            │  (izolowana instancja) │
│  - openrouter.ai │   logins.json               │                        │
│  - github.com    │   storage/                  │  ✓ Zalogowany na:      │
│  - anthropic.com │   cert9.db                  │  - openrouter.ai       │
│  - allegro.pl    │   webappsstore.sqlite       │  - github.com          │
└──────────────────┘                             │  - anthropic.com       │
                                                 └────────────────────────┘
```

## Tryby pracy

### Tryb 1: Chromium + cookie injection (zalecany, domyślny)

```bash
NLP2CMD_USE_FIREFOX_SESSIONS=1 nlp2cmd -r "wyciągnij klucz API z OpenRouter i zapisz do .env"
```

- Czyta `cookies.sqlite` z Firefox (WAL-safe, działa gdy Firefox uruchomiony)
- Uruchamia **Chromium** i wstrzykuje cookies via `context.add_cookies()`
- **Bezpieczny dla SPA** (React, Next.js, Vue) — brak konfliktów localStorage
- Wymaga: `playwright install chromium`
- `=1` i `=cookies` działają identycznie

### Tryb 2: Pełny profil Firefox (eksperymentalny)

```bash
NLP2CMD_USE_FIREFOX_SESSIONS=firefox nlp2cmd -r "otwórz stronę"
```

- Kopiuje cały profil Firefox do `~/.nlp2cmd/firefox_playwright_profile/`
- Uruchamia `pw.firefox.launch_persistent_context()` z tym profilem
- **Wszystkie sesje, cookies, localStorage, certyfikaty** — dostępne
- ⚠️ **UWAGA**: Może crashować SPA (Next.js, React) z powodu konfliktów
  localStorage/IndexedDB między Snap Firefox a Playwright Firefox
- Wymaga: `playwright install firefox`

### Tryb 3: Jawna ścieżka profilu

```bash
NLP2CMD_FIREFOX_PROFILE=~/snap/firefox/common/.mozilla/firefox/abc123.default-release \
NLP2CMD_USE_FIREFOX_SESSIONS=1 nlp2cmd -r "..."
```

### Automatyczny fallback

Jeśli `NLP2CMD_USE_FIREFOX_SESSIONS=1` ale Playwright Firefox nie jest zainstalowany:

```text
⚠ Playwright Firefox nie zainstalowany (uruchom: playwright install firefox)
  ↳ Fallback: Chromium + wstrzykiwanie ciasteczek Firefox
🦊 Wstrzyknięto 1781 ciasteczek Firefox do Chromium
```

System automatycznie przełącza się na Chromium + cookie injection.

## Zmienne środowiskowe

| Zmienna | Wartości | Opis |
|---------|----------|------|
| `NLP2CMD_USE_FIREFOX_SESSIONS` | `1` | Chromium + Firefox cookie injection (zalecany) |
| `NLP2CMD_USE_FIREFOX_SESSIONS` | `cookies` | Identycznie jak `1` |
| `NLP2CMD_USE_FIREFOX_SESSIONS` | `firefox` | Pełny profil Firefox (eksperymentalny, SPA crash!) |
| `NLP2CMD_USE_FIREFOX_SESSIONS` | *(puste/brak)* | Domyślne: czysty Chromium |
| `NLP2CMD_FIREFOX_PROFILE` | `/ścieżka/do/profilu` | Jawna ścieżka do profilu Firefox |

## Wykrywanie profilu na Ubuntu

Moduł przeszukuje standardowe lokalizacje:

| Instalacja | Ścieżka |
|------------|---------|
| **Standard** (apt) | `~/.mozilla/firefox/` |
| **Snap** (domyślna Ubuntu 22+) | `~/snap/firefox/common/.mozilla/firefox/` |
| **Flatpak** | `~/.var/app/org.mozilla.firefox/.mozilla/firefox/` |

Kolejność wykrywania profilu:

1. `profiles.ini` → sekcja z `Default=1`
2. Katalog z `default-release` w nazwie
3. Dowolny katalog z `cookies.sqlite`

## Pliki sesji kopiowane z Firefox

| Plik | Zawartość |
|------|-----------|
| `cookies.sqlite` (+wal) | Ciasteczka wszystkich stron |
| `logins.json` | Zapisane hasła (zaszyfrowane) |
| `key4.db` | Klucze szyfrowania haseł |
| `cert9.db` | Certyfikaty SSL |
| `webappsstore.sqlite` | localStorage |
| `permissions.sqlite` | Uprawnienia stron |
| `formhistory.sqlite` | Historia formularzy |
| `storage/` | IndexedDB, cache API |
| `sessionstore.jsonlz4` | Otwarte karty |

## Kompatybilność z SPA

⚠️ **Pełny profil Firefox (`=firefox`) crashuje strony SPA** jak OpenRouter, GitHub, Anthropic.

Przyczyna: localStorage/IndexedDB/service workers z profilu Snap Firefox są
niekompatybilne z wersją Firefox w Playwright. Strona wyświetla:
`"Application error: a client-side exception has occurred"`.

**Rozwiązanie**: Tryb `=1` (Chromium + cookies) jest bezpieczny — wstrzykuje
tylko ciasteczka, które wystarczają do utrzymania sesji logowania.
LocalStorage nie jest potrzebny do autentykacji.

| Tryb | SPA-safe | localStorage | cookies | Zalecany |
|------|----------|-------------|---------|----------|
| `=1` / `=cookies` | ✅ | ❌ | ✅ | **Tak** |
| `=firefox` | ❌ | ✅ | ✅ | Nie (crashuje SPA) |

## Bezpieczeństwo

- **Kopia, nie oryginał** — profil Firefox jest kopiowany do oddzielnego katalogu.
  Oryginalny Firefox działa normalnie.
- **Pliki blokady** (`lock`, `.parentlock`) są usuwane z kopii, aby Playwright mógł
  otworzyć profil.
- **Świeżość** — kopia jest odświeżana co 24h (konfigurowalne `max_age_hours`).
  Marker: `~/.nlp2cmd/firefox_playwright_profile/.nlp2cmd_session_copied`
- **WAL-safe** — czytanie `cookies.sqlite` odbywa się na kopii w `/tmp`,
  nie blokuje działającego Firefox.

## Diagnostyka

```python
from nlp2cmd.automation.firefox_sessions import FirefoxSessionImporter

importer = FirefoxSessionImporter()
diag = importer.diagnose()

# diag = {
#   "detected_profile": "/home/tom/snap/firefox/common/.mozilla/firefox/fk8ne2tm.default-1742302987775",
#   "cookie_count": 1781,
#   "cookie_domains": [".anthropic.com", ".github.com", ".openrouter.ai", ...],
#   "session_files": {"cookies.sqlite": {"exists": true, "size": 1048576}, ...}
# }
```

## Instalacja wymaganych zależności

```bash
# Playwright + Firefox browser
pip install playwright
playwright install firefox

# LUB tylko Chromium (wystarczy dla trybu cookies)
playwright install chromium
```

## Architektura w nlp2cmd

```text
┌─────────────────────────────────────────────────────┐
│  nlp2cmd -r "wyciągnij klucz z OpenRouter"          │
│                                                     │
│  1. ActionPlanner → plan 10 kroków                  │
│     navigate → check_session → extract_key → ...    │
│                                                     │
│  2. FirefoxSessionImporter                          │
│     detect profile → copy sessions → cleanup locks  │
│                                                     │
│  3. Playwright Firefox launch_persistent_context     │
│     (z skopiowanym profilem = zalogowane sesje)     │
│                                                     │
│  4. StepValidator (pre/post walidacja)              │
│     check_session → "logged_in" ✓                   │
│     extract_key → DOM scan → clipboard → regex      │
│                                                     │
│  5. SchemaFallback (jeśli krok fail)                │
│     rule-based → DOM extraction → clipboard →       │
│     LLM re-planning via Ollama                      │
│                                                     │
│  6. save_env → .env + verify_env                    │
└─────────────────────────────────────────────────────┘
```

## Co chcemy osiągnąć

### Cel główny

Automatyzacja zadań w przeglądarce **bez potrzeby logowania** —
Playwright korzysta z istniejących sesji użytkownika z Firefox.

### Rozwiązywane problemy

1. **Brak sesji w izolowanej przeglądarce** — kopiowanie profilu Firefox
2. **Firefox zablokowany (WAL lock)** — bezpieczne czytanie przez kopię do `/tmp`
3. **Snap Firefox na Ubuntu** — wykrywanie niestandardowej ścieżki profilu
4. **Brak Playwright Firefox binary** — automatyczny fallback do Chromium + cookies
5. **Walidacja kroków** — StepValidator sprawdza czy check_session zwróciło "logged_in"
6. **Dynamiczny fallback** — SchemaFallback generuje alternatywne kroki gdy coś fail

### Docelowy przepływ (end-to-end)

```text
Użytkownik:  nlp2cmd -r "wyciągnij klucz API z OpenRouter i zapisz do .env"

1. [ActionPlanner]    → 10-krokowy plan (navigate, check_session, extract_key, ...)
2. [SessionImporter]  → kopiuje sesje z Firefox Snap
3. [Playwright FF]    → otwiera https://openrouter.ai/settings/keys
4. [check_session]    → "logged_in" ✓ (dzięki skopiowanym cookies!)
5. [extract_key]      → skanuje DOM → znajduje klucz sk-or-v1-...
6. [save_env]         → zapisuje OPENROUTER_API_KEY="sk-or-v1-..." do .env
7. [verify_env]       → potwierdza zapis ✓

Rezultat: Klucz API wyekstrahowany i zapisany bez interakcji użytkownika.
```
