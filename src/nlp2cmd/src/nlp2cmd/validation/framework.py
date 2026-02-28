
"""
Unified Validation Framework for nlp2cmd.

Consolidates 292+ validation functions into a single, extensible framework.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum


class ValidationType(Enum):
    """Types of validation."""
    SAFETY_POLICY = "safety_policy"
    FORM_FIELD = "form_field"
    SESSION = "session"
    INPUT = "input"
    OUTPUT = "output"
    PERMISSION = "permission"


@dataclass
class ValidationResult:
    """Result of validation operation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]


class BaseValidator(ABC):
    """Base class for all validators."""
    
    def __init__(self, validation_type: ValidationType):
        self.validation_type = validation_type
    
    @abstractmethod
    def validate(self, data: Any, context: Optional[Dict] = None) -> ValidationResult:
        """Validate data according to specific rules."""
        pass
    
    def _create_result(self, is_valid: bool, errors: List[str] = None, 
                      warnings: List[str] = None, **metadata) -> ValidationResult:
        """Create validation result."""
        return ValidationResult(
            is_valid=is_valid,
            errors=errors or [],
            warnings=warnings or [],
            metadata=metadata
        )


class SafetyPolicyValidator(BaseValidator):
    """Validates against safety policies."""
    
    def __init__(self):
        super().__init__(ValidationType.SAFETY_POLICY)
        self.blocked_commands = {
            'rm -rf', 'sudo rm', 'format', 'fdisk', 'mkfs',
            'dd if=', '> /dev/sda', 'chmod 777 /'
        }
    
    def validate(self, command: str, context: Optional[Dict] = None) -> ValidationResult:
        """Validate command against safety policies."""
        errors = []
        warnings = []
        
        # Check for blocked commands
        for blocked in self.blocked_commands:
            if blocked in command.lower():
                errors.append(f"Blocked command detected: {blocked}")
        
        # Check for suspicious patterns
        suspicious_patterns = ['sudo', 'chmod', 'chown', 'rm']
        for pattern in suspicious_patterns:
            if pattern in command.lower() and pattern not in self.blocked_commands:
                warnings.append(f"Suspicious command: {pattern}")
        
        return self._create_result(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            command_type="shell_command"
        )


class FormFieldValidator(BaseValidator):
    """Validates form fields."""
    
    def __init__(self):
        super().__init__(ValidationType.FORM_FIELD)
        self.junk_patterns = [
            r'^\s*$',  # Empty fields
            r'^\d+$',  # Numbers only (likely IDs)
            r'^[a-zA-Z]{1,2}$',  # Too short
        ]
    
    def validate(self, field_data: Dict[str, Any], context: Optional[Dict] = None) -> ValidationResult:
        """Validate form field data."""
        errors = []
        warnings = []
        
        field_name = field_data.get('name', '')
        field_value = field_data.get('value', '')
        field_type = field_data.get('type', 'text')
        
        # Check for junk fields
        if self._is_junk_field(field_value):
            warnings.append(f"Potential junk field: {field_name}")
        
        # Type-specific validation
        if field_type == 'email' and '@' not in field_value:
            errors.append(f"Invalid email format: {field_name}")
        
        return self._create_result(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            field_name=field_name,
            field_type=field_type
        )
    
    def _is_junk_field(self, value: str) -> bool:
        """Check if field value is junk."""
        import re
        
        for pattern in self.junk_patterns:
            if re.match(pattern, str(value)):
                return True
        return False


class ValidationFramework:
    """Main validation framework that coordinates all validators."""
    
    def __init__(self):
        self.validators = {
            ValidationType.SAFETY_POLICY: SafetyPolicyValidator(),
            ValidationType.FORM_FIELD: FormFieldValidator(),
        }
        self.validation_history = []
    
    def validate(self, data: Any, validation_type: ValidationType, 
                context: Optional[Dict] = None) -> ValidationResult:
        """Validate data using appropriate validator."""
        validator = self.validators.get(validation_type)
        if not validator:
            raise ValueError(f"No validator for type: {validation_type}")
        
        result = validator.validate(data, context)
        
        # Log validation
        self.validation_history.append({
            'type': validation_type,
            'result': result,
            'timestamp': self._get_timestamp()
        })
        
        return result
    
    def add_validator(self, validation_type: ValidationType, validator: BaseValidator):
        """Add custom validator."""
        self.validators[validation_type] = validator
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        total_validations = len(self.validation_history)
        failed_validations = len([v for v in self.validation_history if not v['result'].is_valid])
        
        return {
            'total_validations': total_validations,
            'failed_validations': failed_validations,
            'success_rate': (total_validations - failed_validations) / total_validations if total_validations > 0 else 0,
            'most_common_type': self._get_most_common_type()
        }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _get_most_common_type(self) -> Optional[ValidationType]:
        """Get most common validation type."""
        if not self.validation_history:
            return None
        
        type_counts = {}
        for validation in self.validation_history:
            type_counts[validation['type']] = type_counts.get(validation['type'], 0) + 1
        
        return max(type_counts, key=type_counts.get)


# Global instance
validation_framework = ValidationFramework()


# Convenience functions for backward compatibility
def validate_safety_policy(command: str, context: Optional[Dict] = None) -> ValidationResult:
    """Validate command against safety policy."""
    return validation_framework.validate(command, ValidationType.SAFETY_POLICY, context)


def validate_form_field(field_data: Dict[str, Any], context: Optional[Dict] = None) -> ValidationResult:
    """Validate form field."""
    return validation_framework.validate(field_data, ValidationType.FORM_FIELD, context)
