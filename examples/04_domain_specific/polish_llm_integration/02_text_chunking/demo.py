#!/usr/bin/env python3
"""
Demo 02: Text Chunking
Dzielenie tekstu na mniejsze fragmenty (chunki) dla LLM.
"""

import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))


class TextChunker:
    """Dzieli tekst na fragmenty odpowiednie dla LLM."""
    
    def __init__(self, chunk_size: int = 1000, overlap: int = 100):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk_text(self, text: str) -> List[str]:
        """Dzieli tekst na chunki ze względnieniem zdań."""
        chunks = []
        sentences = text.split(". ")
        
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            if current_size + sentence_size > self.chunk_size and current_chunk:
                # Zapisz aktualny chunk
                chunks.append(". ".join(current_chunk) + ".")
                # Zachowaj overlap
                overlap_sentences = current_chunk[-2:] if len(current_chunk) >= 2 else current_chunk
                current_chunk = overlap_sentences
                current_size = sum(len(s) for s in current_chunk)
            
            current_chunk.append(sentence)
            current_size += sentence_size
        
        # Dodaj ostatni chunk
        if current_chunk:
            chunks.append(". ".join(current_chunk) + ".")
        
        return chunks
    
    def chunk_with_metadata(self, text: str, source: str) -> List[dict]:
        """Dzieli tekst z zachowaniem metadanych."""
        chunks = self.chunk_text(text)
        return [
            {
                "text": chunk,
                "source": source,
                "chunk_id": i,
                "total_chunks": len(chunks)
            }
            for i, chunk in enumerate(chunks)
        ]


def main():
    print("=" * 60)
    print("Demo 02: Text Chunking")
    print("=" * 60)
    print()
    
    chunker = TextChunker(chunk_size=500, overlap=50)
    
    # Przykładowy długi tekst
    sample_text = """
    Pierwsze zdanie dokumentu. Drugie zdanie zawiera ważne informacje.
    Trzecie zdanie jest krótkie. Czwarte zdanie rozszerza temat.
    Piąte zdanie podsumowuje pierwszą część. Szóste zdanie zaczyna nową sekcję.
    Siódme zdanie zawiera szczegóły techniczne. Ósme zdanie przedstawia przykład.
    Dziewiąte zdanie omawia zastosowanie. Dziesiąte zdanie kończy rozdział.
    """ * 10  # Powiel dla dłuższego tekstu
    
    print("✂️  Chunking tekstu:\n")
    
    chunks = chunker.chunk_text(sample_text)
    print(f"Liczba chunków: {len(chunks)}")
    print(f"Rozmiar chunku: {chunker.chunk_size} znaków")
    print(f"Overlap: {chunker.overlap} znaków")
    print()
    
    print("📄 Przykładowe chunki:")
    for i, chunk in enumerate(chunks[:3], 1):
        print(f"\nChunk {i}/{len(chunks)}:")
        print(f"  Długość: {len(chunk)} znaków")
        print(f"  Treść: {chunk[:100]}...")
    
    print("\n\n📝 Chunki z metadanymi:")
    chunks_with_meta = chunker.chunk_with_metadata(sample_text, "document.pdf")
    for chunk_meta in chunks_with_meta[:2]:
        print(f"\n  Chunk {chunk_meta['chunk_id']}/{chunk_meta['total_chunks']}")
        print(f"  Źródło: {chunk_meta['source']}")
        print(f"  Długość: {len(chunk_meta['text'])} znaków")
    
    print()
    print("=" * 60)
    print("✅ Koniec demo 02")
    print("=" * 60)


if __name__ == "__main__":
    main()
