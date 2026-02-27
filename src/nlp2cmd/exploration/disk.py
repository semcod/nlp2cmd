"""
Disk Explorer - File system exploration.

Find files, directories, and content on disk.
"""

from __future__ import annotations

import fnmatch
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generator, Optional

from nlp2cmd.exploration.base import BaseExplorer, ExplorationContext, ExplorationResult


@dataclass
class FileInfo:
    """Information about a file or directory."""
    path: str
    name: str
    is_dir: bool
    size: int = 0
    modified: float = 0.0
    content_preview: Optional[str] = None


class DiskExplorer(BaseExplorer):
    """Explorer for file systems and disk content."""
    
    def __init__(
        self,
        max_depth: int = 5,
        max_results: int = 20,
        follow_symlinks: bool = False,
        include_hidden: bool = False,
    ):
        super().__init__(max_depth, max_results)
        self.follow_symlinks = follow_symlinks
        self.include_hidden = include_hidden
    
    def supports(self, space_type: str) -> bool:
        return space_type in ("disk", "file", "fs", "filesystem")
    
    def explore(
        self,
        root: Any,
        context: ExplorationContext,
    ) -> ExplorationResult[FileInfo]:
        """Explore file system starting from root path."""
        root_path = Path(root).expanduser().resolve()
        
        if not root_path.exists():
            return ExplorationResult(
                success=False,
                error=f"Path does not exist: {root_path}",
            )
        
        candidates: list[FileInfo] = []
        self._visited = set()
        
        try:
            for item in self._walk(root_path, context, current_depth=0):
                candidates.append(item)
                
                # Check if we've found enough
                if len(candidates) >= self.max_results:
                    break
        except PermissionError as e:
            return ExplorationResult(
                success=False,
                error=f"Permission denied: {e}",
            )
        except Exception as e:
            return ExplorationResult(
                success=False,
                error=f"Exploration error: {e}",
            )
        
        if not candidates:
            return ExplorationResult(
                success=False,
                error=f"No files matching '{context.search_term}' found in {root_path}",
                candidates=[],
            )
        
        # Score and sort candidates
        scored = [(self._score_file(item, context), item) for item in candidates]
        scored.sort(key=lambda x: x[0], reverse=True)
        
        best = scored[0][1] if scored else None
        
        return ExplorationResult(
            success=True,
            target=best,
            path=[best.path] if best else [],
            candidates=[item for _, item in scored],
            metadata={
                "root": str(root_path),
                "search_term": context.search_term,
                "intent": context.intent,
                "total_found": len(candidates),
            },
        )
    
    def _walk(
        self,
        path: Path,
        context: ExplorationContext,
        current_depth: int,
    ) -> Generator[FileInfo, None, None]:
        """Walk directory tree yielding matching files."""
        if self._should_stop(current_depth, len(self._visited)):
            return
        
        if path.is_symlink() and not self.follow_symlinks:
            return
        
        path_str = str(path)
        if path_str in self._visited:
            return
        self._visited.add(path_str)
        
        try:
            stat = path.stat()
            info = FileInfo(
                path=path_str,
                name=path.name,
                is_dir=path.is_dir(),
                size=stat.st_size,
                modified=stat.st_mtime,
            )
            
            # Check if this item matches
            if self._matches_context(info, context):
                yield info
            
            # Recurse into directories
            if path.is_dir() and current_depth < self.max_depth:
                for child in path.iterdir():
                    # Skip hidden files
                    if not self.include_hidden and child.name.startswith("."):
                        continue
                    
                    yield from self._walk(child, context, current_depth + 1)
                    
        except (PermissionError, OSError):
            # Skip files we can't access
            pass
    
    def _matches_context(self, info: FileInfo, context: ExplorationContext) -> bool:
        """Check if file matches search context."""
        # Intent-based matching
        if context.intent == "file":
            return self._match_file_intent(info, context)
        elif context.intent == "config":
            return self._match_config_intent(info, context)
        elif context.intent == "code":
            return self._match_code_intent(info, context)
        elif context.intent == "data":
            return self._match_data_intent(info, context)
        
        # Default: search term matching
        if context.search_term:
            return self._matches_search_term(info, context.search_term)
        
        return True
    
    def _match_file_intent(self, info: FileInfo, context: ExplorationContext) -> bool:
        """Match general file search."""
        if not context.search_term:
            return not info.is_dir
        
        return self._matches_search_term(info, context.search_term)
    
    def _match_config_intent(self, info: FileInfo, context: ExplorationContext) -> bool:
        """Match config files."""
        config_patterns = [
            "*.conf", "*.config", "*.cfg", "*.yaml", "*.yml", 
            "*.json", "*.ini", "*.toml", "*.env", "*.properties",
        ]
        
        if any(fnmatch.fnmatch(info.name.lower(), p) for p in config_patterns):
            if context.search_term:
                return context.search_term.lower() in info.path.lower()
            return True
        
        # Check for config in name
        if "config" in info.path.lower() or ".config" in info.path:
            return True
        
        return False
    
    def _match_code_intent(self, info: FileInfo, context: ExplorationContext) -> bool:
        """Match source code files."""
        code_extensions = [
            ".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".hpp",
            ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".scala",
            ".sh", ".bash", ".zsh", ".ps1", ".bat",
        ]
        
        if not info.is_dir and any(info.name.endswith(ext) for ext in code_extensions):
            if context.search_term:
                return context.search_term.lower() in info.path.lower()
            return True
        
        return False
    
    def _match_data_intent(self, info: FileInfo, context: ExplorationContext) -> bool:
        """Match data files."""
        data_patterns = [
            "*.json", "*.xml", "*.csv", "*.tsv", "*.parquet",
            "*.sqlite", "*.db", "*.sql", "*.xlsx", "*.ods",
        ]
        
        if any(fnmatch.fnmatch(info.name.lower(), p) for p in data_patterns):
            if context.search_term:
                return context.search_term.lower() in info.path.lower()
            return True
        
        return False
    
    def _matches_search_term(self, info: FileInfo, search_term: str) -> bool:
        """Check if file matches search term."""
        search_lower = search_term.lower()
        
        # Match in name
        if search_lower in info.name.lower():
            return True
        
        # Match in path
        if search_lower in info.path.lower():
            return True
        
        # Pattern matching
        try:
            if fnmatch.fnmatch(info.name.lower(), f"*{search_lower}*"):
                return True
        except Exception:
            pass
        
        return False
    
    def _score_file(self, info: FileInfo, context: ExplorationContext) -> float:
        """Score file relevance."""
        score = super()._score_relevance(info.path, context)
        
        # Boost for exact name matches
        if context.search_term:
            search_lower = context.search_term.lower()
            name_lower = info.name.lower()
            
            if name_lower == search_lower:
                score += 5.0  # Exact match
            elif name_lower.startswith(search_lower):
                score += 3.0  # Starts with
            elif search_lower in name_lower:
                score += 1.0  # Contains
        
        # Boost for not being a directory (usually we want files)
        if not info.is_dir:
            score += 0.5
        
        # Boost for reasonable file size (not empty, not huge)
        if 0 < info.size < 1024 * 1024:  # Under 1MB
            score += 0.3
        
        return score
    
    def find_file(
        self,
        start_path: str,
        pattern: str,
        file_type: Optional[str] = None,
    ) -> Optional[FileInfo]:
        """Convenience method to find a single file."""
        context = ExplorationContext(
            intent="file",
            search_term=pattern,
        )
        result = self.explore(start_path, context)
        return result.target if result.success else None
    
    def find_config(
        self,
        start_path: str = "~",
        app_name: Optional[str] = None,
    ) -> list[FileInfo]:
        """Find configuration files."""
        context = ExplorationContext(
            intent="config",
            search_term=app_name,
        )
        result = self.explore(start_path, context)
        return result.candidates if result.success else []


def quick_find_file(
    path: str,
    pattern: str,
    max_depth: int = 5,
) -> Optional[str]:
    """Quick helper to find file path."""
    explorer = DiskExplorer(max_depth=max_depth)
    result = explorer.find_file(path, pattern)
    return result.path if result else None
