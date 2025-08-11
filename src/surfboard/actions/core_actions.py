"""
Core browser automation actions.

This module provides high-level actions for browser automation,
built on top of the CDP domains system.
"""

import asyncio
import base64
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from ..automation.browser_manager import BrowserInstance
from ..protocols.cdp_domains import CDPSession
from ..protocols.cdp import CDPError

logger = logging.getLogger(__name__)


class ActionError(Exception):
    """Exception raised when action execution fails."""
    pass


class ElementNotFoundError(ActionError):
    """Exception raised when element is not found."""
    pass


class TimeoutError(ActionError):
    """Exception raised when action times out."""
    pass


class ElementSelector:
    """Element selector with multiple fallback strategies."""
    
    def __init__(
        self,
        css: Optional[str] = None,
        xpath: Optional[str] = None,
        text: Optional[str] = None,
        placeholder: Optional[str] = None,
        role: Optional[str] = None,
        aria_label: Optional[str] = None
    ):
        """Initialize element selector.
        
        Args:
            css: CSS selector
            xpath: XPath selector (converted to CSS if possible)
            text: Text content selector
            placeholder: Placeholder attribute selector
            role: ARIA role selector
            aria_label: ARIA label selector
        """
        self.css = css
        self.xpath = xpath
        self.text = text
        self.placeholder = placeholder
        self.role = role
        self.aria_label = aria_label
        
    def to_css_selectors(self) -> List[str]:
        """Convert to list of CSS selectors to try.
        
        Returns:
            List of CSS selectors ordered by preference
        """
        selectors = []
        
        if self.css:
            selectors.append(self.css)
            
        if self.text:
            # CSS selector for text content (limited support)
            selectors.append(f"*:contains('{self.text}')")
            
        if self.placeholder:
            selectors.append(f"[placeholder='{self.placeholder}']")
            
        if self.role:
            selectors.append(f"[role='{self.role}']")
            
        if self.aria_label:
            selectors.append(f"[aria-label='{self.aria_label}']")
            
        return selectors
        
    def to_javascript_finder(self) -> str:
        """Convert to JavaScript element finder function.
        
        Returns:
            JavaScript code to find element
        """
        conditions = []
        
        if self.css:
            conditions.append(f"document.querySelector('{self.css}')")
            
        if self.text:
            conditions.append(f"""
                Array.from(document.querySelectorAll('*')).find(el => 
                    el.textContent && el.textContent.trim().includes('{self.text}')
                )
            """)
            
        if self.placeholder:
            conditions.append(f"document.querySelector('[placeholder=\"{self.placeholder}\"]')")
            
        if self.role:
            conditions.append(f"document.querySelector('[role=\"{self.role}\"]')")
            
        if self.aria_label:
            conditions.append(f"document.querySelector('[aria-label=\"{self.aria_label}\"]')")
            
        if not conditions:
            return "null"
            
        return f"({' || '.join(conditions)})"


class CoreActions:
    """Core browser automation actions."""
    
    def __init__(self, session: CDPSession):
        """Initialize core actions.
        
        Args:
            session: CDP session instance
        """
        self.session = session
        
    async def navigate(
        self,
        url: str,
        wait_until: str = "load",
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """Navigate to URL with configurable wait conditions.
        
        Args:
            url: URL to navigate to
            wait_until: Wait condition ('load', 'domcontentloaded', 'networkidle')
            timeout: Navigation timeout in seconds
            
        Returns:
            Navigation result
            
        Raises:
            TimeoutError: If navigation times out
            ActionError: If navigation fails
        """
        try:
            logger.info(f"Navigating to: {url}")
            
            result = await asyncio.wait_for(
                self.session.page.navigate(url, wait_until),
                timeout=timeout
            )
            
            logger.debug(f"Navigation completed: {result}")
            return result
            
        except asyncio.TimeoutError as e:
            raise TimeoutError(f"Navigation to {url} timed out after {timeout}s") from e
        except CDPError as e:
            raise ActionError(f"Navigation failed: {e}") from e
            
    async def find_element(
        self,
        selector: Union[str, ElementSelector],
        timeout: float = 10.0,
        visible_only: bool = True
    ) -> Optional[int]:
        """Find element using flexible selector strategies.
        
        Args:
            selector: Element selector (CSS string or ElementSelector)
            timeout: Search timeout in seconds
            visible_only: Only find visible elements
            
        Returns:
            Node ID if found, None otherwise
            
        Raises:
            ElementNotFoundError: If element not found within timeout
        """
        if isinstance(selector, str):
            selector = ElementSelector(css=selector)
            
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Get document root
                doc = await self.session.dom.get_document()
                root_node_id = doc.get("root", {}).get("nodeId")
                
                if not root_node_id:
                    await asyncio.sleep(0.1)
                    continue
                
                # Try CSS selectors first
                for css_selector in selector.to_css_selectors():
                    node_id = await self.session.dom.query_selector(root_node_id, css_selector)
                    if node_id:
                        # Check visibility if required
                        if visible_only and not await self._is_element_visible(node_id):
                            continue
                        return node_id
                        
                # Try JavaScript-based finding as fallback
                js_finder = selector.to_javascript_finder()
                if js_finder and js_finder != "null":
                    result = await self.session.runtime.evaluate(f"""
                        (function() {{
                            const element = {js_finder};
                            if (element) {{
                                // Create a unique identifier for the element
                                element._surfboardId = Math.random().toString(36);
                                return element._surfboardId;
                            }}
                            return null;
                        }})()
                    """)
                    
                    if result:
                        # Find element by our temporary ID
                        node_id = await self.session.dom.query_selector(
                            root_node_id, 
                            f"[_surfboardId='{result}']"
                        )
                        if node_id and (not visible_only or await self._is_element_visible(node_id)):
                            return node_id
                            
            except CDPError:
                # Ignore CDP errors during search
                pass
                
            await asyncio.sleep(0.1)
            
        return None
        
    async def find_elements(
        self,
        selector: Union[str, ElementSelector],
        timeout: float = 10.0,
        visible_only: bool = True
    ) -> List[int]:
        """Find multiple elements matching selector.
        
        Args:
            selector: Element selector
            timeout: Search timeout in seconds
            visible_only: Only find visible elements
            
        Returns:
            List of node IDs
        """
        if isinstance(selector, str):
            selector = ElementSelector(css=selector)
            
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                doc = await self.session.dom.get_document()
                root_node_id = doc.get("root", {}).get("nodeId")
                
                if not root_node_id:
                    await asyncio.sleep(0.1)
                    continue
                
                # Try CSS selectors
                for css_selector in selector.to_css_selectors():
                    node_ids = await self.session.dom.query_selector_all(root_node_id, css_selector)
                    if node_ids:
                        # Filter for visibility if required
                        if visible_only:
                            visible_nodes = []
                            for node_id in node_ids:
                                if await self._is_element_visible(node_id):
                                    visible_nodes.append(node_id)
                            return visible_nodes
                        return node_ids
                        
            except CDPError:
                pass
                
            await asyncio.sleep(0.1)
            
        return []
        
    async def click_element(
        self,
        selector: Union[str, ElementSelector, int],
        button: str = "left",
        timeout: float = 10.0,
        scroll_into_view: bool = True
    ) -> bool:
        """Click on element.
        
        Args:
            selector: Element selector or node ID
            button: Mouse button ('left', 'middle', 'right')
            timeout: Element search timeout
            scroll_into_view: Whether to scroll element into view
            
        Returns:
            True if clicked successfully
            
        Raises:
            ElementNotFoundError: If element not found
            ActionError: If click fails
        """
        try:
            # Find element if selector provided
            if isinstance(selector, (str, ElementSelector)):
                node_id = await self.find_element(selector, timeout)
                if not node_id:
                    raise ElementNotFoundError(f"Element not found: {selector}")
            else:
                node_id = selector
                
            # Scroll into view if needed
            if scroll_into_view:
                await self._scroll_into_view(node_id)
                
            # Get element center coordinates
            center = await self._get_element_center(node_id)
            if not center:
                raise ActionError("Could not get element coordinates")
                
            x, y = center
            
            # Perform click
            await self.session.input.click(x, y, button)
            
            logger.debug(f"Clicked element at ({x}, {y}) with {button} button")
            return True
            
        except CDPError as e:
            raise ActionError(f"Click failed: {e}") from e
            
    async def type_text(
        self,
        selector: Union[str, ElementSelector, int],
        text: str,
        clear_first: bool = True,
        timeout: float = 10.0,
        delay: float = 0.05
    ) -> bool:
        """Type text into element.
        
        Args:
            selector: Element selector or node ID
            text: Text to type
            clear_first: Whether to clear existing text first
            timeout: Element search timeout
            delay: Delay between characters
            
        Returns:
            True if typing successful
            
        Raises:
            ElementNotFoundError: If element not found
            ActionError: If typing fails
        """
        try:
            # Find and click element first to focus it
            if isinstance(selector, (str, ElementSelector)):
                node_id = await self.find_element(selector, timeout)
                if not node_id:
                    raise ElementNotFoundError(f"Element not found: {selector}")
            else:
                node_id = selector
                
            # Focus the element
            await self.click_element(node_id)
            
            # Clear existing text if requested
            if clear_first:
                await self.session.input.dispatch_key_event("keyDown", key="a", modifiers=2)  # Ctrl+A
                await self.session.input.dispatch_key_event("keyUp", key="a", modifiers=2)
                
            # Type the text
            await self.session.input.type_text(text, delay)
            
            logger.debug(f"Typed text: {text[:50]}..." if len(text) > 50 else f"Typed text: {text}")
            return True
            
        except CDPError as e:
            raise ActionError(f"Type text failed: {e}") from e
            
    async def get_text(
        self,
        selector: Union[str, ElementSelector, int],
        timeout: float = 10.0
    ) -> Optional[str]:
        """Get text content from element.
        
        Args:
            selector: Element selector or node ID
            timeout: Element search timeout
            
        Returns:
            Element text content or None if not found
        """
        try:
            if isinstance(selector, (str, ElementSelector)):
                node_id = await self.find_element(selector, timeout)
                if not node_id:
                    return None
            else:
                node_id = selector
                
            # Get text content using JavaScript
            result = await self.session.runtime.evaluate(f"""
                (function() {{
                    const element = document.querySelector('*[data-node-id="{node_id}"]') || 
                                   Array.from(document.querySelectorAll('*')).find(el => 
                                       el._nodeId === {node_id}
                                   );
                    return element ? element.textContent.trim() : null;
                }})()
            """)
            
            return result
            
        except CDPError:
            return None
            
    async def get_attribute(
        self,
        selector: Union[str, ElementSelector, int],
        attribute: str,
        timeout: float = 10.0
    ) -> Optional[str]:
        """Get element attribute value.
        
        Args:
            selector: Element selector or node ID
            attribute: Attribute name
            timeout: Element search timeout
            
        Returns:
            Attribute value or None if not found
        """
        try:
            if isinstance(selector, (str, ElementSelector)):
                node_id = await self.find_element(selector, timeout)
                if not node_id:
                    return None
            else:
                node_id = selector
                
            attributes = await self.session.dom.get_attributes(node_id)
            return attributes.get(attribute)
            
        except CDPError:
            return None
            
    async def wait_for_element(
        self,
        selector: Union[str, ElementSelector],
        timeout: float = 30.0,
        visible: bool = True
    ) -> int:
        """Wait for element to appear.
        
        Args:
            selector: Element selector
            timeout: Wait timeout
            visible: Whether element must be visible
            
        Returns:
            Node ID when element appears
            
        Raises:
            TimeoutError: If element doesn't appear within timeout
        """
        node_id = await self.find_element(selector, timeout, visible)
        if not node_id:
            raise TimeoutError(f"Element not found within {timeout}s: {selector}")
        return node_id
        
    async def take_screenshot(
        self,
        selector: Optional[Union[str, ElementSelector, int]] = None,
        filepath: Optional[Path] = None,
        format: str = "png",
        quality: int = 100,
        full_page: bool = False
    ) -> bytes:
        """Take screenshot of page or element.
        
        Args:
            selector: Element selector for element screenshot (None for full page)
            filepath: Path to save screenshot
            format: Image format ('png', 'jpeg')
            quality: Image quality (0-100, for jpeg)
            full_page: Whether to capture full page
            
        Returns:
            Screenshot data as bytes
        """
        try:
            clip = None
            
            # Get element bounds if selector provided
            if selector is not None:
                if isinstance(selector, (str, ElementSelector)):
                    node_id = await self.find_element(selector)
                    if not node_id:
                        raise ElementNotFoundError(f"Element not found: {selector}")
                else:
                    node_id = selector
                    
                box_model = await self.session.dom.get_box_model(node_id)
                if box_model and "content" in box_model:
                    content = box_model["content"]
                    clip = {
                        "x": content[0],
                        "y": content[1],
                        "width": content[2] - content[0],
                        "height": content[5] - content[1]
                    }
                    
            # Take screenshot
            screenshot_data = await self.session.page.capture_screenshot(
                format=format,
                quality=quality,
                clip=clip,
                from_surface=full_page
            )
            
            # Save to file if path provided
            if filepath:
                filepath = Path(filepath)
                filepath.parent.mkdir(parents=True, exist_ok=True)
                with open(filepath, 'wb') as f:
                    f.write(screenshot_data)
                logger.info(f"Screenshot saved to: {filepath}")
                
            return screenshot_data
            
        except CDPError as e:
            raise ActionError(f"Screenshot failed: {e}") from e
            
    async def execute_javascript(
        self,
        script: str,
        await_promise: bool = False
    ) -> Any:
        """Execute JavaScript in page context.
        
        Args:
            script: JavaScript code to execute
            await_promise: Whether to await promise resolution
            
        Returns:
            Script execution result
        """
        try:
            result = await self.session.runtime.evaluate(
                script,
                await_promise=await_promise
            )
            return result
            
        except CDPError as e:
            raise ActionError(f"JavaScript execution failed: {e}") from e
            
    async def scroll_to(self, x: int = 0, y: int = 0) -> None:
        """Scroll page to coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
        """
        await self.execute_javascript(f"window.scrollTo({x}, {y})")
        
    async def scroll_by(self, x: int = 0, y: int = 0) -> None:
        """Scroll page by offset.
        
        Args:
            x: X offset
            y: Y offset
        """
        await self.execute_javascript(f"window.scrollBy({x}, {y})")
        
    async def _is_element_visible(self, node_id: int) -> bool:
        """Check if element is visible."""
        try:
            result = await self.session.runtime.evaluate(f"""
                (function() {{
                    const elements = Array.from(document.querySelectorAll('*'));
                    const element = elements.find(el => el._nodeId === {node_id});
                    if (!element) return false;
                    
                    const style = window.getComputedStyle(element);
                    const rect = element.getBoundingClientRect();
                    
                    return style.display !== 'none' && 
                           style.visibility !== 'hidden' && 
                           style.opacity !== '0' &&
                           rect.width > 0 && 
                           rect.height > 0;
                }})()
            """)
            return bool(result)
        except CDPError:
            return False
            
    async def _get_element_center(self, node_id: int) -> Optional[Tuple[float, float]]:
        """Get element center coordinates."""
        try:
            box_model = await self.session.dom.get_box_model(node_id)
            if box_model and "content" in box_model:
                content = box_model["content"]
                x = (content[0] + content[2]) / 2
                y = (content[1] + content[5]) / 2
                return (x, y)
        except CDPError:
            pass
        return None
        
    async def _scroll_into_view(self, node_id: int) -> None:
        """Scroll element into view."""
        try:
            await self.session.runtime.evaluate(f"""
                (function() {{
                    const elements = Array.from(document.querySelectorAll('*'));
                    const element = elements.find(el => el._nodeId === {node_id});
                    if (element) {{
                        element.scrollIntoView({{
                            behavior: 'smooth',
                            block: 'center',
                            inline: 'center'
                        }});
                    }}
                }})()
            """)
            # Wait for scroll to complete
            await asyncio.sleep(0.5)
        except CDPError:
            pass