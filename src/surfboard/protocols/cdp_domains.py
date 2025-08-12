"""
Chrome DevTools Protocol domain implementations.

This module provides high-level interfaces for CDP domains,
making browser automation more intuitive and robust.
"""

import asyncio
import base64
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .cdp import CDPClient, CDPError

logger = logging.getLogger(__name__)


class CDPDomain:
    """Base class for CDP domain implementations."""

    def __init__(self, client: CDPClient):
        """Initialize CDP domain.

        Args:
            client: CDP client instance
        """
        self.client = client
        self.enabled = False

    async def enable(self) -> None:
        """Enable this domain."""
        if not self.enabled:
            await self.client.enable_domain(self.domain_name)
            self.enabled = True

    async def disable(self) -> None:
        """Disable this domain."""
        if self.enabled:
            await self.client.send_command(f"{self.domain_name}.disable")
            self.enabled = False

    @property
    def domain_name(self) -> str:
        """Get domain name."""
        raise NotImplementedError


class PageDomain(CDPDomain):
    """Page domain for navigation and page lifecycle."""

    @property
    def domain_name(self) -> str:
        return "Page"

    async def navigate(self, url: str, wait_until: str = "load") -> Dict[str, Any]:
        """Navigate to URL.

        Args:
            url: URL to navigate to
            wait_until: Wait condition ('load', 'domcontentloaded', 'networkidle')

        Returns:
            Navigation result
        """
        await self.enable()

        # Set up event listeners for navigation
        if wait_until in ["load", "domcontentloaded"]:
            load_event = asyncio.Event()

            def on_load_event(params):
                load_event.set()

            if wait_until == "load":
                self.client.add_event_handler("Page.loadEventFired", on_load_event)
            else:
                self.client.add_event_handler(
                    "Page.domContentEventFired", on_load_event
                )

        # Navigate
        result = await self.client.send_command("Page.navigate", {"url": url})

        # Wait for completion
        if wait_until in ["load", "domcontentloaded"]:
            await asyncio.wait_for(load_event.wait(), timeout=30.0)
        elif wait_until == "networkidle":
            await self._wait_for_network_idle()

        return result

    async def reload(self, ignore_cache: bool = False) -> None:
        """Reload current page.

        Args:
            ignore_cache: Whether to ignore cache
        """
        await self.enable()
        await self.client.send_command("Page.reload", {"ignoreCache": ignore_cache})

    async def get_frame_tree(self) -> Dict[str, Any]:
        """Get page frame tree."""
        await self.enable()
        return await self.client.send_command("Page.getFrameTree")

    async def capture_screenshot(
        self,
        format: str = "png",
        quality: int = 100,
        clip: Optional[Dict[str, float]] = None,
        from_surface: bool = True,
    ) -> bytes:
        """Capture page screenshot.

        Args:
            format: Image format ('png', 'jpeg')
            quality: Image quality (0-100, for jpeg)
            clip: Clipping rectangle
            from_surface: Whether to capture from surface

        Returns:
            Screenshot data as bytes
        """
        await self.enable()

        params = {"format": format, "fromSurface": from_surface}

        if format == "jpeg":
            params["quality"] = quality

        if clip:
            params["clip"] = clip

        result = await self.client.send_command("Page.captureScreenshot", params)
        return base64.b64decode(result["data"])

    async def print_to_pdf(
        self,
        landscape: bool = False,
        display_header_footer: bool = False,
        print_background: bool = False,
        scale: float = 1.0,
        paper_width: float = 8.5,
        paper_height: float = 11.0,
        margin_top: float = 1.0,
        margin_bottom: float = 1.0,
        margin_left: float = 1.0,
        margin_right: float = 1.0,
    ) -> bytes:
        """Print page to PDF.

        Args:
            landscape: Paper orientation
            display_header_footer: Whether to display header/footer
            print_background: Whether to print background graphics
            scale: Scale factor
            paper_width: Paper width in inches
            paper_height: Paper height in inches
            margin_top: Top margin in inches
            margin_bottom: Bottom margin in inches
            margin_left: Left margin in inches
            margin_right: Right margin in inches

        Returns:
            PDF data as bytes
        """
        await self.enable()

        params = {
            "landscape": landscape,
            "displayHeaderFooter": display_header_footer,
            "printBackground": print_background,
            "scale": scale,
            "paperWidth": paper_width,
            "paperHeight": paper_height,
            "marginTop": margin_top,
            "marginBottom": margin_bottom,
            "marginLeft": margin_left,
            "marginRight": margin_right,
        }

        result = await self.client.send_command("Page.printToPDF", params)
        return base64.b64decode(result["data"])

    async def _wait_for_network_idle(self, timeout: float = 30.0) -> None:
        """Wait for network to become idle."""
        # Simple implementation - wait for no network activity
        await asyncio.sleep(2.0)  # Basic network idle simulation


class RuntimeDomain(CDPDomain):
    """Runtime domain for JavaScript execution."""

    @property
    def domain_name(self) -> str:
        return "Runtime"

    async def evaluate(
        self,
        expression: str,
        return_by_value: bool = True,
        await_promise: bool = False,
        context_id: Optional[int] = None,
    ) -> Any:
        """Evaluate JavaScript expression.

        Args:
            expression: JavaScript expression to evaluate
            return_by_value: Whether to return by value
            await_promise: Whether to await promise resolution
            context_id: Execution context ID

        Returns:
            Evaluation result
        """
        await self.enable()

        params = {
            "expression": expression,
            "returnByValue": return_by_value,
            "awaitPromise": await_promise,
        }

        if context_id:
            params["contextId"] = context_id

        result = await self.client.send_command("Runtime.evaluate", params)

        if result.get("exceptionDetails"):
            raise CDPError(f"JavaScript error: {result['exceptionDetails']}")

        return result.get("result", {}).get("value")

    async def call_function_on(
        self,
        function_declaration: str,
        object_id: str,
        arguments: Optional[List[Dict[str, Any]]] = None,
        return_by_value: bool = True,
    ) -> Any:
        """Call function on object.

        Args:
            function_declaration: Function to call
            object_id: Object ID to call function on
            arguments: Function arguments
            return_by_value: Whether to return by value

        Returns:
            Function result
        """
        await self.enable()

        params = {
            "functionDeclaration": function_declaration,
            "objectId": object_id,
            "returnByValue": return_by_value,
        }

        if arguments:
            params["arguments"] = arguments

        result = await self.client.send_command("Runtime.callFunctionOn", params)

        if result.get("exceptionDetails"):
            raise CDPError(f"Function call error: {result['exceptionDetails']}")

        return result.get("result", {}).get("value")

    async def get_properties(self, object_id: str) -> List[Dict[str, Any]]:
        """Get object properties.

        Args:
            object_id: Object ID

        Returns:
            List of properties
        """
        await self.enable()
        result = await self.client.send_command(
            "Runtime.getProperties", {"objectId": object_id}
        )
        return result.get("result", [])


class DOMDomain(CDPDomain):
    """DOM domain for document manipulation."""

    @property
    def domain_name(self) -> str:
        return "DOM"

    async def get_document(self) -> Dict[str, Any]:
        """Get document root node."""
        await self.enable()
        return await self.client.send_command("DOM.getDocument")

    async def query_selector(self, node_id: int, selector: str) -> Optional[int]:
        """Query for single element.

        Args:
            node_id: Parent node ID
            selector: CSS selector

        Returns:
            Node ID if found, None otherwise
        """
        await self.enable()
        try:
            result = await self.client.send_command(
                "DOM.querySelector", {"nodeId": node_id, "selector": selector}
            )
            return result.get("nodeId", 0) or None
        except CDPError:
            return None

    async def query_selector_all(self, node_id: int, selector: str) -> List[int]:
        """Query for all matching elements.

        Args:
            node_id: Parent node ID
            selector: CSS selector

        Returns:
            List of node IDs
        """
        await self.enable()
        try:
            result = await self.client.send_command(
                "DOM.querySelectorAll", {"nodeId": node_id, "selector": selector}
            )
            return result.get("nodeIds", [])
        except CDPError:
            return []

    async def get_box_model(self, node_id: int) -> Optional[Dict[str, Any]]:
        """Get element box model.

        Args:
            node_id: Node ID

        Returns:
            Box model data
        """
        await self.enable()
        try:
            return await self.client.send_command(
                "DOM.getBoxModel", {"nodeId": node_id}
            )
        except CDPError:
            return None

    async def get_attributes(self, node_id: int) -> Dict[str, str]:
        """Get element attributes.

        Args:
            node_id: Node ID

        Returns:
            Attributes dictionary
        """
        await self.enable()
        result = await self.client.send_command(
            "DOM.getAttributes", {"nodeId": node_id}
        )

        # Convert flat list to dictionary
        attrs = result.get("attributes", [])
        return {attrs[i]: attrs[i + 1] for i in range(0, len(attrs), 2)}

    async def set_attribute_value(self, node_id: int, name: str, value: str) -> None:
        """Set element attribute.

        Args:
            node_id: Node ID
            name: Attribute name
            value: Attribute value
        """
        await self.enable()
        await self.client.send_command(
            "DOM.setAttributeValue", {"nodeId": node_id, "name": name, "value": value}
        )


class InputDomain(CDPDomain):
    """Input domain for user interactions."""

    @property
    def domain_name(self) -> str:
        return "Input"

    async def dispatch_mouse_event(
        self,
        type: str,
        x: float,
        y: float,
        modifiers: int = 0,
        button: str = "left",
        click_count: int = 1,
    ) -> None:
        """Dispatch mouse event.

        Args:
            type: Event type ('mousePressed', 'mouseReleased', 'mouseMoved')
            x: X coordinate
            y: Y coordinate
            modifiers: Modifier flags
            button: Mouse button ('left', 'middle', 'right')
            click_count: Click count for double/triple clicks
        """
        await self.enable()
        await self.client.send_command(
            "Input.dispatchMouseEvent",
            {
                "type": type,
                "x": x,
                "y": y,
                "modifiers": modifiers,
                "button": button,
                "clickCount": click_count,
            },
        )

    async def click(self, x: float, y: float, button: str = "left") -> None:
        """Click at coordinates.

        Args:
            x: X coordinate
            y: Y coordinate
            button: Mouse button
        """
        await self.dispatch_mouse_event("mousePressed", x, y, button=button)
        await asyncio.sleep(0.05)  # Small delay between press and release
        await self.dispatch_mouse_event("mouseReleased", x, y, button=button)

    async def dispatch_key_event(
        self,
        type: str,
        modifiers: int = 0,
        key: Optional[str] = None,
        code: Optional[str] = None,
        text: Optional[str] = None,
    ) -> None:
        """Dispatch keyboard event.

        Args:
            type: Event type ('keyDown', 'keyUp', 'char')
            modifiers: Modifier flags
            key: Key value
            code: Key code
            text: Text for char events
        """
        await self.enable()

        params = {"type": type, "modifiers": modifiers}

        if key:
            params["key"] = key
        if code:
            params["code"] = code
        if text:
            params["text"] = text

        await self.client.send_command("Input.dispatchKeyEvent", params)

    async def type_text(self, text: str, delay: float = 0.05) -> None:
        """Type text with realistic timing.

        Args:
            text: Text to type
            delay: Delay between characters
        """
        for char in text:
            await self.dispatch_key_event("char", text=char)
            if delay > 0:
                await asyncio.sleep(delay)


class NetworkDomain(CDPDomain):
    """Network domain for request/response monitoring."""

    @property
    def domain_name(self) -> str:
        return "Network"

    async def set_user_agent_override(self, user_agent: str) -> None:
        """Set user agent override.

        Args:
            user_agent: User agent string
        """
        await self.enable()
        await self.client.send_command(
            "Network.setUserAgentOverride", {"userAgent": user_agent}
        )

    async def clear_browser_cache(self) -> None:
        """Clear browser cache."""
        await self.enable()
        await self.client.send_command("Network.clearBrowserCache")

    async def clear_browser_cookies(self) -> None:
        """Clear browser cookies."""
        await self.enable()
        await self.client.send_command("Network.clearBrowserCookies")


class EmulationDomain(CDPDomain):
    """Emulation domain for device and viewport control."""

    @property
    def domain_name(self) -> str:
        return "Emulation"

    async def set_device_metrics_override(
        self,
        width: int,
        height: int,
        device_scale_factor: float = 1.0,
        mobile: bool = False,
        screen_width: Optional[int] = None,
        screen_height: Optional[int] = None,
    ) -> None:
        """Set device metrics override.

        Args:
            width: Viewport width
            height: Viewport height
            device_scale_factor: Device scale factor
            mobile: Whether to emulate mobile
            screen_width: Screen width
            screen_height: Screen height
        """
        await self.enable()

        params = {
            "width": width,
            "height": height,
            "deviceScaleFactor": device_scale_factor,
            "mobile": mobile,
        }

        if screen_width and screen_height:
            params["screenWidth"] = screen_width
            params["screenHeight"] = screen_height

        await self.client.send_command("Emulation.setDeviceMetricsOverride", params)

    async def set_geolocation_override(
        self, latitude: float, longitude: float, accuracy: float = 100
    ) -> None:
        """Set geolocation override.

        Args:
            latitude: Latitude
            longitude: Longitude
            accuracy: Accuracy in meters
        """
        await self.enable()
        await self.client.send_command(
            "Emulation.setGeolocationOverride",
            {"latitude": latitude, "longitude": longitude, "accuracy": accuracy},
        )


class CDPSession:
    """High-level CDP session with domain support."""

    def __init__(self, client: CDPClient):
        """Initialize CDP session.

        Args:
            client: CDP client instance
        """
        self.client = client
        self.page = PageDomain(client)
        self.runtime = RuntimeDomain(client)
        self.dom = DOMDomain(client)
        self.input = InputDomain(client)
        self.network = NetworkDomain(client)
        self.emulation = EmulationDomain(client)

    async def __aenter__(self):
        """Async context manager entry."""
        await self.client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.__aexit__(exc_type, exc_val, exc_tb)

    async def close(self):
        """Close the CDP session."""
        await self.client.close()


# Convenience functions
async def create_cdp_session(
    host: str = "localhost", port: int = 9222, timeout: float = 30.0
) -> CDPSession:
    """Create CDP session with high-level domain support.

    Args:
        host: Chrome debugging host
        port: Chrome debugging port
        timeout: Connection timeout

    Returns:
        CDP session instance
    """
    client = CDPClient(host=host, port=port, timeout=timeout)
    return CDPSession(client)
