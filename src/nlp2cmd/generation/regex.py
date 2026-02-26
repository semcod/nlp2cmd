"""
Iteration 2: Regex Entity Extraction.

Extract entities from text using regex patterns without LLM.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from nlp2cmd.utils.data_files import find_data_file


@dataclass
class ExtractedEntity:
    """A single extracted entity."""
    
    name: str
    value: Any
    confidence: float
    source_pattern: Optional[str] = None


@dataclass
class ExtractionResult:
    """Result of entity extraction."""
    
    entities: dict[str, Any]
    extracted: list[ExtractedEntity]
    raw_text: str
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class RegexEntityExtractor:
    """
    Extract entities from text using regex patterns.
    
    No LLM needed - uses predefined regex patterns to extract
    entities like table names, columns, paths, etc.
    
    Example:
        extractor = RegexEntityExtractor()
        result = extractor.extract("Pokaż kolumny id, name z tabeli users", domain='sql')
        # result.entities == {'table': 'users', 'columns': ['id', 'name']}
    """
    
    # Common patterns across domains
    COMMON_PATTERNS: dict[str, list[str]] = {
        'number': [
            r'\b(\d+)\b',
        ],
        'quoted_string': [
            r'"([^"]+)"',
            r"'([^']+)'",
            r'`([^`]+)`',
        ],
    }
    
    # Domain-specific patterns
    SQL_PATTERNS: dict[str, list[str]] = {
        'table': [
            r'(?:from|into|update|table|tabeli?|tabelę|z tabeli)\s+[`"\']?(\w+)[`"\']?',
            r'(?:do tabeli|do|from|into)\s+[`"\']?(\w+)[`"\']?',
        ],
        'columns': [
            r'(?:columns?|kolumny?|pola?|select)\s*[:\s]+([a-zA-Z_][\w,\s]*)',
            r'(?:pokaż|wyświetl)\s+([a-zA-Z_][\w,\s]*)\s+(?:z|from)',
        ],
        'limit': [
            r'(?:limit|pierwsz[ye]|top|ostatni[che]?)\s+(\d+)',
            r'(\d+)\s+(?:rekordów|wierszy|rows?|pierwszych|ostatnich)',
        ],
        'where_field': [
            r'(?:where|gdzie|gdy|dla|for)\s+(\w+)\s*[=<>!]',
            r'(\w+)\s*=\s*[\'"]?[\w]+[\'"]?',
        ],
        'where_value': [
            r'(?:where|gdzie|gdy)\s+\w+\s*=\s*[\'"]?(\w+)[\'"]?',
            r'=\s*[\'"]?(\w+)[\'"]?',
        ],
        'order_by': [
            r'(?:order\s+by|sortuj\s+(?:po|wg)|posortuj)\s+(\w+)',
            r'(?:rosnąco|malejąco|asc|desc)\s+(?:po|by)\s+(\w+)',
        ],
        'order_direction': [
            r'\b(asc|desc|rosnąco|malejąco)\b',
        ],
        'aggregation': [
            r'\b(count|sum|avg|min|max|policz|zsumuj|średnia)\b',
        ],
        'group_by': [
            r'(?:group\s+by|grupuj\s+(?:po|wg))\s+(\w+)',
            r'(?:pogrupuj|grupowanie)\s+(?:po|wg)\s+(\w+)',
        ],
    }
    
    SHELL_PATTERNS: dict[str, list[str]] = {
        'path': [
            # User folders patterns - MOST SPECIFIC FIRST
            r'(?:show|pokaż|list|wyświetl)\s+(?:user|użytkownik)\s+(?:folders?|foldery|katalogi|directories?)\b',
            r'(?:user|użytkownik)\s+(?:folders?|foldery|katalogi|directories?)\s+(?:show|pokaż|list|wyświetl)\b',
            r'(?:foldery|folders?)\s+(?:użytkownika|usera|user)\b',
            r'(?:użytkownika|usera|user)\s+(?:foldery|folders?)\b',
            # Direct match for "user folders" pattern
            r'user\s+folders',
            # Generic path patterns with capture groups
            r'(?:w\s+)?(?:katalogu|folderze|ścieżce|directory|folder|path)?\s*[`"\']?([/~][\w\.\-/]+)[`"\']?',
            r'(?:w\s+)?(?:katalogu|folderze)?\s+(?:użytkownika|user|home)\b\s*[`"\']?([/~][\w\.\-/]*)[`"\']?',
            r'(?:do|from|to|z|in)\s+[`"\']?([/~][\w\.\-/]+)[`"\']?',
            r'(?:do|from|to|z|in)\s+[`"\']?((?:\./|\.\./)[\w\.\-/]*|\.{1,2})[`"\']?',
            r'\s([/~][\w\.\-/]+)\s',
            r'\s((?:\./|\.\./)[\w\.\-/]*|\.{1,2})\s',
            # User file patterns
            r'(?:pliki|plików|files?)\s+(?:użytkownika|usera|user)\b',
            r'(?:użytkownika|usera|user)\s+(?:pliki|plików|files?)\b',
            # Generic user home directory with capture group
            r'((?:pliki|plików|files?)\s+(?:użytkownika|usera|user))',
            r'((?:użytkownika|usera|user)\s+(?:pliki|plików|files?))',
        ],
        'username': [
            # Most specific patterns first
            r'(?:show|pokaż|display|list)\s+(?:user|użytkownik)\s+(?:files|pliki|foldery|katalogi)\s+([a-zA-Z0-9_-]+)',
            r'(?:user|użytkownik)\s+(?:files|pliki|foldery|katalogi)\s+([a-zA-Z0-9_-]+)',
            # User + specific username
            r'(?:użytkownika|usera|user)\s+([a-zA-Z0-9_-]+)',
            r'(?:użytkownik|user)\s+([a-zA-Z0-9_-]+)',
            # File/directory patterns with username - ONLY FOR SPECIFIC USERNAMES
            r'(?:foldery|pliki|katalogi|files?)\s+(?:użytkownika|usera|user)\s+([a-zA-Z0-9_-]+)',
            # Generic user context (no specific username) - ONLY IF NO PATH MATCH
            r'(?:użytkownika|usera|user)(?:\s|$)',
        ],
        'file': [
            r'(?:plik|file|log(?:ach|i|ów)?|logs?)\s+[`"\']?((?:\./|\.\./|/)[\w\.\-/]+\.[A-Za-z0-9]{1,8})[`"\']?',
            r'[`"\']?((?:\./|\.\./|/)[\w\.\-/]+\.(?:log|txt|json|ya?ml|csv|tsv|py|sh|md))[`"\']?',
            r'\b([\w\-]+\.(?:log|txt|json|ya?ml|csv|tsv|py|sh|md))\b',
        ],
        'lines': [
            r'(?:ostatni(?:e|ch)?|tail|last)\s+(\d+)\s+(?:lini[ie]|lines?|wiersz(?:y|e))',
            r'(?:pokaż|wyświetl|show)\s+(\d+)\s+(?:lini[ie]|lines?|wiersz(?:y|e))',
            r'(?:--tail|--lines|-n)\s+(\d+)',
        ],
        'file_pattern': [
            r'\*\.(\w+)',
            r'\.(\w+)\s+files?',
            r'(?:pliki?|files?)\s+\.(\w{1,16})\b',
            r'(?:rozszerzenie|extension)\s+\.?((\w+))',
        ],
        'application': [
            # Application name after "run", "start", "launch", "uruchom", etc.
            r'(?:uruchom|urucham|start|run|launch|execute)\s+(?:aplikację|aplikacje|app|application)\s+([a-zA-Z0-9_-]+)',
            r'(?:uruchom|urucham|start|run|launch)\s+([a-zA-Z0-9_-]+)',
            # Just application name (fallback)
            r'\b([a-zA-Z][a-zA-Z0-9_-]{2,})\b',
        ],
        'script': [
            # Python script files
            r'(?:python|uruchom|run)\s+(?:skrypt|script)\s+([a-zA-Z0-9_-]+\.py)',
            r'(?:python|uruchom|run)\s+([a-zA-Z0-9_-]+\.py)',
            r'\b([a-zA-Z0-9_-]+\.py)\b',
        ],
        'server_command': [
            # Server commands
            r'(?:uruchom|start|run)\s+(?:serwer|server)\s+([a-zA-Z0-9_-]+)',
            r'(?:npm start|python manage\.py runserver|yarn start)',
        ],
        'service': [
            # Service name after systemctl commands
            r'(?:systemctl|sudo systemctl)\s+(?:start|stop|restart|reload|enable|disable|uruchom|zatrzymaj|zrestartuj)\s+([a-zA-Z0-9_-]+)',
            r'(?:uruchom|zatrzymaj|zrestartuj|restartuj|włącz|wyłącz)\s+(?:usługę|uslugę|usluge|serwis|service)\s+([a-zA-Z0-9_-]+)',
            r'(?:start|stop|restart)\s+(?:service|usługę|uslugę)\s+([a-zA-Z0-9_-]+)',
            r'(?:status)\s+(?:usługi|uslugi|uslug[ię]|serwisu|service)\s+([a-zA-Z0-9_-]+)',
            # Service name before verb (reversed word order): "nginx uruchom usługę"
            r'([a-zA-Z0-9_-]+)\s+(?:uruchom|zatrzymaj|zrestartuj|restartuj)\s+(?:usługę|uslugę|usluge|serwis)',
            r'(?:usługę|uslugę|usluge|usługi|uslugi|serwis|service)\s+([a-zA-Z0-9_-]+)',
            # Direct: "uruchom <service>" without usługę keyword
            r'(?:uruchom|zatrzymaj|zrestartuj|restartuj)\s+([a-zA-Z0-9_-]+)(?:\s+\d+)?$',
        ],
        'container': [
            # Docker container name
            r'(?:docker|kontener)\s+(?:run|stop|start|restart|kill)\s+([a-zA-Z0-9_-]+)',
            r'(?:uruchom|zatrzymaj|zrestartuj)\s+(?:kontener|docker)\s+([a-zA-Z0-9_-]+)',
        ],
        'image': [
            # Docker image name
            r'(?:docker|kontener)\s+(?:build|run|pull)\s+([a-zA-Z0-9_/:-]+)',
            r'(?:zbuduj|uruchom|pobierz)\s+(?:obraz|docker)\s+([a-zA-Z0-9_/:-]+)',
        ],
        'filename': [
            r'(?:plik|file)\s+[`"\']?([\w\.\-]+)[`"\']?',
            r'(?:katalog|directory|folder)\s+[`"\']?([\w\.\-]+)[`"\']?',
            r'[`"\']?([\w]+\.\w+)[`"\']?',
        ],
        'source': [
            # Source file for copy/move operations
            r'(?:copy|kopiuj|skopiuj)\s+(?:plik|file)?\s*([`"\']?[\w\.\-/]+[`"\']?)\s+(?:to|do)',
            r'(?:move|przenieś|mv)\s+(?:plik|file)?\s*([`"\']?[\w\.\-/]+[`"\']?)\s+(?:to|do)',
        ],
        'destination': [
            # Destination path for copy/move operations
            r'(?:to|do)\s+([`"\']?[\w\.\-/]+[`"\']?)$',
            r'(?:do|to)\s+([`"\']?[\w\.\-/]+[`"\']?)\s*$',
        ],
        'directory': [
            # Directory name for creation
            r'(?:create|make|utwórz|stwórz)\s+(?:directory|folder|katalog)\s+([a-zA-Z0-9_-]+)',
            r'(?:mkdir|mkdir)\s+([a-zA-Z0-9_-]+)',
        ],
        'file': [
            # File name for deletion
            r'(?:delete|remove|usuń|rm)\s+(?:plik|file)?\s*([`"\']?[\w\.\-]+[`"\']?)',
        ],
        'pid': [
            # Process ID for kill command
            r'(?:kill|zabij)\s+(?:process|proces)?\s*(\d+)',
            r'(?:kill|zabij)\s+-9\s+(\d+)',
        ],
        'process_name': [
            # Process name for search
            r'(?:find|znajdź|grep)\s+(?:process|proces)\s+([a-zA-Z0-9_-]+)',
            r'(?:ps aux|grep)\s+([a-zA-Z0-9_-]+)',
        ],
        'size': [
            r'(\d+)\s*([KMGT]?B)',
            r'(?:większ[ey]|larger|bigger)\s+(?:niż|than)?\s*(\d+)\s*([KMGT]?B)?',
            r'(?:mniejsz[ey]|smaller)\s+(?:niż|than)?\s*(\d+)\s*([KMGT]?B)?',
        ],
        'age': [
            r'(?:starsze|older)\s+(?:niż|than)?\s*(\d+)\s*(dni|days?|godzin|hours?|minut|minutes?)',
            r'(?:młodsze|newer)\s+(?:niż|than)?\s*(\d+)\s*(dni|days?|godzin|hours?|minut|minutes?)',
            r'(\d+)\s*(dni|days?|godzin|hours?)\s+(?:temu|ago)',
            r'(?:zmodyfikowane|modified|utworzone|created)\s+(?:w\s+ciągu\s+)?ostatnich\s+(\d+)\s*(dni|days?|godzin|hours?)',
            r'(?:zmodyfikowane|modified|utworzone|created)\s+(?:w\s+ciągu\s+)?ostatnie\s+(\d+)\s*(dni|days?|godzin|hours?)',
            r'(?:zmodyfikowane|modified|utworzone|created)\s+(?:in\s+)?last\s+(\d+)\s*(dni|days?|godzin|hours?)',
        ],
        'process_name': [
            r'(?:proces|process)\s+[`"\']?(\w+)[`"\']?',
            r'(?:kill|zabij)\s+[`"\']?(\w+)[`"\']?',
        ],
        'grep_pattern': [
            r'(?:szukaj|grep|find|wyszukaj)\s+[`"\']?(.+?)[`"\']?\s+(?:w|in)',
            r'(?:pattern|wzorzec)\s+[`"\']?(.+?)[`"\']?',
        ],
        'url': [
            r'(https?://[^\s\'"]+)',
            r'(www\.[^\s\'"]+)',
            r'(?:otwórz|open|go to|navigate to|wejdź na|idź do)\s+[`"\']?([a-zA-Z0-9][a-zA-Z0-9\-]*\.[a-zA-Z]{2,}(?:/[^\s\'"]*)?)[`"\']?',
            r'\b([a-zA-Z0-9][a-zA-Z0-9\-]*\.(?:com|org|net|io|dev|pl|de|uk|eu|gov|edu)(?:/[^\s\'"]*)?)\b',
        ],
        'query': [
            r'(?:wyszukaj|search|szukaj|znajdź|look up)\s+[`"\']?(.+?)[`"\']?(?:\s+w\s+|\s+in\s+|\s*$)',
            r'(?:google|search for)\s+[`"\']?(.+?)[`"\']?',
        ],
        'package': [
            r'(?:zainstaluj|install|apt install|apt-get install)\s+([a-zA-Z0-9][\w\-\+\.]*)',
            r'(?:zainstaluj|install|apt install|apt-get install)\s+pakiet\s+([a-zA-Z0-9][\w\-\+\.]*)',
            r'(?:dodaj|pobierz|wget|curl)\s+([a-zA-Z0-9][\w\-\+\.]*)',
        ],
        'search_query': [
            r'(?:szukaj|wyszukaj|znajdź|szukać|wyszukać|znaleźć)\s+(?:na\s+)?(?:amazon|google|github)\s+(.+?)(?:\s+|$)',
            r'(?:amazon|google|github)\s+(?:search|szukaj|wyszukaj)\s+(.+?)(?:\s+|$)',
            r'(?:szukaj|wyszukaj|znajdź|szukać|wyszukać|znaleźć)\s+(.+?)(?:\s+na\s+(?:amazon|google|github)|\s+w\s+(?:amazon|google|github))',
        ],
        'target': [
            r'(?:foldery|folders?|katalogi|directories?)',
        ],
    }
    
    DOCKER_PATTERNS: dict[str, list[str]] = {
        'flags': [
            r'\b(-a|--all)\b',
            r'\b(--no-trunc)\b',
        ],
        'container': [
            r'(?:kontener[a]?|container)\s+[`"\']?(\w[\w\-]*)[`"\']?',
            r'(?:w|in)\s+[`"\']?(\w[\w\-]*)[`"\']?\s+(?:kontener|container)',
        ],
        'image': [
            r'(?:obraz[u]?|image)\s+[`"\']?([\w\-/:\.]+)[`"\']?',
            r'(?:z|from)\s+[`"\']?([\w]+(?:/[\w\-]+)?(?::[\w\.\-]+)?)[`"\']?',
            r'\b(?:run|start|launch)\s+([a-zA-Z0-9][\w\-./:]+)\b',
        ],
        'port': [
            r'(?:port[u]?|porcie)\s+(\d+)',
            r'(\d+):(\d+)',
            r'-p\s+(\d+):?(\d+)?',
        ],
        'volume': [
            r'(?:wolumen|volume)\s+[`"\']?([/\w\.\-:]+)[`"\']?',
            r'-v\s+[`"\']?([/\w\.\-]+):([/\w\.\-]+)[`"\']?',
        ],
        'network': [
            r'(?:sieć|network)\s+[`"\']?(\w[\w\-]*)[`"\']?',
        ],
        'env_var': [
            r'(?:zmienna|env|environment)\s+(\w+)=([^\s]+)',
            r'-e\s+(\w+)=([^\s]+)',
        ],
        'tail_lines': [
            r'(?:ostatni[che]?|tail|last)\s+(\d+)\s+(?:lini[ie]|lines?|wierszy)',
            r'--tail\s+(\d+)',
        ],
    }
    
    KUBERNETES_PATTERNS: dict[str, list[str]] = {
        'resource_type': [
            r'\b(pod(?:y|a)?|deployment[sy]?|service[sy]?|serwis[y]?|configmap[sy]?|secret[sy]?|ingress|namespace[sy]?|node[sy]?|pv|pvc)\b',
        ],
        'resource_name': [
            r'(?:pod[a]?|deployment[u]?|serwis[u]?)\s+[`"\']?(\w[\w\-]*)[`"\']?',
            r'(?:o\s+nazwie|named|name)\s+[`"\']?(\w[\w\-]*)[`"\']?',
        ],
        'namespace': [
            r'(?:namespace|ns|przestrzeni)\s+[`"\']?(\w[\w\-]*)[`"\']?',
            r'-n\s+(\w[\w\-]*)',
        ],
        'replica_count': [
            r'(?:do|to)\s+(\d+)\s+(?:replik|replicas?|instancji|instances?)',
            r'(\d+)\s+(?:replik|replicas?|instancji|instances?)',
            r'--replicas[=\s]+(\d+)',
        ],
        'selector': [
            r'(?:label|etykiet[aą]|selector|selektor(?:em|a)?)\s+([A-Za-z0-9_.\-]+=[A-Za-z0-9_.\-]+)',
            r'-l\s+([A-Za-z0-9_.\-]+=[A-Za-z0-9_.\-]+)',
        ],
        'container_name': [
            r'(?:kontener|container)\s+[`"\']?(\w[\w\-]*)[`"\']?\s+w\s+(?:podzie|pod)',
            r'-c\s+(\w[\w\-]*)',
        ],
    }
    
    def __init__(
        self,
        custom_patterns: Optional[dict[str, dict[str, list[str]]]] = None,
    ):
        """
        Initialize entity extractor.
        
        Args:
            custom_patterns: Additional patterns per domain
        """
        self.patterns: dict[str, dict[str, list[str]]] = {
            'sql': self.SQL_PATTERNS.copy(),
            'shell': self.SHELL_PATTERNS.copy(),
            'docker': self.DOCKER_PATTERNS.copy(),
            'kubernetes': self.KUBERNETES_PATTERNS.copy(),
            'browser': {
                'url': [
                    r'(https?://[^\s\'"]+)',
                    r'(www\.[^\s\'"]+)',
                    r'(?:otwórz|open|go to|navigate to|wejdź na|idź do)\s+[`"\']?([a-zA-Z0-9][a-zA-Z0-9\-]*\.[a-zA-Z]{2,}(?:/[^\s\'"]*)?)[`"\']?',
                    r'\b([a-zA-Z0-9][a-zA-Z0-9\-]*\.(?:com|org|net|io|dev|pl|de|uk|eu|gov|edu)(?:/[^\s\'"]*)?)\b',
                ],
                'search_query': [
                    r'(?:szukaj|wyszukaj|znajdź|szukać|wyszukać|znaleźć)\s+(?:na\s+)?(?:amazon|google|github)\s+(.+?)(?:\s+|$)',
                    r'(?:amazon|google|github)\s+(?:search|szukaj|wyszukaj)\s+(.+?)(?:\s+|$)',
                    r'(?:szukaj|wyszukaj|znajdź|szukać|wyszukać|znaleźć)\s+(.+?)(?:\s+na\s+(?:amazon|google|github)|\s+w\s+(?:amazon|google|github))',
                ],
                'element': [
                    r'(?:kliknij|click|naciśnij|press|wybierz|select)\s+(?:przycisk|button|link|element)\s+[`"\']?(.+?)[`"\']?',
                    r'(?:przycisk|button|link|element)\s+[`"\']?(.+?)[`"\']?',
                ],
                'form_data': [
                    r'(?:wpisz|type|wypełnij|fill|enter)\s+(?:tekst|text|dane|data|informacje)\s+[`"\']?(.+?)[`"\']?',
                    r'(?:wypełnij|fill)\s+(?:formularz|form)\s+(?:danymi|with)\s+[`"\']?(.+?)[`"\']?',
                ],
            },
            'devops': {
                'service': [
                    r'(?:usług[ęi]|serwis|service)\s+[`"\']?(\w[\w\-]*)[`"\']?',
                    r'(?:systemctl|sudo\s+systemctl)\s+\w+\s+(\w[\w\-]*)',
                    r'(?:uruchom|zatrzymaj|zrestartuj|restart|start|stop|enable|disable)\s+(\w[\w\-]*)',
                ],
                'playbook': [
                    r'(?:playbook|playbooka)\s+[`"\']?([\w\-/.]+\.ya?ml)[`"\']?',
                ],
                'hosts': [
                    r'(?:host[sy]?|serwer[ay]?|maszyn[ay]?)\s+[`"\']?([\w\-.,]+)[`"\']?',
                    r'(?:na|on)\s+[`"\']?([\w\-.,]+)[`"\']?',
                ],
                'resource': [
                    r'(?:zasób|resource)\s+[`"\']?([\w\-.]+)[`"\']?',
                ],
                'domain': [
                    r'(?:domen[ęay]|domain)\s+[`"\']?([\w\-.]+)[`"\']?',
                ],
                'port': [
                    r'(?:port[u]?|porcie)\s+(\d+)',
                ],
            },
            'api': {
                'url': [
                    r'(https?://[^\s\'"]+)',
                    r'(?:endpoint|url|adres)\s+[`"\']?(https?://[^\s\'"]+)[`"\']?',
                ],
                'method': [
                    r'\b(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\b',
                ],
                'token': [
                    r'(?:token|klucz|key)\s+[`"\']?([^\s\'"]+)[`"\']?',
                ],
                'data': [
                    r'(?:dane|data|body|payload)\s+[`"\']?(\{.+?\})[`"\']?',
                ],
                'header': [
                    r'(?:nagłówek|header)\s+[`"\']?([^\s\'"]+:\s*[^\s\'"]+)[`"\']?',
                ],
            },
            'ffmpeg': {
                'input': [
                    r'(?:plik|file|wideo|video|audio|film)\s+[`"\']?([\w\-/.]+\.\w+)[`"\']?',
                    r'[`"\']?([\w\-/]+\.(?:mp4|avi|mkv|mov|wmv|flv|webm|mp3|wav|ogg|flac|aac))[`"\']?',
                ],
                'output': [
                    r'(?:do|to|na|output|wynik)\s+[`"\']?([\w\-/.]+\.\w+)[`"\']?',
                    r'(?:jako|as)\s+[`"\']?([\w\-/.]+\.\w+)[`"\']?',
                ],
                'resolution': [
                    r'(\d{3,4})[xX×](\d{3,4})',
                    r'\b(720p|1080p|4[kK]|2160p|480p|360p)\b',
                ],
                'time': [
                    r'(?:od|from|start)\s+(\d{1,2}:\d{2}(?::\d{2})?)',
                    r'(?:do|to|end)\s+(\d{1,2}:\d{2}(?::\d{2})?)',
                ],
                'codec': [
                    r'(?:kodek|codec)\s+(\w+)',
                    r'\b(h264|h265|hevc|vp9|av1|libx264|libx265|libvpx)\b',
                ],
                'bitrate': [
                    r'(?:bitrate|bitrejt)\s+(\d+[kKmM])',
                ],
            },
            'media': {
                'input': [
                    r'(?:obraz|image|zdjęcie|foto|plik)\s+[`"\']?([\w\-/.]+\.\w+)[`"\']?',
                    r'[`"\']?([\w\-/]+\.(?:jpg|jpeg|png|gif|bmp|tiff|webp|svg|pdf))[`"\']?',
                ],
                'output': [
                    r'(?:do|to|na|output|wynik|zapisz)\s+[`"\']?([\w\-/.]+\.\w+)[`"\']?',
                ],
                'width': [
                    r'(?:szerokość|width)\s+(\d+)',
                    r'(\d+)\s*[xX×]\s*\d+',
                ],
                'height': [
                    r'(?:wysokość|height)\s+(\d+)',
                    r'\d+\s*[xX×]\s*(\d+)',
                ],
                'quality': [
                    r'(?:jakość|quality)\s+(\d+)',
                ],
                'format': [
                    r'(?:format|typ)\s+(jpg|jpeg|png|gif|bmp|tiff|webp|svg|pdf)',
                ],
            },
            'data': {
                'file': [
                    r'[`"\']?([\w\-/]+\.(?:json|csv|tsv|xml|yaml|yml|parquet|sqlite|db))[`"\']?',
                    r'(?:plik|file)\s+[`"\']?([\w\-/.]+)[`"\']?',
                ],
                'field': [
                    r'(?:pole|field|kolumn[ęay]|column)\s+[`"\']?(\w+)[`"\']?',
                ],
                'filter': [
                    r'(?:filtr|filter|warunek|condition)\s+[`"\']?(.+?)[`"\']?',
                ],
                'pattern': [
                    r'(?:wzorzec|pattern)\s+[`"\']?(.+?)[`"\']?',
                ],
                'delimiter': [
                    r'(?:separator|delimiter|sep)\s+[`"\']?(.)[`"\']?',
                ],
                'query': [
                    r'(?:zapytanie|query)\s+[`"\']?(.+?)[`"\']?',
                ],
            },
            'remote': {
                'host': [
                    r'(?:host|serwer|server|maszyn[ęay]|machine)\s+[`"\']?([\w\-.:]+)[`"\']?',
                    r'(\w+)@([\w\-.:]+)',
                ],
                'user': [
                    r'(?:użytkownik|user|jako|as)\s+[`"\']?(\w+)[`"\']?',
                    r'(\w+)@[\w\-.:]+',
                ],
                'port': [
                    r'(?:port[u]?)\s+(\d+)',
                    r'-p\s+(\d+)',
                ],
                'key': [
                    r'(?:klucz|key)\s+[`"\']?([\w\-/.]+)[`"\']?',
                    r'-i\s+[`"\']?([\w\-/.]+)[`"\']?',
                ],
                'command': [
                    r'(?:komend[ęay]|command|wykonaj|execute)\s+[`"\']?(.+?)[`"\']?',
                ],
                'source': [
                    r'(?:z|from|source|źródło)\s+[`"\']?([\w\-/.]+)[`"\']?',
                ],
                'destination': [
                    r'(?:do|to|dest|cel)\s+[`"\']?([\w\-/.@:]+)[`"\']?',
                ],
            },
            'iot': {
                'pin': [
                    r'(?:pin|gpio|nóżk[ęay])\s+(\d+)',
                    r'GPIO\s*(\d+)',
                ],
                'bus': [
                    r'(?:bus|magistral[ęay]|szyn[ęay])\s+(\d+)',
                    r'i2c[- ]?(\d+)',
                ],
                'address': [
                    r'(?:adres|address)\s+(0x[0-9a-fA-F]+|\d+)',
                ],
                'device': [
                    r'(?:urządzeni[eu]|device)\s+[`"\']?([\w\-/.]+)[`"\']?',
                    r'/dev/([\w]+)',
                ],
                'topic': [
                    r'(?:topic|temat)\s+[`"\']?([\w\-/]+)[`"\']?',
                ],
                'sensor': [
                    r'(?:czujnik|sensor)\s+[`"\']?(\w+)[`"\']?',
                    r'\b(DHT\d+|BME\d+|BMP\d+|DS18B20|MQ\d+)\b',
                ],
                'baudrate': [
                    r'(?:baudrate|prędkość)\s+(\d+)',
                    r'\b(9600|115200|57600|38400|19200)\b',
                ],
            },
            'package_mgmt': {
                'package': [
                    r'(?:pakiet|package|bibliotek[ęay]|library|moduł|module)\s+[`"\']?([\w\-@/.]+)[`"\']?',
                    r'(?:zainstaluj|install|dodaj|add)\s+[`"\']?([\w\-@/.]+)[`"\']?',
                ],
                'version': [
                    r'(?:wersj[ęai]|version)\s+[`"\']?([\d.]+)[`"\']?',
                    r'==\s*([\d.]+)',
                    r'@([\d.]+)',
                ],
                'manager': [
                    r'\b(apt|yum|dnf|pip|npm|yarn|snap|flatpak|brew|cargo|go)\b',
                ],
            },
            'rag': {
                'collection': [
                    r'(?:kolekcj[ęai]|collection|indeks|index)\s+[`"\']?([\w\-]+)[`"\']?',
                ],
                'model': [
                    r'(?:model[u]?|model)\s+[`"\']?([\w\-/:]+)[`"\']?',
                ],
                'query': [
                    r'(?:zapytanie|query|pytanie|question|szukaj|search)\s+[`"\']?(.+?)[`"\']?',
                ],
                'db_path': [
                    r'(?:baz[ęay]|database|db)\s+[`"\']?([\w\-/.]+)[`"\']?',
                ],
                'file': [
                    r'(?:dokument|document|plik|file)\s+[`"\']?([\w\-/.]+)[`"\']?',
                ],
            },
            'presentation': {
                'input': [
                    r'(?:plik|file|dokument|document)\s+[`"\']?([\w\-/.]+\.\w+)[`"\']?',
                    r'[`"\']?([\w\-/]+\.(?:md|tex|rst|adoc|ipynb|html|csv|json))[`"\']?',
                ],
                'output': [
                    r'(?:do|to|na|output|wynik|zapisz)\s+[`"\']?([\w\-/.]+\.\w+)[`"\']?',
                ],
                'format': [
                    r'(?:format|typ)\s+(html|pdf|docx|pptx|png|svg|epub)',
                    r'\.(html|pdf|docx|pptx|png|svg|epub)\b',
                ],
                'title': [
                    r'(?:tytuł|title)\s+[`"\']?(.+?)[`"\']?',
                ],
            },
        }

        self._custom_patterns_provided = custom_patterns is not None
        self._load_patterns_from_json()
        
        if custom_patterns:
            for domain, domain_patterns in custom_patterns.items():
                if domain not in self.patterns:
                    self.patterns[domain] = {}
                self.patterns[domain].update(domain_patterns)

    def _load_patterns_from_json(self) -> None:
        if self._custom_patterns_provided:
            return

        p = find_data_file(
            explicit_path=os.environ.get("NLP2CMD_REGEX_PATTERNS_FILE"),
            default_filename="regex_patterns.json",
        )
        if not p:
            return

        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return
        if not isinstance(payload, dict):
            return

        for domain, domain_patterns in payload.items():
            if not isinstance(domain, str) or not domain.strip() or domain.startswith("$"):
                continue
            if not isinstance(domain_patterns, dict):
                continue

            bucket = self.patterns.setdefault(domain.strip(), {})
            if not isinstance(bucket, dict):
                continue

            for entity_type, patterns in domain_patterns.items():
                if not isinstance(entity_type, str) or not entity_type.strip() or not isinstance(patterns, list):
                    continue
                clean = [x.strip() for x in patterns if isinstance(x, str) and x.strip()]
                if not clean:
                    continue
                prev = bucket.get(entity_type)
                prev_list = prev if isinstance(prev, list) else []
                bucket[entity_type.strip()] = prev_list + clean
    
    def extract(self, text: str, domain: str) -> ExtractionResult:
        """
        Extract entities from text.
        
        Args:
            text: Natural language input
            domain: Target domain (sql, shell, docker, kubernetes)
            
        Returns:
            ExtractionResult with extracted entities
        """
        entities: dict[str, Any] = {}
        extracted: list[ExtractedEntity] = []
        
        # Get patterns for domain
        domain_patterns = self.patterns.get(domain, {})
        
        for entity_type, patterns in domain_patterns.items():
            for pattern in patterns:
                try:
                    match = re.search(pattern, text, re.IGNORECASE)
                except re.error:
                    continue
                if match:
                    value = self._process_match(entity_type, match)
                    if value is not None:
                        # Handle special cases
                        if entity_type == 'columns':
                            value = self._parse_columns(value)
                        elif entity_type == 'order_direction':
                            value = self._normalize_direction(value)
                        
                        entities[entity_type] = value
                        extracted.append(ExtractedEntity(
                            name=entity_type,
                            value=value,
                            confidence=0.8,
                            source_pattern=pattern,
                        ))
                        break  # Use first match for each entity type
        
        # Post-processing: build structured entities
        entities = self._post_process(entities, domain, text.lower())
        
        return ExtractionResult(
            entities=entities,
            extracted=extracted,
            raw_text=text,
        )
    
    def _process_match(self, entity_type: str, match: re.Match) -> Any:
        """Process regex match and return value."""
        groups = match.groups()
        
        if not groups:
            return match.group(0)
        
        # For patterns with multiple groups, handle specially
        if entity_type == 'port' and len(groups) >= 2:
            host_port = groups[0]
            container_port = groups[1] if groups[1] else groups[0]
            return {'host': host_port, 'container': container_port}
        
        if entity_type == 'size' and len(groups) >= 2:
            size = groups[0]
            unit = groups[1] if len(groups) > 1 and groups[1] else 'B'
            return {'value': int(size), 'unit': unit}
        
        if entity_type == 'age' and len(groups) >= 2:
            value = groups[0]
            unit = groups[1]
            return {'value': int(value), 'unit': self._normalize_time_unit(unit)}
        
        if entity_type == 'volume' and len(groups) >= 2:
            return {'host': groups[0], 'container': groups[1] if groups[1] else groups[0]}
        
        if entity_type == 'env_var' and len(groups) >= 2:
            return {'name': groups[0], 'value': groups[1]}
        
        if entity_type == 'path':
            # For path patterns, return the first group (path value)
            return groups[0] if groups else match.group(0)
        
        return groups[0]
    
    def _parse_columns(self, value: str) -> list[str]:
        """Parse column list from string."""
        if not value:
            return ['*']
        
        # Split by comma and clean up
        columns = [col.strip() for col in value.split(',')]
        blocked = {
            'z', 'from', 'tabeli', 'table',
            # Generic words that often appear in NL queries but are not real columns
            'dane', 'data', 'rekordy', 'wiersze', 'wszystko', 'wszystkie',
            'all', 'everything',
        }
        columns = [col for col in columns if col and col.lower() not in blocked]
        
        return columns if columns else ['*']
    
    def _normalize_direction(self, value: str) -> str:
        """Normalize sort direction."""
        if value.lower() in ('asc', 'rosnąco'):
            return 'ASC'
        if value.lower() in ('desc', 'malejąco'):
            return 'DESC'
        return 'ASC'
    
    def _normalize_time_unit(self, unit: str) -> str:
        """Normalize time unit."""
        unit_map = {
            'dni': 'days',
            'day': 'days',
            'days': 'days',
            'godzin': 'hours',
            'hour': 'hours',
            'hours': 'hours',
            'minut': 'minutes',
            'minute': 'minutes',
            'minutes': 'minutes',
        }
        return unit_map.get(unit.lower(), unit)
    
    def _post_process(self, entities: dict[str, Any], domain: str, text_lower: str) -> dict[str, Any]:
        """Post-process entities for adapter compatibility."""
        result = entities.copy()
        
        if domain == 'sql':
            # Convert to adapter format
            if 'where_field' in entities and 'where_value' in entities:
                result['filters'] = [{
                    'field': entities['where_field'],
                    'operator': '=',
                    'value': entities['where_value'],
                }]
            
            if 'order_by' in entities:
                direction = entities.get('order_direction', 'ASC')
                result['ordering'] = [{
                    'field': entities['order_by'],
                    'direction': direction,
                }]
            
            if 'aggregation' in entities:
                canonical_map = {
                    'policz': 'count',
                    'count': 'count',
                    'zsumuj': 'sum',
                    'sum': 'sum',
                    'średnia': 'avg',
                    'avg': 'avg',
                    'min': 'min',
                    'max': 'max',
                }
                canonical = canonical_map.get(str(entities['aggregation']).lower(), 'count')
                result['aggregation'] = canonical
                agg_map = {
                    'count': 'COUNT',
                    'policz': 'COUNT',
                    'sum': 'SUM',
                    'zsumuj': 'SUM',
                    'avg': 'AVG',
                    'średnia': 'AVG',
                    'min': 'MIN',
                    'max': 'MAX',
                }
                result['aggregations'] = [{
                    'function': agg_map.get(str(entities['aggregation']).lower(), 'COUNT'),
                    'field': '*',
                }]
            
            if 'group_by' in entities:
                result['grouping'] = [entities['group_by']]
        
        elif domain == 'shell':
            if 'filename' in entities and entities.get('filename') and 'file' not in entities:
                result['file'] = entities['filename']
            # Check for user folders pattern in raw text first
            if re.search(r'show\s+list\s+user\s+folders|pokaż\s+listę\s+użytkownik\s+foldery|list\s+user\s+folders|show\s+user\s+folders', text_lower):
                result['path'] = '~'
            # Handle user files patterns
            elif 'path' in entities and entities['path']:
                path = entities['path']
                if re.search(r'pliki.*(?:użytkownika|usera|user)|(?:użytkownika|usera|user).*pliki', path, re.IGNORECASE):
                    result['path'] = '~'
                elif re.search(r'foldery.*(?:użytkownika|usera|user)|(?:użytkownika|usera|user).*foldery', path, re.IGNORECASE):
                    result['path'] = '~'
                elif 'folderze użytkownika' in text_lower or 'folderze usera' in text_lower:
                    result['path'] = '~'
                else:
                    result['path'] = path
            # Handle "folderze użytkownika" -> default to ~ if no path found
            elif 'path' not in entities or not entities['path']:
                if 'file' not in result and 'filename' not in entities:
                    if re.search(r'folderze\s+użytkownika|katalogu\s+użytkownika|listę\s+folderów\s+użytkownika|listę\s+katalogów\s+użytkownika|foldery\s+użytkownika|user\s+folders|show\s+list\s+user\s+folders|show\s+user\s+folders|list\s+user\s+folders|user\s+folders', text_lower):
                        result['path'] = '~'
                    else:
                        result['path'] = '.'
            
            # Normalize path
            if 'path' in result and result['path']:
                path = result['path']
                if path.startswith('~'):
                    path = path.replace('~', '$HOME', 1)
                result['path'] = path

            # Backwards compatible: tests expect size as a string (e.g. "100MB")
            if 'size' in entities and isinstance(entities.get('size'), dict):
                parsed = entities.get('size') or {}
                try:
                    val = parsed.get('value')
                    unit = parsed.get('unit')
                    if val is not None and unit:
                        result['size_parsed'] = parsed
                        result['size'] = f"{val}{str(unit).upper()}"
                except Exception:
                    pass
            
            # Build find pattern
            if 'file_pattern' in entities:
                result['pattern'] = f"*.{entities['file_pattern']}"
        
        elif domain == 'docker':
            # Ensure container/image names are clean
            if 'container' in entities:
                result['container'] = entities['container'].strip('`"\'')
            if 'image' in entities:
                result['image'] = entities['image'].strip('`"\'')
        
        elif domain == 'kubernetes':
            # Normalize resource types
            if 'resource_type' in entities:
                resource_map = {
                    'pody': 'pods',
                    'pod': 'pods',
                    'deploymenty': 'deployments',
                    'serwisy': 'services',
                    'serwis': 'services',
                }
                rt = entities['resource_type'].lower()
                result['resource_type'] = resource_map.get(rt, rt)
        
        return result
    
    def extract_all_numbers(self, text: str) -> list[int]:
        """Extract all numbers from text."""
        return [int(m) for m in re.findall(r'\b(\d+)\b', text)]
    
    def extract_quoted_strings(self, text: str) -> list[str]:
        """Extract all quoted strings from text."""
        results = []
        for pattern in self.COMMON_PATTERNS['quoted_string']:
            results.extend(re.findall(pattern, text))
        return results
    
    def add_pattern(self, domain: str, entity_type: str, patterns: list[str]) -> None:
        """
        Add custom patterns.
        
        Args:
            domain: Domain name
            entity_type: Entity type name
            patterns: Regex patterns to add
        """
        if domain not in self.patterns:
            self.patterns[domain] = {}
        if entity_type not in self.patterns[domain]:
            self.patterns[domain][entity_type] = []
        self.patterns[domain][entity_type].extend(patterns)
