"""Entity Resolution - Steps 3a-3e.

3a. Entity types to extract (function, class, module, variable, file)
3b. Name matching threshold
3c. Context-aware disambiguation
3d. Hierarchical resolution (class.method -> method)
3e. Alias resolution (short names -> qualified names)
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from difflib import SequenceMatcher

from .config import EntityResolutionConfig


@dataclass
class Entity:
    """Resolved entity."""
    name: str
    qualified_name: str
    entity_type: str  # function, class, module, variable, file
    confidence: float
    source_file: Optional[str] = None
    line_number: Optional[int] = None
    context: Optional[str] = None
    aliases: List[str] = field(default_factory=list)


@dataclass
class EntityResolutionResult:
    """Result of entity resolution."""
    query: str
    entities: List[Entity] = field(default_factory=list)
    primary_entity: Optional[Entity] = None
    disambiguation_needed: bool = False
    
    def get_by_type(self, entity_type: str) -> List[Entity]:
        """Get entities of specific type."""
        return [e for e in self.entities if e.entity_type == entity_type]
    
    def get_best_match(self) -> Optional[Entity]:
        """Get highest confidence entity."""
        if not self.entities:
            return None
        return max(self.entities, key=lambda e: e.confidence)


class EntityResolver:
    """Resolve entities (functions, classes, etc.) from queries."""
    
    def __init__(
        self,
        config: Optional[EntityResolutionConfig] = None,
        codebase_entities: Optional[Dict[str, List[Entity]]] = None
    ):
        self.config = config or EntityResolutionConfig()
        # Initialize with empty dict, populate from codebase analysis
        self.codebase_entities = codebase_entities or {}
    
    def resolve(
        self,
        query: str,
        context: Optional[str] = None,
        expected_types: Optional[List[str]] = None
    ) -> EntityResolutionResult:
        """Resolve entities from query (steps 3a-3e)."""
        result = EntityResolutionResult(query=query)
        
        # Determine expected entity types
        if expected_types is None:
            expected_types = self.config.entity_types
        
        # 3a. Extract candidate entities by type
        candidates = []
        for entity_type in expected_types:
            type_candidates = self._extract_candidates(query, entity_type)
            candidates.extend(type_candidates)
        
        # 3b. Match with threshold
        threshold = self.config.name_match_threshold
        matches = [c for c in candidates if c.confidence >= threshold]
        
        # 3c. Context-aware disambiguation
        if context and self.config.context_disambiguation:
            matches = self._disambiguate(matches, context)
        
        # 3d. Hierarchical resolution
        if self.config.hierarchical_resolution:
            matches = self._resolve_hierarchical(matches)
        
        # 3e. Alias resolution
        if self.config.alias_resolution:
            matches = self._resolve_aliases(matches)
        
        result.entities = matches
        
        # Determine if disambiguation needed
        if len(matches) > 1:
            top_confidences = [m.confidence for m in matches[:2]]
            if abs(top_confidences[0] - top_confidences[1]) < 0.1:
                result.disambiguation_needed = True
        
        # Set primary entity
        if matches:
            result.primary_entity = matches[0]
        
        return result
    
    def _extract_candidates(self, query: str, entity_type: str) -> List[Entity]:
        """3a. Extract candidate entities of given type from query."""
        candidates = []
        
        # Get entities from codebase
        type_entities = self.codebase_entities.get(entity_type, [])
        
        for entity in type_entities:
            # Calculate name similarity
            similarity = self._name_similarity(query, entity.name)
            
            if similarity > 0.5:  # Minimum threshold for candidacy
                candidate = Entity(
                    name=entity.name,
                    qualified_name=entity.qualified_name,
                    entity_type=entity_type,
                    confidence=similarity,
                    source_file=entity.source_file,
                    line_number=entity.line_number,
                )
                candidates.append(candidate)
        
        # Also extract potential entities from query patterns
        pattern_matches = self._extract_from_patterns(query, entity_type)
        candidates.extend(pattern_matches)
        
        return candidates
    
    def _extract_from_patterns(self, query: str, entity_type: str) -> List[Entity]:
        """Extract entities using regex patterns."""
        candidates = []
        
        if entity_type == "function":
            # Match patterns like: function_name(), call function_name, etc.
            patterns = [
                r'\b(\w+)\s*\(',  # function_name(
                r'function\s+(\w+)',
                r'call\s+(\w+)',
                r'wywołaj\s+(\w+)',  # Polish
            ]
        elif entity_type == "class":
            patterns = [
                r'class\s+(\w+)',
                r'klasa\s+(\w+)',
                r'(\w+)\s*\.\s*\w+\s*\(',  # ClassName.method()
            ]
        elif entity_type == "file":
            patterns = [
                r'(\w+\.py)\b',
                r'file\s+(\w+)',
                r'plik\s+(\w+)',
            ]
        else:
            patterns = [r'\b(\w+)\b']
        
        for pattern in patterns:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                name = match.group(1)
                candidates.append(Entity(
                    name=name,
                    qualified_name=name,
                    entity_type=entity_type,
                    confidence=0.7,  # Pattern-based confidence
                ))
        
        return candidates
    
    def _disambiguate(
        self,
        candidates: List[Entity],
        context: str
    ) -> List[Entity]:
        """3c. Disambiguate entities using context."""
        if not candidates:
            return candidates
        
        context_lower = context.lower()
        
        # Boost confidence for entities mentioned in context
        for candidate in candidates:
            # Check if entity name or related terms appear in context
            if candidate.name.lower() in context_lower:
                candidate.confidence = min(1.0, candidate.confidence + 0.15)
            
            # Check if source file is mentioned in context
            if candidate.source_file:
                file_name = candidate.source_file.split('/')[-1].lower()
                if file_name in context_lower:
                    candidate.confidence = min(1.0, candidate.confidence + 0.1)
        
        # Re-sort by updated confidence
        return sorted(candidates, key=lambda e: e.confidence, reverse=True)
    
    def _resolve_hierarchical(self, candidates: List[Entity]) -> List[Entity]:
        """3d. Resolve hierarchical names (Class.method -> method)."""
        resolved = []
        
        for candidate in candidates:
            # Check if name contains hierarchy separator
            if '.' in candidate.name:
                parts = candidate.name.split('.')
                
                # Create resolved entity with short name
                short_name = parts[-1]
                resolved_entity = Entity(
                    name=short_name,
                    qualified_name=candidate.qualified_name,
                    entity_type=candidate.entity_type,
                    confidence=candidate.confidence,
                    source_file=candidate.source_file,
                    line_number=candidate.line_number,
                    context=candidate.context,
                    aliases=candidate.aliases + [candidate.name]
                )
                resolved.append(resolved_entity)
                
                # Also keep original
                resolved.append(candidate)
            else:
                resolved.append(candidate)
        
        return resolved
    
    def _resolve_aliases(self, candidates: List[Entity]) -> List[Entity]:
        """3e. Resolve aliases to canonical names."""
        resolved = []
        
        for candidate in candidates:
            # Check for known aliases
            if candidate.aliases:
                # Prefer qualified name as canonical
                if len(candidate.qualified_name) > len(candidate.name):
                    candidate.aliases.append(candidate.name)
                    candidate.name = candidate.qualified_name
            
            resolved.append(candidate)
        
        return resolved
    
    def _name_similarity(self, query: str, name: str) -> float:
        """Calculate similarity between query and entity name."""
        # Direct match
        if name.lower() in query.lower():
            return 0.95
        
        if query.lower() in name.lower():
            return 0.9
        
        # Fuzzy match
        return SequenceMatcher(None, query.lower(), name.lower()).ratio()
    
    def load_from_analysis(self, analysis_result) -> None:
        """Load entities from code analysis result."""
        self.codebase_entities = {
            "function": [],
            "class": [],
            "module": [],
        }
        
        # Load functions
        for func_name, func_info in analysis_result.functions.items():
            entity = Entity(
                name=func_info.name,
                qualified_name=func_info.qualified_name,
                entity_type="function",
                confidence=1.0,
                source_file=func_info.file,
                line_number=func_info.line,
            )
            self.codebase_entities["function"].append(entity)
        
        # Load classes
        for class_name, class_info in analysis_result.classes.items():
            entity = Entity(
                name=class_info.name,
                qualified_name=class_info.qualified_name,
                entity_type="class",
                confidence=1.0,
                source_file=class_info.file,
                line_number=class_info.line,
            )
            self.codebase_entities["class"].append(entity)
        
        # Load modules
        for mod_name, mod_info in analysis_result.modules.items():
            entity = Entity(
                name=mod_info.name,
                qualified_name=mod_info.name,
                entity_type="module",
                confidence=1.0,
                source_file=mod_info.file,
            )
            self.codebase_entities["module"].append(entity)
    
    # Individual step methods
    def step_3a_extract_entities(self, query: str, entity_type: str) -> List[Entity]:
        """Step 3a: Extract entities by type."""
        return self._extract_candidates(query, entity_type)
    
    def step_3b_match_threshold(self, candidates: List[Entity]) -> List[Entity]:
        """Step 3b: Apply name matching threshold."""
        threshold = self.config.name_match_threshold
        return [c for c in candidates if c.confidence >= threshold]
    
    def step_3c_disambiguate(self, candidates: List[Entity], context: str) -> List[Entity]:
        """Step 3c: Context-aware disambiguation."""
        return self._disambiguate(candidates, context)
    
    def step_3d_hierarchical_resolve(self, candidates: List[Entity]) -> List[Entity]:
        """Step 3d: Resolve hierarchical names."""
        return self._resolve_hierarchical(candidates)
    
    def step_3e_alias_resolve(self, candidates: List[Entity]) -> List[Entity]:
        """Step 3e: Resolve aliases."""
        return self._resolve_aliases(candidates)
