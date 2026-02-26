"""
Template modules for NLP2CMD generation.

This package contains domain-specific template collections.
"""

from .sql_templates import SQL_TEMPLATES
from .shell_templates import SHELL_TEMPLATES
from .docker_templates import DOCKER_TEMPLATES
from .kubernetes_templates import KUBERNETES_TEMPLATES
from .browser_templates import BROWSER_TEMPLATES
from .git_templates import GIT_TEMPLATES
from .devops_templates import DEVOPS_TEMPLATES
from .api_templates import API_TEMPLATES
from .ffmpeg_templates import FFMPEG_TEMPLATES
from .media_templates import MEDIA_TEMPLATES
from .data_templates import DATA_TEMPLATES
from .remote_templates import REMOTE_TEMPLATES
from .iot_templates import IOT_TEMPLATES
from .package_mgmt_templates import PACKAGE_MGMT_TEMPLATES
from .rag_templates import RAG_TEMPLATES
from .presentation_templates import PRESENTATION_TEMPLATES

__all__ = [
    'SQL_TEMPLATES',
    'SHELL_TEMPLATES', 
    'DOCKER_TEMPLATES',
    'KUBERNETES_TEMPLATES',
    'BROWSER_TEMPLATES',
    'GIT_TEMPLATES',
    'DEVOPS_TEMPLATES',
    'API_TEMPLATES',
    'FFMPEG_TEMPLATES',
    'MEDIA_TEMPLATES',
    'DATA_TEMPLATES',
    'REMOTE_TEMPLATES',
    'IOT_TEMPLATES',
    'PACKAGE_MGMT_TEMPLATES',
    'RAG_TEMPLATES',
    'PRESENTATION_TEMPLATES',
]
