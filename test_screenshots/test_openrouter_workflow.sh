#!/bin/bash
#
# Test OpenRouter API Key Workflow
# Testuje pełny proces: otwarcie Firefox, pobranie klucza, zapisanie do .env
#

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$SCRIPT_DIR/workflow_test.log"
SCREENSHOTS_DIR="$SCRIPT_DIR/workflow_screenshots"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $*" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $*" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[✗]${NC} $*" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $*" | tee -a "$LOG_FILE"
}

# Initialize
rm -f "$LOG_FILE"
mkdir -p "$SCREENSHOTS_DIR"

log "========================================="
log "OpenRouter API Key Workflow Test"
log "========================================="
log "Czas rozpoczęcia: $(date)"
log "Projekt: $PROJECT_ROOT"
log ""

# Step 1: Sprawdź czy Firefox jest uruchomiony
log "Krok 1: Sprawdzanie czy Firefox jest uruchomiony..."
if pgrep -x firefox > /dev/null; then
    log_success "Firefox jest uruchomiony"
    FIREFOX_RUNNING=true
else
    log_warning "Firefox nie jest uruchomiony - zostanie otwarty"
    FIREFOX_RUNNING=false
fi

# Step 2: Zrób zrzut ekranu przed rozpoczęciem
log ""
log "Krok 2: Zrzut ekranu stanu początkowego..."
SCREENSHOT_BEFORE="$SCREENSHOTS_DIR/01_before_$(date +%Y%m%d_%H%M%S).png"
if scrot "$SCREENSHOT_BEFORE" 2>/dev/null; then
    log_success "Zrzut zapisany: $SCREENSHOT_BEFORE"
else
    log_warning "Nie udało się zrobić zrzutu ekranu"
fi

# Step 3: Backup .env
log ""
log "Krok 3: Backup pliku .env..."
if [ -f "$PROJECT_ROOT/.env" ]; then
    cp "$PROJECT_ROOT/.env" "$PROJECT_ROOT/.env.backup.$(date +%Y%m%d_%H%M%S)"
    log_success "Backup utworzony"
    OPENROUTER_BEFORE=$(grep "^OPENROUTER_API_KEY=" "$PROJECT_ROOT/.env" 2>/dev/null || echo "")
    if [ -n "$OPENROUTER_BEFORE" ]; then
        log "Obecna wartość: $OPENROUTER_BEFORE"
    fi
else
    log_warning "Plik .env nie istnieje"
fi

# Step 4: Uruchom nlp2cmd
log ""
log "Krok 4: Uruchamianie nlp2cmd..."
log "Komenda: nlp2cmd -r \"otwórz tab w już otwartym oknie przegladarki firefox wyciągnij klucz API z OpenRouter i zapisz do .env\""

# Zrób zrzut przed wykonaniem
sleep 1
SCREENSHOT_DURING="$SCREENSHOTS_DIR/02_during_$(date +%Y%m%d_%H%M%S).png"
scrot "$SCREENSHOT_DURING" 2>/dev/null || true

# Execute nlp2cmd (symulacja - w prawdziwym teście trzeba ręcznie wprowadzić klucz)
log ""
log_warning "UWAGA: Ten test wymaga ręcznej interakcji!"
log_warning "Po uruchomieniu nlp2cmd:"
log_warning "  1. Firefox otworzy nową kartę"
log_warning "  2. Przejdź do https://openrouter.ai/keys"
log_warning "  3. Skopiuj klucz API"
log_warning "  4. Wklej gdy zostaniesz zapytany"
log ""
log "Naciśnij Enter aby kontynuować lub Ctrl+C aby anulować..."
read -r

# Run the actual command
cd "$PROJECT_ROOT"
START_TIME=$(date +%s)
./venv/bin/nlp2cmd -r "otwórz tab w już otwartym oknie przegladarki firefox wyciągnij klucz API z OpenRouter i zapisz do .env"
EXIT_CODE=$?
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# Step 5: Zrzut po wykonaniu
log ""
log "Krok 5: Zrzut ekranu po wykonaniu..."
sleep 1
SCREENSHOT_AFTER="$SCREENSHOTS_DIR/03_after_$(date +%Y%m%d_%H%M%S).png"
scrot "$SCREENSHOT_AFTER" 2>/dev/null || true
log_success "Zrzut zapisany: $SCREENSHOT_AFTER"

# Step 6: Weryfikacja wyniku
log ""
log "Krok 6: Weryfikacja wyniku..."
log "Kod wyjścia nlp2cmd: $EXIT_CODE"
log "Czas wykonania: ${DURATION}s"

if [ $EXIT_CODE -eq 0 ]; then
    log_success "nlp2cmd zakończył się sukcesem"
else
    log_error "nlp2cmd zakończył się błędem (exit code: $EXIT_CODE)"
fi

# Step 7: Sprawdź czy klucz został zapisany
log ""
log "Krok 7: Sprawdzanie czy klucz został zapisany do .env..."

if [ -f "$PROJECT_ROOT/.env" ]; then
    OPENROUTER_AFTER=$(grep "^OPENROUTER_API_KEY=" "$PROJECT_ROOT/.env" 2>/dev/null || echo "")
    
    if [ -n "$OPENROUTER_AFTER" ]; then
        log_success "Znaleziono OPENROUTER_API_KEY w .env"
        log "Wartość: $OPENROUTER_AFTER"
        
        # Sprawdź czy się zmieniła
        if [ "$OPENROUTER_BEFORE" != "$OPENROUTER_AFTER" ]; then
            log_success "Klucz został zaktualizowany"
        else
            log_warning "Klucz nie zmienił się"
        fi
        
        # Wyciągnij samą wartość (bez cudzysłowów)
        API_KEY=$(echo "$OPENROUTER_AFTER" | cut -d'=' -f2 | tr -d '"')
        
        if [ ${#API_KEY} -gt 10 ]; then
            log_success "Długość klucza: ${#API_KEY} znaków (poprawna)"
        else
            log_error "Długość klucza: ${#API_KEY} znaków (podejrzanie krótka)"
        fi
    else
        log_error "OPENROUTER_API_KEY nie znaleziony w .env"
    fi
else
    log_error "Plik .env nie istnieje"
fi

# Step 8: Test weryfikacyjny (opcjonalny)
log ""
log "Krok 8: Test weryfikacyjny klucza API..."
if [ -n "$API_KEY" ] && [ "$API_KEY" != "sk-test" ]; then
    log "Testowanie klucza poprzez API OpenRouter..."
    
    # Simple API test
    TEST_RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X POST https://openrouter.ai/api/v1/chat/completions \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d '{
            "model": "openai/gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "test"}],
            "max_tokens": 5
        }' 2>/dev/null || echo "000")
    
    HTTP_CODE=$(echo "$TEST_RESPONSE" | tail -1)
    
    if [ "$HTTP_CODE" = "200" ]; then
        log_success "Klucz API działa poprawnie (HTTP 200)"
    elif [ "$HTTP_CODE" = "401" ]; then
        log_error "Klucz API nieprawidłowy (HTTP 401 Unauthorized)"
    elif [ "$HTTP_CODE" = "000" ]; then
        log_warning "Nie udało się przetestować klucza (brak połączenia)"
    else
        log_warning "Nieoczekiwany kod odpowiedzi: $HTTP_CODE"
    fi
else
    log_warning "Pomijam test API (klucz testowy lub brak klucza)"
fi

# Step 9: Analiza zrzutów ekranu
log ""
log "Krok 9: Analiza zrzutów ekranu..."
SCREENSHOT_COUNT=$(ls -1 "$SCREENSHOTS_DIR"/*.png 2>/dev/null | wc -l)
log "Liczba zrzutów: $SCREENSHOT_COUNT"

if [ $SCREENSHOT_COUNT -gt 0 ]; then
    log_success "Zrzuty ekranu zapisane w: $SCREENSHOTS_DIR"
    ls -lh "$SCREENSHOTS_DIR"/*.png | while read -r line; do
        log "  $line"
    done
fi

# Final summary
log ""
log "========================================="
log "PODSUMOWANIE TESTU"
log "========================================="
log "Czas trwania: ${DURATION}s"
log "Zrzuty ekranu: $SCREENSHOT_COUNT"
log "Exit code: $EXIT_CODE"

if [ $EXIT_CODE -eq 0 ] && [ -n "$OPENROUTER_AFTER" ]; then
    log_success "TEST ZAKOŃCZONY SUKCESEM ✓"
    exit 0
else
    log_error "TEST ZAKOŃCZONY NIEPOWODZENIEM ✗"
    exit 1
fi
