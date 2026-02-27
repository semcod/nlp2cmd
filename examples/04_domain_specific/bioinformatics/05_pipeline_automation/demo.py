#!/usr/bin/env python3
"""
Demo 05: Pipeline Automation
Automatyzacja pipeline'ów bioinformatycznych.
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List

sys.path.append(str(Path(__file__).resolve().parents[2]))


@dataclass
class PipelineStep:
    """Krok w pipeline."""
    step_number: int
    description: str
    command: str


def main():
    print("=" * 60)
    print("Demo 05: Pipeline Automation")
    print("=" * 60)
    print()
    
    pipeline: List[PipelineStep] = [
        PipelineStep(
            1, "Kontrola jakości (QC)",
            "fastqc reads.fastq -o qc_results/"
        ),
        PipelineStep(
            2, "Przycinanie sekwencji",
            "trimmomatic SE reads.fastq trimmed.fastq SLIDINGWINDOW:4:20"
        ),
        PipelineStep(
            3, "Mapowanie do referencji",
            "bwa mem reference.fa trimmed.fastq > aligned.sam"
        ),
        PipelineStep(
            4, "Konwersja do BAM",
            "samtools view -b aligned.sam > aligned.bam"
        ),
        PipelineStep(
            5, "Sortowanie BAM",
            "samtools sort aligned.bam -o aligned.sorted.bam"
        ),
        PipelineStep(
            6, "Indeksowanie",
            "samtools index aligned.sorted.bam"
        ),
        PipelineStep(
            7, "Wariant calling",
            "bcftools mpileup -f reference.fa aligned.sorted.bam | bcftools call -mv -Oz -o variants.vcf.gz"
        ),
    ]
    
    print(f"Pipeline analizy ({len(pipeline)} kroków):\n")
    
    for step in pipeline:
        print(f"{step.step_number}. {step.description}")
        print(f"   Komenda: {step.command}")
        print()
    
    print("📝 Pełny pipeline jako skrypt bash:")
    print("""
#!/bin/bash
# Pipeline analizy NGS
set -e

# QC
fastqc reads.fastq -o qc_results/

# Trimming
trimmomatic SE reads.fastq trimmed.fastq SLIDINGWINDOW:4:20

# Alignment
bwa mem reference.fa trimmed.fastq > aligned.sam

# Konwersja i sortowanie
samtools view -b aligned.sam | samtools sort - aligned.sorted
samtools index aligned.sorted.bam

# Variant calling
bcftools mpileup -f reference.fa aligned.sorted.bam | \
  bcftools call -mv -Oz -o variants.vcf.gz

# Statystyki
bcftools stats variants.vcf.gz > stats.txt
""")
    
    print("=" * 60)
    print("✅ Koniec demo 05")
    print("=" * 60)


if __name__ == "__main__":
    main()
