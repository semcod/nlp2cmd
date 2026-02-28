"""Pattern detection for behavioral analysis."""

from typing import List, Dict, Set
from collections import defaultdict

from ..core.config import Config
from ..core.models import AnalysisResult


class PatternDetector:
    """Detect behavioral patterns in code."""
    
    def __init__(self, config: Config):
        self.config = config
        
    def detect_patterns(self, result: AnalysisResult) -> List[Dict]:
        """Detect all behavioral patterns in analysis result."""
        patterns = []
        
        # Detect recursive patterns
        if self.config.detect_recursion:
            patterns.extend(self._detect_recursion(result))
            
        # Detect state machines
        if self.config.detect_state_machines:
            patterns.extend(self._detect_state_machines(result))
            
        # Detect factory patterns
        patterns.extend(self._detect_factory_pattern(result))
        
        # Detect singleton pattern
        patterns.extend(self._detect_singleton(result))
        
        # Detect strategy pattern
        patterns.extend(self._detect_strategy_pattern(result))
        
        return patterns
        
    def _detect_recursion(self, result: AnalysisResult) -> List[Dict]:
        """Detect recursive function calls."""
        patterns = []
        
        for func_name, func_info in result.functions.items():
            if func_name in func_info.calls:
                patterns.append({
                    'type': 'recursive',
                    'name': f'recursive_{func_name}',
                    'function': func_name,
                    'confidence': 1.0,
                    'description': f'Function {func_name} calls itself recursively'
                })
                
        return patterns
        
    def _detect_state_machines(self, result: AnalysisResult) -> List[Dict]:
        """Detect state machine patterns in classes."""
        patterns = []
        
        for class_name, class_info in result.classes.items():
            # Look for state-related attributes and transition methods
            has_state = False
            transition_methods = []
            
            for method in class_info.get('methods', []):
                method_lower = method.lower()
                if 'state' in method_lower:
                    has_state = True
                if any(word in method_lower for word in ['transition', 'change', 'set', 'next', 'prev']):
                    transition_methods.append(method)
                    
            if has_state or transition_methods:
                patterns.append({
                    'type': 'state_machine',
                    'name': f'state_machine_{class_name}',
                    'class': class_name,
                    'transitions': transition_methods,
                    'confidence': 0.8 if transition_methods else 0.5,
                    'description': f'Class {class_name} appears to implement a state machine'
                })
                
        return patterns
        
    def _detect_factory_pattern(self, result: AnalysisResult) -> List[Dict]:
        """Detect factory method pattern."""
        patterns = []
        
        for func_name, func_info in result.functions.items():
            # Check if function returns instances of different classes
            name_lower = func_name.lower()
            if 'create' in name_lower or 'factory' in name_lower or 'build' in name_lower:
                # Check if it returns different types
                returns_classes = self._check_returns_classes(result, func_name)
                if returns_classes:
                    patterns.append({
                        'type': 'factory',
                        'name': f'factory_{func_name}',
                        'function': func_name,
                        'creates': list(returns_classes),
                        'confidence': 0.7,
                        'description': f'Function {func_name} appears to be a factory'
                    })
                    
        return patterns
        
    def _detect_singleton(self, result: AnalysisResult) -> List[Dict]:
        """Detect singleton pattern."""
        patterns = []
        
        for class_name, class_info in result.classes.items():
            methods = class_info.get('methods', [])
            
            # Check for getInstance or similar
            has_get_instance = any(
                m.lower() in ('getinstance', 'get_instance', 'instance') 
                for m in methods
            )
            
            # Check for __new__ override
            has_new = '__new__' in methods
            
            if has_get_instance or has_new:
                patterns.append({
                    'type': 'singleton',
                    'name': f'singleton_{class_name}',
                    'class': class_name,
                    'confidence': 0.75,
                    'description': f'Class {class_name} appears to be a singleton'
                })
                
        return patterns
        
    def _detect_strategy_pattern(self, result: AnalysisResult) -> List[Dict]:
        """Detect strategy pattern."""
        patterns = []
        
        # Look for interface-like classes with execute/run methods
        strategy_candidates = []
        
        for class_name, class_info in result.classes.items():
            methods = class_info.get('methods', [])
            
            # Look for execute, run, or process methods
            if any(m in methods for m in ['execute', 'run', 'process', 'apply']):
                strategy_candidates.append(class_name)
                
        # Check if these are used interchangeably
        if len(strategy_candidates) > 1:
            for func_name, func_info in result.functions.items():
                calls = func_info.calls
                called_strategies = [s for s in strategy_candidates if s in str(calls)]
                
                if len(called_strategies) > 1:
                    patterns.append({
                        'type': 'strategy',
                        'name': f'strategy_in_{func_name}',
                        'context': func_name,
                        'strategies': called_strategies,
                        'confidence': 0.7,
                        'description': f'Function {func_name} uses strategy pattern'
                    })
                    break
                    
        return patterns
        
    def _check_returns_classes(self, result: AnalysisResult, func_name: str) -> Set[str]:
        """Check what classes a function might return."""
        # Simplified - in full implementation would analyze return statements
        return set()  # Placeholder
