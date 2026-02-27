#!/usr/bin/env python3
"""
Porównanie zrzutów ekranu - wykrywa różnice między kolejnymi zrzutami.
Używa porównania pikseli i różnic strukturalnych.
"""

import os
import sys
from pathlib import Path
from PIL import Image, ImageChops, ImageStat
import hashlib

def image_similarity(img1, img2):
    """Oblicza podobieństwo między dwoma obrazami (0-100%)."""
    # Upewnij się że obrazy mają ten sam rozmiar
    if img1.size != img2.size:
        img2 = img2.resize(img1.size, Image.Resampling.LANCZOS)
    
    # Oblicz różnicę
    diff = ImageChops.difference(img1, img2)
    
    # Oblicz średnią różnicę
    stat = ImageStat.Stat(diff)
    avg_diff = sum(stat.mean) / len(stat.mean)
    
    # Konwertuj na podobieństwo (0-100%)
    max_diff = 255.0
    similarity = 100.0 * (1.0 - avg_diff / max_diff)
    
    return similarity

def detect_changes(folder="test_screenshots"):
    """Wykrywa zmiany między kolejnymi zrzutami ekranu."""
    folder_path = Path(folder)
    
    if not folder_path.exists():
        print(f"❌ Folder {folder} nie istnieje!")
        return
    
    # Znajdź wszystkie PNG, posortowane według czasu modyfikacji
    png_files = sorted(folder_path.glob("screenshot_*.png"), key=lambda p: p.stat().st_mtime)
    
    if len(png_files) < 2:
        print(f"❌ Potrzeba co najmniej 2 zrzutów do porównania (znaleziono: {len(png_files)})")
        return
    
    print(f"🔍 Analiza zmian między {len(png_files)} zrzutami ekranu")
    print("=" * 80)
    
    prev_img = None
    prev_name = None
    changes_detected = []
    
    for i, png_file in enumerate(png_files):
        with Image.open(png_file) as img:
            print(f"\n📸 {i+1}. {png_file.name}")
            print(f"    Rozmiar: {img.size[0]}x{img.size[1]} px")
            
            if prev_img is not None:
                # Porównaj z poprzednim
                similarity = image_similarity(prev_img, img)
                difference = 100.0 - similarity
                
                print(f"    Różnica od poprzedniego: {difference:.2f}%")
                
                if difference > 0.1:  # Więcej niż 0.1% różnicy
                    status = "🔴 ZMIANA WYKRYTA" if difference > 5.0 else "🟡 Niewielka zmiana"
                    print(f"    {status}")
                    changes_detected.append({
                        'from': prev_name,
                        'to': png_file.name,
                        'difference': difference
                    })
                else:
                    print(f"    ✅ Identyczny jak poprzedni")
            
            prev_img = img.copy()
            prev_name = png_file.name
    
    # Podsumowanie
    print("\n" + "=" * 80)
    print("📊 PODSUMOWANIE ZMIAN:")
    
    if changes_detected:
        print(f"Wykryto {len(changes_detected)} zmian:")
        for change in changes_detected:
            print(f"  • {change['from']} → {change['to']}: {change['difference']:.2f}% różnicy")
    else:
        print("❌ Nie wykryto żadnych zmian - wszystkie zrzuty identyczne!")
        print("    To może oznaczać, że ekran nie był aktywnie używany podczas testów.")
    
    return changes_detected

def create_diff_images(folder="test_screenshots", output_folder="test_screenshots/diffs"):
    """Tworzy obrazy różnic między kolejnymi zrzutami."""
    folder_path = Path(folder)
    output_path = Path(output_folder)
    output_path.mkdir(exist_ok=True, parents=True)
    
    png_files = sorted(folder_path.glob("screenshot_*.png"), key=lambda p: p.stat().st_mtime)
    
    if len(png_files) < 2:
        return
    
    print(f"\n🔧 Tworzenie obrazów różnic...")
    
    for i in range(len(png_files) - 1):
        with Image.open(png_files[i]) as img1, Image.open(png_files[i+1]) as img2:
            # Upewnij się że mają ten sam rozmiar
            if img1.size != img2.size:
                img2 = img2.resize(img1.size, Image.Resampling.LANCZOS)
            
            # Utwórz obraz różnic
            diff = ImageChops.difference(img1, img2)
            
            # Zwiększ kontrast różnic
            diff_enhanced = diff.point(lambda p: p * 10)  # 10x kontrast
            
            # Zapisz
            diff_name = f"diff_{i+1}_to_{i+2}.png"
            diff_path = output_path / diff_name
            diff_enhanced.save(diff_path)
            
            print(f"  ✓ {diff_name}")
    
    print(f"  Obrazy różnic zapisane w: {output_path}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Porównanie zrzutów ekranu")
    parser.add_argument("--folder", default="test_screenshots", help="Folder ze zrzutami")
    parser.add_argument("--create-diffs", action="store_true", help="Utwórz obrazy różnic")
    
    args = parser.parse_args()
    
    print("🖼️  ANALIZA ZRZUTÓW EKRANU")
    print("=" * 80)
    
    changes = detect_changes(args.folder)
    
    if args.create_diffs:
        create_diff_images(args.folder)
    
    print("\n✅ Analiza zakończona!")
    
    # Exit code: 0 jeśli znaleziono zmiany (oczekiwane), 1 jeśli nie
    sys.exit(0 if changes else 1)

if __name__ == "__main__":
    main()
