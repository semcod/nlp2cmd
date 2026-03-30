"""Handler registry for plan step dispatching."""

from __future__ import annotations
from typing import Optional, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from .base import StepHandler


class HandlerRegistry:
    """Registry mapping action names to their handlers."""
    
    _handlers: dict[str, Type[StepHandler]] = {}
    
    @classmethod
    def register(cls, action_name: str, handler_class: Type[StepHandler]) -> None:
        """Register a handler class for an action name."""
        cls._handlers[action_name] = handler_class
    
    @classmethod
    def get(cls, action_name: str) -> Optional[Type[StepHandler]]:
        """Get the handler class for an action name."""
        return cls._handlers.get(action_name)
    
    @classmethod
    def list_actions(cls) -> list[str]:
        """List all registered action names."""
        return list(cls._handlers.keys())
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered handlers (mainly for testing)."""
        cls._handlers.clear()
        _register_default_handlers(cls)


def _register_default_handlers(registry_cls: type[HandlerRegistry]) -> None:
    """Re-register built-in step handlers after a registry reset."""
    from .navigate import NavigateHandler
    from .interaction import (
        ClickHandler,
        ClickRadioHandler,
        DismissOverlayHandler,
        TypeTextHandler,
        FillFormHandler,
        SubmitFormHandler,
        LoginHandler,
        NewTabHandler,
        WaitHandler,
        ScreenshotHandler,
    )
    from .drawing import (
        WaitForCanvasHandler,
        GetCanvasCenterHandler,
        SelectToolHandler,
        SetColorHandler,
        SetLineWidthHandler,
        DrawCircleHandler,
        DrawFilledCircleHandler,
        DrawFilledEllipseHandler,
        DrawFilledRectangleHandler,
    )
    from .extraction import (
        ExtractKeyHandler,
        CheckClipboardHandler,
        SaveEnvHandler,
        VerifyEnvHandler,
        PromptSecretHandler,
        EchoHandler,
        ExtractTextHandler,
    )
    from .session import (
        CheckSessionHandler,
        SubmitAndExtractKeyHandler,
        DiscoverServiceSectionHandler,
    )

    registry_cls._handlers.update({
        "navigate": NavigateHandler,
        "click": ClickHandler,
        "click_radio": ClickRadioHandler,
        "dismiss_overlay": DismissOverlayHandler,
        "type_text": TypeTextHandler,
        "fill_form": FillFormHandler,
        "submit_form": SubmitFormHandler,
        "login": LoginHandler,
        "new_tab": NewTabHandler,
        "wait": WaitHandler,
        "screenshot": ScreenshotHandler,
        "wait_for_canvas": WaitForCanvasHandler,
        "get_canvas_center": GetCanvasCenterHandler,
        "select_tool": SelectToolHandler,
        "set_color": SetColorHandler,
        "set_line_width": SetLineWidthHandler,
        "draw_circle": DrawCircleHandler,
        "draw_filled_circle": DrawFilledCircleHandler,
        "draw_filled_ellipse": DrawFilledEllipseHandler,
        "draw_filled_rectangle": DrawFilledRectangleHandler,
        "extract_key": ExtractKeyHandler,
        "check_clipboard": CheckClipboardHandler,
        "save_env": SaveEnvHandler,
        "verify_env": VerifyEnvHandler,
        "prompt_secret": PromptSecretHandler,
        "echo": EchoHandler,
        "extract_text": ExtractTextHandler,
        "check_session": CheckSessionHandler,
        "submit_and_extract_key": SubmitAndExtractKeyHandler,
        "discover_service_section": DiscoverServiceSectionHandler,
    })


def register_handler(action_name: str):
    """Decorator to register a handler class.
    
    Usage:
        @register_handler("navigate")
        class NavigateHandler(StepHandler):
            ...
    """
    def decorator(handler_class: Type[StepHandler]) -> Type[StepHandler]:
        HandlerRegistry.register(action_name, handler_class)
        handler_class.action_name = action_name
        return handler_class
    return decorator


def get_handler(action_name: str) -> Optional[Type[StepHandler]]:
    """Get the handler class for an action name."""
    return HandlerRegistry.get(action_name)
