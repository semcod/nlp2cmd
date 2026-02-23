"""
Iteration 3: Template-Based Generation.

Generate DSL commands from templates using detected intent and entities.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
import getpass
import json
import os
import re
from pathlib import Path

from nlp2cmd.utils.data_files import find_data_files
from nlp2cmd.generation.templates import (
    SQL_TEMPLATES,
    SHELL_TEMPLATES,
    DOCKER_TEMPLATES,
    KUBERNETES_TEMPLATES,
    BROWSER_TEMPLATES,
    GIT_TEMPLATES,
)


@dataclass
class TemplateResult:
    """Result of template generation."""
    
    command: str
    template_used: str
    entities_used: dict[str, Any]
    missing_entities: list[str]
    success: bool


class TemplateGenerator:
    """
    Generate DSL commands from templates.
    
    Uses predefined templates filled with extracted entities.
    Falls back to sensible defaults when entities are missing.
    
    Example:
        generator = TemplateGenerator()
        result = generator.generate(
            domain='sql',
            intent='select',
            entities={'table': 'users', 'columns': ['id', 'name']}
        )
        # result.command == "SELECT id, name FROM users;"
    """
    
    def __init__(
        self,
        custom_templates: Optional[dict[str, dict[str, str]]] = None,
    ):
        """
        Initialize template generator.
        
        Args:
            custom_templates: Additional templates per domain
        """
        self.templates: dict[str, dict[str, str]] = {
            'sql': SQL_TEMPLATES.copy(),
            'shell': SHELL_TEMPLATES.copy(),
            'docker': DOCKER_TEMPLATES.copy(),
            'kubernetes': KUBERNETES_TEMPLATES.copy(),
            'browser': BROWSER_TEMPLATES.copy(),
            'git': GIT_TEMPLATES.copy(),
        }

        self.defaults: dict[str, Any] = {}
        self._defaults_loaded = False
        self._templates_loaded = False
        self._load_defaults_from_json()
        self._load_templates_from_json()

        # Apply custom templates
        if custom_templates:
            for domain, domain_templates in custom_templates.items():
                if domain not in self.templates:
                    self.templates[domain] = {}
                self.templates[domain].update(domain_templates)

    def _load_defaults_from_json(self) -> None:
        for p in find_data_files(
            explicit_path=os.environ.get("NLP2CMD_DEFAULTS_FILE"),
            default_filename="defaults.json",
        ):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    payload = json.load(f)
                if not isinstance(payload, dict):
                    continue
                self._defaults_loaded = True
                self.defaults.update(payload)
            except Exception:
                continue

    def _load_templates_from_json(self) -> None:
        for p in find_data_files(
            explicit_path=os.environ.get("NLP2CMD_TEMPLATES_FILE"),
            default_filename="templates.json",
        ):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    payload = json.load(f)
                if not isinstance(payload, dict):
                    continue

                self._templates_loaded = True

                # Expected format: {"shell": {"intent": "template"}, "docker": {...}, ...}
                for domain, templates in payload.items():
                    if not isinstance(templates, dict):
                        continue
                    if domain not in self.templates:
                        self.templates[domain] = {}
                    bucket = self.templates[domain]
                    for intent, template in templates.items():
                        if isinstance(intent, str) and intent and isinstance(template, str) and template:
                            bucket[intent] = template
            except Exception:
                continue

    def _get_default(self, key: str, fallback: Any) -> Any:
        if key in self.defaults:
            v = self.defaults.get(key)
            return v if v is not None and v != "" else fallback
        return fallback
    
    def generate(
        self,
        domain: str,
        intent: str,
        entities: dict[str, Any],
        context: Optional[dict[str, Any]] = None,
    ) -> TemplateResult:
        """
        Generate DSL command from template.
        
        Args:
            domain: Target domain (sql, shell, docker, etc.)
            intent: Specific intent within domain
            entities: Extracted entities to fill template
            context: Additional context for generation
            
        Returns:
            TemplateResult with generated command and metadata
        """
        # Normalize domain
        effective_domain = domain.lower()
        if effective_domain == 'bash':
            effective_domain = 'shell'

        # Get template
        domain_templates = self.templates.get(effective_domain, {})
        template = domain_templates.get(intent)
        
        # Special case: for shell domain with list intent, always check for alternatives
        if effective_domain == 'shell' and intent == 'list' and not template:
            template = self._find_alternative_template(effective_domain, intent, entities, context)
        
        if not template:
            return TemplateResult(
                command="",
                template_used="",
                entities_used={},
                missing_entities=[],
                success=False,
            )
        
        # Prepare entities based on domain
        prepared_entities = self._prepare_entities(effective_domain, intent, entities, context or {})
        
        # Fill template
        filled_template = self._fill_template(template, prepared_entities)
        
        # Clean command
        command = self._clean_command(filled_template)
        
        # Find missing entities
        missing = self._find_missing(template, prepared_entities)
        
        return TemplateResult(
            command=command,
            template_used=template,
            entities_used=prepared_entities,
            missing_entities=missing,
            success=bool(command.strip()),
        )
    
    def _find_alternative_template(
        self,
        domain: str,
        intent: str,
        entities: dict[str, Any],
        context: dict[str, Any],
    ) -> Optional[str]:
        """Find alternative template based on entities and context."""
        if domain == 'shell' and intent == 'list':
            # Check if we're looking for directories vs files
            text_lower = str(entities.get('text') or '').lower()
            if any(word in text_lower for word in ['folder', 'directory', 'dir', 'katalog', 'folderze']):
                return self.templates[domain].get('list_dirs')
            elif any(word in text_lower for word in ['process', 'proces']):
                return self.templates[domain].get('process_list')
        
        # Check intent aliases
        intent_aliases = self._get_intent_aliases()
        if intent_aliases:
            domain_aliases = intent_aliases.get(domain, {})
            return domain_aliases.get(intent)
        
        return None
    
    def _get_intent_aliases(self) -> Optional[dict[str, dict[str, str]]]:
        """Get intent aliases from defaults."""
        return self.defaults.get('intent_aliases')
    
    def _prepare_entities(
        self,
        domain: str,
        intent: str,
        entities: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Prepare entities for template filling."""
        result = entities.copy()
        
        # Apply domain-specific preparation
        if domain == 'sql':
            result = self._prepare_sql_entities(intent, result)
        elif domain == 'shell':
            result = self._prepare_shell_entities(intent, result, context)
        elif domain == 'docker':
            result = self._prepare_docker_entities(intent, result)
        elif domain == 'kubernetes':
            result = self._prepare_kubernetes_entities(intent, result)
        elif domain == 'git':
            result = self._prepare_git_entities(intent, result)
        
        return result
    
    def _prepare_sql_entities(self, intent: str, entities: dict[str, Any]) -> dict[str, Any]:
        """Prepare SQL entities."""
        result = entities.copy()
        
        # Handle columns
        if 'columns' in result:
            columns = result['columns']
            if isinstance(columns, list):
                result['columns'] = ', '.join(columns)
            elif isinstance(columns, str):
                result['columns'] = columns
            else:
                result['columns'] = '*'
        else:
            result['columns'] = '*'
        
        # Handle WHERE clause
        where_conditions = []
        if 'where' in result:
            where = result['where']
            if isinstance(where, dict):
                conditions = []
                for field, value in where.items():
                    if isinstance(value, str):
                        conditions.append(f"{field} = '{value}'")
                    else:
                        conditions.append(f"{field} = {value}")
                if conditions:
                    where_conditions.append(f" WHERE {' AND '.join(conditions)}")
            elif isinstance(where, str) and where.strip():
                where_conditions.append(f" WHERE {where}")
        
        # Handle ORDER BY
        if 'order' in result:
            order = result['order']
            if isinstance(order, dict):
                order_clause = f" ORDER BY {order.get('column', 'id')} {order.get('direction', 'ASC')}"
                where_conditions.append(order_clause)
            elif isinstance(order, str) and order.strip():
                where_conditions.append(f" ORDER BY {order}")
        
        # Handle LIMIT
        if 'limit' in result:
            limit = result['limit']
            if isinstance(limit, (int, str)) and str(limit).isdigit():
                where_conditions.append(f" LIMIT {limit}")
        
        result['where'] = ''.join(where_conditions)
        result['order'] = ''
        result['limit'] = ''
        
        return result
    
    def _prepare_shell_entities(self, intent: str, entities: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        """Prepare shell entities."""
        result = entities.copy()
        
        # Apply path defaults
        self._apply_shell_path_defaults(intent, entities, result)
        
        # Apply pattern defaults
        self._apply_shell_pattern_defaults(entities, result)
        
        # Apply find flags for find commands
        if intent.startswith('find') or intent == 'file_search':
            self._apply_shell_find_flags(intent, entities, result)
        
        # Apply common defaults
        self._apply_shell_common_defaults(entities, result)
        
        # Apply text processing defaults
        self._apply_shell_text_processing_defaults(intent, entities, result)
        
        # Apply intent-specific defaults
        if intent == 'file_search':
            self._shell_intent_file_search(entities, result)
        elif intent == 'file_content':
            self._shell_intent_file_content(entities, result)
        
        return result
    
    def _get_user_home_dir(self, username: str) -> str:
        if os.name != "posix":
            return f"~{username}"
        
        try:
            import pwd
            pw = pwd.getpwnam(username)
            return pw.pw_dir
        except Exception:
            return f"/home/{username}"

    def _apply_shell_path_defaults(self, intent: str, entities: dict[str, Any], result: dict[str, Any]) -> None:
        if 'user' in entities and entities['user'] == 'current':
            result.setdefault('path', '~')
        elif 'username' in entities:
            result.setdefault('path', self._get_user_home_dir(entities['username']))
        elif 'path' not in result:
            # Default to current directory for most operations
            if intent in ['list', 'list_dirs', 'find', 'file_search']:
                result.setdefault('path', '.')
            else:
                result.setdefault('path', '.')

    def _apply_shell_pattern_defaults(self, entities: dict[str, Any], result: dict[str, Any]) -> None:
        pattern = entities.get('pattern', entities.get('file_pattern'))
        if pattern:
            if not pattern.startswith('*'):
                result['name_flag_count'] = f"-name '*{pattern}*'"
            else:
                result['name_flag_count'] = f"-name '{pattern}'"
        else:
            result['name_flag_count'] = ''

    def _apply_shell_find_flags(self, intent: str, entities: dict[str, Any], result: dict[str, Any]) -> None:
        target = self._infer_shell_find_target(intent, entities)
        result['type_flag'] = self._build_shell_find_type_flag(target)
        result['name_flag'] = self._build_shell_find_name_flag(result.get('pattern', '*'))
        result['exec_flag'] = self._build_shell_find_exec_flag(intent, entities)
        result['size_flag'] = self._build_shell_find_size_flag(entities)
        result['time_flag'] = self._build_shell_find_time_flag(entities)

    def _infer_shell_find_target(self, intent: str, entities: dict[str, Any]) -> str:
        target = entities.get('target')
        if not target and intent == 'find':
            text_lower = str(entities.get('text') or '').lower()
            if any(word in text_lower for word in ['file', 'plik', 'files']):
                return 'files'
            elif any(word in text_lower for word in ['directory', 'dir', 'folder', 'katalog']):
                return 'directories'
        return str(target or '')

    def _build_shell_find_type_flag(self, target: str) -> str:
        if target == 'files':
            return '-type f'
        if target == 'directories':
            return '-type d'
        return ''

    def _build_shell_find_name_flag(self, pattern: str) -> str:
        return f"-name '{pattern}'" if pattern and pattern != '*' else ''

    def _build_shell_find_exec_flag(self, intent: str, entities: dict[str, Any]) -> str:
        if intent != 'find':
            return ''
        text_lower = str(entities.get('text') or '').lower()
        if any(word in text_lower for word in ['list', 'show', 'display', 'pokaż']):
            return '-ls'
        return ''

    def _build_shell_find_size_flag(self, entities: dict[str, Any]) -> str:
        size = entities.get('size')
        text = str(entities.get('text', ''))
        size_operator = str(entities.get('size_operator') or entities.get('operator') or '>')
        
        if size:
            if isinstance(size, str):
                import re
                m = re.match(r'([<>]=?)(\d+)([KMGT]?)(B?)', size.upper())
                if m:
                    sign = m.group(1)
                    val = m.group(2)
                    unit = m.group(3) or 'c'
                    return f"-size {sign}{val}{unit}"
            return f"-size {size_operator}{size}"
        elif 'large' in text.lower() or 'big' in text.lower():
            return "-size +100M"
        elif 'small' in text.lower():
            return "-size -1M"
        return ''

    def _build_shell_find_time_flag(self, entities: dict[str, Any]) -> str:
        age = entities.get('age')
        if age and isinstance(age, dict):
            val = age.get('value', 0)
            unit = age.get('unit', 'd')
            time_operator = age.get('operator', '+')
            return f"-mtime {time_operator}{val}"
        return ''

    def _apply_shell_common_defaults(self, entities: dict[str, Any], result: dict[str, Any]) -> None:
        result.setdefault('metric', 'mem')
        result.setdefault('limit', '10')
        result.setdefault('process_name', '')
        result.setdefault('pattern', '*')
        result.setdefault('flags', '')
        result.setdefault('source', '')
        result.setdefault('destination', '')
        result.setdefault('target', '')
        result.setdefault('file', '')

    def _apply_shell_text_processing_defaults(self, intent: str, entities: dict[str, Any], result: dict[str, Any]) -> None:
        self._apply_shell_text_tail_defaults(intent, entities, result)
        self._apply_shell_text_cat_defaults(intent, entities, result)
        self._apply_shell_json_defaults(intent, entities, result)
        self._apply_shell_text_wc_defaults(intent, entities, result)

    def _apply_shell_file_default(self, entities: dict[str, Any], result: dict[str, Any]) -> None:
        if result.get('file'):
            return
        result['file'] = (
            entities.get('file_path')
            or entities.get('filename')
            or entities.get('target')
            or entities.get('file', '')
        )

    def _apply_shell_text_tail_defaults(self, intent: str, entities: dict[str, Any], result: dict[str, Any]) -> None:
        if intent not in {'text_tail', 'text_head', 'text_tail_follow'}:
            return
        result.setdefault('lines', str(entities.get('lines', entities.get('limit', '10'))))
        
        # Extract lines from text if needed
        text = str(entities.get('text', ''))
        import re
        m = re.search(r'(\d+)\s+(?:line|linii|wierszy)', text.lower())
        if m:
            result['lines'] = m.group(1)

    def _apply_shell_text_cat_defaults(self, intent: str, entities: dict[str, Any], result: dict[str, Any]) -> None:
        if intent not in {'text_cat', 'text_cat_number'}:
            return
        self._apply_shell_file_default(entities, result)

    def _apply_shell_json_defaults(self, intent: str, entities: dict[str, Any], result: dict[str, Any]) -> None:
        if intent not in {'json_jq', 'json_jq_pretty', 'json_jq_keys'}:
            return
        self._apply_shell_file_default(entities, result)
        if not result.get('filter'):
            result['filter'] = '.'

    def _apply_shell_text_wc_defaults(self, intent: str, entities: dict[str, Any], result: dict[str, Any]) -> None:
        if intent not in {'text_wc', 'text_wc_lines', 'text_wc_words'}:
            return
        self._apply_shell_file_default(entities, result)
        
        # Determine flags based on intent
        if intent == 'text_wc_lines':
            result['flags'] = '-l'
        elif intent == 'text_wc_words':
            result['flags'] = '-w'
        else:
            # Auto-detect from text
            text_lower = str(entities.get('text', '')).lower()
            if any(x in text_lower for x in ('lines', 'linie', 'wierszy')):
                result['flags'] = '-l'
            elif any(x in text_lower for x in ('słow', 'slow', 'words')):
                result['flags'] = '-w'

    def _shell_intent_file_search(self, entities: dict[str, Any], result: dict[str, Any]) -> None:
        result.setdefault('extension', entities.get('file_pattern', entities.get('extension', 'py')))
        result.setdefault('path', '.')

    def _shell_intent_file_content(self, entities: dict[str, Any], result: dict[str, Any]) -> None:
        result.setdefault('file_path', entities.get('target', ''))
    
    def _prepare_docker_entities(self, intent: str, entities: dict[str, Any]) -> dict[str, Any]:
        """Prepare Docker entities."""
        result = entities.copy()
        
        # Apply Docker-specific defaults
        result.setdefault('flags', '')
        result.setdefault('image', entities.get('container', ''))
        result.setdefault('container', entities.get('name', ''))
        result.setdefault('command', '')
        result.setdefault('volume', '')
        result.setdefault('mount', '')
        result.setdefault('host_port', '8080')
        result.setdefault('container_port', '80')
        result.setdefault('registry', 'docker.io')
        result.setdefault('network', '')
        result.setdefault('service', '')
        
        return result
    
    def _prepare_kubernetes_entities(self, intent: str, entities: dict[str, Any]) -> dict[str, Any]:
        """Prepare Kubernetes entities."""
        result = entities.copy()
        
        # Apply Kubernetes-specific defaults
        result.setdefault('namespace', '')
        result.setdefault('selector', '')
        result.setdefault('output', '')
        result.setdefault('flags', '')
        result.setdefault('file', '')
        result.setdefault('context', '')
        result.setdefault('cluster', '')
        result.setdefault('user', '')
        result.setdefault('resource', 'pods')
        result.setdefault('name', '')
        result.setdefault('replicas', '1')
        result.setdefault('min', '1')
        result.setdefault('max', '3')
        result.setdefault('condition', 'available')
        result.setdefault('timeout', '300s')
        result.setdefault('local_port', '8080')
        result.setdefault('remote_port', '80')
        result.setdefault('container', '')
        result.setdefault('labels', '')
        result.setdefault('annotations', '')
        result.setdefault('port', '80')
        result.setdefault('target_port', '80')
        result.setdefault('env_vars', '')
        result.setdefault('directory', '')
        result.setdefault('patch', '')
        result.setdefault('sort_by', '.metadata.creationTimestamp')
        result.setdefault('csr', '')
        result.setdefault('taint', '')
        result.setdefault('node', '')
        result.setdefault('pod', '')
        result.setdefault('source', '')
        result.setdefault('destination', '')
        result.setdefault('verb', 'get')
        result.setdefault('command', '')
        
        return result
    
    def _prepare_git_entities(self, intent: str, entities: dict[str, Any]) -> dict[str, Any]:
        """Prepare Git entities."""
        result = entities.copy()
        
        # Apply Git-specific defaults
        result.setdefault('files', '.')
        result.setdefault('message', '')
        result.setdefault('remote', 'origin')
        result.setdefault('branch', 'main')
        result.setdefault('commit', 'HEAD')
        result.setdefault('url', '')
        result.setdefault('directory', '')
        result.setdefault('depth', '1')
        result.setdefault('name', '')
        result.setdefault('file', '')
        result.setdefault('pattern', '')
        result.setdefault('commit1', 'HEAD')
        result.setdefault('commit2', 'HEAD~1')
        result.setdefault('key', '')
        result.setdefault('value', '')
        result.setdefault('path', '')
        result.setdefault('old', '')
        result.setdefault('new', '')
        result.setdefault('flags', '')
        result.setdefault('scope', '--local')
        result.setdefault('env_file', '.env')
        result.setdefault('pod', '')
        result.setdefault('source', '')
        result.setdefault('target', '')
        result.setdefault('condition', 'ready')
        result.setdefault('command', '')
        
        return result
    
    def _fill_template(self, template: str, entities: dict[str, Any]) -> str:
        """Fill template with entities."""
        result = template
        
        for key, value in entities.items():
            placeholder = f"{{{key}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(value) if value else '')
        
        return result
    
    def _clean_command(self, command: str) -> str:
        """Clean up generated command."""
        # Remove multiple spaces
        import re
        command = re.sub(r'\s+', ' ', command)
        
        # Remove trailing/leading spaces
        command = command.strip()
        
        # Remove empty flags (only remove standalone flags, not flags with values)
        # This regex removes flags like "-flag " but keeps "-flag value"
        command = re.sub(r'\s+-[a-zA-Z]+\s+$', ' ', command)
        command = re.sub(r'\s+-[a-zA-Z]+\s+(?=-[a-zA-Z])', ' ', command)
        
        # Clean up again
        command = re.sub(r'\s+', ' ', command)
        
        return command.strip()
    
    def _find_missing(self, template: str, entities: dict[str, Any]) -> list[str]:
        """Find missing entities in template."""
        import re
        placeholders = re.findall(r'\{(\w+)\}', template)
        return [p for p in placeholders if p not in entities or not entities[p]]
    
    def add_template(self, domain: str, intent: str, template: str) -> None:
        """
        Add custom template.
        
        Args:
            domain: Domain name
            intent: Intent name
            template: Template string with {placeholders}
        """
        if domain not in self.templates:
            self.templates[domain] = {}
        self.templates[domain][intent] = template
    
    def get_template(self, domain: str, intent: str) -> Optional[str]:
        """Get template for domain/intent."""
        return self.templates.get(domain, {}).get(intent)
    
    def list_templates(self, domain: Optional[str] = None):
        """List available templates.

        Backwards compatible behavior:
        - If domain is provided: returns list[str] of intents for that domain
        - If domain is None: returns dict[str, list[str]] for all domains
        """
        if domain is None:
            return {d: list(intents.keys()) for d, intents in self.templates.items()}
        return list(self.templates.get(domain, {}).keys())
