# Demo 02: Decision Router

Demonstracja Decision Router - decyzja czy potrzebny LLM.

## Zawartość

- `demo.py` - Decision Router
- `run.sh` - Skrypt uruchamiający demo

## Uruchomienie

```bash
./run.sh
```

## Co pokazuje ten przykład

- Enum `RoutingDecision` (USE_RULE, USE_LLM, NEEDS_CLARIFICATION)
- Klasa `DecisionRouter`
- Logika routingu na podstawie wzorców
- Testowe przypadki decyzji
- Logika wyboru metody obsługi zapytania
