#!/usr/bin/env python3
"""
Demo 04: Results Ranking
Ranking i filtrowanie wyników wyszukiwania.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))


@dataclass
class SearchResult:
    """Wynik wyszukiwania."""
    chunk_id: int
    text: str
    relevance: float
    source: str
    timestamp: str = ""


class ResultsRanker:
    """Ranks and filters search results."""
    
    def __init__(self, min_relevance: float = 0.5):
        self.min_relevance = min_relevance
    
    def rank_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Sortuje wyniki po relevance."""
        # Filtrowanie
        filtered = [r for r in results if r.relevance >= self.min_relevance]
        
        # Sortowanie
        ranked = sorted(filtered, key=lambda x: x.relevance, reverse=True)
        
        return ranked
    
    def diversify_results(self, results: List[SearchResult], max_per_source: int = 2) -> List[SearchResult]:
        """Zapewnia różnorodność źródeł."""
        source_counts: Dict[str, int] = {}
        diversified = []
        
        for result in results:
            source = result.source
            current_count = source_counts.get(source, 0)
            
            if current_count < max_per_source:
                diversified.append(result)
                source_counts[source] = current_count + 1
        
        return diversified
    
    def get_top_k(self, results: List[SearchResult], k: int = 5) -> List[SearchResult]:
        """Zwraca top K wyników."""
        ranked = self.rank_results(results)
        return ranked[:k]


def main():
    print("=" * 60)
    print("Demo 04: Results Ranking")
    print("=" * 60)
    print()
    
    ranker = ResultsRanker(min_relevance=0.4)
    
    # Przykładowe wyniki
    mock_results = [
        SearchResult(1, "Tekst A", 0.95, "doc1.pdf", "2024-01-15"),
        SearchResult(2, "Tekst B", 0.87, "doc1.pdf", "2024-01-15"),
        SearchResult(3, "Tekst C", 0.82, "doc2.pdf", "2024-01-10"),
        SearchResult(4, "Tekst D", 0.75, "doc1.pdf", "2024-01-15"),
        SearchResult(5, "Tekst E", 0.65, "doc3.pdf", "2024-01-08"),
        SearchResult(6, "Tekst F", 0.45, "doc2.pdf", "2024-01-10"),
        SearchResult(7, "Tekst G", 0.35, "doc1.pdf", "2024-01-15"),  # Poniżej threshold
    ]
    
    print("📊 Ranking wyników:\n")
    print(f"Liczba wyników przed filtrowaniem: {len(mock_results)}")
    print(f"Min relevance threshold: {ranker.min_relevance}")
    print()
    
    # Ranking
    ranked = ranker.rank_results(mock_results)
    print(f"Po filtrowaniu: {len(ranked)} wyników")
    print()
    
    print("🏆 Top wyniki:")
    for i, result in enumerate(ranked[:5], 1):
        print(f"  {i}. [{result.relevance:.0%}] {result.source}")
        print(f"      {result.text[:50]}...")
    
    print("\n🔄 Różnorodność źródeł:")
    diversified = ranker.diversify_results(ranked, max_per_source=2)
    print(f"  Po dywersyfikacji: {len(diversified)} wyników")
    
    source_stats = {}
    for r in diversified:
        source_stats[r.source] = source_stats.get(r.source, 0) + 1
    
    for source, count in source_stats.items():
        print(f"  - {source}: {count} wyników")
    
    print("\n📈 Top 3:")
    top_3 = ranker.get_top_k(ranked, k=3)
    for i, result in enumerate(top_3, 1):
        print(f"  {i}. {result.text} ({result.relevance:.0%})")
    
    print()
    print("=" * 60)
    print("✅ Koniec demo 04")
    print("=" * 60)


if __name__ == "__main__":
    main()
