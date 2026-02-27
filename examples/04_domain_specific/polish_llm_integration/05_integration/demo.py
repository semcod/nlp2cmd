#!/usr/bin/env python3
"""
Demo 05: Integration
Integracja wszystkich komponentów - pełny pipeline.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))


class PDFExtractor:
    def extract_text(self, pdf_path: str) -> str:
        return f"Mock text from {pdf_path}"


class TextChunker:
    def __init__(self, chunk_size: int = 1000):
        self.chunk_size = chunk_size
    
    def chunk_text(self, text: str) -> List[str]:
        return [text[i:i+self.chunk_size] for i in range(0, len(text), self.chunk_size)]


class LLMSearcher:
    def search(self, query: str, chunks: List[str]) -> List[Dict]:
        return [{"chunk_id": i, "relevance": 0.8} for i in range(min(3, len(chunks)))]


class PDFSearchPipeline:
    """Pełny pipeline wyszukiwania w PDF."""
    
    def __init__(self):
        self.extractor = PDFExtractor()
        self.chunker = TextChunker(chunk_size=500)
        self.searcher = LLMSearcher()
    
    def search_pdf(self, pdf_path: str, query: str) -> Dict[str, Any]:
        """Wyszukuje informacje w PDF."""
        # Step 1: Ekstrakcja
        text = self.extractor.extract_text(pdf_path)
        
        # Step 2: Chunking
        chunks = self.chunker.chunk_text(text)
        
        # Step 3: Wyszukiwanie
        results = self.searcher.search(query, chunks)
        
        return {
            "pdf": pdf_path,
            "query": query,
            "chunks_processed": len(chunks),
            "results_found": len(results),
            "top_results": results[:3]
        }
    
    def batch_search(self, pdf_paths: List[str], query: str) -> List[Dict[str, Any]]:
        """Wyszukuje w wielu PDF."""
        return [self.search_pdf(pdf, query) for pdf in pdf_paths]


def main():
    print("=" * 60)
    print("Demo 05: Integration")
    print("=" * 60)
    print()
    
    pipeline = PDFSearchPipeline()
    
    # Pojedyncze wyszukiwanie
    print("🔍 Pojedyncze wyszukiwanie:\n")
    
    result = pipeline.search_pdf("document.pdf", "jaki był zysk")
    print(f"PDF: {result['pdf']}")
    print(f"Query: {result['query']}")
    print(f"Przetworzono chunków: {result['chunks_processed']}")
    print(f"Znaleziono wyników: {result['results_found']}")
    print(f"Top wyniki: {result['top_results']}")
    print()
    
    # Batch wyszukiwanie
    print("📚 Batch wyszukiwanie:\n")
    
    pdf_files = ["doc1.pdf", "doc2.pdf", "doc3.pdf"]
    batch_results = pipeline.batch_search(pdf_files, "dane kontaktowe")
    
    for r in batch_results:
        print(f"  {r['pdf']}: {r['results_found']} wyników")
    
    print("\n🔄 Pipeline flow:")
    print("   PDF → Extractor → Chunker → Searcher → Results")
    
    print("\n💡 Zalety pipeline:")
    print("   • Modularność - każdy krok niezależny")
    print("   • Łatwe testowanie i debugowanie")
    print("   • Możliwość cachowania między krokami")
    print("   • Proste rozszerzanie o nowe kroki")
    
    print()
    print("=" * 60)
    print("✅ Koniec demo 05")
    print("=" * 60)


if __name__ == "__main__":
    main()
