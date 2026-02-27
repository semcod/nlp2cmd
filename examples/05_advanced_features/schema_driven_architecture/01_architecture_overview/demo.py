#!/usr/bin/env python3
"""
Demo 01: Architecture Overview
Przegląd architektury LLM as Planner + Typed Actions.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))


def main():
    print("=" * 60)
    print("Demo 01: Architecture Overview")
    print("=" * 60)
    print()
    
    print("🏗️ Architektura: LLM as Planner + Typed Actions\n")
    
    print("📊 6-warstwowa architektura:\n")
    
    layers = [
        ("1️⃣ NLP Layer", "Rozumienie intencji i encji z inputu użytkownika"),
        ("2️⃣ Decision Router", "Decyzja czy potrzebny LLM czy wystarczy reguła"),
        ("3️⃣ LLM Planner", "Generowanie planu wieloetapowego (jeśli potrzeba)"),
        ("4️⃣ Plan Validator", "Walidacja planu względem rejestru akcji"),
        ("5️⃣ Plan Executor", "Wykonanie typowanych akcji"),
        ("6️⃣ Result Aggregator", "Formatowanie i agregacja wyników"),
    ]
    
    for i, (layer, desc) in enumerate(layers, 1):
        print(f"{layer}")
        print(f"   {desc}")
        print()
    
    print("🎯 Kluczowa zasada:")
    print('   "LLM plans. Code executes. System controls."')
    print()
    
    print("📈 Przepływ danych:")
    print("""
   User Input → NLP Layer → Decision Router
                    ↓
            [LLM needed?]
                 /    \
              YES      NO
               ↓        ↓
         LLM Planner  Rule Action
               ↓        ↓
         Plan Validator  ↓
               ↓        ↓
         Plan Executor ←-┘
               ↓
         Result Aggregator
               ↓
          Final Output
""")
    
    print()
    print("=" * 60)
    print("✅ Koniec demo 01")
    print("=" * 60)


if __name__ == "__main__":
    main()
