"""
Conceptual Commands Module

Generates commands using virtual objects and semantic concepts.
Provides intelligent command generation with environment awareness.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from .environment import EnvironmentContext
from .virtual_objects import VirtualObject, ObjectType, VirtualObjectManager
from .semantic_objects import SemanticObjectFactory
from .dependency_resolver import DependencyResolver, DependencyResult
from ..generation.template_generator import TemplateGenerator


@dataclass
class ConceptualCommand:
    """Command generated from conceptual understanding."""
    
    command: str
    intent: str
    objects: List[VirtualObject]
    dependencies: List[DependencyResult]
    environment_context: Dict[str, Any]
    confidence: float
    reasoning: List[str]
    alternatives: List[str] = None
    
    def __post_init__(self):
        if self.alternatives is None:
            self.alternatives = []


class ConceptualCommandGenerator:
    """Generates commands using conceptual understanding."""
    
    def __init__(self):
        self.environment = EnvironmentContext()
        self.object_manager = VirtualObjectManager()
        self.semantic_factory = SemanticObjectFactory()
        self.dependency_resolver = DependencyResolver(self.environment)
        self.template_generator = TemplateGenerator()
    
    def generate_command(self, query: str) -> ConceptualCommand:
        """Generate command from query using conceptual understanding."""
        
        # Step 1: Create virtual objects from semantic analysis
        objects = self.semantic_factory.create_objects_from_query(query)
        
        # Step 2: Get conceptual context
        context = self.semantic_factory.get_conceptual_context(query)
        
        # Step 3: Resolve dependencies
        dependencies = self._resolve_dependencies(query, context, objects)
        
        # Step 4: Generate base command
        base_command, intent = self._generate_base_command(query, context, objects)
        
        # Step 5: Enhance command with conceptual understanding
        enhanced_command = self._enhance_command_with_concepts(
            base_command, context, objects, dependencies
        )
        
        # Step 6: Generate reasoning and alternatives
        reasoning = self._generate_reasoning(query, context, objects, dependencies)
        alternatives = self._generate_alternatives(base_command, context, objects)
        
        # Step 7: Calculate confidence
        confidence = self._calculate_confidence(context, dependencies, objects)
        
        return ConceptualCommand(
            command=enhanced_command,
            intent=intent,
            objects=objects,
            dependencies=dependencies,
            environment_context=context,
            confidence=confidence,
            reasoning=reasoning,
            alternatives=alternatives
        )
    
    def _resolve_dependencies(self, 
                             query: str, 
                             context: Dict[str, Any], 
                             objects: List[VirtualObject]) -> List[DependencyResult]:
        """Resolve dependencies for command execution."""
        
        # Generate base command to check dependencies
        base_command, _ = self._generate_base_command(query, context, objects)
        
        # Resolve dependencies
        dependencies = self.dependency_resolver.resolve_command_dependencies(
            base_command, context
        )
        
        return dependencies
    
    def _generate_base_command(self, 
                              query: str, 
                              context: Dict[str, Any], 
                              objects: List[VirtualObject]) -> Tuple[str, str]:
        """Generate base command from semantic intent."""
        
        # Get semantic intent
        semantic_intent = context.get('semantic_intent')
        if not semantic_intent:
            return "# Could not determine intent", "unknown"
        
        domain = semantic_intent['domain']
        intent = semantic_intent['intent']
        
        # Prepare entities with conceptual understanding
        entities = self._prepare_entities_from_objects(objects, context)
        
        # Generate command using template generator
        try:
            template_result = self.template_generator.generate(domain, intent, entities)
            if template_result.success:
                return template_result.command, intent
            else:
                return f"# Template generation failed: {template_result.template_used}", intent
        except Exception as e:
            return f"# Error generating command: {e}", intent
    
    def _prepare_entities_from_objects(self, 
                                     objects: List[VirtualObject], 
                                     context: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare entities for template generation from virtual objects."""
        entities = {}
        
        # Add user context
        if context.get('user_context'):
            entities['user'] = 'current'
        
        # Add object-based entities
        for obj in objects:
            if obj.type == ObjectType.USER:
                if obj.get_property('is_current_user'):
                    entities['user'] = 'current'
                    entities['username'] = obj.name
                else:
                    entities['user'] = obj.name
            
            elif obj.type == ObjectType.FILE:
                if obj.get_property('user_context'):
                    entities['path'] = '~'
                    entities['target'] = 'files'
                else:
                    if obj.path:
                        entities['path'] = str(obj.path.parent)
                        entities['pattern'] = obj.path.name
            
            elif obj.type == ObjectType.DIRECTORY:
                if obj.get_property('user_context'):
                    entities['path'] = '~'
                else:
                    if obj.path:
                        entities['path'] = str(obj.path)
        
        # Add text for context
        entities['text'] = context.get('query', '')
        
        return entities
    
    def _enhance_command_with_concepts(self, 
                                      base_command: str, 
                                      context: Dict[str, Any], 
                                      objects: List[VirtualObject],
                                      dependencies: List[DependencyResult]) -> str:
        """Enhance command with conceptual understanding."""
        
        # If base command failed, return as-is
        if base_command.startswith('#'):
            return base_command
        
        # Apply conceptual enhancements
        enhanced_command = base_command
        
        # User directory enhancement
        if context.get('user_context'):
            enhanced_command = self._apply_user_directory_enhancement(enhanced_command, objects)
        
        # Environment variable enhancement
        enhanced_command = self._apply_environment_enhancement(enhanced_command, context)
        
        # Dependency-based enhancement
        enhanced_command = self._apply_dependency_enhancement(enhanced_command, dependencies)
        
        # Path resolution enhancement
        enhanced_command = self._apply_path_resolution_enhancement(enhanced_command, objects)
        
        return enhanced_command
    
    def _apply_user_directory_enhancement(self, 
                                         command: str, 
                                         objects: List[VirtualObject]) -> str:
        """Apply user directory enhancements to command."""
        
        # Replace current directory with user home for user context
        if 'find .' in command or 'ls .' in command:
            user_home = Path.home()
            command = command.replace('find .', f'find {user_home}')
            command = command.replace('ls .', f'ls {user_home}')
        
        # Add user-specific options
        if 'find' in command and '-type f' in command:
            # Ensure we're searching in user directory
            if not any(path in command for path in ['~', str(Path.home())]):
                command = command.replace('find', f'find {Path.home()}')
        
        return command
    
    def _apply_environment_enhancement(self, 
                                       command: str, 
                                       context: Dict[str, Any]) -> str:
        """Apply environment variable enhancements to command."""
        
        env_vars = context.get('environment_variables', {})
        
        # Replace environment variables in command
        for var, value in env_vars.items():
            if value and f'${{{var}}}' in command:
                command = command.replace(f'${{{var}}}', value)
        
        return command
    
    def _apply_dependency_enhancement(self, 
                                      command: str, 
                                      dependencies: List[DependencyResult]) -> str:
        """Apply dependency-based enhancements to command."""
        
        # Add dependency-specific options
        for dep_result in dependencies:
            if not dep_result.satisfied:
                continue
            
            dep = dep_result.dependency
            
            # Add tool-specific options
            if dep.type.value == 'tool':
                if dep.name == 'git' and 'git' in command:
                    # Add common git options for user context
                    if 'status' not in command and 'log' not in command:
                        command = command.replace('git', 'git --no-pager')
                
                elif dep.name == 'docker' and 'docker' in command:
                    # Add user context for docker
                    if 'run' in command and '-u' not in command:
                        command = command.replace('docker run', 'docker run -u $(id -u):$(id -g)')
        
        return command
    
    def _apply_path_resolution_enhancement(self, 
                                         command: str, 
                                         objects: List[VirtualObject]) -> str:
        """Apply path resolution enhancements to command."""
        
        # Resolve paths based on object context
        for obj in objects:
            if obj.path and obj.type in [ObjectType.FILE, ObjectType.DIRECTORY]:
                path_str = str(obj.path)
                
                # Replace relative paths with absolute paths
                if not obj.path.is_absolute():
                    if obj.get_property('user_context'):
                        resolved_path = Path.home() / obj.path
                    else:
                        resolved_path = Path.cwd() / obj.path
                    
                    command = command.replace(str(obj.path), str(resolved_path))
        
        return command
    
    def _generate_reasoning(self, 
                           query: str, 
                           context: Dict[str, Any], 
                           objects: List[VirtualObject],
                           dependencies: List[DependencyResult]) -> List[str]:
        """Generate reasoning for command generation."""
        reasoning = []
        
        # Semantic reasoning
        semantic_intent = context.get('semantic_intent')
        if semantic_intent:
            reasoning.append(f"Detected intent: {semantic_intent['domain']}/{semantic_intent['intent']}")
        
        # Object-based reasoning
        if objects:
            obj_types = [obj.type.value for obj in objects]
            reasoning.append(f"Identified objects: {', '.join(obj_types)}")
        
        # Context reasoning
        if context.get('user_context'):
            reasoning.append("User context detected - using user home directory")
        
        # Dependency reasoning
        satisfied_deps = [d for d in dependencies if d.satisfied]
        if satisfied_deps:
            reasoning.append(f"Dependencies satisfied: {len(satisfied_deps)} tools available")
        
        # Enhancement reasoning
        reasoning.append("Applied conceptual enhancements for environment awareness")
        
        return reasoning
    
    def _generate_alternatives(self, 
                              base_command: str, 
                              context: Dict[str, Any], 
                              objects: List[VirtualObject]) -> List[str]:
        """Generate alternative commands."""
        alternatives = []
        
        # Generate alternatives based on different tools
        if 'find' in base_command:
            # Alternative with ls
            if 'find ~ -type f' in base_command:
                alternatives.append('ls -la ~')
            
            # Alternative with different find options
            if '-type f' in base_command:
                alternatives.append(base_command.replace('-type f', '-type f -name "*"'))
        
        # Generate alternatives based on context
        if context.get('user_context'):
            if 'find ~' in base_command:
                alternatives.append(f'find {Path.home()} -maxdepth 1 -type f')
        
        return alternatives
    
    def _calculate_confidence(self, 
                             context: Dict[str, Any], 
                             dependencies: List[DependencyResult],
                             objects: List[VirtualObject]) -> float:
        """Calculate confidence in generated command."""
        confidence = 0.0
        
        # Semantic confidence
        semantic_intent = context.get('semantic_intent')
        if semantic_intent:
            confidence += semantic_intent.get('confidence', 0.0) * 0.4
        
        # Object confidence
        if objects:
            obj_confidence = sum(obj.get_property('semantic_confidence', 0.5) for obj in objects) / len(objects)
            confidence += obj_confidence * 0.3
        
        # Dependency confidence
        if dependencies:
            satisfied_ratio = sum(1 for d in dependencies if d.satisfied) / len(dependencies)
            confidence += satisfied_ratio * 0.3
        
        return min(confidence, 1.0)
    
    def explain_command(self, command: ConceptualCommand) -> Dict[str, Any]:
        """Explain generated command."""
        return {
            'command': command.command,
            'intent': command.intent,
            'confidence': command.confidence,
            'reasoning': command.reasoning,
            'objects': [obj.to_dict() for obj in command.objects],
            'dependencies': [
                {
                    'name': dep.dependency.name,
                    'type': dep.dependency.type.value,
                    'satisfied': dep.satisfied,
                    'error': dep.error_message if not dep.satisfied else None
                }
                for dep in command.dependencies
            ],
            'environment': command.environment_context,
            'alternatives': command.alternatives
        }
