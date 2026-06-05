"""SQLValidator - extracted from __init__.py."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
import re
from nlp2cmd.validators.base_validator import BaseValidator
from nlp2cmd.validators.syntax_validator import SyntaxValidator
from nlp2cmd.validators.validation_result import ValidationResult

class SQLValidator(BaseValidator):
    """SQL-specific validator."""

    DANGEROUS_PATTERNS = [
        ("DROP DATABASE", "DROP DATABASE is extremely dangerous"),
        ("TRUNCATE TABLE", "TRUNCATE removes all data permanently"),
        ("; DROP", "Possible SQL injection pattern detected"),
        ("--", "SQL comment detected - review for injection"),
    ]

    def __init__(self, strict: bool = False):
        self.strict = strict

    def validate(self, content: str) -> ValidationResult:
        """Validate SQL statement."""
        errors = []
        warnings = []
        suggestions = []

        content_upper = content.upper()

        # Check for dangerous patterns
        injection_detected = False
        for pattern, message in self.DANGEROUS_PATTERNS:
            if pattern in content_upper:
                if self.strict or pattern in ["; DROP", "DROP DATABASE"]:
                    errors.append(message)
                    injection_detected = True
                else:
                    warnings.append(message)

        # If injection detected and not strict, still mark as invalid
        if injection_detected and not self.strict:
            # Still mark as invalid for security, but allow warnings
            pass

        # Check DELETE without WHERE
        if "DELETE FROM" in content_upper and "WHERE" not in content_upper:
            warnings.append("DELETE without WHERE clause will affect all rows")
            suggestions.append("Add WHERE clause to limit affected rows")

        # Check UPDATE without WHERE
        if "UPDATE" in content_upper and "SET" in content_upper:
            if "WHERE" not in content_upper:
                warnings.append("UPDATE without WHERE clause will affect all rows")
                suggestions.append("Add WHERE clause to limit affected rows")

        # Check DROP TABLE warning
        if "DROP TABLE" in content_upper:
            warnings.append("DROP TABLE operation detected - ensure you have a backup")

        # Check reserved keywords in identifiers (basic check)
        reserved_keywords = ['SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER', 'ORDER', 'GROUP', 'HAVING']
        # Simple check for keywords used as column/table names without backticks
        words = re.findall(r'\b\w+\b', content)
        for word in words:
            if word.upper() in reserved_keywords and word.upper() not in ['SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER']:
                # Check if it's likely used as an identifier (not a keyword)
                context = content_upper
                if f' {word.upper()} ' in context or f'{word.upper()} ' in context or f' {word.upper()}' in context:
                    if not any(f'{word.upper()}(' in context for word in ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX']):
                        warnings.append(f"Reserved keyword '{word}' used as identifier - consider using backticks")
                        break

        # Check aggregate without GROUP BY
        aggregate_functions = ['COUNT(', 'SUM(', 'AVG(', 'MIN(', 'MAX(']
        has_aggregate = any(func in content_upper for func in aggregate_functions)
        has_group_by = 'GROUP BY' in content_upper
        
        if has_aggregate and not has_group_by and 'WHERE' in content_upper:
            warnings.append("Aggregate function without GROUP BY may return unexpected results")
        elif has_aggregate and not has_group_by:
            warnings.append("Consider using GROUP BY with aggregate functions")

        # Check LIMIT clause
        if 'LIMIT' in content_upper:
            limit_match = re.search(r'LIMIT\s+(-?\d+)', content_upper)
            if limit_match and int(limit_match.group(1)) < 0:
                errors.append("LIMIT value cannot be negative")

        # Check JOIN syntax
        join_types = ['JOIN', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN', 'CROSS JOIN']
        for join_type in join_types:
            if join_type in content_upper:
                # Basic check for JOIN condition
                if ' ON ' not in content_upper and ' USING ' not in content_upper:
                    errors.append(f"JOIN without condition - missing ON or USING clause")
                break

        # Basic syntax check
        syntax_result = SyntaxValidator().validate(content)
        errors.extend(syntax_result.errors)
        warnings.extend(syntax_result.warnings)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
        )

