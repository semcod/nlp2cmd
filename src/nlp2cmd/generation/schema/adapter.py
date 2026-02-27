#!/usr/bin/env python3
"""Enhanced AppSpec adapter with schema-based generation."""

from typing import Any, Dict, Optional
from pathlib import Path

from nlp2cmd.adapters.appspec import AppSpecAdapter
from nlp2cmd.generation.schema.generator import SchemaRegistry
from nlp2cmd.ir import ActionIR


class SchemaDrivenAppSpecAdapter(AppSpecAdapter):
    """AppSpec adapter that uses schema-based generation."""
    
    def __init__(
        self,
        *,
        appspec_path: Optional[str] = None,
        config: Optional[Any] = None,
        safety_policy: Optional[Any] = None,
        llm_config: Optional[Dict] = None,
    ):
        """Initialize with schema registry."""
        super().__init__(
            appspec_path=appspec_path,
            config=config,
            safety_policy=safety_policy
        )
        
        # Initialize schema registry
        self.schema_registry = SchemaRegistry(llm_config)
        
        # Load schemas from existing sources
        self._load_schemas()
    
    def _load_schemas(self):
        """Load schemas from various sources."""
        # Load from validated schemas if available
        validated_candidates = [
            Path("./command_schemas/exports/validated_schemas.json"),
            Path("./validated_schemas.json"),
        ]
        for p in validated_candidates:
            if p.exists():
                self.schema_registry.load_from_file(str(p))
                break
        
        # Extract schemas from AppSpec actions
        if self._spec:
            for action in self._spec.actions:
                # Convert action to schema format
                schema = self._action_to_schema(action)
                self.schema_registry.register_schema(schema)
    
    def _action_to_schema(self, action) -> Any:
        """Convert AppSpec action to schema."""
        from nlp2cmd.schema_extraction import CommandSchema, ExtractedSchema
        
        # Extract command from DSL
        dsl = action.dsl or {}
        command = dsl.get('command', action.id)
        
        # Create command schema
        cmd_schema = CommandSchema(
            name=command,
            description=action.description or f"{command} command",
            category=self._infer_category(action),
            parameters=[],
            examples=action.examples or [],
            patterns=action.match.get('patterns', []) if action.match else [],
            source_type="appspec",
            metadata={'action_id': action.id},
            template=dsl.get('template'),
        )
        
        return ExtractedSchema(
            source=action.id,
            source_type="appspec",
            commands=[cmd_schema],
            metadata={'appspec_action': True}
        )
    
    def _infer_category(self, action) -> str:
        """Infer category from action metadata."""
        if hasattr(action, 'type'):
            type_map = {
                'file': 'file',
                'text': 'text',
                'network': 'network',
                'system': 'system',
                'process': 'process',
                'development': 'development'
            }
            return type_map.get(action.type, 'system')
        return 'system'
    
    def generate(self, plan: Dict[str, Any]) -> str:
        """Generate command using schema-based approach."""
        # Try standard generation first
        try:
            return super().generate(plan)
        except:
            # Fallback to schema-based generation
            action_id = plan.get('action_id')
            context = plan.get('context', {})
            
            # Extract command name from action_id
            command = action_id.split('_')[0] if '_' in action_id else action_id
            
            # Generate using schema registry
            return self.schema_registry.generate_command(command, context)
    
    def transform_ir(self, text: str) -> ActionIR:
        """Transform with schema-based enhancement."""
        # Get standard IR
        ir = self._engine.transform(text) if self._engine else None
        
        if not ir:
            # Try direct schema matching
            command = self._extract_command_from_text(text)
            context = self._extract_context_from_text(text)
            
            generated = self.schema_registry.generate_command(command, context)
            
            return ActionIR(
                action_id=command,
                dsl=generated,
                dsl_kind="shell",
                params=context,
                output_format="raw",
                confidence=0.7,
                explanation="schema-based generation",
                metadata={"method": "schema_based"}
            )
        
        # Enhance existing IR with schema-based improvements
        if ir.action_id:
            context = self._extract_context_from_text(text)
            improved = self.schema_registry.generate_command(ir.action_id, context)
            
            # Update if improvement is better
            if improved != ir.dsl:
                ir.dsl = improved
                ir.metadata.update({"schema_improved": True})
        
        return ir
    
    def _extract_command_from_text(self, text: str) -> str:
        """Extract command name from text."""
        # Simple keyword extraction
        text_lower = text.lower()
        
        # Common command mappings
        mappings = {
            'find': 'find',
            'search': 'grep',
            'copy': 'cp',
            'move': 'mv',
            'remove': 'rm',
            'delete': 'rm',
            'list': 'ls',
            'compress': 'tar',
            'extract': 'tar',
            'download': 'wget',
            'connect': 'ssh',
            'check': 'ps',
            'process': 'ps',
            'network': 'netstat',
            'git': 'git',
            'docker': 'docker',
            'kubernetes': 'kubectl',
        }
        
        for keyword, command in mappings.items():
            if keyword in text_lower:
                return command
        
        # Fallback to first word
        words = text.split()
        return words[0] if words else 'echo'
    
    def _extract_context_from_text(self, text: str) -> Dict[str, Any]:
        """Extract context parameters from text."""
        import re
        
        context = {}
        
        # Extract file paths
        paths = re.findall(r'[/][^\s]*', text)
        if paths:
            context['path'] = paths[0]
        
        # Extract file extensions
        extensions = re.findall(r'\.\w+\b', text)
        if extensions:
            context['pattern'] = f"*{extensions[0]}"
        
        # Extract sizes
        sizes = re.findall(r'\d+[KMGT]?B?', text)
        if sizes:
            context['size'] = sizes[0]
        
        # Extract hosts/URLs
        hosts = re.findall(r'[\w.-]+\.(?:com|org|net|gov|edu|io|local)', text)
        if hosts:
            context['host'] = hosts[0]
        
        # Extract patterns in quotes
        quoted = re.findall(r'"([^"]*)"', text)
        if quoted:
            context['pattern'] = quoted[0]
        
        return context
    
    def learn_from_feedback(self, query: str, generated: str, correction: Optional[str] = None):
        """Learn from user feedback."""
        command = self._extract_command_from_text(query)
        self.schema_registry.improve_from_feedback(command, query, generated, correction)
    
    def save_improvements(self, path: str):
        """Save learned improvements."""
        self.schema_registry.save_improvements(path)
