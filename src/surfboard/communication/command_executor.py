"""
Command executor for LLM browser automation commands.

This module executes LLM commands using the browser automation system,
translating high-level commands into low-level browser actions.
"""

import asyncio
import base64
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..actions.core_actions import (
    ActionError,
    CoreActions,
    ElementNotFoundError,
    ElementSelector,
    TimeoutError,
)
from ..automation.browser_manager import BrowserInstance, BrowserManager
from ..protocols.llm_protocol import (
    BaseCommand,
    BaseResponse,
    BrowserInfo,
    CommandType,
    ElementInfo,
)
from ..protocols.llm_protocol import ElementSelector as LLMElementSelector
from ..protocols.llm_protocol import (
    FindElementResponse,
    ListBrowsersResponse,
    PageInfo,
    PageSummaryResponse,
    ScreenshotResponse,
    ScriptResponse,
    StatusType,
    TextResponse,
    create_error_response,
)
from .page_analyzer import PageAnalyzer

logger = logging.getLogger(__name__)


class CommandExecutor:
    """Executes LLM commands using browser automation system."""

    def __init__(self, browser_manager: BrowserManager):
        """Initialize command executor.

        Args:
            browser_manager: Browser manager instance
        """
        self.browser_manager = browser_manager
        self.page_analyzer = PageAnalyzer()
        self.default_browser_id = "default"

    async def execute_command(
        self, command: BaseCommand, session_id: str
    ) -> BaseResponse:
        """Execute LLM command and return response.

        Args:
            command: Command to execute
            session_id: Client session ID

        Returns:
            Command execution response
        """
        start_time = time.time()

        try:
            # Route command to appropriate handler
            handler_map = {
                CommandType.NAVIGATE: self._handle_navigate,
                CommandType.RELOAD: self._handle_reload,
                CommandType.GO_BACK: self._handle_go_back,
                CommandType.GO_FORWARD: self._handle_go_forward,
                CommandType.FIND_ELEMENT: self._handle_find_element,
                CommandType.FIND_ELEMENTS: self._handle_find_elements,
                CommandType.CLICK: self._handle_click,
                CommandType.TYPE_TEXT: self._handle_type_text,
                CommandType.CLEAR_TEXT: self._handle_clear_text,
                CommandType.GET_TEXT: self._handle_get_text,
                CommandType.GET_ATTRIBUTE: self._handle_get_attribute,
                CommandType.GET_PAGE_TITLE: self._handle_get_page_title,
                CommandType.GET_PAGE_URL: self._handle_get_page_url,
                CommandType.GET_PAGE_SOURCE: self._handle_get_page_source,
                CommandType.TAKE_SCREENSHOT: self._handle_take_screenshot,
                CommandType.GET_ELEMENT_SCREENSHOT: self._handle_get_element_screenshot,
                CommandType.EXECUTE_SCRIPT: self._handle_execute_script,
                CommandType.GET_PAGE_SUMMARY: self._handle_get_page_summary,
                CommandType.ANALYZE_ELEMENTS: self._handle_analyze_elements,
                CommandType.GET_FORM_DATA: self._handle_get_form_data,
                CommandType.WAIT_FOR_ELEMENT: self._handle_wait_for_element,
                CommandType.WAIT_FOR_PAGE_LOAD: self._handle_wait_for_page_load,
                CommandType.SLEEP: self._handle_sleep,
                CommandType.CREATE_BROWSER: self._handle_create_browser,
                CommandType.CLOSE_BROWSER: self._handle_close_browser,
                CommandType.SWITCH_BROWSER: self._handle_switch_browser,
                CommandType.LIST_BROWSERS: self._handle_list_browsers,
            }

            handler = handler_map.get(command.command_type)
            if not handler:
                raise ValueError(f"Unknown command type: {command.command_type}")

            # Execute command with timeout
            response = await asyncio.wait_for(
                handler(command, session_id), timeout=command.timeout
            )

            return response

        except asyncio.TimeoutError:
            return create_error_response(
                command.command_id,
                f"Command timed out after {command.timeout}s",
                StatusType.TIMEOUT,
                time.time() - start_time,
            )
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            return create_error_response(
                command.command_id, str(e), StatusType.ERROR, time.time() - start_time
            )

    async def _get_browser_instance(
        self, browser_id: Optional[str], session_id: str
    ) -> BrowserInstance:
        """Get browser instance, creating default if needed."""
        if not browser_id:
            browser_id = f"{session_id}_{self.default_browser_id}"

        instance = await self.browser_manager.get_instance(browser_id)

        if not instance:
            # Create default browser instance
            logger.info(f"Creating default browser instance: {browser_id}")
            instance = await self.browser_manager.create_instance(
                instance_id=browser_id, headless=True, auto_connect_cdp=True
            )

        return instance

    def _convert_selector(self, llm_selector: LLMElementSelector) -> ElementSelector:
        """Convert LLM selector to internal selector."""
        kwargs = {
            "timeout": llm_selector.timeout,
        }

        if llm_selector.type.value == "css":
            kwargs["css"] = llm_selector.value
        elif llm_selector.type.value == "xpath":
            kwargs["xpath"] = llm_selector.value
        elif llm_selector.type.value == "text":
            kwargs["text"] = llm_selector.value
        elif llm_selector.type.value == "placeholder":
            kwargs["placeholder"] = llm_selector.value
        elif llm_selector.type.value == "role":
            kwargs["role"] = llm_selector.value
        elif llm_selector.type.value == "aria_label":
            kwargs["aria_label"] = llm_selector.value
        elif llm_selector.type.value == "tag_name":
            kwargs["css"] = llm_selector.value  # Convert tag to CSS

        return ElementSelector(**kwargs)

    # Navigation command handlers

    async def _handle_navigate(
        self, command: BaseCommand, session_id: str
    ) -> BaseResponse:
        """Handle navigate command."""
        instance = await self._get_browser_instance(command.browser_id, session_id)
        session = await instance.get_cdp_session()
        actions = CoreActions(session)

        await actions.navigate(command.url, wait_until=command.wait_until.value)

        return BaseResponse(
            command_id=command.command_id,
            status=StatusType.SUCCESS,
            execution_time=0.0,
            message=f"Navigated to {command.url}",
        )

    async def _handle_reload(
        self, command: BaseCommand, session_id: str
    ) -> BaseResponse:
        """Handle reload command."""
        instance = await self._get_browser_instance(command.browser_id, session_id)
        session = await instance.get_cdp_session()

        await session.page.reload()

        return BaseResponse(
            command_id=command.command_id,
            status=StatusType.SUCCESS,
            execution_time=0.0,
            message="Page reloaded",
        )

    async def _handle_go_back(
        self, command: BaseCommand, session_id: str
    ) -> BaseResponse:
        """Handle go back command."""
        instance = await self._get_browser_instance(command.browser_id, session_id)
        session = await instance.get_cdp_session()
        actions = CoreActions(session)

        await actions.execute_javascript("window.history.back()")

        return BaseResponse(
            command_id=command.command_id,
            status=StatusType.SUCCESS,
            execution_time=0.0,
            message="Navigated back",
        )

    async def _handle_go_forward(
        self, command: BaseCommand, session_id: str
    ) -> BaseResponse:
        """Handle go forward command."""
        instance = await self._get_browser_instance(command.browser_id, session_id)
        session = await instance.get_cdp_session()
        actions = CoreActions(session)

        await actions.execute_javascript("window.history.forward()")

        return BaseResponse(
            command_id=command.command_id,
            status=StatusType.SUCCESS,
            execution_time=0.0,
            message="Navigated forward",
        )

    # Element interaction handlers

    async def _handle_find_element(
        self, command: BaseCommand, session_id: str
    ) -> FindElementResponse:
        """Handle find element command."""
        instance = await self._get_browser_instance(command.browser_id, session_id)
        session = await instance.get_cdp_session()
        actions = CoreActions(session)

        selector = self._convert_selector(command.selector)

        if command.multiple:
            node_ids = await actions.find_elements(
                selector, visible_only=command.selector.visible_only
            )
        else:
            node_id = await actions.find_element(
                selector, visible_only=command.selector.visible_only
            )
            node_ids = [node_id] if node_id else []

        elements = []
        for node_id in node_ids:
            if node_id:
                element_info = await self._get_element_info(actions, node_id)
                elements.append(element_info)

        return FindElementResponse(
            command_id=command.command_id,
            status=StatusType.SUCCESS if elements else StatusType.NOT_FOUND,
            execution_time=0.0,
            element_found=bool(elements),
            elements=elements,
            total_count=len(elements),
            message=f"Found {len(elements)} element(s)"
            if elements
            else "No elements found",
        )

    async def _handle_find_elements(
        self, command: BaseCommand, session_id: str
    ) -> FindElementResponse:
        """Handle find elements command (alias for find_element with multiple=True)."""
        command.multiple = True
        return await self._handle_find_element(command, session_id)

    async def _handle_click(
        self, command: BaseCommand, session_id: str
    ) -> BaseResponse:
        """Handle click command."""
        instance = await self._get_browser_instance(command.browser_id, session_id)
        session = await instance.get_cdp_session()
        actions = CoreActions(session)

        selector = self._convert_selector(command.selector)

        success = await actions.click_element(
            selector, button=command.button, scroll_into_view=command.scroll_into_view
        )

        return BaseResponse(
            command_id=command.command_id,
            status=StatusType.SUCCESS if success else StatusType.ERROR,
            execution_time=0.0,
            message="Element clicked successfully" if success else "Click failed",
        )

    async def _handle_type_text(
        self, command: BaseCommand, session_id: str
    ) -> BaseResponse:
        """Handle type text command."""
        instance = await self._get_browser_instance(command.browser_id, session_id)
        session = await instance.get_cdp_session()
        actions = CoreActions(session)

        selector = self._convert_selector(command.selector)

        success = await actions.type_text(
            selector, command.text, clear_first=command.clear_first, delay=command.delay
        )

        return BaseResponse(
            command_id=command.command_id,
            status=StatusType.SUCCESS if success else StatusType.ERROR,
            execution_time=0.0,
            message=f"Typed text: {command.text[:50]}..."
            if len(command.text) > 50
            else f"Typed text: {command.text}",
        )

    async def _handle_clear_text(
        self, command: BaseCommand, session_id: str
    ) -> BaseResponse:
        """Handle clear text command."""
        instance = await self._get_browser_instance(command.browser_id, session_id)
        session = await instance.get_cdp_session()
        actions = CoreActions(session)

        selector = self._convert_selector(command.selector)

        # Click element and select all, then delete
        await actions.click_element(selector)
        session = await instance.get_cdp_session()
        await session.input.dispatch_key_event(
            "keyDown", key="a", modifiers=2
        )  # Ctrl+A
        await session.input.dispatch_key_event("keyUp", key="a", modifiers=2)
        await session.input.dispatch_key_event("keyDown", key="Delete")
        await session.input.dispatch_key_event("keyUp", key="Delete")

        return BaseResponse(
            command_id=command.command_id,
            status=StatusType.SUCCESS,
            execution_time=0.0,
            message="Text cleared",
        )

    # Information retrieval handlers

    async def _handle_get_text(
        self, command: BaseCommand, session_id: str
    ) -> TextResponse:
        """Handle get text command."""
        instance = await self._get_browser_instance(command.browser_id, session_id)
        session = await instance.get_cdp_session()
        actions = CoreActions(session)

        selector = self._convert_selector(command.selector)
        text = await actions.get_text(selector)

        return TextResponse(
            command_id=command.command_id,
            status=StatusType.SUCCESS if text is not None else StatusType.NOT_FOUND,
            execution_time=0.0,
            text=text,
            length=len(text) if text else 0,
            message="Text retrieved" if text else "No text found",
        )

    async def _handle_get_attribute(
        self, command: BaseCommand, session_id: str
    ) -> TextResponse:
        """Handle get attribute command."""
        instance = await self._get_browser_instance(command.browser_id, session_id)
        session = await instance.get_cdp_session()
        actions = CoreActions(session)

        selector = self._convert_selector(command.selector)
        value = await actions.get_attribute(selector, command.attribute_name)

        return TextResponse(
            command_id=command.command_id,
            status=StatusType.SUCCESS if value is not None else StatusType.NOT_FOUND,
            execution_time=0.0,
            text=value,
            length=len(value) if value else 0,
            message=f"Attribute '{command.attribute_name}' retrieved"
            if value
            else f"Attribute '{command.attribute_name}' not found",
        )

    async def _handle_get_page_title(
        self, command: BaseCommand, session_id: str
    ) -> TextResponse:
        """Handle get page title command."""
        instance = await self._get_browser_instance(command.browser_id, session_id)
        session = await instance.get_cdp_session()
        actions = CoreActions(session)

        title = await actions.execute_javascript("return document.title")

        return TextResponse(
            command_id=command.command_id,
            status=StatusType.SUCCESS,
            execution_time=0.0,
            text=title or "",
            length=len(title) if title else 0,
            message="Page title retrieved",
        )

    async def _handle_get_page_url(
        self, command: BaseCommand, session_id: str
    ) -> TextResponse:
        """Handle get page URL command."""
        instance = await self._get_browser_instance(command.browser_id, session_id)
        session = await instance.get_cdp_session()
        actions = CoreActions(session)

        url = await actions.execute_javascript("return window.location.href")

        return TextResponse(
            command_id=command.command_id,
            status=StatusType.SUCCESS,
            execution_time=0.0,
            text=url or "",
            length=len(url) if url else 0,
            message="Page URL retrieved",
        )

    async def _handle_get_page_source(
        self, command: BaseCommand, session_id: str
    ) -> TextResponse:
        """Handle get page source command."""
        instance = await self._get_browser_instance(command.browser_id, session_id)
        session = await instance.get_cdp_session()
        actions = CoreActions(session)

        source = await actions.execute_javascript(
            "return document.documentElement.outerHTML"
        )

        return TextResponse(
            command_id=command.command_id,
            status=StatusType.SUCCESS,
            execution_time=0.0,
            text=source or "",
            length=len(source) if source else 0,
            message="Page source retrieved",
        )

    # Screenshot handlers

    async def _handle_take_screenshot(
        self, command: BaseCommand, session_id: str
    ) -> ScreenshotResponse:
        """Handle take screenshot command."""
        instance = await self._get_browser_instance(command.browser_id, session_id)
        session = await instance.get_cdp_session()
        actions = CoreActions(session)

        selector = None
        if command.selector:
            selector = self._convert_selector(command.selector)

        screenshot_data = await actions.take_screenshot(
            selector=selector,
            format=command.format,
            quality=command.quality,
            full_page=command.full_page,
        )

        # Encode as base64
        image_base64 = base64.b64encode(screenshot_data).decode("utf-8")

        return ScreenshotResponse(
            command_id=command.command_id,
            status=StatusType.SUCCESS,
            execution_time=0.0,
            image_data=image_base64,
            image_format=command.format,
            dimensions={"width": 0, "height": 0},  # Could calculate if needed
            message="Screenshot captured",
        )

    async def _handle_get_element_screenshot(
        self, command: BaseCommand, session_id: str
    ) -> ScreenshotResponse:
        """Handle get element screenshot command."""
        command.selector = command.element_selector  # Alias
        return await self._handle_take_screenshot(command, session_id)

    # Script execution

    async def _handle_execute_script(
        self, command: BaseCommand, session_id: str
    ) -> ScriptResponse:
        """Handle execute script command."""
        instance = await self._get_browser_instance(command.browser_id, session_id)
        session = await instance.get_cdp_session()
        actions = CoreActions(session)

        result = await actions.execute_javascript(
            command.script, await_promise=command.await_promise
        )

        return ScriptResponse(
            command_id=command.command_id,
            status=StatusType.SUCCESS,
            execution_time=0.0,
            result=result,
            console_logs=[],  # Could capture console logs if needed
            message="Script executed successfully",
        )

    # Page analysis

    async def _handle_get_page_summary(
        self, command: BaseCommand, session_id: str
    ) -> PageSummaryResponse:
        """Handle get page summary command."""
        instance = await self._get_browser_instance(command.browser_id, session_id)
        session = await instance.get_cdp_session()

        page_info = await self.page_analyzer.analyze_page(
            session,
            include_text=command.include_text,
            include_links=command.include_links,
            include_images=command.include_images,
            include_forms=command.include_forms,
            max_elements=command.max_elements,
        )

        return PageSummaryResponse(
            command_id=command.command_id,
            status=StatusType.SUCCESS,
            execution_time=0.0,
            page_info=page_info,
            elements_analyzed=command.max_elements,
            processing_time=0.0,
            message="Page summary generated",
        )

    async def _handle_analyze_elements(
        self, command: BaseCommand, session_id: str
    ) -> BaseResponse:
        """Handle analyze elements command."""
        # Placeholder for future element analysis
        return BaseResponse(
            command_id=command.command_id,
            status=StatusType.SUCCESS,
            execution_time=0.0,
            message="Element analysis not yet implemented",
        )

    async def _handle_get_form_data(
        self, command: BaseCommand, session_id: str
    ) -> BaseResponse:
        """Handle get form data command."""
        # Placeholder for form data extraction
        return BaseResponse(
            command_id=command.command_id,
            status=StatusType.SUCCESS,
            execution_time=0.0,
            message="Form data extraction not yet implemented",
        )

    # Waiting commands

    async def _handle_wait_for_element(
        self, command: BaseCommand, session_id: str
    ) -> FindElementResponse:
        """Handle wait for element command."""
        instance = await self._get_browser_instance(command.browser_id, session_id)
        session = await instance.get_cdp_session()
        actions = CoreActions(session)

        selector = self._convert_selector(command.selector)

        try:
            node_id = await actions.wait_for_element(selector, timeout=command.timeout)
            element_info = await self._get_element_info(actions, node_id)

            return FindElementResponse(
                command_id=command.command_id,
                status=StatusType.SUCCESS,
                execution_time=0.0,
                element_found=True,
                elements=[element_info],
                total_count=1,
                message="Element found",
            )
        except TimeoutError:
            return FindElementResponse(
                command_id=command.command_id,
                status=StatusType.TIMEOUT,
                execution_time=0.0,
                element_found=False,
                elements=[],
                total_count=0,
                message=f"Element not found within {command.timeout}s",
            )

    async def _handle_wait_for_page_load(
        self, command: BaseCommand, session_id: str
    ) -> BaseResponse:
        """Handle wait for page load command."""
        # Simple wait implementation
        await asyncio.sleep(command.wait_time or 2.0)

        return BaseResponse(
            command_id=command.command_id,
            status=StatusType.SUCCESS,
            execution_time=0.0,
            message="Page load wait completed",
        )

    async def _handle_sleep(
        self, command: BaseCommand, session_id: str
    ) -> BaseResponse:
        """Handle sleep command."""
        await asyncio.sleep(command.duration)

        return BaseResponse(
            command_id=command.command_id,
            status=StatusType.SUCCESS,
            execution_time=command.duration,
            message=f"Slept for {command.duration}s",
        )

    # Browser management

    async def _handle_create_browser(
        self, command: BaseCommand, session_id: str
    ) -> BaseResponse:
        """Handle create browser command."""
        config = command.config

        instance = await self.browser_manager.create_instance(
            instance_id=command.browser_id,
            headless=config.headless,
            window_size=(config.viewport.width, config.viewport.height)
            if config.viewport
            else None,
            user_agent=config.user_agent,
            profile=config.profile,
            additional_args=config.additional_args,
        )

        return BaseResponse(
            command_id=command.command_id,
            status=StatusType.SUCCESS,
            execution_time=0.0,
            message=f"Browser created: {instance.instance_id}",
        )

    async def _handle_close_browser(
        self, command: BaseCommand, session_id: str
    ) -> BaseResponse:
        """Handle close browser command."""
        browser_id = command.browser_id or f"{session_id}_{self.default_browser_id}"

        success = await self.browser_manager.close_instance(browser_id)

        return BaseResponse(
            command_id=command.command_id,
            status=StatusType.SUCCESS if success else StatusType.NOT_FOUND,
            execution_time=0.0,
            message=f"Browser closed: {browser_id}" if success else "Browser not found",
        )

    async def _handle_switch_browser(
        self, command: BaseCommand, session_id: str
    ) -> BaseResponse:
        """Handle switch browser command."""
        # This would set the default browser for subsequent commands
        return BaseResponse(
            command_id=command.command_id,
            status=StatusType.SUCCESS,
            execution_time=0.0,
            message=f"Switched to browser: {command.browser_id}",
        )

    async def _handle_list_browsers(
        self, command: BaseCommand, session_id: str
    ) -> ListBrowsersResponse:
        """Handle list browsers command."""
        instances = await self.browser_manager.list_instances()

        browsers = []
        for instance_info in instances:
            browser = BrowserInfo(
                browser_id=instance_info["id"],
                is_active=instance_info["running"],
                current_url=None,  # Could retrieve if needed
                title=None,  # Could retrieve if needed
                viewport=None,  # Could retrieve if needed
                created_at=instance_info["created_at"],
            )
            browsers.append(browser)

        return ListBrowsersResponse(
            command_id=command.command_id,
            status=StatusType.SUCCESS,
            execution_time=0.0,
            browsers=browsers,
            total_count=len(browsers),
            message=f"Found {len(browsers)} browser(s)",
        )

    # Helper methods

    async def _get_element_info(
        self, actions: CoreActions, node_id: int
    ) -> ElementInfo:
        """Get detailed element information."""
        try:
            # Get element details using JavaScript
            element_data = await actions.execute_javascript(
                f"""
                (function() {{
                    const elements = Array.from(document.querySelectorAll('*'));
                    const element = elements.find(el => el._nodeId === {node_id});

                    if (!element) return null;

                    const rect = element.getBoundingClientRect();
                    const style = window.getComputedStyle(element);

                    return {{
                        tagName: element.tagName.toLowerCase(),
                        text: element.textContent ? element.textContent.trim() : '',
                        attributes: Object.fromEntries(
                            Array.from(element.attributes).map(attr => [attr.name, attr.value])
                        ),
                        isVisible: style.display !== 'none' &&
                                  style.visibility !== 'hidden' &&
                                  style.opacity !== '0' &&
                                  rect.width > 0 && rect.height > 0,
                        boundingBox: {{
                            x: rect.x,
                            y: rect.y,
                            width: rect.width,
                            height: rect.height
                        }}
                    }};
                }})()
            """
            )

            if element_data:
                return ElementInfo(
                    tag_name=element_data.get("tagName", "unknown"),
                    text=element_data.get("text", ""),
                    attributes=element_data.get("attributes", {}),
                    is_visible=element_data.get("isVisible", False),
                    bounding_box=element_data.get("boundingBox", {}),
                )
        except:
            pass

        # Fallback to basic info
        return ElementInfo(
            tag_name="unknown",
            text="",
            attributes={},
            is_visible=False,
            bounding_box={},
        )
