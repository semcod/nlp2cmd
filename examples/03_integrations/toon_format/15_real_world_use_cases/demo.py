#!/usr/bin/env python3
"""
Demo 15: Real World Use Cases
Rzeczywiste przypadki użycia TOON.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))


def main():
    print("=" * 60)
    print("Demo 15: Real World Use Cases")
    print("=" * 60)
    print()
    
    print("🌍 Rzeczywiste przypadki użycia TOON:\n")
    
    print("1️⃣ System zarządzania konfiguracją:")
    print("""
# Użycie: Centralne zarządzanie komendami w organizacji

- Jedno źródło prawdy dla wszystkich komend
- Wersjonowanie zmian w komendach
- Dystrybucja przez CDN
- Rollback do poprzednich wersji
""")
    
    print("2️⃣ CLI Tool z dynamicznymi komendami:")
    print("""
# Użycie: Narzędzie CLI z ładowaniem komend z TOON

- Użytkownicy mogą dodawać własne komendy
- Plugin system oparty na TOON
- Hot-reload bez restartu
- Współdzielenie komend w zespole
""")
    
    print("3️⃣ System dokumentacji:")
    print("""
# Użycie: Automatyczna dokumentacja komend

- Generowanie strony HTML z komendami
- Wyszukiwalna baza wiedzy
- Przykłady użycia dla każdej komendy
- Automatyczne aktualizacje
""")
    
    print("4️⃣ Test framework:")
    print("""
# Użycie: Testowanie komend

- Walidacja szablonów przed deploymentem
- Regression testing dla zmian komend
- Benchmarking wydajności
- CI/CD integration
""")
    
    print("5️⃣ API Gateway:")
    print("""
# Użycie: REST API oparte na TOON

- Endpointy generowane z komend TOON
- Automatyczna walidacja parametrów
- Rate limiting per komenda
- Audit logging
""")
    
    print()
    print("💡 Wspólne korzyści:")
    print("   ✓ Standaryzacja formatu")
    print("   ✓ Łatwa migracja między systemami")
    print("   ✓ Wsparcie dla wielu języków programowania")
    print("   ✓ Rozszerzalność przez dodawanie pól")
    
    print()
    print("=" * 60)
    print("✅ Koniec demo 15")
    print("=" * 60)


if __name__ == "__main__":
    main()
