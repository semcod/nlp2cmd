#!/usr/bin/env python3
"""
Prosty skrypt do pobierania modelu Bielik-1.5B GGUF
"""

import os
import sys
import requests
from pathlib import Path

def download_bielik():
    """Pobierz model Bielik-1.5B GGUF."""
    
    model_url = "https://huggingface.co/speakleash/Bielik-1.5B-v3.0-Instruct-GGUF/resolve/main/Bielik-1.5B-v3.0-Instruct.Q8_0.gguf"
    model_filename = "bielik-1.5b.gguf"
    models_dir = Path.home() / ".cache" / "bielik"
    model_path = models_dir / model_filename
    
    print("🤖 Pobieranie modelu Bielik-1.5B")
    print("=" * 50)
    
    if model_path.exists():
        print(f"✅ Model już istnieje: {model_path}")
        print(f"📊 Rozmiar: {model_path.stat().st_size // 1024 // 1024}MB")
        return str(model_path)
    
    print(f"📥 Pobieranie: {model_filename}")
    print(f"📁 Lokalizacja: {model_path}")
    print(f"🌐 URL: {model_url}")
    
    # Utwórz katalog
    models_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        response = requests.get(model_url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(model_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\r📊 Postęp: {percent:.1f}% ({downloaded//1024//1024}MB/{total_size//1024//1024}MB)", end="")
        
        print(f"\n✅ Model pobrany: {model_path}")
        print(f"📊 Rozmiar: {model_path.stat().st_size // 1024 // 1024}MB")
        
        # Ustaw zmienną środowiskową
        os.environ["NLP2CMD_LLM_MODEL_PATH"] = str(model_path)
        print(f"🔧 Ustawiono NLP2CMD_LLM_MODEL_PATH={model_path}")
        
        return str(model_path)
        
    except Exception as e:
        print(f"\n❌ Błąd pobierania: {e}")
        return None

if __name__ == "__main__":
    model_path = download_bielik()
    if model_path:
        print(f"\n💡 Użyj w skryptach:")
        print(f"export NLP2CMD_LLM_MODEL_PATH=\"{model_path}\"")
        print(f"python3 example_pdf_search.py")
    else:
        print(f"\n❌ Nie udało się pobrać modelu")
