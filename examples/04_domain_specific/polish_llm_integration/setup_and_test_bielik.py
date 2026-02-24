#!/usr/bin/env python3
"""
Automatyczna konfiguracja i test modelu Bielik-1.5B dla NLP2CMD

Pobiera model Bielik GGUF i testuje integrację z polskim LLM.
"""

import os
import sys
import json
import subprocess
import requests
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))


class BielikSetup:
    """Automatyczna konfiguracja modelu Bielik."""
    
    def __init__(self):
        self.model_url = "https://huggingface.co/speakleash/Bielik-1.5B-v3.0-Instruct-GGUF/resolve/main/Bielik-1.5B-v3.0-Instruct.Q8_0.gguf"
        self.model_filename = "bielik-1.5b.gguf"
        self.models_dir = Path.home() / ".cache" / "bielik"
        self.model_path = self.models_dir / self.model_filename
        
    def check_dependencies(self) -> bool:
        """Sprawdź wymagane zależności."""
        print("🔍 Sprawdzanie zależności...")
        
        missing = []
        
        # Check llama-cpp-python
        try:
            import llama_cpp
            print("✅ llama-cpp-python zainstalowany")
        except ImportError:
            missing.append("llama-cpp-python")
            print("❌ llama-cpp-python brakuje")
        
        # Check nlp2cmd
        try:
            import nlp2cmd
            print("✅ nlp2cmd dostępny")
        except ImportError:
            missing.append("nlp2cmd[all]")
            print("❌ nlp2cmd brakuje")
        
        if missing:
            print(f"\n📦 Instalacja brakujących pakietów: {', '.join(missing)}")
            print("⚠️  Wykryto środowisko zewnętrznie zarządzane")
            print("💡 Opcje instalacji:")
            print("   1. Użyj --break-system-packages (ryzykowne)")
            print("   2. Utwórz wirtualne środowisko (polecane)")
            print("   3. Użyj pipx (dla aplikacji)")
            
            try:
                choice = input("\n🔧 Wybierz opcję (1/2/3): ").strip()
                if choice == "1":
                    # Instalacja z --break-system-packages
                    subprocess.check_call([
                        sys.executable, "-m", "pip", "install", "--break-system-packages"
                    ] + missing)
                    print("✅ Pakiety zainstalowane z --break-system-packages")
                    return True
                elif choice == "2":
                    # Tworzenie wirtualnego środowiska
                    venv_path = Path("bielik_venv")
                    print(f"📁 Tworzenie wirtualnego środowiska: {venv_path}")
                    subprocess.check_call([sys.executable, "-m", "venv", str(venv_path)])
                    
                    venv_pip = venv_path / "bin" / "pip"
                    print(f"📦 Instalacja pakietów w wirtualnym środowisku...")
                    subprocess.check_call([str(venv_pip), "install"] + missing)
                    
                    print(f"✅ Wirtualne środowisko gotowe!")
                    print(f"💡 Użyj: source {venv_path}/bin/activate")
                    print(f"📝 Następnie uruchom ponownie: python3 setup_and_test_bielik.py")
                    return False
                elif choice == "3":
                    print("📦 Użyj pipx do instalacji:")
                    for pkg in missing:
                        print(f"   pipx install {pkg}")
                    return False
                else:
                    print("❌ Nieprawidłowy wybór")
                    return False
                    
            except (subprocess.CalledProcessError, KeyboardInterrupt) as e:
                print(f"❌ Błąd instalacji: {e}")
                return False
        
        return True
    
    def download_model(self, force: bool = False) -> bool:
        """Pobierz model Bielik GGUF."""
        if self.model_path.exists() and not force:
            print(f"✅ Model już istnieje: {self.model_path}")
            return True
        
        print(f"📥 Pobieranie modelu Bielik-1.5B...")
        print(f"📁 Lokalizacja: {self.model_path}")
        print(f"🌐 URL: {self.model_url}")
        
        # Utwórz katalog models
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Pobierz plik
            response = requests.get(self.model_url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(self.model_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Progress bar
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\r📊 Postęp: {percent:.1f}% ({downloaded//1024//1024}MB/{total_size//1024//1024}MB)", end="")
            
            print(f"\n✅ Model pobrany pomyślnie: {self.model_path}")
            print(f"📊 Rozmiar: {self.model_path.stat().st_size // 1024 // 1024}MB")
            return True
            
        except Exception as e:
            print(f"\n❌ Błąd pobierania: {e}")
            return False
    
    def setup_environment(self) -> None:
        """Ustaw zmienne środowiskowe."""
        print(f"\n🔧 Ustawianie środowiska...")
        
        # Ustaw zmienną środowiskową
        os.environ["NLP2CMD_LLM_MODEL_PATH"] = str(self.model_path)
        
        print(f"📝 NLP2CMD_LLM_MODEL_PATH={self.model_path}")
        
        # Dodaj do .env jeśli istnieje
        env_file = project_root / ".env"
        if env_file.exists():
            with open(env_file, "a") as f:
                f.write(f"\n# Bielik Model Configuration\nNLP2CMD_LLM_MODEL_PATH={self.model_path}\n")
            print(f"✅ Dodano do .env")
    
    def test_integration(self) -> bool:
        """Test integracji z modelem Bielik."""
        print(f"\n🧪 Test integracji z Bielik-1.5B...")
        
        try:
            # Import po konfiguracji
            from llama_cpp import Llama
            from example_pdf_search import PolishPDFSearchLLM
            
            print("🤖 Ładowanie modelu Bielik...")
            llm = Llama(
                model_path=str(self.model_path),
                n_ctx=2048,
                verbose=False,
                n_gpu_layers=0,  # CPU-only dla kompatybilności
                seed=42
            )
            print("✅ Model załadowany pomyślnie")
            
            # Test PDF search
            pdf_searcher = PolishPDFSearchLLM(
                model_path=str(self.model_path),
                use_lite_llm=False
            )
            
            # Testowe zapytania
            test_queries = [
                "znajdź wszystkie pliki PDF",
                "pokaż PDF większe niż 2MB",
                "wyszukaj PDF z ostatniego tygodnia"
            ]
            
            print(f"\n📝 Testowe zapytania:")
            results = []
            
            for i, query in enumerate(test_queries, 1):
                print(f"\n{i}. {query}")
                try:
                    result = pdf_searcher.generate_pdf_search_command(query)
                    print(f"   💻 {result['command']}")
                    print(f"   ✅ {result['model']}")
                    results.append(result)
                except Exception as e:
                    print(f"   ❌ Błąd: {e}")
                    results.append({"query": query, "error": str(e)})
            
            # Podsumowanie
            successful = sum(1 for r in results if r.get("success", False))
            total = len(results)
            
            print(f"\n📊 Wyniki testu: {successful}/{total} sukcesów")
            
            if successful == total:
                print("🎉 Wszystkie testy przeszły pomyślnie!")
                return True
            else:
                print("⚠️  Niektóre testy nie przeszły")
                return False
                
        except Exception as e:
            print(f"❌ Błąd testu: {e}")
            return False
    
    def run_interactive_demo(self) -> None:
        """Uruchom interaktywny demo."""
        print(f"\n🎮 Interaktywny demo (wpisz 'exit' aby zakończyć)")
        
        try:
            from example_pdf_search import PolishPDFSearchLLM
            
            pdf_searcher = PolishPDFSearchLLM(
                model_path=str(self.model_path),
                use_lite_llm=False
            )
            
            while True:
                try:
                    query = input("\n📝 Wpisz zapytanie o PDF: ").strip()
                    if query.lower() in ['exit', 'quit', 'wyjdź']:
                        break
                    
                    if not query:
                        continue
                    
                    print("🧠 Przetwarzanie...")
                    result = pdf_searcher.generate_pdf_search_command(query)
                    
                    print(f"💻 Komenda: {result['command']}")
                    print(f"🤖 Model: {result['model']}")
                    print(f"✅ Status: {'Sukces' if result['success'] else 'Błąd'}")
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"❌ Błąd: {e}")
            
            print("\n👋 Koniec demo")
            
        except Exception as e:
            print(f"❌ Błąd demo: {e}")
    
    def setup_complete(self) -> None:
        """Podsumowanie konfiguracji."""
        print(f"\n🎉 Konfiguracja Bielik-1.5B zakończona!")
        print(f"{'='*60}")
        print(f"📁 Model: {self.model_path}")
        print(f"📊 Rozmiar: {self.model_path.stat().st_size // 1024 // 1024}MB")
        print(f"🔧 Zmienna: NLP2CMD_LLM_MODEL_PATH={self.model_path}")
        
        print(f"\n📋 Użycie w innych skryptach:")
        print(f"export NLP2CMD_LLM_MODEL_PATH=\"{self.model_path}\"")
        print(f"python3 example_pdf_search.py")
        
        print(f"\n💡 Wskazówki:")
        print(f"- Model Bielik-1.5B jest gotowy do użycia")
        print(f"- Możesz używać go w swoich projektach NLP2CMD")
        print(f"- Dla lepszej wydajności rozważ użycie GPU (n_gpu_layers)")
        print(f"- Model działa dobrze z zapytaniami w języku polskim")


def main():
    """Główna funkcja setup."""
    print("🤖 Konfiguracja Automatyczna Modelu Bielik-1.5B")
    print("=" * 60)
    
    setup = BielikSetup()
    
    # 1. Sprawdź zależności
    if not setup.check_dependencies():
        print("❌ Nie udało się zainstalować zależności")
        return
    
    # 2. Pobierz model
    if not setup.download_model():
        print("❌ Nie udało się pobrać modelu")
        return
    
    # 3. Ustaw środowisko
    setup.setup_environment()
    
    # 4. Test integracji
    if setup.test_integration():
        # 5. Uruchom demo (opcjonalnie)
        try:
            response = input("\n🎮 Czy chcesz uruchomić interaktywny demo? (t/n): ").strip().lower()
            if response in ['t', 'tak', 'yes', 'y']:
                setup.run_interactive_demo()
        except KeyboardInterrupt:
            pass
        
        # 6. Podsumowanie
        setup.setup_complete()
    else:
        print("❌ Test integracji nie przeszedł")


if __name__ == "__main__":
    main()
