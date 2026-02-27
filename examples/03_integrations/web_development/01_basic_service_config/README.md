# Demo 01: Basic Service Configuration

Demonstracja konfiguracji podstawowych usług w nlp2cmd.

## Zawartość

- `demo.py` - Konfiguracja usług (ServiceType, ServiceConfig)
- `run.sh` - Skrypt uruchamiający demo

## Uruchomienie

```bash
./run.sh
```

Lub bezpośrednio:

```bash
python3 demo.py
```

## Co pokazuje ten przykład

- Enum `ServiceType` z typami usług
- Dataclass `ServiceConfig` z konfiguracją
- Przykładowe konfiguracje:
  - Frontend (nginx)
  - Backend API (Python)
  - Database (PostgreSQL)
  - Cache (Redis)
