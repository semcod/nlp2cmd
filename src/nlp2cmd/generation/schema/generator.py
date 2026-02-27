#!/usr/bin/env python3
"""Schema-based command generator without hardcoded templates."""

import json
from typing import Dict, List, Optional, Any
from pathlib import Path

from nlp2cmd.schema_extraction import CommandSchema, ExtractedSchema
from nlp2cmd.schema_extraction.llm_extractor import LLMSchemaExtractor


class SchemaBasedGenerator:
    """Generates commands using schemas instead of templates."""
    
    def __init__(self, llm_config: Optional[Dict] = None):
        """Initialize with LLM configuration."""
        self.llm_config = llm_config or {
            "model": "ollama/qwen2.5-coder:7b",
            "api_base": "http://localhost:11434",
            "temperature": 0.1,
            "max_tokens": 512,
            "timeout": 10,
        }
        self.llm_extractor = LLMSchemaExtractor(self.llm_config)
        
        # Schema cache for learning
        self.schema_cache: Dict[str, CommandSchema] = {}
        self.pattern_cache: Dict[str, List[str]] = {}
        
    def learn_from_schema(self, schema: ExtractedSchema):
        """Learn patterns from existing schemas."""
        if not schema.commands:
            return
            
        for cmd_schema in schema.commands:
            cmd_name = cmd_schema.name
            self.schema_cache[cmd_name] = cmd_schema
            
            # Extract patterns from examples
            patterns = []
            for example in cmd_schema.examples:
                # Extract command pattern from example
                words = example.split()
                if words and words[0] == cmd_name:
                    # Find placeholders in the command
                    pattern = self._extract_pattern(words[1:])
                    if pattern:
                        patterns.append(pattern)
            
            self.pattern_cache[cmd_name] = patterns
    
    def generate_command(self, command: str, context: Dict[str, Any]) -> str:
        """
        Generate a command based on learned schemas.
        
        Args:
            command: The base command name
            context: Context parameters (file, path, pattern, etc.)
            
        Returns:
            Generated command string
        """
        # Get schema for command
        schema = self.schema_cache.get(command)
        if not schema:
            # Try to extract schema dynamically
            try:
                extracted = self.llm_extractor.extract_from_command(command)
                if extracted.commands:
                    schema = extracted.commands[0]
                    self.schema_cache[command] = schema
            except:
                # Fallback to basic pattern
                return self._generate_fallback(command, context)
        
        # Use learned patterns or generate from schema
        patterns = self.pattern_cache.get(command, [])
        if patterns:
            # Use the best matching pattern
            return self._apply_pattern(patterns[0], context)
        else:
            # Generate from schema properties
            return self._generate_from_schema(schema, context)
    
    def _extract_pattern(self, command_parts: List[str]) -> str:
        """Extract pattern from command parts."""
        pattern_parts = []
        for part in command_parts:
            if part.startswith('-'):
                # Option flag
                pattern_parts.append(part)
            elif part.startswith('/') or '.' in part:
                # Path or file
                pattern_parts.append('{path}')
            elif part.isdigit() or part.replace('.', '').isdigit():
                # Number
                pattern_parts.append('{number}')
            elif '=' in part:
                # Key=value
                key, _ = part.split('=', 1)
                pattern_parts.append(f'{{{key}}}')
            else:
                # General argument
                pattern_parts.append('{arg}')
        
        return ' '.join(pattern_parts)
    
    def _apply_pattern(self, pattern: str, context: Dict[str, Any]) -> str:
        """Apply context to a pattern."""
        result = pattern
        
        # Replace placeholders with context values
        replacements = {
            '{path}': context.get('path', context.get('file', '/path/to/file')),
            '{file}': context.get('file', 'filename'),
            '{pattern}': context.get('pattern', 'pattern'),
            '{number}': str(context.get('number', '')),
            '{arg}': context.get('arg', ''),
        }
        
        for placeholder, value in replacements.items():
            result = result.replace(placeholder, str(value))
        
        return result
    
    def _generate_from_schema(self, schema: CommandSchema, context: Dict[str, Any]) -> str:
        """Generate command from schema properties."""
        cmd = schema.name
        
        # Add parameters based on context
        if context.get('recursive') and schema.name in ['find', 'grep', 'cp', 'rm']:
            cmd += ' -r'
        
        if context.get('all') and schema.name in ['ls', 'ps']:
            cmd += ' -a'
        
        if context.get('long') and schema.name in ['ls', 'ps']:
            cmd += ' -l'
        
        if context.get('force') and schema.name in ['rm', 'cp', 'mv']:
            cmd += ' -f'
        
        # Add context-specific arguments
        if 'file' in context:
            cmd += f' {context["file"]}'
        elif 'path' in context:
            cmd += f' {context["path"]}'
        elif 'pattern' in context:
            cmd += f' {context["pattern"]}'
        
        return cmd
    
    def _generate_fallback(self, command: str, context: Dict[str, Any]) -> str:
        """Generate fallback command without schema."""
        cmd = command
        
        # Basic context handling
        if 'file' in context:
            cmd += f' {context["file"]}'
        if 'pattern' in context:
            cmd += f' "{context["pattern"]}"'
        if 'path' in context:
            cmd += f' {context["path"]}'
        
        return cmd
    
    def improve_from_usage(self, command: str, input_text: str, generated: str, actual: Optional[str] = None):
        """Improve schemas based on actual usage."""
        if actual and actual != generated:
            # Learn from the correction
            schema = self.schema_cache.get(command)
            if schema:
                # Add the actual command as a new example
                if actual not in schema.examples:
                    schema.examples.append(actual)
                    print(f"[SchemaBasedGenerator] Learned new example for {command}: {actual}")


class SchemaRegistry:
    """Registry for managing and improving schemas."""
    
    def __init__(self, llm_config: Optional[Dict] = None):
        """Initialize registry."""
        self.generator = SchemaBasedGenerator(llm_config)
        self.schemas: Dict[str, ExtractedSchema] = {}
        
    def register_schema(self, schema: ExtractedSchema):
        """Register a new schema."""
        self.schemas[schema.source] = schema
        self.generator.learn_from_schema(schema)
    
    def load_from_file(self, path: str):
        """Load schemas from a JSON file."""
        with open(path) as f:
            data = json.load(f)
            
        for source, schema_data in data.get('schemas', {}).items():
            # Convert to ExtractedSchema
            schema = self._convert_from_json(schema_data, source)
            self.register_schema(schema)
    
    def _convert_from_json(self, data: Dict, source: str) -> ExtractedSchema:
        """Convert JSON data to ExtractedSchema."""
        commands = []
        for cmd_data in data.get('commands', []):
            cmd = CommandSchema(
                name=cmd_data['name'],
                description=cmd_data['description'],
                category=cmd_data['category'],
                parameters=cmd_data.get('parameters', []),
                examples=cmd_data.get('examples', []),
                patterns=cmd_data.get('patterns', []),
                source_type=cmd_data.get('source_type', 'unknown'),
                metadata=cmd_data.get('metadata', {}),
                template=cmd_data.get('template'),
            )
            commands.append(cmd)
        
        return ExtractedSchema(
            source=source,
            source_type=data.get('source_type', 'unknown'),
            commands=commands,
            metadata=data.get('metadata', {}),
        )
    
    def generate_command(self, command: str, context: Dict[str, Any]) -> str:
        """Generate command using learned schemas."""
        return self.generator.generate_command(command, context)
    
    def improve_from_feedback(self, command: str, query: str, generated: str, correction: Optional[str] = None):
        """Improve schemas based on user feedback."""
        self.generator.improve_from_usage(command, query, generated, correction)
    
    def save_improvements(self, path: str):
        """Save improved schemas to file."""
        output = {
            'schemas': {},
            'metadata': {
                'improved': True,
                'total_schemas': len(self.schemas)
            }
        }
        
        for source, schema in self.schemas.items():
            output['schemas'][source] = {
                'source_type': schema.source_type,
                'commands': [
                    {
                        'name': cmd.name,
                        'description': cmd.description,
                        'category': cmd.category,
                        'parameters': cmd.parameters,
                        'examples': cmd.examples,
                        'patterns': cmd.patterns,
                        'source_type': cmd.source_type,
                        'metadata': cmd.metadata,
                        'template': cmd.template,
                    }
                    for cmd in schema.commands
                ],
                'metadata': schema.metadata,
            }
        
        with open(path, 'w') as f:
            json.dump(output, f, indent=2)
