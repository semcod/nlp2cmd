"""Vector store for drawing patterns using ChromaDB.

Provides semantic search for drawing instructions based on object descriptions.
Uses sentence-transformers for embeddings and ChromaDB for storage.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger(__name__)


@dataclass
class DrawingPattern:
    """A drawing pattern with metadata and steps."""
    
    name: str
    description: str
    category: str  # animal, vehicle, building, nature, object
    steps: list[dict[str, Any]]  # Drawing actions
    tags: list[str]
    complexity: int  # 1-10
    source: str  # "llm", "manual", "imported"
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "steps": self.steps,
            "tags": self.tags,
            "complexity": self.complexity,
            "source": self.source,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DrawingPattern":
        return cls(
            name=data["name"],
            description=data["description"],
            category=data["category"],
            steps=data["steps"],
            tags=data.get("tags", []),
            complexity=data.get("complexity", 5),
            source=data.get("source", "unknown"),
        )


class DrawingVectorStore:
    """Vector database for storing and retrieving drawing patterns."""
    
    def __init__(self, persist_dir: Optional[str] = None):
        self.persist_dir = Path(persist_dir) if persist_dir else Path.home() / ".nlp2cmd" / "vector_store"
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._client: Optional[Any] = None
        self._collection: Optional[Any] = None
        self._embedding_fn: Optional[Any] = None
        
    def _get_client(self):
        """Lazy initialization of ChromaDB client."""
        if self._client is None:
            try:
                import chromadb
                from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
                
                self._client = chromadb.PersistentClient(path=str(self.persist_dir))
                self._embedding_fn = SentenceTransformerEmbeddingFunction(
                    model_name="all-MiniLM-L6-v2"
                )
                
                # Get or create collection
                self._collection = self._client.get_or_create_collection(
                    name="drawing_patterns",
                    embedding_function=self._embedding_fn,
                    metadata={"hnsw:space": "cosine"}
                )
                log.info("Vector store initialized at %s", self.persist_dir)
                
            except ImportError:
                log.warning("ChromaDB not installed. Run: pip install chromadb")
                return None
        return self._client
    
    def is_available(self) -> bool:
        """Check if vector store is available."""
        try:
            import chromadb  # noqa: F401
            return True
        except ImportError:
            return False
    
    def add_pattern(self, pattern: DrawingPattern) -> bool:
        """Add a drawing pattern to the vector store."""
        if not self._get_client():
            return False
            
        try:
            # Create searchable text from pattern
            search_text = f"{pattern.name} {pattern.description} {' '.join(pattern.tags)} {pattern.category}"
            
            self._collection.add(
                ids=[pattern.name],
                documents=[search_text],
                metadatas=[{
                    "name": pattern.name,
                    "category": pattern.category,
                    "complexity": pattern.complexity,
                    "source": pattern.source,
                    "steps_json": json.dumps(pattern.steps),
                    "description": pattern.description,
                    "tags": json.dumps(pattern.tags),
                }]
            )
            log.info("Added pattern: %s", pattern.name)
            return True
            
        except Exception as e:
            log.error("Failed to add pattern: %s", e)
            return False
    
    def search(
        self, 
        query: str, 
        n_results: int = 5,
        category: Optional[str] = None,
        min_confidence: float = 0.5
    ) -> list[tuple[DrawingPattern, float]]:
        """Search for drawing patterns by semantic similarity.
        
        Returns list of (pattern, confidence) tuples sorted by confidence.
        """
        if not self._get_client():
            return []
            
        try:
            # Build where clause for category filter
            where_clause = None
            if category:
                where_clause = {"category": category}
            
            results = self._collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_clause,
                include=["metadatas", "distances"]
            )
            
            patterns = []
            if results["metadatas"] and results["distances"]:
                for metadata, distance in zip(
                    results["metadatas"][0], 
                    results["distances"][0]
                ):
                    # Convert cosine distance to confidence (0-1)
                    # Chroma uses cosine distance where 0 = identical, 2 = opposite
                    confidence = 1.0 - (distance / 2.0)
                    
                    if confidence >= min_confidence:
                        pattern = DrawingPattern(
                            name=metadata.get("name", query),
                            description=metadata.get("description", ""),
                            category=metadata.get("category", "object"),
                            steps=json.loads(metadata.get("steps_json", "[]")),
                            tags=json.loads(metadata.get("tags", "[]")),
                            complexity=metadata.get("complexity", 5),
                            source=metadata.get("source", "vector_db"),
                        )
                        patterns.append((pattern, confidence))
            
            return sorted(patterns, key=lambda x: x[1], reverse=True)
            
        except Exception as e:
            log.error("Search failed: %s", e)
            return []
    
    def get_pattern(self, name: str) -> Optional[DrawingPattern]:
        """Get a specific pattern by name."""
        if not self._get_client():
            return None
            
        try:
            result = self._collection.get(
                ids=[name],
                include=["metadatas"]
            )
            
            if result["metadatas"]:
                metadata = result["metadatas"][0]
                return DrawingPattern(
                    name=name,
                    description=metadata.get("description", ""),
                    category=metadata.get("category", "object"),
                    steps=json.loads(metadata.get("steps_json", "[]")),
                    tags=json.loads(metadata.get("tags", "[]")),
                    complexity=metadata.get("complexity", 5),
                    source=metadata.get("source", "vector_db"),
                )
            return None
            
        except Exception as e:
            log.error("Get pattern failed: %s", e)
            return None
    
    def list_patterns(self, category: Optional[str] = None) -> list[str]:
        """List all pattern names, optionally filtered by category."""
        if not self._get_client():
            return []
            
        try:
            where_clause = {"category": category} if category else None
            result = self._collection.get(
                where=where_clause,
                include=[]
            )
            return result.get("ids", [])
            
        except Exception as e:
            log.error("List patterns failed: %s", e)
            return []
    
    def delete_pattern(self, name: str) -> bool:
        """Delete a pattern from the store."""
        if not self._get_client():
            return False
            
        try:
            self._collection.delete(ids=[name])
            return True
        except Exception as e:
            log.error("Delete failed: %s", e)
            return False
    
    def count(self) -> int:
        """Get total number of patterns."""
        if not self._get_client():
            return 0
            
        try:
            return self._collection.count()
        except Exception:
            return 0


# Singleton instance
_vector_store: Optional[DrawingVectorStore] = None


def get_vector_store(persist_dir: Optional[str] = None) -> DrawingVectorStore:
    """Get or create the global vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = DrawingVectorStore(persist_dir)
    return _vector_store


def initialize_default_patterns() -> bool:
    """Initialize vector store with default drawing patterns."""
    store = get_vector_store()
    
    if not store.is_available():
        log.warning("Vector store not available, skipping initialization")
        return False
    
    # Check if already initialized
    if store.count() > 0:
        log.info("Vector store already has %d patterns", store.count())
        return True
    
    # Default patterns with detailed descriptions for better search
    default_patterns = [
        DrawingPattern(
            name="ladybug",
            description="biedronka ladybug small red beetle with black spots round body black head six legs insects owad chrząszcz czerwona kropki",
            category="animal",
            steps=[
                {"action": "set_color", "params": {"color": "#FF0000"}},
                {"action": "draw_filled_circle", "params": {"radius": 40, "offset": [0, 0]}},
                {"action": "set_color", "params": {"color": "#000000"}},
                {"action": "draw_filled_circle", "params": {"radius": 20, "offset": [0, -50]}},
                {"action": "draw_circle", "params": {"radius": 8, "offset": [-15, 5]}},
                {"action": "draw_circle", "params": {"radius": 8, "offset": [15, 5]}},
                {"action": "draw_circle", "params": {"radius": 6, "offset": [0, 20]}},
                {"action": "screenshot", "params": {"suffix": "ladybug"}},
            ],
            tags=["insect", "beetle", "red", "spots", "round"],
            complexity=3,
            source="manual"
        ),
        DrawingPattern(
            name="rabbit",
            description="królik zajączek zając rabbit bunny fluffy with long ears small round body cute animal mammal hop",
            category="animal",
            steps=[
                {"action": "set_color", "params": {"color": "#D2B48C"}},
                {"action": "draw_filled_ellipse", "params": {"rx": 50, "ry": 80, "offset": [0, 0]}},
                {"action": "set_color", "params": {"color": "#FFE4B5"}},
                {"action": "draw_filled_circle", "params": {"radius": 35, "offset": [0, -90]}},
                {"action": "set_color", "params": {"color": "#D2B48C"}},
                {"action": "draw_polygon", "params": {"points": [[-15, 0], [-35, -50], [0, -15]], "offset": [-20, -120], "fill": True}},
                {"action": "draw_polygon", "params": {"points": [[15, 0], [35, -50], [0, -15]], "offset": [20, -120], "fill": True}},
                {"action": "set_color", "params": {"color": "#000000"}},
                {"action": "draw_circle", "params": {"radius": 5, "offset": [-12, -95]}},
                {"action": "draw_circle", "params": {"radius": 5, "offset": [12, -95]}},
                {"action": "screenshot", "params": {"suffix": "rabbit"}},
            ],
            tags=["animal", "bunny", "ears", "cute", "mammal", "fluffy"],
            complexity=5,
            source="manual"
        ),
        DrawingPattern(
            name="cat",
            description="kot kotek kotka cat kitten domestic feline pet whiskers pointy ears tail fur meow animal",
            category="animal",
            steps=[
                {"action": "set_color", "params": {"color": "#808080"}},
                {"action": "draw_filled_ellipse", "params": {"rx": 60, "ry": 40, "offset": [0, 30]}},
                {"action": "draw_filled_circle", "params": {"radius": 35, "offset": [0, -35]}},
                {"action": "set_color", "params": {"color": "#696969"}},
                {"action": "draw_polygon", "params": {"points": [[-25, -5], [-40, -45], [-8, -25]], "offset": [0, -35], "fill": True}},
                {"action": "draw_polygon", "params": {"points": [[25, -5], [40, -45], [8, -25]], "offset": [0, -35], "fill": True}},
                {"action": "set_color", "params": {"color": "#32CD32"}},
                {"action": "draw_filled_ellipse", "params": {"rx": 8, "ry": 6, "offset": [-12, -40]}},
                {"action": "draw_filled_ellipse", "params": {"rx": 8, "ry": 6, "offset": [12, -40]}},
                {"action": "set_color", "params": {"color": "#000000"}},
                {"action": "draw_filled_ellipse", "params": {"rx": 3, "ry": 5, "offset": [-12, -40]}},
                {"action": "draw_filled_ellipse", "params": {"rx": 3, "ry": 5, "offset": [12, -40]}},
                {"action": "screenshot", "params": {"suffix": "cat"}},
            ],
            tags=["animal", "pet", "feline", "whiskers", "ears", "meow"],
            complexity=6,
            source="manual"
        ),
        DrawingPattern(
            name="car",
            description="samochód auto car automobile vehicle four wheels driving transportation motor engine pojazd koła",
            category="vehicle",
            steps=[
                {"action": "set_color", "params": {"color": "#FF4444"}},
                {"action": "draw_filled_ellipse", "params": {"rx": 80, "ry": 35, "offset": [0, 0]}},
                {"action": "set_color", "params": {"color": "#87CEEB"}},
                {"action": "draw_filled_ellipse", "params": {"rx": 40, "ry": 20, "offset": [15, -25]}},
                {"action": "set_color", "params": {"color": "#333333"}},
                {"action": "draw_filled_circle", "params": {"radius": 22, "offset": [-45, 25]}},
                {"action": "draw_filled_circle", "params": {"radius": 22, "offset": [45, 25]}},
                {"action": "set_color", "params": {"color": "#888888"}},
                {"action": "draw_circle", "params": {"radius": 10, "offset": [-45, 25]}},
                {"action": "draw_circle", "params": {"radius": 10, "offset": [45, 25]}},
                {"action": "screenshot", "params": {"suffix": "car"}},
            ],
            tags=["vehicle", "auto", "wheels", "drive", "transport"],
            complexity=5,
            source="manual"
        ),
        DrawingPattern(
            name="tree",
            description="drzewo drzewko tree tall plant with trunk branches leaves green nature forest wood las roślina",
            category="nature",
            steps=[
                {"action": "set_color", "params": {"color": "#8B4513"}},
                {"action": "draw_filled_ellipse", "params": {"rx": 18, "ry": 45, "offset": [0, 35]}},
                {"action": "set_color", "params": {"color": "#228B22"}},
                {"action": "draw_filled_ellipse", "params": {"rx": 60, "ry": 50, "offset": [0, -35]}},
                {"action": "draw_filled_ellipse", "params": {"rx": 45, "ry": 40, "offset": [0, -70]}},
                {"action": "draw_filled_circle", "params": {"radius": 20, "offset": [-30, -20]}},
                {"action": "draw_filled_circle", "params": {"radius": 15, "offset": [25, -30]}},
                {"action": "screenshot", "params": {"suffix": "tree"}},
            ],
            tags=["nature", "plant", "green", "forest", "wood", "leaves"],
            complexity=4,
            source="manual"
        ),
        DrawingPattern(
            name="sun",
            description="słońce słoneczko sun bright star in sky yellow orange hot light day sunshine warm ciepło niebo",
            category="nature",
            steps=[
                {"action": "set_color", "params": {"color": "#FFD700"}},
                {"action": "draw_filled_circle", "params": {"radius": 55, "offset": [0, 0]}},
                {"action": "set_color", "params": {"color": "#FFA500"}},
                {"action": "draw_line", "params": {"from_offset": [0, -65], "to_offset": [0, -95]}},
                {"action": "draw_line", "params": {"from_offset": [46, -46], "to_offset": [67, -67]}},
                {"action": "draw_line", "params": {"from_offset": [65, 0], "to_offset": [95, 0]}},
                {"action": "draw_line", "params": {"from_offset": [46, 46], "to_offset": [67, 67]}},
                {"action": "draw_line", "params": {"from_offset": [0, 65], "to_offset": [0, 95]}},
                {"action": "draw_line", "params": {"from_offset": [-46, 46], "to_offset": [-67, 67]}},
                {"action": "draw_line", "params": {"from_offset": [-65, 0], "to_offset": [-95, 0]}},
                {"action": "draw_line", "params": {"from_offset": [-46, -46], "to_offset": [-67, -67]}},
                {"action": "screenshot", "params": {"suffix": "sun"}},
            ],
            tags=["nature", "sky", "yellow", "light", "warm", "day"],
            complexity=4,
            source="manual"
        ),
        DrawingPattern(
            name="house",
            description="dom domek house home building with roof walls door windows shelter residence budynek dach",
            category="building",
            steps=[
                {"action": "set_color", "params": {"color": "#F4A460"}},
                {"action": "draw_filled_ellipse", "params": {"rx": 60, "ry": 50, "offset": [0, 10]}},
                {"action": "set_color", "params": {"color": "#8B4513"}},
                {"action": "draw_polygon", "params": {"points": [[-60, -50], [0, -110], [60, -50]], "offset": [0, 0], "fill": True}},
                {"action": "draw_filled_ellipse", "params": {"rx": 18, "ry": 25, "offset": [0, 15]}},
                {"action": "set_color", "params": {"color": "#87CEEB"}},
                {"action": "draw_filled_circle", "params": {"radius": 12, "offset": [-30, -25]}},
                {"action": "draw_filled_circle", "params": {"radius": 12, "offset": [30, -25]}},
                {"action": "screenshot", "params": {"suffix": "house"}},
            ],
            tags=["building", "home", "roof", "shelter", "residence", "door"],
            complexity=4,
            source="manual"
        ),
        DrawingPattern(
            name="flower",
            description="kwiat kwiatek flower colorful plant with petals bloom blossom garden nature pretty roślina ogród",
            category="nature",
            steps=[
                {"action": "set_color", "params": {"color": "#228B22"}},
                {"action": "draw_filled_ellipse", "params": {"rx": 8, "ry": 60, "offset": [0, 30]}},
                {"action": "set_color", "params": {"color": "#FF69B4"}},
                {"action": "draw_filled_ellipse", "params": {"rx": 20, "ry": 20, "offset": [0, -40]}},
                {"action": "draw_filled_ellipse", "params": {"rx": 20, "ry": 20, "offset": [35, -20]}},
                {"action": "draw_filled_ellipse", "params": {"rx": 20, "ry": 20, "offset": [35, 20]}},
                {"action": "draw_filled_ellipse", "params": {"rx": 20, "ry": 20, "offset": [0, 40]}},
                {"action": "draw_filled_ellipse", "params": {"rx": 20, "ry": 20, "offset": [-35, 20]}},
                {"action": "draw_filled_ellipse", "params": {"rx": 20, "ry": 20, "offset": [-35, -20]}},
                {"action": "set_color", "params": {"color": "#FFD700"}},
                {"action": "draw_filled_circle", "params": {"radius": 18, "offset": [0, 0]}},
                {"action": "screenshot", "params": {"suffix": "flower"}},
            ],
            tags=["nature", "plant", "bloom", "petals", "garden", "colorful"],
            complexity=5,
            source="manual"
        ),
        DrawingPattern(
            name="cloud",
            description="chmura chmurka cloud white fluffy sky weather soft cotton atmosphere moisture niebo pogoda",
            category="nature",
            steps=[
                {"action": "set_color", "params": {"color": "#FFFFFF"}},
                {"action": "draw_filled_circle", "params": {"radius": 35, "offset": [-30, 0]}},
                {"action": "draw_filled_circle", "params": {"radius": 40, "offset": [0, -15]}},
                {"action": "draw_filled_circle", "params": {"radius": 35, "offset": [30, 0]}},
                {"action": "draw_filled_circle", "params": {"radius": 25, "offset": [-20, 10]}},
                {"action": "draw_filled_circle", "params": {"radius": 25, "offset": [20, 10]}},
                {"action": "screenshot", "params": {"suffix": "cloud"}},
            ],
            tags=["nature", "sky", "weather", "fluffy", "white", "soft"],
            complexity=3,
            source="manual"
        ),
        DrawingPattern(
            name="star",
            description="gwiazda gwiazdka star pointy night sky shining celestial sparkle twinkle bright noc niebo",
            category="nature",
            steps=[
                {"action": "set_color", "params": {"color": "#FFD700"}},
                {"action": "draw_filled_circle", "params": {"radius": 15, "offset": [0, -50]}},
                {"action": "draw_filled_circle", "params": {"radius": 15, "offset": [47, -15]}},
                {"action": "draw_filled_circle", "params": {"radius": 15, "offset": [29, 40]}},
                {"action": "draw_filled_circle", "params": {"radius": 15, "offset": [-29, 40]}},
                {"action": "draw_filled_circle", "params": {"radius": 15, "offset": [-47, -15]}},
                {"action": "set_color", "params": {"color": "#FFA500"}},
                {"action": "draw_filled_circle", "params": {"radius": 25, "offset": [0, 0]}},
                {"action": "screenshot", "params": {"suffix": "star"}},
            ],
            tags=["nature", "sky", "night", "bright", "sparkle", "celestial"],
            complexity=3,
            source="manual"
        ),
    ]
    
    added = 0
    for pattern in default_patterns:
        if store.add_pattern(pattern):
            added += 1
    
    log.info("Initialized %d/%d default patterns", added, len(default_patterns))
    return added > 0


def export_patterns_to_file(filepath: str) -> bool:
    """Export all patterns to a JSON file for backup/sharing."""
    store = get_vector_store()
    
    if not store.is_available():
        return False
    
    try:
        names = store.list_patterns()
        patterns = []
        for name in names:
            pattern = store.get_pattern(name)
            if pattern:
                patterns.append(pattern.to_dict())
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(patterns, f, indent=2, ensure_ascii=False)
        
        log.info("Exported %d patterns to %s", len(patterns), filepath)
        return True
        
    except Exception as e:
        log.error("Export failed: %s", e)
        return False


def import_patterns_from_file(filepath: str) -> int:
    """Import patterns from a JSON file."""
    store = get_vector_store()
    
    if not store.is_available():
        return 0
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        added = 0
        for item in data:
            pattern = DrawingPattern.from_dict(item)
            if store.add_pattern(pattern):
                added += 1
        
        log.info("Imported %d patterns from %s", added, filepath)
        return added
        
    except Exception as e:
        log.error("Import failed: %s", e)
        return 0
