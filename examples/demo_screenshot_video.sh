#!/bin/bash
# Demonstracja funkcjonalności screenshot i video recording + ekstrakcja Oferteo
# Użycie: ./demo_screenshot_video.sh

set -e

echo "=========================================="
echo "DEMO: Screenshot + Video + Oferteo extraction"
echo "=========================================="
echo ""

# Konfiguracja
RESULTS_DIR="./demo_results"
mkdir -p "$RESULTS_DIR/screenshots"
mkdir -p "$RESULTS_DIR/recordings"

echo "1. FORMFILL Z SCREENSHOT (auto-confirm)"
echo "   Strona: brainbox.com.pl"
echo "   Oczekiwane: formularz wypełniony, screenshot zapisany"
echo "   ----------------------------------------"
python3 -m nlp2cmd -r -q "Znajdź i wypełnij formularz kontaktowy na https://www.brainbox.com.pl" --auto-confirm 2>&1 | tee "$RESULTS_DIR/brainbox_auto.log"
echo ""

echo "2. FORMFILL Z VIDEO RECORDING (auto-confirm)"
echo "   Strona: axsoft.pl"  
echo "   Oczekiwane: nagranie video zapisane w ./recordings/"
echo "   ----------------------------------------"
python3 -m nlp2cmd -r -q "Znajdź i wypełnij formularz kontaktowy na https://www.axsoft.pl" --auto-confirm 2>&1 | tee "$RESULTS_DIR/axsoft_video.log"
echo ""

echo "3. EKSTRAKCJA OFERTEO (auto-confirm)"
echo "   Zapytanie: firmy budowlane Gdańsk"
echo "   Oczekiwane: 20 firm zapisanych do pliku"
echo "   ----------------------------------------"
python3 -m nlp2cmd -r -q "Wyszukaj firmy budowlane w Gdańsku na oferteo.pl i zapisz do pliku" --auto-confirm 2>&1 | tee "$RESULTS_DIR/oferteo_extraction.log"
echo ""

echo "=========================================="
echo "REZULTATY:"
echo "=========================================="
echo ""
echo "Screenshots:"
ls -la ./screenshots/ 2>/dev/null || echo "   (brak)"
echo ""
echo "Video recordings:"
ls -la ./recordings/ 2>/dev/null || echo "   (brak)"
echo ""
echo "Oferteo output:"
ls -la oferteo_*.txt 2>/dev/null || echo "   (brak)"
echo ""
echo "Logi w: $RESULTS_DIR/"
ls -la "$RESULTS_DIR/"
echo ""
echo "=========================================="
echo "DEMO ZAKOŃCZONE"
echo "=========================================="
