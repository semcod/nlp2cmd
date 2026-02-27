# Demo 05: Integration

Integracja wszystkich komponentów - pełny pipeline.

## Zawartość

- `demo.py` - Pełny pipeline integracji
- `run.sh` - Skrypt uruchamiający demo

## Uruchomienie

```bash
./run.sh
```

## Co pokazuje ten przykład

- Klasa `PDFSearchPipeline` - pełny pipeline
- Pojedyncze wyszukiwanie w PDF
- Batch wyszukiwanie w wielu PDF
- Pipeline flow: PDF → Extractor → Chunker → Searcher → Results
- Zalety architektury pipeline
