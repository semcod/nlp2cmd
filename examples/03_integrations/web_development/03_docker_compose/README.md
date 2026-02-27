# Demo 03: Docker Compose Generation

Demonstracja generowania plików docker-compose.yml.

## Zawartość

- `demo.py` - Generowanie docker-compose
- `run.sh` - Skrypt uruchamiający demo

## Uruchomienie

```bash
./run.sh
```

## Co pokazuje ten przykład

- Funkcja `generate_compose()` tworząca strukturę YAML
- Automatyczne dodawanie portów, sieci, zmiennych środowiskowych
- Obsługa zależności między usługami
- Generowanie wolumenów
