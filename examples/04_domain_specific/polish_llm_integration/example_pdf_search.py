#!/usr/bin/env python3
"""
Przykład wyszukiwania plików PDF z użyciem polskiego LLM w NLP2CMD

Demonstruje integrację lokalnego modelu Bielik-1.5B-v3.0-Instruct
do generowania komend wyszukiwania plików PDF w języku polskim.
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add project root to path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

try:
    from llama_cpp import Llama
    LLAMA_AVAILABLE = True
except ImportError:
    LLAMA_AVAILABLE = False
    print("⚠️  llama-cpp-python nie zainstalowany - używam mock")

try:
    from nlp2cmd.planner import LLMPlanner, PlannerConfig
    from nlp2cmd.executor import PlanExecutor
    from nlp2cmd.generation.llm_simple import LiteLLMClient, SimpleLLMShellGenerator
    NLP2CMD_AVAILABLE = True
except ImportError as e:
    NLP2CMD_AVAILABLE = False
    print(f"⚠️  nlp2cmd nie dostępne: {e}")
    print("Please install required packages:")
    print("pip install llama-cpp-python nlp2cmd[all]")
    # Nie kończ programu, pozwól na mock


class PolishPDFSearchLLM:
    """Integracja polskiego LLM do wyszukiwania plików PDF."""
    
    def __init__(self, model_path: Optional[str] = None, use_lite_llm: bool = False):
        """Inicjalizacja polskiego LLM."""
        self.use_lite_llm = use_lite_llm
        
        # Check dependencies
        if not NLP2CMD_AVAILABLE:
            raise ImportError("nlp2cmd not available")
        
        if use_lite_llm:
            # Użycie LiteLLM (dla serwerów lokalnych jak Ollama)
            self.llm_client = LiteLLMClient(
                model=os.environ.get("LITELLM_MODEL", "ollama/bielik-1.5b"),
                api_base=os.environ.get("LITELLM_API_BASE", "http://localhost:11434")
            )
            print(f"🤖 Używam LiteLLM: {self.llm_client.model}")
        else:
            # Użycie lokalnego modelu GGUF
            if not LLAMA_AVAILABLE:
                raise ImportError("llama-cpp-python not available")
            
            model_path = model_path or os.environ.get("NLP2CMD_LLM_MODEL_PATH", "bielik-1.5b.gguf")
            
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model file not found: {model_path}")
            
            print(f"🤖 Ładuję lokalny model: {model_path}")
            self.llm = Llama(
                model_path=model_path,
                n_ctx=2048,
                verbose=False,
                n_gpu_layers=0,  # CPU-only dla kompatybilności
                seed=42
            )
            print("✅ Model załadowany pomyślnie")
    
    def generate_pdf_search_command(self, query: str) -> Dict[str, Any]:
        """Generuj komendę wyszukiwania PDF z polskiego zapytania."""
        
        if self.use_lite_llm:
            return self._generate_with_lite_llm(query)
        else:
            return self._generate_with_local_llm(query)
    
    def _generate_with_lite_llm(self, query: str) -> Dict[str, Any]:
        """Generuj komendę używając LiteLLM."""
        
        generator = SimpleLLMShellGenerator(self.llm_client)
        
        # Dodaj kontekst o PDF
        context = {
            "schema": None,
            "history": None
        }
        
        # Uruchom asynchronicznie
        async def _generate():
            result = await generator.generate(
                f"Wyszukaj pliki PDF: {query}",
                context=context
            )
            return result
        
        # Uruchom w synchronicznym kontekście
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_generate())
        finally:
            loop.close()
        
        return {
            "query": query,
            "command": result.command,
            "success": result.success,
            "model": self.llm_client.model,
            "method": "LiteLLM"
        }
    
    def _generate_with_local_llm(self, query: str) -> Dict[str, Any]:
        """Generuj komendę używając lokalnego modelu LLaMA."""
        
        # System prompt dla polskiego LLM
        system_prompt = """Jesteś ekspertem od komend Linux/Unix. Użytkownik opisuje, jakie pliki chce znaleźć, a ty generujesz odpowiednią komendę.

Zasady:
1. Odpowiadaj TYLKO komendą shell, bez wyjaśnień
2. Używaj find do wyszukiwania plików
3. Dodawaj filtry odpowiednie dla zapytania
4. Dla wielu typów plików, używaj -o (OR) lub wielokrotnych -name
5. Dla zapytań o datę, używaj -mtime lub -newer
6. Dla rozmiaru, używaj -size
7. Sortuj wyniki jeśli potrzebne (| sort, | head)

Przykłady:
- "znajdź wszystkie PDF" → find . -name "*.pdf"
- "znajdź PDF i TXT" → find . -name "*.pdf" -o -name "*.txt"
- "znajdź obrazy" → find . -name "*.jpg" -o -name "*.png" -o -name "*.gif"
- "pliki większe niż 1MB" → find . -size +1M
- "pliki z ostatniego tygodnia" → find . -mtime -7
- "znajdź dokumenty" → find . -name "*.pdf" -o -name "*.doc" -o -name "*.docx"
- "wszystkie pliki" → find . -type f

Odpowiedz TYLKO komendą shell."""

        # User prompt
        user_prompt = f"Wyszukaj pliki: {query}"
        
        # Generuj odpowiedź
        full_prompt = f"""<system>
{system_prompt}
</system>

<user>
{user_prompt}
</user>

<assistant>
"""
        
        response = self.llm(
            full_prompt,
            max_tokens=200,
            temperature=0.2,
            stop=["\n\n", "```", "#", "</assistant>"],
            echo=False
        )
        
        raw_command = response["choices"][0]["text"].strip()
        
        # Czyść komendę
        command = self._clean_command(raw_command)
        
        return {
            "query": query,
            "command": command,
            "success": True,
            "model": "local/bielik-1.5b",
            "method": "Local LLaMA"
        }
    
    def _clean_command(self, command: str) -> str:
        """Oczyść komendę z niechcianych elementów."""
        # Usuń markdown
        if "```" in command:
            import re
            match = re.search(r'```(?:bash|shell)?\s*(.*?)\s*```', command, re.DOTALL)
            if match:
                command = match.group(1).strip()
        
        # Usuń komentarze
        lines = command.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                cleaned_lines.append(line)
        
        return ' '.join(cleaned_lines)


def test_pdf_search_queries():
    """Test różnych zapytań o wyszukiwanie PDF."""
    
    # Testowe zapytania w języku polskim
    test_queries = [
        "znajdź wszystkie pliki PDF w bieżącym katalogu",
        "wyszukaj PDF większe niż 5 megabajtów",
        "pokaż PDF zmodyfikowane w ostatnich 30 dniach",
        "znajdź PDF z nazwą zawierającą 'faktura'",
        "wyszukaj wszystkie PDF i posortuj według rozmiaru malejąco",
        "pokaż 10 największych plików PDF",
        "znajdź PDF starsze niż rok",
        "wyszukaj PDF w podkatalogach /home/user/Documents",
        "pokaż PDF z bieżącego miesiąca",
        "znajdź PDF i policz ich liczbę"
    ]
    
    print("🔍 Test wyszukiwania plików PDF z polskim LLM")
    print("=" * 60)
    
    # Konfiguracja
    model_path = os.environ.get("NLP2CMD_LLM_MODEL_PATH")
    use_lite_llm = bool(os.environ.get("LITELLM_MODEL"))
    
    try:
        pdf_searcher = PolishPDFSearchLLM(
            model_path=model_path,
            use_lite_llm=use_lite_llm
        )
    except Exception as e:
        print(f"❌ Błąd inicjalizacji: {e}")
        print("\n💡 Używam mock implementacji dla demonstracji")
        pdf_searcher = MockPolishPDFSearchLLM()
    
    results = []
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 Zapytanie {i}: {query}")
        print("-" * 50)
        
        try:
            result = pdf_searcher.generate_pdf_search_command(query)
            results.append(result)
            
            print(f"🤖 Metoda: {result['method']}")
            print(f"🔧 Model: {result['model']}")
            print(f"💻 Komenda: {result['command']}")
            print(f"✅ Status: {'Sukces' if result['success'] else 'Błąd'}")
            
        except Exception as e:
            print(f"❌ Błąd: {e}")
            results.append({
                "query": query,
                "command": f"# Błąd: {e}",
                "success": False,
                "error": str(e)
            })
    
    # Podsumowanie
    print(f"\n{'='*60}")
    print("📊 PODSUMOWANIE")
    print(f"{'='*60}")
    
    successful = sum(1 for r in results if r.get("success", False))
    total = len(results)
    
    print(f"Przetworzono zapytań: {total}")
    print(f"Udane: {successful}")
    print(f"Nieudane: {total - successful}")
    print(f"Sukces: {successful/total*100:.1f}%")
    
    # Pokaż przykładowe komendy
    print(f"\n🔧 Przykładowe wygenerowane komendy:")
    for i, result in enumerate(results[:5]):
        if result.get("success"):
            print(f"\n{i+1}. {result['query']}")
            print(f"   → {result['command']}")
    
    return results


class MockPolishPDFSearchLLM:
    """Mock implementation dla demonstracji bez prawdziwego LLM."""
    
    def __init__(self):
        print("🤖 Używam mock implementacji")
    
    def _get_command_for_query(self, query_lower: str) -> str:
        """Get find command based on query patterns."""
        pattern_map = [
            (lambda q: "wszystkie" in q or "wszystkich" in q, lambda: "find . -name '*.pdf'"),
            (lambda q: "megabajt" in q or "mb" in q or "rozmiar" in q, lambda: self._get_size_command(query_lower)),
            (lambda q: "30" in q or "miesiąc" in q or "miesiąca" in q or "miesiącu" in q or "bieżącym" in q, lambda: "find . -name '*.pdf' -mtime -30"),
            (lambda q: "dni" in q or "ostatnich" in q, lambda: "find . -name '*.pdf' -mtime -7"),
            (lambda q: "faktura" in q, lambda: "find . -name '*faktura*.pdf'"),
            (lambda q: "posortuj" in q or "sortuj" in q, lambda: self._get_sort_command(query_lower)),
            (lambda q: "10" in q or "największych" in q, lambda: "find . -name '*.pdf' -exec ls -s {} \\; | sort -nr | head -10"),
            (lambda q: "starsze" in q or "rok" in q, lambda: "find . -name '*.pdf' -mtime +365"),
            (lambda q: "/home/user" in q, lambda: "find /home/user/Documents -name '*.pdf'"),
            (lambda q: "liczbę" in q or "policz" in q, lambda: "find . -name '*.pdf' | wc -l"),
        ]
        
        for condition, command in pattern_map:
            if condition(query_lower):
                return command()
        
        return "find . -name '*.pdf'"
    
    def _get_size_command(self, query_lower: str) -> str:
        """Get size-based find command."""
        if "5" in query_lower:
            return "find . -name '*.pdf' -size +5M"
        return "find . -name '*.pdf' -size +1M"
    
    def _get_sort_command(self, query_lower: str) -> str:
        """Get sort-based find command."""
        if "rozmiar" in query_lower:
            return "find . -name '*.pdf' -exec ls -h {} \\; | sort -hr"
        return "find . -name '*.pdf' | sort"
    
    def generate_pdf_search_command(self, query: str) -> Dict[str, Any]:
        """Generuj mock komendę wyszukiwania PDF."""
        query_lower = query.lower()
        command = self._get_command_for_query(query_lower)
        
        return {
            "query": query,
            "command": command,
            "success": True,
            "model": "mock/rules-based",
            "method": "Mock"
        }


def show_configuration_guide():
    """Pokaż przewodnik konfiguracji."""
    
    print("\n🔧 KONFIGURACJA PRAWDZIWEGO LLM")
    print("=" * 60)
    
    config_guide = '''
1. KONFIGURACJA MODELU LOKALNEGO (GGUF):
   export NLP2CMD_LLM_MODEL_PATH="bielik-1.5b.gguf"
   python3 example_pdf_search.py

2. KONFIGURACJA LITELLM (Ollama z polskim modelem):
   export LITELLM_MODEL="ollama/bielik-1.5b"
   export LITELLM_API_BASE="http://localhost:11434"
   python3 example_pdf_search.py

3. KONFIGURACJA LITELLM (OpenAI):
   export LITELLM_MODEL="openai/gpt-4"
   export LITELLM_API_BASE="https://api.openai.com/v1"
   export LITELLM_API_KEY="your-api-key"
   python3 example_pdf_search.py

4. INSTALACJA WYMAGANYCH PAKIETÓW:
   pip install llama-cpp-python nlp2cmd[all]
   # Lub dla LiteLLM:
   pip install litellm nlp2cmd[all]

5. POBIERZ MODEL POLSKI:
   wget https://huggingface.co/speakleash/Bielik-1.5B-v3.0-Instruct-GGUF/resolve/main/Bielik-1.5B-v3.0-Instruct.Q8_0.gguf -O bielik-1.5b.gguf
'''
    
    print(config_guide)


if __name__ == "__main__":
    print("🤖 Przykład Wyszukiwania PDF z Polskim LLM")
    print("=" * 60)
    
    # Testy
    results = test_pdf_search_queries()
    
    # Przewodnik konfiguracji
    show_configuration_guide()
    
    print(f"\n✅ Test zakończony!")
    print("\n💡 Wskazówki:")
    print("- Dla prawdziwego LLM ustaw zmienne środowiskowe")
    print("- Model polski lepiej rozumie zapytania w języku polskim")
    print("- Możesz dostosować prompty dla swoich potrzeb")
    print("- Testuj różne typy zapytań o pliki PDF")
