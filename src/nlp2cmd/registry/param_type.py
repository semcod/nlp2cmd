"""ParamType - extracted from __init__.py."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, TypeVar, Generic

class ParamType(Enum):
    """Parameter types for action validation."""
    
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    ANY = "any"
    FILE_PATH = "file_path"
    GLOB_PATTERN = "glob_pattern"
    REGEX_PATTERN = "regex_pattern"
    SQL_IDENTIFIER = "sql_identifier"
    K8S_RESOURCE = "k8s_resource"

