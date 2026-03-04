"""Navigation DOM action handlers."""

from __future__ import annotations
from typing import TYPE_CHECKING

from .base import DomAction, ActionContext, ActionResult
from .registry import register_action

if TYPE_CHECKING:
    pass


@register_action("goto")
@register_action("navigate")
class NavigateAction(DomAction):
    """Navigate to a URL."""
    
    def execute(self, ctx: ActionContext) -> ActionResult:
        """Navigate to the specified URL."""
        action_url = ctx.action_spec.get("url", ctx.url)
        
        try:
            ctx.page.goto(str(action_url), wait_until="domcontentloaded")
            ctx.page.wait_for_timeout(500)
            
            # Try to dismiss common popups/cookie consents
            self._dismiss_popups(ctx.page, ctx.schema_loader)
            
            return ActionResult(success=True)
        except Exception as e:
            return ActionResult(success=False, error=f"Navigation failed: {e}")


@register_action("explore_for_content")
class ExploreForContentAction(DomAction):
    """Explore site to find content."""
    
    def execute(self, ctx: ActionContext) -> ActionResult:
        """Explore site to find content like articles or docs."""
        try:
            from nlp2cmd.web_schema.site_explorer import SiteExplorer
            
            content_type = ctx.action_spec.get("content_type", "article")
            ctx.console.print(f"🔍 Exploring site for {content_type}...", language="text")
            
            # Use smaller limits for docs to avoid timeouts
            max_pages = 2 if content_type == "docs" else 8
            max_depth = 1 if content_type == "docs" else 2
            
            explorer = SiteExplorer(
                max_depth=max_depth,
                max_pages=max_pages,
                headless=False,  # Will be set from context
                timeout_ms=5000,
                dynamic_wait_ms=1000
            )
            
            # Don't close browser - reuse current context
            explore_result = explorer.find_content(
                url=ctx.url,
                content_type=content_type,
                page=ctx.page,
                context=ctx.context,
                close_browser=False,
            )
            
            if explore_result.success and explore_result.form_url:
                content_url = explore_result.form_url
                ctx.console.print(f"✓ Found {content_type} at: {content_url}", language="text")
                
                # Navigate to the discovered content page
                if content_url != ctx.page.url:
                    ctx.page.goto(content_url, wait_until="domcontentloaded")
                    ctx.page.wait_for_timeout(1500)
                
                return ActionResult(success=True, data={"content_url": content_url})
            else:
                ctx.console.print(f"No {content_type} found during exploration", language="text")
                return ActionResult(success=True, data={"content_url": None})
                
        except Exception as e:
            ctx.console.print(f"Content exploration failed: {e}", language="text")
            return ActionResult(success=False, error=str(e))


@register_action("explore_for_form")
class ExploreForFormAction(DomAction):
    """Explore site to find forms."""
    
    def execute(self, ctx: ActionContext) -> ActionResult:
        """Explore site to find forms before filling."""
        try:
            from nlp2cmd.web_schema.site_explorer import SiteExplorer
            
            intent = ctx.action_spec.get("intent", "contact")
            ctx.console.print(f"🔍 Exploring site for {intent} form...", language="text")
            
            explorer = SiteExplorer(max_depth=2, max_pages=8, headless=False)
            
            # Don't close browser - reuse current context
            explore_result = explorer.find_form(
                url=ctx.url,
                intent=intent,
                page=ctx.page,
                context=ctx.context,
                close_browser=False,
            )
            
            if explore_result.success and explore_result.form_url:
                form_url = explore_result.form_url
                ctx.console.print(f"✓ Found form at: {form_url}", language="text")
                
                # Navigate to the discovered form page
                if form_url != ctx.page.url:
                    ctx.page.goto(form_url, wait_until="domcontentloaded")
                    ctx.page.wait_for_timeout(1500)
                
                return ActionResult(success=True, data={"form_url": form_url})
            else:
                ctx.console.print("No form found during exploration", language="text")
                return ActionResult(success=True, data={"form_url": None})
                
        except Exception as e:
            ctx.console.print(f"Site exploration failed: {e}", language="text")
            return ActionResult(success=False, error=str(e))
