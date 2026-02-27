#!/usr/bin/env python3
"""
Demo 03: LLM Search
Wyszukiwanie informacji w PDF za pomocą LLM.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))


class LLMSearcher:
    """Wyszukiwanie informacji za pomocą LLM."""
    
    def __init__(self):
        self.query_history: List[Dict[str, Any]] = []
    
    def search(self, query: str, chunks: List[str]) -> List[Dict[str, Any]]:
        """Wyszukuje informacje w chunkach."""
        results = []
        
        # Mock wyszukiwania - symulacja semantic search
        for i, chunk in enumerate(chunks):
            # Symulacja relevance score
            relevance = self._calculate_relevance(query, chunk)
            
            if relevance > 0.3:  # Threshold
                results.append({
                    "chunk_id": i,
                    "text": chunk[:200] + "...",
                    "relevance": relevance,
                    "matches": self._extract_matches(query, chunk)
                })
        
        # Sortuj po relevance
        results.sort(key=lambda x: x["relevance"], reverse=True)
        
        # Zapisz w historii
        self.query_history.append({
            "query": query,
            "results_count": len(results),
            "top_relevance": results[0]["relevance"] if results else 0
        })
        
        return results
    
    def _calculate_relevance(self, query: str, text: str) -> float:
        """Mock obliczania relevance."""
        query_words = set(query.lower().split())
        text_words = set(text.lower().split())
        
        if not query_words:
            return 0.0
        
        matches = len(query_words & text_words)
        return min(matches / len(query_words) * 1.5, 1.0)
    
    def _extract_matches(self, query: str, text: str) -> List[str]:
        """Ekstraktuje pasujące fragmenty."""
        query_words = query.lower().split()
        text_lower = text.lower()
        
        matches = []
        for word in query_words:
            if word in text_lower:
                # Znajdź kontekst
                idx = text_lower.index(word)
                start = max(0, idx - 30)
                end = min(len(text), idx + len(word) + 30)
                context = text[start:end]
                matches.append(context)
        
        return matches[:3]  # Max 3 matches


def main():
    print("=" * 60)
    print("Demo 03: LLM Search")
    print("=" * 60)
    print()
    
    searcher = LLMSearcher()
    
    # Przykładowe chunki
    chunks = [
        "Raport finansowy za Q1 2024. Przychód wyniósł 100mln zł."
        "Koszty operacyjne to 60mln zł. Zysk netto: 40mln zł.",
        
        "Dane techniczne produktu X. Waga: 1.5kg. Wymiary: 20x15x10cm."
        "Materiał: aluminium. Cena produkcji: 50zł.",
        
        "Kontakt: Jan Kowalski, email: jan@example.com, tel: 123-456-789."
        "Stanowisko: Dyrektor Techniczny. Dział: R&D.",
    ]
    
    test_queries = [
        "jaki był zysk w Q1",
        "dane techniczne produktu",
        "kontakt do Kowalskiego",
    ]
    
    print("🔍 Wyszukiwanie w dokumentach:\n")
    
    for query in test_queries:
        print(f"❓ Zapytanie: {query}")
        
        results = searcher.search(query, chunks)
        
        if results:
            print(f"   Znaleziono {len(results)} wyników:")
            for i, result in enumerate(results[:2], 1):
                print(f"   {i}. Relevance: {result['relevance']:.2%}")
                print(f"      Tekst: {result['text'][:80]}...")
                if result['matches']:
                    print(f"      Matches: {len(result['matches'])} fragmentów")
        else:
            print("   Brak wyników")
        
        print()
    
    print("📊 Historia zapytań:")
    for entry in searcher.query_history:
        print(f"   - '{entry['query'][:30]}...' -> {entry['results_count']} wyników")
    
    print()
    print("=" * 60)
    print("✅ Koniec demo 03")
    print("=" * 60)


if __name__ == "__main__":
    main()
