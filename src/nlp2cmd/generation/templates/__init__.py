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

__all__ = [
    'SQL_TEMPLATES',
    'SHELL_TEMPLATES', 
    'DOCKER_TEMPLATES',
    'KUBERNETES_TEMPLATES',
    'BROWSER_TEMPLATES',
    'GIT_TEMPLATES',
]
