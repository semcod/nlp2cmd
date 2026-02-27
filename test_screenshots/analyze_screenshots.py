#!/usr/bin/env python3
"""
Skrypt do analizy i przetwarzania zrzutów ekranu:
- Sprawdza poprawność pobranych plików
- Zmniejsza zrzuty o 30%
- Generuje raport analizy
"""

import os
import sys
from pathlib import Path
from PIL import Image
import hashlib

def calculate_file_hash(filepath):
    """Oblicza hash MD5 pliku."""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def analyze_screenshots(folder="test_screenshots"):
    """Analizuje zrzuty ekranu w podanym folderze."""
    folder_path = Path(folder)
    
    if not folder_path.exists():
        print(f"❌ Folder {folder} nie istnieje!")
        return
    
    # Znajdź wszystkie pliki PNG
    png_files = list(folder_path.glob("*.png"))
    
    if not png_files:
        print(f"❌ Nie znaleziono plików PNG w folderze {folder}")
        return
    
    print(f"📊 Analiza zrzutów ekranu w folderze: {folder}")
    print(f"📁 Znaleziono {len(png_files)} plików PNG")
    print("=" * 60)
    
    analysis_results = []
    
    for i, png_file in enumerate(png_files, 1):
        try:
            # Sprawdź rozmiar pliku
            file_size = png_file.stat().st_size
            
            # Sprawdź obrazek
            with Image.open(png_file) as img:
                width, height = img.size
                mode = img.mode
                format_name = img.format
                
                # Oblicz hash
                file_hash = calculate_file_hash(png_file)
                
                analysis_results.append({
                    'filename': png_file.name,
                    'size_bytes': file_size,
                    'size_mb': round(file_size / (1024*1024), 2),
                    'dimensions': f"{width}x{height}",
                    'mode': mode,
                    'format': format_name,
                    'hash': file_hash[:8] + "...",  # skrócony hash
                    'valid': True
                })
                
                print(f"📸 {i:2d}. {png_file.name}")
                print(f"    Rozmiar: {file_size:,} bytes ({round(file_size/(1024*1024), 2)} MB)")
                print(f"    Wymiary: {width}x{height} px")
                print(f"    Tryb: {mode} | Format: {format_name}")
                print(f"    Hash: {file_hash[:16]}...")
                print()
                
        except Exception as e:
            analysis_results.append({
                'filename': png_file.name,
                'error': str(e),
                'valid': False
            })
            print(f"❌ {i:2d}. {png_file.name} - BŁĄD: {e}")
    
    # Podsumowanie
    valid_files = [r for r in analysis_results if r.get('valid', False)]
    invalid_files = [r for r in analysis_results if not r.get('valid', False)]
    
    print("=" * 60)
    print("📈 PODSUMOWANIE:")
    print(f"✅ Poprawne pliki: {len(valid_files)}")
    print(f"❌ Błędne pliki: {len(invalid_files)}")
    
    if valid_files:
        total_size = sum(r['size_bytes'] for r in valid_files)
        avg_size = total_size / len(valid_files)
        print(f"📊 Całkowity rozmiar: {total_size:,} bytes ({round(total_size/(1024*1024), 2)} MB)")
        print(f"📊 Średni rozmiar: {round(avg_size, 0)} bytes ({round(avg_size/(1024*1024), 2)} MB)")
    
    return analysis_results

def resize_screenshots(folder="test_screenshots", scale_factor=0.7):
    """Zmniejsza zrzuty ekranu o podany czynnik (domyślnie 30%)."""
    folder_path = Path(folder)
    output_folder = folder_path / f"resized_{int(scale_factor*100)}percent"
    
    if not folder_path.exists():
        print(f"❌ Folder {folder} nie istnieje!")
        return
    
    # Znajdź wszystkie pliki PNG
    png_files = list(folder_path.glob("*.png"))
    
    if not png_files:
        print(f"❌ Nie znaleziono plików PNG w folderze {folder}")
        return
    
    # Utwórz folder wyjściowy
    output_folder.mkdir(exist_ok=True)
    
    print(f"🔧 Zmniejszanie zrzutów o {int((1-scale_factor)*100)}% (współczynnik: {scale_factor})")
    print(f"📁 Folder wyjściowy: {output_folder}")
    print("=" * 60)
    
    resize_results = []
    
    for i, png_file in enumerate(png_files, 1):
        try:
            with Image.open(png_file) as img:
                # Oblicz nowe wymiary
                original_width, original_height = img.size
                new_width = int(original_width * scale_factor)
                new_height = int(original_height * scale_factor)
                
                # Zmień rozmiar
                resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Zapisz
                output_path = output_folder / png_file.name
                resized_img.save(output_path, optimize=True)
                
                # Sprawdź rozmiary
                original_size = png_file.stat().st_size
                new_size = output_path.stat().st_size
                size_reduction = round((1 - new_size/original_size) * 100, 1)
                
                resize_results.append({
                    'filename': png_file.name,
                    'original_size': f"{original_width}x{original_height}",
                    'new_size': f"{new_width}x{new_height}",
                    'original_bytes': original_size,
                    'new_bytes': new_size,
                    'size_reduction_percent': size_reduction,
                    'success': True
                })
                
                print(f"🔧 {i:2d}. {png_file.name}")
                print(f"    {original_width}x{original_height} → {new_width}x{new_height}")
                print(f"    {original_size:,} → {new_size:,} bytes (-{size_reduction}%)")
                print()
                
        except Exception as e:
            resize_results.append({
                'filename': png_file.name,
                'error': str(e),
                'success': False
            })
            print(f"❌ {i:2d}. {png_file.name} - BŁĄD: {e}")
    
    # Podsumowanie
    successful = [r for r in resize_results if r.get('success', False)]
    failed = [r for r in resize_results if not r.get('success', False)]
    
    print("=" * 60)
    print("📈 PODSUMOWANIE ZMIANY ROZMIARU:")
    print(f"✅ Przetworzono: {len(successful)}")
    print(f"❌ Błędy: {len(failed)}")
    
    if successful:
        total_original = sum(r['original_bytes'] for r in successful)
        total_new = sum(r['new_bytes'] for r in successful)
        total_reduction = round((1 - total_new/total_original) * 100, 1)
        print(f"📊 Całkowita redukcja rozmiaru: {total_reduction}%")
        print(f"📊 Oszczędność miejsca: {total_original - total_new:,} bytes")
    
    return resize_results

def main():
    """Główna funkcja."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analiza i przetwarzanie zrzutów ekranu")
    parser.add_argument("--folder", default="test_screenshots", help="Folder ze zrzutami")
    parser.add_argument("--scale", type=float, default=0.7, help="Współczynnik skali (0.7 = 30% mniejsze)")
    parser.add_argument("--analyze-only", action="store_true", help="Tylko analiza, bez zmiany rozmiaru")
    
    args = parser.parse_args()
    
    print("🖼️  NARZĘDZIE DO ANALIZY ZRZUTÓW EKRANU")
    print("=" * 60)
    
    # Analiza
    analysis_results = analyze_screenshots(args.folder)
    
    if not analysis_results:
        print("❌ Nie wykonano analizy.")
        return
    
    if not args.analyze_only:
        print("\n" + "=" * 60)
        # Zmiana rozmiaru
        resize_results = resize_screenshots(args.folder, args.scale)
        
        if resize_results:
            print("\n✅ Zakończono przetwarzanie!")

if __name__ == "__main__":
    main()
