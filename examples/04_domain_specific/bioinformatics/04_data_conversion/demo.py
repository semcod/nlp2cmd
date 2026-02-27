#!/usr/bin/env python3
"""
Demo 04: Data Conversion
Konwersja formatów danych bioinformatycznych.
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List

sys.path.append(str(Path(__file__).resolve().parents[2]))


@dataclass
class ConversionCommand:
    """Komenda konwersji formatów."""
    description: str
    command: str


def main():
    print("=" * 60)
    print("Demo 04: Data Conversion")
    print("=" * 60)
    print()
    
    commands: List[ConversionCommand] = [
        ConversionCommand(
            "Konwertuj FASTA do FASTQ (symulacja)",
            "seqkit fx2tab sequences.fasta | awk '{print \"@\"NR\"\\n\"$2\"\\n+\\n\"gensub(/./,\"I\",\"g\",$2)}' > sequences.fastq"
        ),
        ConversionCommand(
            "Konwertuj VCF do TSV",
            "bcftools query -f '%CHROM\\t%POS\\t%REF\\t%ALT\\n' variants.vcf > variants.tsv"
        ),
        ConversionCommand(
            "Konwertuj BAM do SAM",
            "samtools view -h alignments.bam > alignments.sam"
        ),
        ConversionCommand(
            "Konwertuj GFF3 do BED",
            "awk 'BEGIN{OFS=\"\\t\"} !/^#/ {print $1,$4-1,$5,$3,0,$7}' annotations.gff > annotations.bed"
        ),
        ConversionCommand(
            "Konwertuj sekwencje DNA do RNA",
            "seqkit seq --rna sequences.fasta > sequences_rna.fasta"
        ),
    ]
    
    print(f"Konwersja formatów ({len(commands)} komend):\n")
    
    for i, cmd in enumerate(commands, 1):
        print(f"{i}. {cmd.description}")
        print(f"   Komenda: {cmd.command}")
        print()
    
    print("=" * 60)
    print("✅ Koniec demo 04")
    print("=" * 60)


if __name__ == "__main__":
    main()
