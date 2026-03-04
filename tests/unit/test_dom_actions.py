"""Tests for dom_actions package."""

import pytest
from unittest.mock import MagicMock

from nlp2cmd.dom_actions import (
    DomAction,
    ActionContext,
    ActionResult,
    ActionRegistry,
    ActionDispatcher,
    get_action,
    register_action,
)


class TestActionRegistry:
    """Test action registry functionality."""
    
    def test_register_and_get_handler(self):
        """Test registering and retrieving handlers."""
        
        class TestAction(DomAction):
            action_name = "test_action"
            def execute(self, ctx):
                return ActionResult(success=True)
        
        ActionRegistry.register("test_action", TestAction)
        
        retrieved = ActionRegistry.get("test_action")
        assert retrieved is TestAction
    
    def test_get_nonexistent_handler(self):
        """Test getting handler that doesn't exist."""
        result = ActionRegistry.get("nonexistent")
        assert result is None
    
    def test_list_actions(self):
        """Test listing registered actions."""
        ActionRegistry.clear()
        
        class Action1(DomAction):
            def execute(self, ctx): pass
        
        class Action2(DomAction):
            def execute(self, ctx): pass
        
        ActionRegistry.register("action1", Action1)
        ActionRegistry.register("action2", Action2)
        
        actions = ActionRegistry.list_actions()
        assert "action1" in actions
        assert "action2" in actions


class TestActionDispatcher:
    """Test action dispatcher functionality."""
    
    def test_has_handler_true(self):
        """Test checking if handler exists."""
        ActionRegistry.clear()
        
        class TestAction(DomAction):
            def execute(self, ctx): pass
        
        ActionRegistry.register("existing_action", TestAction)
        
        assert ActionDispatcher.has_handler("existing_action") is True
    
    def test_has_handler_false(self):
        """Test checking if handler doesn't exist."""
        ActionRegistry.clear()
        assert ActionDispatcher.has_handler("missing_action") is False
    
    def test_dispatch_success(self):
        """Test successful dispatch."""
        ActionRegistry.clear()
        
        class SuccessAction(DomAction):
            def execute(self, ctx):
                return ActionResult(success=True, data={"result": "test"})
        
        ActionRegistry.register("success_action", SuccessAction)
        
        mock_page = MagicMock()
        mock_context = MagicMock()
        mock_console = MagicMock()
        mock_loader = MagicMock()
        
        result = ActionDispatcher.dispatch(
            action="success_action",
            action_spec={},
            page=mock_page,
            context=mock_context,
            url="https://example.com",
            console=mock_console,
            schema_loader=mock_loader,
            extracted_data=[],
        )
        
        assert result.success is True
        assert result.data == {"result": "test"}
    
    def test_dispatch_failure(self):
        """Test dispatch with handler failure."""
        ActionRegistry.clear()
        
        class FailureAction(DomAction):
            def execute(self, ctx):
                return ActionResult(success=False, error="test_error", should_continue=False)
        
        ActionRegistry.register("failure_action", FailureAction)
        
        mock_page = MagicMock()
        mock_context = MagicMock()
        mock_console = MagicMock()
        mock_loader = MagicMock()
        
        result = ActionDispatcher.dispatch(
            action="failure_action",
            action_spec={},
            page=mock_page,
            context=mock_context,
            url="https://example.com",
            console=mock_console,
            schema_loader=mock_loader,
            extracted_data=[],
        )
        
        assert result.success is False
        assert result.error == "test_error"
        assert result.should_continue is False
    
    def test_dispatch_unknown_action(self):
        """Test dispatch with unknown action."""
        ActionRegistry.clear()
        
        mock_page = MagicMock()
        mock_context = MagicMock()
        mock_console = MagicMock()
        mock_loader = MagicMock()
        
        result = ActionDispatcher.dispatch(
            action="unknown_action",
            action_spec={},
            page=mock_page,
            context=mock_context,
            url="https://example.com",
            console=mock_console,
            schema_loader=mock_loader,
            extracted_data=[],
        )
        
        assert result.success is False
        assert "Unsupported action" in result.error
        assert result.should_continue is False


class TestActionContext:
    """Test ActionContext dataclass."""
    
    def test_context_creation(self):
        """Test creating action context."""
        mock_page = MagicMock()
        mock_context = MagicMock()
        mock_console = MagicMock()
        mock_loader = MagicMock()
        extracted = []
        
        ctx = ActionContext(
            page=mock_page,
            context=mock_context,
            url="https://example.com",
            action_spec={"action": "test"},
            console=mock_console,
            schema_loader=mock_loader,
            extracted_data=extracted,
        )
        
        assert ctx.page is mock_page
        assert ctx.url == "https://example.com"
        assert ctx.action_spec == {"action": "test"}


class TestActionResult:
    """Test ActionResult dataclass."""
    
    def test_result_defaults(self):
        """Test action result defaults."""
        result = ActionResult()
        assert result.success is True
        assert result.error is None
        assert result.data is None
        assert result.should_continue is True
    
    def test_result_custom(self):
        """Test action result with custom values."""
        result = ActionResult(
            success=False,
            error="error_msg",
            data={"key": "value"},
            should_continue=False,
        )
        assert result.success is False
        assert result.error == "error_msg"
        assert result.data == {"key": "value"}
        assert result.should_continue is False


class TestBaseAction:
    """Test base DomAction functionality."""
    
    def test_abstract_execute(self):
        """Test that execute is abstract."""
        with pytest.raises(TypeError):
            DomAction()


class TestRegisteredActions:
    """Test that all expected actions are registered."""
    
    def test_navigate_actions_registered(self):
        """Test navigate actions are registered."""
        from nlp2cmd.dom_actions.navigation import NavigateAction
        assert get_action("goto") is NavigateAction
        assert get_action("navigate") is NavigateAction
    
    def test_explore_actions_registered(self):
        """Test explore actions are registered."""
        from nlp2cmd.dom_actions.navigation import ExploreForContentAction, ExploreForFormAction
        assert get_action("explore_for_content") is ExploreForContentAction
        assert get_action("explore_for_form") is ExploreForFormAction
    
    def test_form_action_registered(self):
        """Test form action is registered."""
        from nlp2cmd.dom_actions.forms import FillFormAction
        assert get_action("fill_form") is FillFormAction
    
    def test_company_actions_registered(self):
        """Test company extraction actions are registered."""
        from nlp2cmd.dom_actions.companies import ExtractCompaniesAction
        assert get_action("extract_companies") is ExtractCompaniesAction
        assert get_action("extract_company_websites_deep") is ExtractCompaniesAction
    
    def test_save_actions_registered(self):
        """Test save actions are registered."""
        from nlp2cmd.dom_actions.save import SaveToFileAction, SaveToCsvAction
        assert get_action("save_to_file") is SaveToFileAction
        assert get_action("save_to_csv") is SaveToCsvAction
