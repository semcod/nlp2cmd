#!/usr/bin/env python3
"""
Demo 03: BLAST Operations
Operacje wyszukiwania BLAST.
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List

sys.path.append(str(Path(__file__).resolve().parents[2]))


@dataclass
class BlastCommand:
    """Komenda BLAST."""
    description: str
    command: str


def main():
    print("=" * 60)
    print("Demo 03: BLAST Operations")
    print("=" * 60)
    print()
    
    commands: List[BlastCommand] = [
        BlastCommand(
            "Utwórz bazę danych BLAST",
            "makeblastdb -in sequences.fasta -dbtype nucl -out mydb"
        ),
        BlastCommand(
            "Wyszukaj podobne sekwencje (nucleotide)",
            "blastn -db mydb -query query.fasta -out results.txt"
        ),
        BlastCommand(
            "Wyszukaj podobne białka",
            "blastp -db protein_db -query protein.fasta -out protein_results.txt"
        ),
        BlastCommand(
            "Wyszukaj z opcją e-value < 0.001",
            "blastn -db mydb -query query.fasta -evalue 0.001 -outfmt 6"
        ),
        BlastCommand(
            "Wyszukaj i pokaż top 10 wyników",
            "blastn -db mydb -query query.fasta -max_target_seqs 10"
        ),
    ]
    
    print(f"Operacje BLAST ({len(commands)} komend):\n")
    
    for i, cmd in enumerate(commands, 1):
        print(f"{i}. {cmd.description}")
        print(f"   Komenda: {cmd.command}")
        print()
    
    print("=" * 60)
    print("✅ Koniec demo 03")
    print("=" * 60)


if __name__ == "__main__":
    main()
