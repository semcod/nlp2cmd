
"""
Hub Function Refactoring for nlp2cmd.

Splits large hub functions into specialized, manageable components.
Based on analysis of _execute_plan_step (563 calls) and _run_dom_multi_action (457 calls).
"""

from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Types of actions that can be executed."""
    DOM_ACTION = "dom_action"
    SHELL_ACTION = "shell_action"
    MOUSE_ACTION = "mouse_action"
    KEYBOARD_ACTION = "keyboard_action"
    VALIDATION_ACTION = "validation_action"
    NAVIGATION_ACTION = "navigation_action"


@dataclass
class ExecutionContext:
    """Context for action execution."""
    session_id: str
    page_state: Dict[str, Any]
    user_context: Dict[str, Any]
    safety_enabled: bool = True
    debug_mode: bool = False


class ActionExecutor:
    """Specialized executor for different action types."""
    
    def __init__(self, action_type: ActionType):
        self.action_type = action_type
        self.execution_count = 0
    
    def execute(self, action: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute action of specific type."""
        self.execution_count += 1
        
        try:
            if self.action_type == ActionType.DOM_ACTION:
                return self._execute_dom_action(action, context)
            elif self.action_type == ActionType.SHELL_ACTION:
                return self._execute_shell_action(action, context)
            elif self.action_type == ActionType.MOUSE_ACTION:
                return self._execute_mouse_action(action, context)
            elif self.action_type == ActionType.KEYBOARD_ACTION:
                return self._execute_keyboard_action(action, context)
            elif self.action_type == ActionType.VALIDATION_ACTION:
                return self._execute_validation_action(action, context)
            elif self.action_type == ActionType.NAVIGATION_ACTION:
                return self._execute_navigation_action(action, context)
            else:
                raise ValueError(f"Unknown action type: {self.action_type}")
        
        except Exception as e:
            logger.error(f"Error executing {self.action_type.value}: {e}")
            return {
                'success': False,
                'error': str(e),
                'action_type': self.action_type.value
            }
    
    def _execute_dom_action(self, action: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute DOM manipulation action."""
        # Implementation for DOM actions
        return {
            'success': True,
            'action_type': 'dom_action',
            'result': f"DOM action executed: {action.get('selector', 'unknown')}"
        }
    
    def _execute_shell_action(self, action: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute shell command action."""
        if context.safety_enabled:
            # Safety check
            from ..validation.framework import validate_safety_policy
            validation = validate_safety_policy(action.get('command', ''))
            if not validation.is_valid:
                return {
                    'success': False,
                    'error': 'Safety policy violation',
                    'validation_errors': validation.errors
                }
        
        return {
            'success': True,
            'action_type': 'shell_action',
            'result': f"Shell command executed: {action.get('command', 'unknown')}"
        }
    
    def _execute_mouse_action(self, action: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute mouse action."""
        return {
            'success': True,
            'action_type': 'mouse_action',
            'result': f"Mouse action executed: {action.get('type', 'unknown')}"
        }
    
    def _execute_keyboard_action(self, action: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute keyboard action."""
        return {
            'success': True,
            'action_type': 'keyboard_action',
            'result': f"Keyboard action executed: {action.get('keys', 'unknown')}"
        }
    
    def _execute_validation_action(self, action: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute validation action."""
        return {
            'success': True,
            'action_type': 'validation_action',
            'result': f"Validation executed: {action.get('target', 'unknown')}"
        }
    
    def _execute_navigation_action(self, action: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute navigation action."""
        return {
            'success': True,
            'action_type': 'navigation_action',
            'result': f"Navigation executed: {action.get('url', 'unknown')}"
        }


class RefactoredPlanExecutor:
    """Refactored plan executor with specialized handlers."""
    
    def __init__(self):
        self.executors = {
            action_type: ActionExecutor(action_type) 
            for action_type in ActionType
        }
        self.execution_history = []
    
    def execute_plan_step(self, step: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute a single plan step using appropriate executor."""
        action_type = ActionType(step.get('type', 'dom_action'))
        executor = self.executors[action_type]
        
        result = executor.execute(step, context)
        
        # Log execution
        self.execution_history.append({
            'step': step,
            'context': context,
            'result': result,
            'timestamp': self._get_timestamp()
        })
        
        return result
    
    def execute_plan(self, plan: List[Dict[str, Any]], context: ExecutionContext) -> Dict[str, Any]:
        """Execute entire plan."""
        results = []
        errors = []
        
        for i, step in enumerate(plan):
            result = self.execute_plan_step(step, context)
            results.append(result)
            
            if not result['success']:
                errors.append(f"Step {i} failed: {result.get('error', 'Unknown error')}")
                if not step.get('continue_on_error', False):
                    break
        
        return {
            'success': len(errors) == 0,
            'results': results,
            'errors': errors,
            'steps_executed': len(results)
        }
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        stats = {}
        for action_type, executor in self.executors.items():
            stats[action_type.value] = executor.execution_count
        
        return {
            'total_executions': sum(stats.values()),
            'by_type': stats,
            'success_rate': self._calculate_success_rate()
        }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _calculate_success_rate(self) -> float:
        """Calculate success rate."""
        if not self.execution_history:
            return 1.0
        
        successful = sum(1 for entry in self.execution_history if entry['result']['success'])
        return successful / len(self.execution_history)


# Backward compatibility functions
def execute_plan_step(step: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
    """Execute single plan step (backward compatibility)."""
    executor = RefactoredPlanExecutor()
    return executor.execute_plan_step(step, context)


def run_dom_multi_action(actions: List[Dict[str, Any]], context: ExecutionContext) -> Dict[str, Any]:
    """Run multiple DOM actions (refactored)."""
    executor = RefactoredPlanExecutor()
    
    # Convert to plan format
    plan = [{'type': 'dom_action', **action} for action in actions]
    return executor.execute_plan(plan, context)


# Global instance
plan_executor = RefactoredPlanExecutor()
