#!/usr/bin/env python3
"""
Prosty test modelu Bielik-1.5B bez interaktywnej instalacji
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

def test_bielik():
    """Test modelu Bielik-1.5B."""
    
    print("🤖 Test Modelu Bielik-1.5B")
    print("=" * 40)
    
    # Sprawdź zależności
    try:
        import llama_cpp
        print("✅ llama-cpp-python dostępny")
    except ImportError:
        print("❌ llama-cpp-python brakuje")
        print("💡 Zainstaluj: pip install --break-system-packages llama-cpp-python")
        return False
    
    try:
        import nlp2cmd
        print("✅ nlp2cmd dostępny")
    except ImportError:
        print("❌ nlp2cmd brakuje")
        print("💡 Zainstaluj: pip install --break-system-packages nlp2cmd[all]")
        return False
    
    # Ścieżka modelu
    model_path = os.environ.get("NLP2CMD_LLM_MODEL_PATH")
    if not model_path:
        model_path = "/home/tom/.cache/bielik/bielik-1.5b.gguf"
    
    if not os.path.exists(model_path):
        print(f"❌ Model nie znaleziony: {model_path}")
        return False
    
    print(f"📁 Model: {model_path}")
    
    # Test ładowania
    try:
        print("🤖 Ładowanie modelu...")
        llm = llama_cpp.Llama(
            model_path=model_path,
            n_ctx=2048,
            verbose=False,
            n_gpu_layers=0,
            seed=42
        )
        print("✅ Model załadowany")
    except Exception as e:
        print(f"❌ Błąd ładowania: {e}")
        return False
    
    # Test generowania
    try:
        print("\n🧪 Test generowania komend PDF...")
        
        # System prompt
        system_prompt = """Jesteś ekspertem od komend Linux. Użytkownik opisuje, jakie pliki PDF chce znaleźć, a ty generujesz odpowiednią komendę.

Zasady:
1. Odpowiadaj TYLKO komendą shell
2. Używaj find do wyszukiwania plików
3. Dodawaj filtry odpowiednie dla zapytania
4. Używaj -name "*.pdf" dla plików PDF

Przykłady:
- "znajdź wszystkie PDF" → find . -name "*.pdf"
- "PDF większe niż 1MB" → find . -name "*.pdf" -size +1M

Odpowiedz TYLKO komendą shell."""
        
        # Testowe zapytania
        queries = [
            "znajdź wszystkie pliki PDF",
            "pokaż PDF większe niż 2MB",
            "wyszukaj PDF z ostatniego tygodnia"
        ]
        
        for i, query in enumerate(queries, 1):
            print(f"\n{i}. {query}")
            
            # Przygotuj prompt
            full_prompt = f"""<system>
{system_prompt}
</system>

<user>
Wyszukaj pliki PDF: {query}
</user>

<assistant>
"""
            
            # Generuj
            response = llm(
                full_prompt,
                max_tokens=100,
                temperature=0.2,
                stop=["\n\n", "```", "#", "</assistant>"],
                echo=False
            )
            
            raw_command = response["choices"][0]["text"].strip()
            
            # Czyść komendę
            if "```" in raw_command:
                import re
                match = re.search(r'```(?:bash|shell)?\s*(.*?)\s*```', raw_command, re.DOTALL)
                if match:
                    raw_command = match.group(1).strip()
            
            # Usuń dodatkowe linie
            lines = raw_command.split('\n')
            cleaned_lines = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    cleaned_lines.append(line)
            
            command = ' '.join(cleaned_lines)
            
            print(f"   💻 {command}")
        
        print(f"\n✅ Test zakończony pomyślnie!")
        return True
        
    except Exception as e:
        print(f"❌ Błąd generowania: {e}")
        return False

if __name__ == "__main__":
    success = test_bielik()
    if success:
        print(f"\n🎉 Model Bielik-1.5B działa poprawnie!")
        print(f"💡 Możesz używać go w swoich projektach NLP2CMD")
    else:
        print(f"\n❌ Test nie przeszedł")
        print(f"💡 Sprawdź instalację i konfigurację")
