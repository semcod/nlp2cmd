# Demo 04: Service Deployment

Demonstracja wdrożenia usług z użyciem natural language.

## Zawartość

- `demo.py` - Przykłady komend deploymentu
- `run.sh` - Skrypt uruchamiający demo

## Uruchomienie

```bash
./run.sh
```

## Co pokazuje ten przykład

- Klasa `DeployCommand` z natural language komendami
- Mapowanie zapytań na konfiguracje usług
- Przykłady wdrożenia:
  - Serwis czatu z Redis
  - Frontend z nginx
  - API z PostgreSQL i Redis
  - Klient email
