#!/usr/bin/env python3
"""
Demo 01: PDF Extraction
Ekstrakcja tekstu z plików PDF.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))


class PDFExtractor:
    """Ekstraktor tekstu z PDF."""
    
    def __init__(self):
        self.pdf_cache: Dict[str, str] = {}
    
    def extract_text(self, pdf_path: str) -> str:
        """Ekstraktuje tekst z PDF."""
        if pdf_path in self.pdf_cache:
            return self.pdf_cache[pdf_path]
        
        # Mock ekstrakcji
        mock_text = f"Mock text from {Path(pdf_path).name}\n"
        mock_text += "This is sample content from PDF file.\n"
        mock_text += "Contains multiple paragraphs and formatting.\n"
        
        self.pdf_cache[pdf_path] = mock_text
        return mock_text
    
    def extract_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """Ekstraktuje metadata z PDF."""
        return {
            "title": Path(pdf_path).stem,
            "pages": 10,
            "author": "Unknown",
            "creation_date": "2024-01-01"
        }
    
    def batch_extract(self, pdf_paths: List[str]) -> Dict[str, str]:
        """Ekstraktuje tekst z wielu PDF."""
        results = {}
        for path in pdf_paths:
            try:
                results[path] = self.extract_text(path)
            except Exception as e:
                results[path] = f"Error: {e}"
        return results


def main():
    print("=" * 60)
    print("Demo 01: PDF Extraction")
    print("=" * 60)
    print()
    
    extractor = PDFExtractor()
    
    # Przykładowe pliki
    sample_pdfs = [
        "/path/to/document1.pdf",
        "/path/to/document2.pdf",
        "/path/to/report.pdf"
    ]
    
    print("📄 Ekstrakcja tekstu z PDF:\n")
    
    for pdf_path in sample_pdfs:
        print(f"📑 Plik: {Path(pdf_path).name}")
        
        # Metadata
        metadata = extractor.extract_metadata(pdf_path)
        print(f"   Metadata: {metadata}")
        
        # Tekst
        text = extractor.extract_text(pdf_path)
        preview = text[:100].replace("\n", " ")
        print(f"   Tekst (preview): {preview}...")
        print()
    
    print("📊 Batch processing:")
    batch_results = extractor.batch_extract(sample_pdfs)
    print(f"   Przetworzono {len(batch_results)} plików")
    
    print()
    print("=" * 60)
    print("✅ Koniec demo 01")
    print("=" * 60)


if __name__ == "__main__":
    main()
