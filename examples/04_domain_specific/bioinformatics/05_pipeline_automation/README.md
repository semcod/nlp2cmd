# Demo 05: Pipeline Automation

Automatyzacja pipeline'ów bioinformatycznych.

## Zawartość

- `demo.py` - Automatyzacja pipeline
- `run.sh` - Skrypt uruchamiający demo

## Uruchomienie

```bash
./run.sh
```

## Co pokazuje ten przykład

- 7-krokowy pipeline NGS:
  1. Kontrola jakości (QC)
  2. Przycinanie sekwencji
  3. Mapowanie do referencji
  4. Konwersja do BAM
  5. Sortowanie BAM
  6. Indeksowanie
  7. Variant calling
- Pełny skrypt bash z pipeline
