#!/usr/bin/env python3
"""
Demo 02: File Processing
Przetwarzanie plików bioinformatycznych.
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List

sys.path.append(str(Path(__file__).resolve().parents[2]))


@dataclass
class FileCommand:
    """Komenda przetwarzania plików."""
    description: str
    command: str


def main():
    print("=" * 60)
    print("Demo 02: File Processing")
    print("=" * 60)
    print()
    
    commands: List[FileCommand] = [
        FileCommand(
            "Wypisz nagłówki plików FASTA",
            "grep '^>' sequences.fasta | head -20"
        ),
        FileCommand(
            "Wyciągnij sekwencje o długości > 1000 bp",
            "seqkit seq -m 1000 sequences.fasta"
        ),
        FileCommand(
            "Podziel plik FASTA na mniejsze części",
            "seqkit split -s 1000 sequences.fasta"
        ),
        FileCommand(
            "Usuń duplikaty sekwencji",
            "seqkit rmdup -s sequences.fasta"
        ),
        FileCommand(
            "Złóż wiele plików FASTA w jeden",
            "cat *.fasta > combined.fasta"
        ),
    ]
    
    print(f"Przetwarzanie plików ({len(commands)} komend):\n")
    
    for i, cmd in enumerate(commands, 1):
        print(f"{i}. {cmd.description}")
        print(f"   Komenda: {cmd.command}")
        print()
    
    print("=" * 60)
    print("✅ Koniec demo 02")
    print("=" * 60)


if __name__ == "__main__":
    main()
