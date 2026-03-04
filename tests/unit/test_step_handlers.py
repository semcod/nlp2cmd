"""Tests for step handlers package."""

import pytest
from unittest.mock import MagicMock, patch

from nlp2cmd.step_handlers import (
    StepHandler,
    HandlerContext,
    HandlerResult,
    HandlerRegistry,
    StepDispatcher,
    get_handler,
    register_handler,
)


class TestHandlerRegistry:
    """Test handler registry functionality."""
    
    def test_register_and_get_handler(self):
        """Test registering and retrieving handlers."""
        
        class TestHandler(StepHandler):
            action_name = "test_action"
            def execute(self, ctx):
                return HandlerResult(success=True)
        
        HandlerRegistry.register("test_action", TestHandler)
        
        retrieved = HandlerRegistry.get("test_action")
        assert retrieved is TestHandler
    
    def test_get_nonexistent_handler(self):
        """Test getting handler that doesn't exist."""
        result = HandlerRegistry.get("nonexistent")
        assert result is None
    
    def test_list_actions(self):
        """Test listing registered actions."""
        # Clear and register test handlers
        HandlerRegistry.clear()
        
        class Handler1(StepHandler):
            def execute(self, ctx): pass
        
        class Handler2(StepHandler):
            def execute(self, ctx): pass
        
        HandlerRegistry.register("action1", Handler1)
        HandlerRegistry.register("action2", Handler2)
        
        actions = HandlerRegistry.list_actions()
        assert "action1" in actions
        assert "action2" in actions


class TestStepDispatcher:
    """Test step dispatcher functionality."""
    
    def test_has_handler_true(self):
        """Test checking if handler exists."""
        HandlerRegistry.clear()
        
        class TestHandler(StepHandler):
            def execute(self, ctx): pass
        
        HandlerRegistry.register("existing_action", TestHandler)
        
        assert StepDispatcher.has_handler("existing_action") is True
    
    def test_has_handler_false(self):
        """Test checking if handler doesn't exist."""
        HandlerRegistry.clear()
        assert StepDispatcher.has_handler("missing_action") is False
    
    def test_dispatch_success(self):
        """Test successful dispatch."""
        HandlerRegistry.clear()
        
        class SuccessHandler(StepHandler):
            def execute(self, ctx):
                return HandlerResult(success=True, value="test_result")
        
        HandlerRegistry.register("success_action", SuccessHandler)
        
        mock_page = MagicMock()
        mock_context = MagicMock()
        mock_console = MagicMock()
        
        result = StepDispatcher.dispatch(
            action="success_action",
            page=mock_page,
            context=mock_context,
            params={},
            variables={},
            console=mock_console,
        )
        
        assert result == "test_result"
    
    def test_dispatch_failure(self):
        """Test dispatch with handler failure."""
        HandlerRegistry.clear()
        
        class FailureHandler(StepHandler):
            def execute(self, ctx):
                return HandlerResult(success=False, error="test_error")
        
        HandlerRegistry.register("failure_action", FailureHandler)
        
        mock_page = MagicMock()
        mock_context = MagicMock()
        mock_console = MagicMock()
        
        with pytest.raises(RuntimeError, match="test_error"):
            StepDispatcher.dispatch(
                action="failure_action",
                page=mock_page,
                context=mock_context,
                params={},
                variables={},
                console=mock_console,
            )
    
    def test_dispatch_unknown_action(self):
        """Test dispatch with unknown action."""
        HandlerRegistry.clear()
        
        mock_page = MagicMock()
        mock_context = MagicMock()
        mock_console = MagicMock()
        
        with pytest.raises(ValueError, match="Unknown action"):
            StepDispatcher.dispatch(
                action="unknown_action",
                page=mock_page,
                context=mock_context,
                params={},
                variables={},
                console=mock_console,
            )


class TestHandlerContext:
    """Test HandlerContext dataclass."""
    
    def test_context_creation(self):
        """Test creating handler context."""
        mock_page = MagicMock()
        mock_context = MagicMock()
        mock_console = MagicMock()
        
        ctx = HandlerContext(
            page=mock_page,
            context=mock_context,
            params={"url": "https://example.com"},
            variables={"key": "value"},
            console=mock_console,
        )
        
        assert ctx.page is mock_page
        assert ctx.context is mock_context
        assert ctx.params == {"url": "https://example.com"}
        assert ctx.variables == {"key": "value"}


class TestHandlerResult:
    """Test HandlerResult dataclass."""
    
    def test_result_defaults(self):
        """Test handler result defaults."""
        result = HandlerResult()
        assert result.success is True
        assert result.value is None
        assert result.error is None
        assert result.retry_allowed is True
    
    def test_result_custom(self):
        """Test handler result with custom values."""
        result = HandlerResult(
            success=False,
            value="test",
            error="error_msg",
            retry_allowed=False,
        )
        assert result.success is False
        assert result.value == "test"
        assert result.error == "error_msg"
        assert result.retry_allowed is False


class TestBaseHandler:
    """Test base StepHandler functionality."""
    
    def test_abstract_execute(self):
        """Test that execute is abstract."""
        with pytest.raises(TypeError):
            StepHandler()
    
    def test_resolve_variables(self):
        """Test variable resolution."""
        
        class TestHandler(StepHandler):
            action_name = "test"
            def execute(self, ctx):
                pass
        
        handler = TestHandler()
        variables = {"existing": "value"}
        
        # Test resolving existing variable
        result = handler._resolve_variables("$existing", variables)
        assert result == "value"
        
        # Test non-variable value
        result = handler._resolve_variables("plain_text", variables)
        assert result == "plain_text"
        
        # Test missing variable
        result = handler._resolve_variables("$missing", variables)
        assert result == "$missing"


class TestRegisteredHandlers:
    """Test that all expected handlers are registered."""
    
    def test_navigate_handler_registered(self):
        """Test navigate handler is registered."""
        from nlp2cmd.step_handlers.navigate import NavigateHandler
        handler = get_handler("navigate")
        assert handler is NavigateHandler
    
    def test_click_handler_registered(self):
        """Test click handler is registered."""
        from nlp2cmd.step_handlers.interaction import ClickHandler
        handler = get_handler("click")
        assert handler is ClickHandler
    
    def test_drawing_handlers_registered(self):
        """Test drawing handlers are registered."""
        from nlp2cmd.step_handlers.drawing import (
            WaitForCanvasHandler,
            SetColorHandler,
            DrawCircleHandler,
        )
        assert get_handler("wait_for_canvas") is WaitForCanvasHandler
        assert get_handler("set_color") is SetColorHandler
        assert get_handler("draw_circle") is DrawCircleHandler
    
    def test_extraction_handlers_registered(self):
        """Test extraction handlers are registered."""
        from nlp2cmd.step_handlers.extraction import (
            ExtractKeyHandler,
            SaveEnvHandler,
            PromptSecretHandler,
        )
        assert get_handler("extract_key") is ExtractKeyHandler
        assert get_handler("save_env") is SaveEnvHandler
        assert get_handler("prompt_secret") is PromptSecretHandler
    
    def test_session_handlers_registered(self):
        """Test session handlers are registered."""
        from nlp2cmd.step_handlers.session import (
            CheckSessionHandler,
            SubmitAndExtractKeyHandler,
            DiscoverServiceSectionHandler,
        )
        assert get_handler("check_session") is CheckSessionHandler
        assert get_handler("submit_and_extract_key") is SubmitAndExtractKeyHandler
        assert get_handler("discover_service_section") is DiscoverServiceSectionHandler
    
    def test_interaction_handlers_registered(self):
        """Test interaction handlers are registered."""
        from nlp2cmd.step_handlers.interaction import (
            ClickHandler,
            DismissOverlayHandler,
            TypeTextHandler,
            FillFormHandler,
            NewTabHandler,
            WaitHandler,
        )
        assert get_handler("click") is ClickHandler
        assert get_handler("dismiss_overlay") is DismissOverlayHandler
        assert get_handler("type_text") is TypeTextHandler
        assert get_handler("fill_form") is FillFormHandler
        assert get_handler("new_tab") is NewTabHandler
        assert get_handler("wait") is WaitHandler
