# Demo 02: Text Chunking

Dzielenie tekstu na mniejsze fragmenty (chunki) dla LLM.

## Zawartość

- `demo.py` - Text chunking
- `run.sh` - Skrypt uruchamiający demo

## Uruchomienie

```bash
./run.sh
```

## Co pokazuje ten przykład

- Klasa `TextChunker` - dzielenie tekstu
- Chunkowanie ze względnieniem zdań
- Konfiguracja rozmiaru chunku i overlapu
- Chunki z metadanymi (źródło, id, total)
