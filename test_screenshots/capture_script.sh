#!/bin/bash

# Skrypt do robienia zrzutów ekranu co 2 sekundy
# Usage: ./capture_script.sh [liczba_zrzutow] [folder]

LICZBA_ZRZUTOW=${1:-10}  # domyślnie 10 zrzutów
FOLDER=${2:-"test_screenshots"}
INTERWAL=2  # sekundy

echo "Rozpoczynam robienie $LICZBA_ZRZUTOW zrzutów ekranu co $INTERWAL sekund..."
echo "Folder docelowy: $FOLDER"

mkdir -p "$FOLDER"

for i in $(seq 1 $LICZBA_ZRZUTOW); do
    timestamp=$(date +"%Y%m%d_%H%M%S")
    filename="screenshot_${timestamp}_${i}.png"
    filepath="$FOLDER/$filename"
    
    echo "Zrzut $i/$LICZBA_ZRZUTOW: $filename"
    
    if scrot "$filepath"; then
        size=$(stat -c%s "$filepath")
        echo "  ✓ Zapisano (${size} bytes)"
    else
        echo "  ✗ Błąd podczas zapisu"
    fi
    
    if [ $i -lt $LICZBA_ZRZUTOW ]; then
        sleep $INTERWAL
    fi
done

echo "Zakończono. Zrobiono $LICZBA_ZRZUTOW zrzutów."
