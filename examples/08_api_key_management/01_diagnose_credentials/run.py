#!/usr/bin/env python3
"""
Example 01: Diagnose Credentials

Sprawdza dostępność haseł i kluczy API dla wszystkich znanych providerów.
Pokazuje które serwisy mają zapisane hasła w Firefox, klucze w .env,
i które mogą być w pełni zautomatyzowane.

Użycie:
    python run.py
    python run.py --verbose
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))


def main():
    parser = argparse.ArgumentParser(description="Diagnose API provider credentials")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed info")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    from nlp2cmd.automation.password_store import get_password_store

    store = get_password_store()

    if args.json:
        import json
        results = store.diagnose_providers()
        # Remove sensitive data
        for r in results:
            r.pop("login_user", None)
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        store.print_diagnosis(verbose=args.verbose)

        # Show actionable examples
        results = store.diagnose_providers()
        green = [r for r in results if r["has_api_key"] and r["has_login"]]
        yellow = [r for r in results if r["has_login"] and not r["has_api_key"]]

        if green or yellow:
            print("\n" + "=" * 60)
            print("Przykłady komend do uruchomienia:")
            print("=" * 60)

        for r in green:
            svc = r["service"]
            print(f'\n  # {svc} — w pełni automatyczne (klucz + login)')
            print(f'  nlp2cmd -r "wyciągnij klucz API z {svc} i zapisz do .env"')

        for r in yellow:
            svc = r["service"]
            print(f'\n  # {svc} — auto-login, ale wymaga stworzenia klucza')
            print(f'  nlp2cmd -r "otwórz {svc}, zaloguj się, stwórz klucz API i zapisz do .env"')

        no_cred = [r for r in results if not r["has_api_key"] and not r["has_login"]]
        if no_cred:
            print(f'\n  # Brak danych logowania dla: {", ".join(r["service"] for r in no_cred)}')
            print('  # Tip: Zaloguj się na te serwisy w Firefox, potem uruchom ponownie')


if __name__ == "__main__":
    main()
