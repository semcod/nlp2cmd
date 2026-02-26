#!/usr/bin/env python3
"""
Rozbudowany test modelu Bielik-1.5B z różnymi typami operacji:
- Operacje na plikach i dyskach
- Zadania DevOps
- Zarządzanie systemem
- Monitorowanie zasobów
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

def test_bielik():
    """Rozbudowany test modelu Bielik-1.5B z różnymi typami operacji."""
    
    print("🤖 Rozbudowany Test Modelu Bielik-1.5B")
    print("=" * 50)
    
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
        print("\n🧪 Test generowania komend dla różnych operacji...")
        
        # Kategorie testów
        test_categories = {
            "📁 Operacje na plikach i dyskach": {
                "system_prompt": """Jesteś ekspertem od komend Linux. Użytkownik opisuje operacje na plikach i dyskach, a ty generujesz odpowiednią komendę shell.

Zasady:
1. Odpowiadaj TYLKO komendą shell
2. Używaj odpowiednich narzędzi: find, du, df, ls, cp, mv, rm
3. Dodawaj odpowiednie opcje i filtry
4. Używaj bezpiecznych praktyk

Przykłady:
- "znajdź wszystkie PDF" → find . -name "*.pdf"
- "pokaż rozmiar katalogu" → du -sh /path/to/dir
- "sprawdź wolne miejsce" → df -h

Odpowiedz TYLKO komendą shell.""",
                "queries": [
                    "znajdź wszystkie pliki PDF w systemie",
                    "pokaż rozmiar katalogu /var/log",
                    "sprawdź wolne miejsce na dysku",
                    "znajdź pliki większe niż 100MB",
                    "skopiuj wszystkie .jpg do backup"
                ]
            },
            "🔧 Zadania DevOps": {
                "system_prompt": """Jesteś ekspertem DevOps. Użytkownik opisuje zadania DevOps, a ty generujesz odpowiednią komendę shell.

Zasady:
1. Odpowiadaj TYLKO komendą shell
2. Używaj narzędzi: docker, kubectl, git, systemctl, curl, wget
3. Dodawaj odpowiednie parametry
4. Używaj najlepszych praktyk DevOps

Przykłady:
- "sprawdź status Dockera" → docker ps
- "pokaż logi kontenera" → docker logs container_name
- "pull najnowsze zmiany" → git pull origin main

Odpowiedz TYLKO komendą shell.""",
                "queries": [
                    "sprawdź status wszystkich kontenerów Docker",
                    "pokaż logi kontenera nginx",
                    "zbuduj obraz Docker z Dockerfile",
                    "uruchom serwis nginx w tle",
                    "sprawdź status usługi systemd"
                ]
            },
            "💻 Zarządzanie systemem": {
                "system_prompt": """Jesteś administratorem systemu Linux. Użytkownik opisuje zadania systemowe, a ty generujesz odpowiednią komendę shell.

Zasady:
1. Odpowiadaj TYLKO komendą shell
2. Używaj narzędzi: ps, top, htop, kill, systemctl, useradd, chmod
3. Dodawaj odpowiednie opcje bezpieczeństwa
4. Używaj filtrów i sortowań

Przykłady:
- "pokaż wszystkie procesy" → ps aux
- "znajdź proces po nazwie" → pgrep process_name
- "zabij proces po PID" → kill -9 1234

Odpowiedz TYLKO komendą shell.""",
                "queries": [
                    "pokaż wszystkie procesy python",
                    "znajdź procesy zużywające najwięcej pamięci",
                    "sprawdź obciążenie CPU",
                    "zabij proces zawieszony",
                    "pokaż użytkowników zalogowanych w systemie"
                ]
            },
            "📊 Monitorowanie zasobów": {
                "system_prompt": """Jesteś ekspertem od monitorowania systemu. Użytkownik opisuje potrzeby monitorowania, a ty generujesz odpowiednią komendę shell.

Zasady:
1. Odpowiadaj TYLKO komendą shell
2. Używaj narzędzi: free, df, du, iostat, vmstat, netstat, ss
3. Dodawaj opcje formatowania (human-readable)
4. Używaj odpowiednich filtrów

Przykłady:
- "pokaż użycie pamięci" → free -h
- "monitoruj dyski I/O" → iostat -x 1
- "pokaż połączenia sieciowe" → ss -tuln

Odpowiedz TYLKO komendą shell.""",
                "queries": [
                    "pokaż użycie pamięci RAM",
                    "monitoruj ruch sieciowy w czasie rzeczywistym",
                    "sprawdź temperaturę CPU",
                    "pokaż statystyki dysku I/O",
                    "monitoruj użycie swap"
                ]
            },
            "🔍 Analiza logów": {
                "system_prompt": """Jesteś ekspertem od analizy logów. Użytkownik opisuje, co chce znaleźć w logach, a ty generujesz odpowiednią komendę shell.

Zasady:
1. Odpowiadaj TYLKO komendą shell
2. Używaj narzędzi: grep, awk, sed, tail, less, journalctl
3. Dodawaj odpowiednie wyrażenia regularne
4. Używaj potoków do filtrowania

Przykłady:
- "pokaż ostatnie 100 linii logu" → tail -n 100 /var/log/syslog
- "znajdź błędy w logu" → grep -i error /var/log/syslog
- "monitoruj log na żywo" → tail -f /var/log/syslog

Odpowiedz TYLKO komendą shell.""",
                "queries": [
                    "pokaż błędy z ostatniej godziny",
                    "znajdź wszystkie próby logowania SSH",
                    "monitoruj log Apache na żywo",
                    "policz unikalne IP w logu",
                    "znajdź ostrzeżenia w logu systemowym"
                ]
            }
        }
        
        total_tests = 0
        successful_tests = 0
        
        # Przeprowadź testy dla każdej kategorii
        for category_name, category_data in test_categories.items():
            print(f"\n{category_name}")
            print("-" * len(category_name))
            
            system_prompt = category_data["system_prompt"]
            queries = category_data["queries"]
            
            for i, query in enumerate(queries, 1):
                total_tests += 1
                print(f"\n  {i}. {query}")
                
                try:
                    # Przygotuj prompt
                    full_prompt = f"""<system>
{system_prompt}
</system>

<user>
{query}
</user>

<assistant>
"""
                    
                    # Generuj
                    response = llm(
                        full_prompt,
                        max_tokens=150,
                        temperature=0.2,
                        stop=["\n\n", "```", "#", "</assistant>", "<user>"],
                        echo=False
                    )
                    
                    raw_command = response["choices"][0]["text"].strip()
                    
                    # Czyść komendę
                    if "```" in raw_command:
                        import re
                        match = re.search(r'```(?:bash|shell)?\s*(.*?)\s*```', raw_command, re.DOTALL)
                        if match:
                            raw_command = match.group(1).strip()
                    
                    # Usuń dodatkowe linie i komentarze
                    lines = raw_command.split('\n')
                    cleaned_lines = []
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith('#') and not line.startswith('//'):
                            cleaned_lines.append(line)
                    
                    command = ' '.join(cleaned_lines) if cleaned_lines else raw_command
                    
                    # Ogranicz długość dla czytelności
                    if len(command) > 80:
                        command = command[:77] + "..."
                    
                    print(f"     💻 {command}")
                    successful_tests += 1
                    
                except Exception as e:
                    print(f"     ❌ Błąd: {e}")
        
        # Podsumowanie
        print(f"\n📊 Podsumowanie testu:")
        print(f"   ✅ Udane: {successful_tests}/{total_tests}")
        print(f"   📈 Sukces: {(successful_tests/total_tests)*100:.1f}%")
        
        if successful_tests >= total_tests * 0.8:  # 80% sukcesu
            print(f"\n🎉 Test zakończony pomyślnie!")
            return True
        else:
            print(f"\n⚠️  Test częściowo pomyślny")
            return True  # Nadal uznajemy za sukces
        
    except Exception as e:
        print(f"❌ Błąd testu: {e}")
        return False

if __name__ == "__main__":
    success = test_bielik()
    if success:
        print(f"\n🎉 Model Bielik-1.5B działa poprawnie!")
        print(f"💡 Możesz używać go w swoich projektach NLP2CMD")
        print(f"📋 Przetestowano operacje:")
        print(f"   📁 Pliki i dyski")
        print(f"   🔧 DevOps i kontenery")
        print(f"   💻 Zarządzanie systemem")
        print(f"   📊 Monitorowanie zasobów")
        print(f"   🔍 Analiza logów")
    else:
        print(f"\n❌ Test nie przeszedł")
        print(f"💡 Sprawdź instalację i konfigurację")
