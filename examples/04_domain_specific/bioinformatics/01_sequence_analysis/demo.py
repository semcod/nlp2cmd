#!/usr/bin/env python3
"""
Demo 01: Sequence Analysis
Analiza sekwencji biologicznych.
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List

sys.path.append(str(Path(__file__).resolve().parents[2]))


@dataclass
class SequenceCommand:
    """Komenda do analizy sekwencji."""
    query: str
    command: str
    tool: str


def main():
    print("=" * 60)
    print("Demo 01: Sequence Analysis")
    print("=" * 60)
    print()
    
    commands: List[SequenceCommand] = [
        SequenceCommand(
            "Znajdź sekwencje FASTA w pliku sequences.fasta",
            "grep -c '^>' sequences.fasta",
            "grep"
        ),
        SequenceCommand(
            "Policz długość sekwencji",
            "awk '/^>/ {if (seqlen) print seqlen; seqlen=0} !/^>/ {seqlen+=length} END {print seqlen}' sequences.fasta",
            "awk"
        ),
        SequenceCommand(
            "Konwertuj FASTA do formatu tabular",
            "seqkit fx2tab sequences.fasta",
            "seqkit"
        ),
        SequenceCommand(
            "Wyszukaj motyw DNA 'ATG' w sekwencjach",
            "seqkit grep -s -p 'ATG' sequences.fasta",
            "seqkit"
        ),
        SequenceCommand(
            "Odwróć i uzupełnij sekwencje",
            "seqkit revcomp sequences.fasta",
            "seqkit"
        ),
    ]
    
    print(f"Przykłady analizy sekwencji ({len(commands)} komend):\n")
    
    for i, cmd in enumerate(commands, 1):
        print(f"{i}. {cmd.query}")
        print(f"   Narzędzie: {cmd.tool}")
        print(f"   Komenda: {cmd.command}")
        print()
    
    print("=" * 60)
    print("✅ Koniec demo 01")
    print("=" * 60)


if __name__ == "__main__":
    main()
