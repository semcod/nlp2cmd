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
    confidence: Optional[float] = None  # Backward compatibility


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
                confidence=0.0,
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
            confidence=1.0 if bool(command.strip()) else 0.0,
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
        
        # Normalize alternate entity key names
        if 'filters' in result and 'where' not in result:
            result['where'] = result.pop('filters')
        if 'ordering' in result and 'order' not in result:
            result['order'] = result.pop('ordering')

        # Initialize clauses
        where_clause = ''
        order_clause = ''
        limit_clause = ''

        # Handle WHERE clause (supports dict, list of filter dicts, or string)
        if 'where' in result:
            where = result['where']
            if isinstance(where, list):
                conditions = []
                for f in where:
                    if isinstance(f, dict):
                        field = f.get('field', '')
                        op = f.get('operator', '=')
                        val = f.get('value', '')
                        if isinstance(val, str):
                            conditions.append(f"{field} {op} '{val}'")
                        else:
                            conditions.append(f"{field} {op} {val}")
                if conditions:
                    where_clause = f" WHERE {' AND '.join(conditions)}"
            elif isinstance(where, dict):
                conditions = []
                for field, value in where.items():
                    if isinstance(value, str):
                        conditions.append(f"{field} = '{value}'")
                    else:
                        conditions.append(f"{field} = {value}")
                if conditions:
                    where_clause = f" WHERE {' AND '.join(conditions)}"
            elif isinstance(where, str) and where.strip():
                where_clause = f" WHERE {where}"

        # Handle ORDER BY (supports list of ordering dicts, dict, or string)
        if 'order' in result:
            order = result['order']
            if isinstance(order, list):
                order_items = []
                for item in order:
                    if isinstance(item, dict):
                        direction = item.get('direction', 'ASC').upper()
                        order_items.append(f"{item.get('field', 'id')} {direction}")
                    else:
                        order_items.append(str(item))
                if order_items:
                    order_clause = f" ORDER BY {', '.join(order_items)}"
            elif isinstance(order, dict):
                order_clause = f" ORDER BY {order.get('column', 'id')} {order.get('direction', 'ASC').upper()}"
            elif isinstance(order, str) and order.strip():
                order_clause = f" ORDER BY {order}"

        # Handle LIMIT
        if 'limit' in result:
            limit = result['limit']
            if isinstance(limit, (int, str)) and str(limit).isdigit():
                limit_clause = f" LIMIT {limit}"

        # Handle aggregation on select intent — redirect to COUNT/SUM/etc template
        if intent == 'select' and 'aggregation' in result:
            agg_map = {
                'count': 'COUNT', 'policz': 'COUNT',
                'sum': 'SUM', 'zsumuj': 'SUM',
                'avg': 'AVG', 'średnia': 'AVG',
                'min': 'MIN', 'max': 'MAX',
            }
            agg_fn = agg_map.get(str(result['aggregation']).lower(), 'COUNT')
            cols = result.get('columns', '*')
            if isinstance(cols, list):
                cols = ', '.join(cols)
            result['columns'] = f"{agg_fn}({cols})"

        # Set final clauses
        result['where'] = where_clause
        result['order'] = order_clause
        result['limit'] = limit_clause

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
        
        # Map port to ports for template compatibility
        if 'port' in result and 'ports' not in result:
            result['ports'] = result['port']
        
        # Map tail_lines to flags for logs command
        if intent == 'logs' and 'tail_lines' in result:
            tail_lines = result['tail_lines']
            if tail_lines and str(tail_lines).isdigit():
                result['flags'] = f"--tail {tail_lines}"
        
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
        
        # Map resource_type to resource for template compatibility
        if 'resource_type' in result and 'resource' not in result:
            result['resource'] = result['resource_type']
        
        # Map replica_count to replicas for template compatibility
        if 'replica_count' in result and 'replicas' not in result:
            result['replicas'] = result['replica_count']
        
        # Map name to pod for logs template
        if intent == 'logs' and 'name' in result and 'pod' not in result:
            result['pod'] = result['name']
        
        # Map tail_lines to follow and tail for logs template
        if intent == 'logs':
            if 'tail_lines' in result:
                result['tail'] = f"--tail={result['tail_lines']}"
            result.setdefault('follow', '-f' if result.get('follow') else '')
        
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

    # ── Shell intent-specific default methods ──────────────────────────

    def _shell_intent_file_search(self, entities: dict[str, Any], result: dict[str, Any]) -> None:
        result.setdefault('extension', entities.get('file_pattern', entities.get('extension', 'py')))
        result.setdefault('path', '.')

    def _shell_intent_file_content(self, entities: dict[str, Any], result: dict[str, Any]) -> None:
        result.setdefault('file_path', entities.get('target', ''))

    def _shell_intent_file_tail(self, entities: dict[str, Any], result: dict[str, Any]) -> None:
        result.setdefault('lines', '10')
        result.setdefault('file_path', entities.get('target', ''))

    def _shell_intent_file_size(self, entities: dict[str, Any], result: dict[str, Any]) -> None:
        result.setdefault('file_path', entities.get('target', ''))

    def _shell_intent_file_rename(self, entities: dict[str, Any], result: dict[str, Any]) -> None:
        result.setdefault('old_name', entities.get('old_name', ''))
        result.setdefault('new_name', entities.get('new_name', ''))

    def _shell_intent_file_delete_all(self, entities: dict[str, Any], result: dict[str, Any]) -> None:
        result.setdefault('extension', entities.get('file_pattern', entities.get('extension', 'tmp')))

    def _shell_intent_dir_create(self, entities: dict[str, Any], result: dict[str, Any]) -> None:
        result.setdefault('directory', entities.get('target', ''))

    def _shell_intent_remove_all(self, entities: dict[str, Any], result: dict[str, Any]) -> None:
        result.setdefault('extension', entities.get('file_pattern', entities.get('extension', 'tmp')))

    def _shell_intent_file_operation(self, entities: dict[str, Any], result: dict[str, Any]) -> None:
        text_lower = str(entities.get('text', '')).lower()
        handlers = (
            (self._shell_file_op_is_all, self._shell_file_op_all),
            (self._shell_file_op_is_directory, self._shell_file_op_directory),
            (self._shell_file_op_is_rename, self._shell_file_op_rename),
            (self._shell_file_op_is_size, self._shell_file_op_size),
            (self._shell_file_op_is_copy, self._shell_file_op_copy),
            (self._shell_file_op_is_move, self._shell_file_op_move),
            (self._shell_file_op_is_delete, self._shell_file_op_delete),
        )
        for predicate, handler in handlers:
            if predicate(text_lower):
                handler(entities, result)
                return
        self._shell_file_op_default(entities, result)

    def _shell_file_op_is_all(self, text_lower: str) -> bool:
        return 'wszystkie' in text_lower or 'all' in text_lower

    def _shell_file_op_is_directory(self, text_lower: str) -> bool:
        return 'katalog' in text_lower or 'directory' in text_lower or 'utwórz' in text_lower

    def _shell_file_op_is_rename(self, text_lower: str) -> bool:
        return 'zmień nazwę' in text_lower or 'rename' in text_lower

    def _shell_file_op_is_size(self, text_lower: str) -> bool:
        return 'rozmiar' in text_lower or 'size' in text_lower

    def _shell_file_op_is_copy(self, text_lower: str) -> bool:
        return 'skopiuj' in text_lower or 'copy' in text_lower

    def _shell_file_op_is_move(self, text_lower: str) -> bool:
        return 'przenieś' in text_lower or 'move' in text_lower

    def _shell_file_op_is_delete(self, text_lower: str) -> bool:
        return 'usuń' in text_lower or 'delete' in text_lower or 'remove' in text_lower

    def _shell_file_op_all(self, entities: dict[str, Any], result: dict[str, Any]) -> None:
        result.setdefault('extension', entities.get('file_pattern', entities.get('extension', 'tmp')))

    def _shell_file_op_directory(self, entities: dict[str, Any], result: dict[str, Any]) -> None:
        result.setdefault('directory', entities.get('target', ''))

    def _shell_file_op_rename(self, entities: dict[str, Any], result: dict[str, Any]) -> None:
        result.setdefault('old_name', entities.get('old_name', ''))
        result.setdefault('new_name', entities.get('new_name', ''))

    def _shell_file_op_size(self, entities: dict[str, Any], result: dict[str, Any]) -> None:
        result.setdefault('file_path', entities.get('target', ''))

    def _shell_file_op_copy(self, entities: dict[str, Any], result: dict[str, Any]) -> None:
        result.setdefault('source', entities.get('source', '.'))
        result.setdefault('destination', entities.get('destination', '.'))

    def _shell_file_op_move(self, entities: dict[str, Any], result: dict[str, Any]) -> None:
        result.setdefault('source', entities.get('source', '.'))
        result.setdefault('destination', entities.get('destination', '.'))

    def _shell_file_op_delete(self, entities: dict[str, Any], result: dict[str, Any]) -> None:
        result.setdefault('target', entities.get('target', ''))

    def _shell_file_op_default(self, entities: dict[str, Any], result: dict[str, Any]) -> None:
        result.setdefault('target', entities.get('target', ''))

    def _shell_intent_process_user(self, entities: dict[str, Any], result: dict[str, Any]) -> None:
        result.setdefault('user', self._get_default('shell.user', os.environ.get('USER') or getpass.getuser()))

    def _shell_intent_network_ping(self, result: dict[str, Any]) -> None:
        result.setdefault('host', self._get_default('shell.ping_host', os.environ.get('NLP2CMD_DEFAULT_PING_HOST') or 'google.com'))

    def _shell_intent_network_lsof(self, result: dict[str, Any]) -> None:
        result.setdefault('port', self._get_default('shell.default_port', os.environ.get('NLP2CMD_DEFAULT_PORT') or '8080'))

    def _shell_intent_network_scan(self, result: dict[str, Any]) -> None:
        result.setdefault('cidr', self._get_default('shell.scan_cidr', os.environ.get('NLP2CMD_DEFAULT_SCAN_CIDR') or '192.168.1.0/24'))

    def _shell_intent_network_speed(self, result: dict[str, Any]) -> None:
        result.setdefault('url', self._get_default('shell.speedtest_url', os.environ.get('NLP2CMD_DEFAULT_SPEEDTEST_URL') or 'http://speedtest.net'))

    def _shell_intent_disk_device(self, result: dict[str, Any]) -> None:
        result.setdefault('device', self._get_default('shell.disk_device', os.environ.get('NLP2CMD_DEFAULT_DISK_DEVICE') or '/dev/sda1'))

    def _shell_intent_backup_create(self, entities: dict[str, Any], result: dict[str, Any]) -> None:
        result.setdefault('source', entities.get('target', '.'))

    def _shell_intent_backup_copy(self, entities: dict[str, Any], result: dict[str, Any]) -> None:
        result.setdefault('source', entities.get('source', '.'))
        result.setdefault('destination', entities.get('destination', '.'))

    def _shell_intent_backup_restore(self, entities: dict[str, Any], result: dict[str, Any]) -> None:
        result.setdefault('file', entities.get('target', ''))

    def _shell_intent_backup_integrity(self, entities: dict[str, Any], result: dict[str, Any]) -> None:
        result.setdefault(
            'file',
            entities.get(
                'target',
                self._get_default('shell.backup_archive', os.environ.get('NLP2CMD_DEFAULT_BACKUP_ARCHIVE') or 'backup.tar.gz'),
            ),
        )

    def _shell_intent_backup_path(self, entities: dict[str, Any], result: dict[str, Any]) -> None:
        result.setdefault('path', entities.get('path', self._get_default('shell.backup_path', os.environ.get('NLP2CMD_DEFAULT_BACKUP_PATH') or './backup')))

    def _shell_intent_backup_size(self, entities: dict[str, Any], result: dict[str, Any]) -> None:
        result.setdefault(
            'file',
            entities.get(
                'target',
                self._get_default('shell.backup_archive', os.environ.get('NLP2CMD_DEFAULT_BACKUP_ARCHIVE') or 'backup.tar.gz'),
            ),
        )

    def _shell_intent_system_logs(self, result: dict[str, Any]) -> None:
        result.setdefault('file', self._get_default('shell.system_log_file', os.environ.get('NLP2CMD_DEFAULT_SYSTEM_LOG_FILE') or '/var/log/syslog'))

    def _shell_intent_dev_lint(self, result: dict[str, Any]) -> None:
        result.setdefault('path', 'src')

    def _shell_intent_dev_logs(self, result: dict[str, Any]) -> None:
        result.setdefault('file', self._get_default('shell.dev_log_file', os.environ.get('NLP2CMD_DEFAULT_DEV_LOG_FILE') or 'app.log'))

    def _shell_intent_dev_debug(self, result: dict[str, Any]) -> None:
        result.setdefault('script', self._get_default('shell.debug_script', os.environ.get('NLP2CMD_DEFAULT_DEBUG_SCRIPT') or 'script.py'))

    def _shell_intent_dev_docs(self, result: dict[str, Any]) -> None:
        result.setdefault('path', 'docs')

    def _shell_intent_security_permissions(self, entities: dict[str, Any], result: dict[str, Any]) -> None:
        result.setdefault('file_path', entities.get('file_path', 'config.conf'))

    def _shell_intent_process_kill(self, result: dict[str, Any]) -> None:
        result.setdefault('pid', 'PID')

    def _shell_intent_process_background(self, result: dict[str, Any]) -> None:
        result.setdefault('command', 'python script.py')

    def _shell_intent_process_script(self, entities: dict[str, Any], result: dict[str, Any]) -> None:
        result.setdefault('script', entities.get('target', 'script.sh'))

    def _shell_intent_service(self, entities: dict[str, Any], result: dict[str, Any]) -> None:
        result.setdefault('service', entities.get('service', self._get_default('shell.default_service', os.environ.get('NLP2CMD_DEFAULT_SERVICE') or 'nginx')))

    def _shell_intent_text_search_errors(self, result: dict[str, Any]) -> None:
        result.setdefault('file', self._get_default('shell.system_log_file', os.environ.get('NLP2CMD_DEFAULT_SYSTEM_LOG_FILE') or '/var/log/syslog'))

    def _shell_intent_open_url(self, entities: dict[str, Any], result: dict[str, Any]) -> None:
        url = entities.get('url', '')
        if url and not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        result['url'] = url or self._get_default('shell.default_url', os.environ.get('NLP2CMD_DEFAULT_URL') or 'https://google.com')

    def _shell_intent_search_web(self, entities: dict[str, Any], result: dict[str, Any]) -> None:
        query = entities.get('query', '')
        if not query:
            text = entities.get('text', '')
            match = re.search(r'(?:wyszukaj|search|szukaj|google)\s+(.+?)(?:\s+w\s+|\s*$)', text, re.IGNORECASE)
            if match:
                query = match.group(1).strip()
        result['query'] = query or 'nlp2cmd'

    # ── Shell category dispatch methods ────────────────────────────────

    def _apply_shell_backup_defaults(self, intent: str, entities: dict[str, Any], result: dict[str, Any]) -> bool:
        backup_handlers = {
            'backup_create': self._shell_intent_backup_create,
            'backup_copy': self._shell_intent_backup_copy,
            'backup_restore': self._shell_intent_backup_restore,
            'backup_integrity': self._shell_intent_backup_integrity,
            'backup_status': self._shell_intent_backup_path,
            'backup_cleanup': self._shell_intent_backup_path,
            'backup_size': self._shell_intent_backup_size,
        }
        handler = backup_handlers.get(intent)
        if handler is None:
            return False
        handler(entities, result)
        return True

    def _apply_shell_system_defaults(self, intent: str, entities: dict[str, Any], result: dict[str, Any]) -> bool:
        system_handlers = {
            'system_logs': lambda e, r: self._shell_intent_system_logs(r),
        }
        handler = system_handlers.get(intent)
        if handler is None:
            return False
        handler(entities, result)
        return True

    def _apply_shell_dev_defaults(self, intent: str, entities: dict[str, Any], result: dict[str, Any]) -> bool:
        dev_handlers = {
            'dev_lint': lambda e, r: self._shell_intent_dev_lint(r),
            'dev_logs': lambda e, r: self._shell_intent_dev_logs(r),
            'dev_debug': lambda e, r: self._shell_intent_dev_debug(r),
            'dev_docs': lambda e, r: self._shell_intent_dev_docs(r),
        }
        handler = dev_handlers.get(intent)
        if handler is None:
            return False
        handler(entities, result)
        return True

    def _apply_shell_security_defaults(self, intent: str, entities: dict[str, Any], result: dict[str, Any]) -> bool:
        security_handlers = {
            'security_permissions': self._shell_intent_security_permissions,
        }
        handler = security_handlers.get(intent)
        if handler is None:
            return False
        handler(entities, result)
        return True

    def _apply_shell_text_search_defaults(self, intent: str, entities: dict[str, Any], result: dict[str, Any]) -> bool:
        text_handlers = {
            'text_search_errors': lambda e, r: self._shell_intent_text_search_errors(r),
        }
        handler = text_handlers.get(intent)
        if handler is None:
            return False
        handler(entities, result)
        return True

    def _apply_shell_network_defaults(self, intent: str, entities: dict[str, Any], result: dict[str, Any]) -> bool:
        network_handlers = {
            'network_ping': lambda e, r: self._shell_intent_network_ping(r),
            'network_lsof': lambda e, r: self._shell_intent_network_lsof(r),
            'network_scan': lambda e, r: self._shell_intent_network_scan(r),
            'network_speed': lambda e, r: self._shell_intent_network_speed(r),
        }
        handler = network_handlers.get(intent)
        if handler is None:
            return False
        handler(entities, result)
        return True

    def _apply_shell_disk_defaults(self, intent: str, entities: dict[str, Any], result: dict[str, Any]) -> bool:
        disk_handlers = {
            'disk_health': lambda e, r: self._shell_intent_disk_device(r),
            'disk_defrag': lambda e, r: self._shell_intent_disk_device(r),
        }
        handler = disk_handlers.get(intent)
        if handler is None:
            return False
        handler(entities, result)
        return True

    def _apply_shell_process_defaults(self, intent: str, entities: dict[str, Any], result: dict[str, Any]) -> bool:
        process_handlers = {
            'process_user': self._shell_intent_process_user,
            'process_kill': lambda e, r: self._shell_intent_process_kill(r),
            'process_background': lambda e, r: self._shell_intent_process_background(r),
            'process_script': self._shell_intent_process_script,
        }
        handler = process_handlers.get(intent)
        if handler is None:
            return False
        handler(entities, result)
        return True

    def _apply_shell_service_defaults(self, intent: str, entities: dict[str, Any], result: dict[str, Any]) -> bool:
        service_intents = {
            'service_start': self._shell_intent_service,
            'service_stop': self._shell_intent_service,
            'service_restart': self._shell_intent_service,
            'service_status': self._shell_intent_service,
        }
        handler = service_intents.get(intent)
        if handler is None:
            return False
        handler(entities, result)
        return True

    def _apply_shell_browser_defaults(self, intent: str, entities: dict[str, Any], result: dict[str, Any]) -> bool:
        if intent in ('open_url', 'open_browser', 'browse'):
            self._shell_intent_open_url(entities, result)
            return True
        browser_handlers = {
            'search_web': self._shell_intent_search_web,
        }
        handler = browser_handlers.get(intent)
        if handler is None:
            return False
        handler(entities, result)
        return True

    def _apply_shell_intent_specific_defaults(self, intent: str, entities: dict[str, Any], result: dict[str, Any]) -> None:
        file_handlers: dict[str, Any] = {
            'file_search': self._shell_intent_file_search,
            'file_content': self._shell_intent_file_content,
            'file_tail': self._shell_intent_file_tail,
            'file_size': self._shell_intent_file_size,
            'file_rename': self._shell_intent_file_rename,
            'file_delete_all': self._shell_intent_file_delete_all,
            'dir_create': self._shell_intent_dir_create,
            'remove_all': self._shell_intent_remove_all,
            'file_operation': self._shell_intent_file_operation,
        }
        handler = file_handlers.get(intent)
        if handler is not None:
            handler(entities, result)
            return

        category_handlers = (
            self._apply_shell_backup_defaults,
            self._apply_shell_system_defaults,
            self._apply_shell_dev_defaults,
            self._apply_shell_security_defaults,
            self._apply_shell_text_search_defaults,
            self._apply_shell_network_defaults,
            self._apply_shell_disk_defaults,
            self._apply_shell_process_defaults,
            self._apply_shell_service_defaults,
            self._apply_shell_browser_defaults,
        )
        for handler_func in category_handlers:
            if handler_func(intent, entities, result):
                return
