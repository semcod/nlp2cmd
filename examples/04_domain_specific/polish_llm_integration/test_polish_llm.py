#!/usr/bin/env python3
"""
Polish LLM Integration Test for NLP2CMD

Tests TinyLlama/Polka-1.1B-Chat model integration with nlp2cmd
for Polish language command generation and execution.

Requirements:
- llama-cpp-python
- Local GGUF model file (polka-1.1b-chat.gguf)
- nlp2cmd[all]
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any

# Add project root to path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

try:
    from llama_cpp import Llama
    from nlp2cmd.planner import LLMPlanner, PlannerConfig
    from nlp2cmd.executor import PlanExecutor
    from nlp2cmd.generation.llm_simple import LiteLLMClient, SimpleLLMSQLGenerator
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please install required packages:")
    print("pip install llama-cpp-python nlp2cmd[all]")
    sys.exit(1)


class PolishLLMClient:
    """Wrapper for Polish TinyLlama model for nlp2cmd integration."""
    
    def __init__(self, model_path: str, n_ctx: int = 2048):
        """Initialize Polish LLM model."""
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        print(f"🤖 Loading Polish LLM model: {model_path}")
        self.llm = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            verbose=False,
            n_gpu_layers=0,  # CPU-only for compatibility
            seed=42
        )
        print("✅ Model loaded successfully")
    
    def generate_plan(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate execution plan for Polish query."""
        
        # Polish-specific system prompt
        system_prompt = """Jesteś asystentem generującym plany wykonania dla poleceń w języku polskim.

Twoim zadaniem jest tworzenie planów wykonania krok po kroku.

Dostępne akcje:
- playwright_open: Otwórz stronę WWW
- playwright_fill: Wypełnij formularz
- playwright_click: Kliknij element
- playwright_submit: Wyślij formularz
- shell_command: Wykonaj komendę shell
- sql_select: Wykonaj zapytanie SQL

Format odpowiedzi (tylko JSON):
{
  "steps": [
    {
      "action": "nazwa_akcji",
      "params": {"parametr": "wartość"},
      "store_as": "zmienna"
    }
  ]
}

Przykład:
Query: "Otwórz google.pl i wyszukaj 'nlp2cmd'"
{
  "steps": [
    {
      "action": "playwright_open",
      "params": {"url": "https://google.pl"},
      "store_as": "page"
    },
    {
      "action": "playwright_fill",
      "params": {"selector": "input[name='q']", "value": "nlp2cmd"},
      "store_as": "search_filled"
    },
    {
      "action": "playwright_submit",
      "params": {"selector": "form"},
      "store_as": "search_results"
    }
  ]
}"""

        # Build user prompt
        user_prompt = f"Użytkownik pyta: {query}"
        if context:
            user_prompt += f"\nKontekst: {json.dumps(context, ensure_ascii=False)}"
        
        # Generate response
        response = self.llm(
            user_prompt,
            system_prompt=system_prompt,
            max_tokens=500,
            temperature=0.3,
            stop=["\n\n", "```"],
            echo=False
        )
        
        raw_text = response["choices"][0]["text"].strip()
        
        # Extract JSON from response
        try:
            # Try direct JSON parse
            return json.loads(raw_text)
        except json.JSONDecodeError:
            # Try to extract JSON from text
            import re
            json_match = re.search(r'\{[\s\S]*\}', raw_text)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass
            
            # Fallback plan
            return {
                "steps": [
                    {
                        "action": "shell_command",
                        "params": {"command": f"echo 'Nie udało się przetworzyć: {query}'"},
                        "store_as": "fallback"
                    }
                ]
            }


class PolishNLP2CMD:
    """Polish NLP2CMD integration with local LLM."""
    
    def __init__(self, model_path: str):
        """Initialize Polish NLP2CMD."""
        self.llm_client = PolishLLMClient(model_path)
        self.executor = PlanExecutor()
    
    def process_query(self, query: str, run: bool = False) -> Dict[str, Any]:
        """Process Polish query and optionally execute."""
        print(f"\n📝 Zapytanie: {query}")
        print("-" * 50)
        
        # Generate plan
        print("🧠 Generowanie planu...")
        plan = self.llm_client.generate_plan(query)
        
        print("📋 Plan wykonania:")
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        
        if run and plan.get("steps"):
            print("\n🚀 Wykonywanie planu...")
            try:
                # Execute plan (mock for now)
                results = []
                for i, step in enumerate(plan["steps"]):
                    step_result = {
                        "step": i + 1,
                        "action": step["action"],
                        "params": step["params"],
                        "status": "simulated",
                        "output": f"Symulowany wynik dla {step['action']}"
                    }
                    results.append(step_result)
                
                print("✅ Plan wykonany (symulacja)")
                return {
                    "query": query,
                    "plan": plan,
                    "results": results,
                    "success": True
                }
            except Exception as e:
                print(f"❌ Błąd wykonania: {e}")
                return {
                    "query": query,
                    "plan": plan,
                    "error": str(e),
                    "success": False
                }
        
        return {
            "query": query,
            "plan": plan,
            "success": True,
            "executed": False
        }


def test_polish_queries():
    """Test Polish language queries."""
    
    # Test queries in Polish
    test_queries = [
        "Otwórz https://www.google.pl",
        "Pokaż wszystkie pliki .log w katalogu /var/log",
        "Wyświetl 10 ostatnich zamówień z bazy danych",
        "Znajdź procesy używające najwięcej pamięci",
        "Sprawdź status kontenera docker nginx",
        "Wyczyść cache systemowy",
        "Pokaż użycie dysku dla wszystkich partycji"
    ]
    
    # Check for model file
    model_paths = [
        "polka-1.1b-chat.gguf",
        "models/polka-1.1b-chat.gguf",
        "/home/tom/.cache/huggingface/hub/models--*polka*/gguf/polka-1.1b-chat.gguf"
    ]
    
    model_path = None
    for path in model_paths:
        if "*" in path:
            # Handle glob pattern
            import glob
            matches = glob.glob(path)
            if matches:
                model_path = matches[0]
                break
        elif os.path.exists(path):
            model_path = path
            break
    
    if not model_path:
        print("❌ Model file not found!")
        print("Please download polka-1.1b-chat.gguf and place it in one of:")
        for path in model_paths:
            if "*" not in path:
                print(f"  - {path}")
        return
    
    print(f"🔍 Using model: {model_path}")
    
    # Initialize Polish NLP2CMD
    try:
        polish_nlp = PolishNLP2CMD(model_path)
    except Exception as e:
        print(f"❌ Failed to initialize Polish NLP2CMD: {e}")
        return
    
    # Test queries
    results = []
    
    for query in test_queries:
        try:
            result = polish_nlp.process_query(query, run=False)  # Don't actually run
            results.append(result)
            print(f"\n{'='*60}")
        except Exception as e:
            print(f"❌ Error processing query '{query}': {e}")
            results.append({
                "query": query,
                "error": str(e),
                "success": False
            })
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 PODSUMOWANIE TESTU")
    print(f"{'='*60}")
    
    successful = sum(1 for r in results if r.get("success", False))
    total = len(results)
    
    print(f"Przetworzono zapytań: {total}")
    print(f"Udane: {successful}")
    print(f"Nieudane: {total - successful}")
    print(f"Sukces: {successful/total*100:.1f}%")
    
    # Show examples
    print(f"\n📝 Przykładowe plany:")
    for i, result in enumerate(results[:3]):
        if result.get("success") and "plan" in result:
            print(f"\n{i+1}. {result['query']}")
            plan = result["plan"]
            if "steps" in plan:
                for step in plan["steps"]:
                    print(f"   → {step['action']}: {step.get('params', {})}")


def test_simple_llm_integration():
    """Test simple LLM integration with LiteLLM fallback."""
    
    print("\n🧪 Test prostego integracji LLM (LiteLLM)")
    print("-" * 50)
    
    # Try to use LiteLLM with local model
    try:
        # This would work if you have ollama or local LLM server
        llm_client = LiteLLMClient(
            model="ollama/qwen2.5-coder:7b",  # or local model
            api_base="http://localhost:11434"
        )
        
        generator = SimpleLLMSQLGenerator(llm_client)
        
        # Test Polish SQL generation
        async def test_sql():
            result = await generator.generate(
                "Pokaż wszystkich użytkowników z Warszawy",
                context={"schema": {"users": ["id", "name", "city", "email"]}}
            )
            print(f"Generated SQL: {result.command}")
            return result
        
        asyncio.run(test_sql())
        
    except Exception as e:
        print(f"LiteLLM test failed (expected if no local server): {e}")


if __name__ == "__main__":
    print("🤖 Test Integracji Polskiego LLM z NLP2CMD")
    print("=" * 60)
    
    # Test main functionality
    test_polish_queries()
    
    # Test simple LLM integration
    test_simple_llm_integration()
    
    print(f"\n✅ Test zakończony!")
    print("\n💡 Wskazówki:")
    print("- Upewnij się, że masz plik modelu GGUF")
    print("- Dla lepszej wydajności użyj GPU (n_gpu_layers)")
    print("- Możesz dostosować prompty dla swoich potrzeb")
    print("- Testuj różne zapytania w języku polskim")
