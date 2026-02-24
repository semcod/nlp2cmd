# Polish LLM Integration with NLP2CMD

Integracja Bielik-1.5B-v3.0-Instruct modelu z nlp2cmd do generowania poleceń w języku polskim.

## 🎯 Cel

Demonstracja, jak używać lokalnego polskiego modelu LLM (1.5B parametrów) do generowania planów wykonania i poleceń systemowych z naturalnych zapytań w języku polskim.

## 📋 Wymagania

### Podstawowe
- Python 3.8+
- nlp2cmd z pełnymi zależnościami

```bash
pip install nlp2cmd[all]
```

### LLM Integration
```bash
# Dla modeli GGUF (llama.cpp)
pip install llama-cpp-python

# Alternatywnie dla LiteLLM
pip install litellm
```

## 🚀 Szybki start

### Automatyczna konfiguracja (polecane)

```bash
# Automatyczne pobranie i konfiguracja Bielik-1.5B
python3 examples/04_domain_specific/polish_llm_integration/setup_and_test_bielik.py
```

### Ręczna konfiguracja

#### 1. Pobierz model

```bash
# Bielik-1.5B-v3.0-Instruct (polski)
wget https://huggingface.co/speakleash/Bielik-1.5B-v3.0-Instruct-GGUF/resolve/main/Bielik-1.5B-v3.0-Instruct.Q8_0.gguf -O bielik-1.5b.gguf

# Lub z Hugging Face CLI
huggingface-cli download speakleash/Bielik-1.5B-v3.0-Instruct-GGUF Bielik-1.5B-v3.0-Instruct.Q8_0.gguf
```

#### 2. Podstawowe użycie

```python
from llama_cpp import Llama
from nlp2cmd.planner import LLMPlanner, PlannerConfig
from nlp2cmd.executor import PlanExecutor

# 1️⃣ Załaduj polski LLM
llm = Llama(model_path="bielik-1.5b.gguf", n_ctx=2048, verbose=False)

# 2️⃣ Zainicjalizuj planner
planner = LLMPlanner(llm_client=llm)

# 3️⃣ Zapytanie po polsku
query = "Otwórz https://www.prototypowanie.pl/kontakt/ i wypełnij formularz kontaktowy i wyślij"

# 4️⃣ Wygeneruj plan
plan_result = planner.plan(intent=None, entities={}, text=query)
plan = plan_result.plan

print("Plan JSON/DSL:")
print(plan)
```

### 3. Wykonanie planu

```python
# 5️⃣ Inicjalizacja executor
executor = PlanExecutor()

# 6️⃣ Wykonaj plan
exec_result = executor.execute(plan)

# 7️⃣ Wyświetl wyniki
print(f"Wykonano {len(exec_result.results)} kroków")
for step_result in exec_result.results:
    print(f"- {step_result.action}: {step_result.status}")
```

## 📁 Pliki

- `setup_and_test_bielik.py` - **Automatyczna konfiguracja** Bielik-1.5B (pobiera, instaluje, testuje)
- `example_pdf_search.py` - Przykład wyszukiwania plików PDF z Bielik-1.5B
- `test_polish_llm.py` - Pełny test z prawdziwym modelem LLM
- `mock_test_polish_llm.py` - Test mock (bez potrzeby pobierania modelu)
- `README.md` - Ten dokument

## 🧪 Testy

### Test Mock (bez modelu)

```bash
python3 examples/04_domain_specific/polish_llm_integration/mock_test_polish_llm.py
```

Wynik:
- ✅ 100% sukcesu w testach
- ✅ Poprawne rozpoznawanie polskich zapytań
- ✅ Generowanie planów wykonania

### Test z prawdziwym modelem

```bash
python3 examples/04_domain_specific/polish_llm_integration/test_polish_llm.py
```

## 🔧 Konfiguracja

### Optymalne parametry dla polskiego

```python
config = PlannerConfig(
    temperature=0.3,      # Mniej losowe dla polskiego
    max_tokens=500,       # Krótsze odpowiedzi
    max_steps=10,         # Ogranicz liczbę kroków
    include_examples=True # Przykłady pomagają w polskim
)
```

### Wsparcie GPU

```python
llm = Llama(
    model_path="polka-1.1b-chat.gguf",
    n_ctx=2048,
    n_gpu_layers=-1,      # Wszystkie warstwy na GPU
    verbose=False
)
```

## 💡 Przykłady użycia

### 1. Automatyzacja przeglądarki

```python
query = "Otwórz stronę banku i zaloguj się używając mojego emaila"
plan_result = planner.plan(intent=None, entities={}, text=query)

# Wygeneruje plan:
# {
#   "steps": [
#     {"action": "playwright_open", "params": {"url": "..."}},
#     {"action": "playwright_fill", "params": {"selector": "#email", "value": "..."}},
#     {"action": "playwright_click", "params": {"selector": "#login"}}
#   ]
# }
```

### 2. Operacje systemowe

```python
query = "Znajdź wszystkie pliki .tmp starsze niż 7 dni i usuń je"
plan_result = planner.plan(intent=None, entities={}, text=query)

# Wygeneruje plan z shell commands
```

### 3. Zapytania SQL

```python
query = "Pokaż klientów z Warszawy którzy złożyli zamówienia w tym miesiącu"
plan_result = planner.plan(intent=None, entities={}, text=query)

# Wygeneruje plan z krokami SQL
```

## 🌐 Dostępne modele polskie

### Polecane (Bielik-1.5B)

1. **Bielik-1.5B-v3.0-Instruct**
   - Rozmiar: ~900MB (GGUF Q4_K_M)
   - Język: Polski
   - Specjalizacja: Instrukcje, nowocześniejszy architektura
   - **Zalecany dla nowych projektów**

2. Ollama lokalne modele:
   ```bash
   ollama pull bielik-1.5b
   # Użyj z LiteLLM: model="ollama/bielik-1.5b"
   ```

### Alternatywy

- Modele z Hugging Face (speakleash/Bielik)
- Własne fine-tuningi na Bielik
- Modele multilingual (np. Qwen2.5)

## 🔍 Integracja z nlp2cmd

### Przez LLMPlanner

```python
from nlp2cmd.planner import LLMPlanner

planner = LLMPlanner(llm_client=llm)
result = planner.plan(intent=None, entities={}, text="polskie zapytanie")
```

### Przez LiteLLM

```python
from nlp2cmd.generation.llm_simple import LiteLLMClient, SimpleLLMSQLGenerator

client = LiteLLMClient(
    model="ollama/qwen2.5-coder:7b",
    api_base="http://localhost:11434"
)

generator = SimpleLLMSQLGenerator(client)
result = await generator.generate("Pokaż użytkowników z Polski")
```

### CLI Integration

```python
from nlp2cmd import nlp2cmd

result = nlp2cmd(
    query="Otwórz stronę i wypełnij formularz",
    llm_model_path="bielik-1.5b.gguf",
    run=True
)
```

## 📊 Wyniki testów

### Mock test (8 zapytań polskich)

| Kategoria | Sukces | Przykłady |
|-----------|--------|-----------|
| Przeglądarka | ✅ 100% | "Otwórz stronę", "wypełnij formularz" |
| Shell | ✅ 100% | "Pokaż pliki", "znajdź procesy" |
| SQL | ✅ 100% | "Pokaż zamówienia" |
| Docker | ✅ 100% | "Sprawdź kontener" |

### Rozpoznawanie intencji

- **playwright**: strony, formularze, klikanie
- **shell**: pliki, procesy, system
- **sql**: baza danych, zamówienia, użytkownicy
- **docker**: kontenery, obrazy

## 🛠️ Rozwiązywanie problemów

### Brak modelu

```bash
# Download error
wget https://huggingface.co/TinyLlama/Polka-1.1B-Chat-GGUF/resolve/main/polka-1.1b-chat.gguf

# Sprawdź ścieżkę
ls -la polka-1.1b-chat.gguf
```

### Problemy z pamięcią

```python
# Mniejszy context
llm = Llama(model_path="polka-1.1b-chat.gguf", n_ctx=1024)

# Lub ogranicz warstwy GPU
llm = Llama(model_path="polka-1.1b-chat.gguf", n_gpu_layers=10)
```

### Słaba jakość polskiego

```python
# Dostosuj prompt
system_prompt = """Jesteś polskim asystentem. Odpowiadaj w języku polskim.
Generuj plany wykonania krok po kroku."""

# Lub użyj higher temperature
config = PlannerConfig(temperature=0.5)
```

## 🔄 Zaawansowane użycie

### Custom prompts

```python
class PolishLLMPlanner(LLMPlanner):
    def _build_prompt(self, intent, entities, text, context, domain):
        # Custom polish prompt
        base_prompt = super()._build_prompt(...)
        return base_prompt.replace("You are", "Jesteś")
```

### Hybrid approach

```python
# Rule-based dla prostych, LLM dla złożonych
if len(text.split()) < 5:
    # Użyj rule-based
    return rule_based_plan(text)
else:
    # Użyj LLM
    return llm_planner.plan(...)
```

## 📚 Dokumentacja

- [nlp2cmd Core](../../../README.md)
- [LLM Integration](../../../docs/LLM_INTEGRATION.md)
- [Planner API](../../../src/nlp2cmd/planner/)
- [Examples](../../../examples/)

## 🤝 Współpraca

- Testuj z różnymi polskimi modelami
- Raportuj problemy z językiem polskim
- Sugeruj ulepszenia promptów
- Dodawaj przykłady użycia

---

**Uwaga**: Ten przykład demonstruje integrację polskiego LLM z nlp2cmd. 
W produkcji używaj odpowiednich zabezpieczeń i walidacji.
