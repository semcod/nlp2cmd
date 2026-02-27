# Browser Automation Examples

Kolekcja mniejszych, ukierunkowanych demonstracji funkcji browser automation w nlp2cmd.

## Struktura

| Demo | Opis | Czas |
|------|------|------|
| `01_screenshot_only.sh` | Tylko screenshot (auto-confirm) | ~30s |
| `02_video_only.sh` | Tylko video recording (auto-confirm) | ~30s |
| `03_interactive_mode.sh` | Tryb interaktywny z pytaniami | ~60s |
| `04_oferteo_extraction.sh` | Ekstrakcja firm z Oferteo | ~150s |
| `05_simple_formfill.sh` | Proste wypełnienie formularza | ~20s |
| `06_formfill_with_discovery.sh` | Wypełnienie z auto-discovery | ~40s |
| `07_batch_multiple.sh` | Testowanie wielu stron | ~60s |

## Użycie

```bash
# Pojedynczy demo
./01_screenshot_only.sh

# Wszystkie dema (kolejno)
for demo in *.sh; do
    echo "=== Running: $demo ==="
    ./$demo
    sleep 2
done
```

## Wymagania

- Playwright zainstalowany: `playwright install chromium`
- Środowisko nlp2cmd skonfigurowane
- Dla trybu interaktywnego: terminal z obsługą inputu

## Logi

Wszystkie dema zapisują logi do `/tmp/demo*.log`.

## Wyjścia

- Screenshots: `./screenshots/form_YYYYMMDD_HHMMSS.png`
- Video: `./recordings/form_automation_YYYYMMDD_HHMMSS.webm`
- Oferteo: `oferteo_*.txt`
