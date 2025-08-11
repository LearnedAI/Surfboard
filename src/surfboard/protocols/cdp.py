"""
Chrome DevTools Protocol (CDP) implementation.

This module provides a Python client for communicating with Chrome 
via the DevTools Protocol over WebSocket connections.
"""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, Optional

import aiohttp
import websockets
from websockets import WebSocketServerProtocol

logger = logging.getLogger(__name__)


class CDPError(Exception):
    """Base exception for CDP-related errors."""

    pass


class CDPConnectionError(CDPError):
    """Exception raised when CDP connection fails."""

    pass


class CDPTimeoutError(CDPError):
    """Exception raised when CDP operation times out."""

    pass


class CDPClient:
    """Chrome DevTools Protocol client."""

    def __init__(
        self, host: str = "localhost", port: int = 9222, timeout: float = 30.0
    ):
        """Initialize CDP client.

        Args:
            host: Chrome debugging host (default: localhost)
            port: Chrome debugging port (default: 9222)
            timeout: Default timeout for operations (default: 30.0)
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self._websocket: Optional[WebSocketServerProtocol] = None
        self._message_id = 0
        self._pending_messages: Dict[int, asyncio.Future] = {}
        self._event_handlers: Dict[str, Callable] = {}
        self._receive_task: Optional[asyncio.Task] = None

    async def connect(self, tab_id: Optional[str] = None) -> None:
        """Connect to Chrome DevTools.

        Args:
            tab_id: Specific tab ID to connect to (default: first available tab)

        Raises:
            CDPConnectionError: If connection fails
        """
        try:
            # Get available tabs
            tab_url = await self._get_tab_websocket_url(tab_id)

            # Connect to WebSocket
            self._websocket = await websockets.connect(
                tab_url,
                timeout=self.timeout,
                max_size=10 * 1024 * 1024,  # 10MB max message size
                ping_timeout=20,
                ping_interval=30,
            )

            # Start message receiving task
            self._receive_task = asyncio.create_task(self._receive_messages())

            logger.info(f"Connected to Chrome CDP on {tab_url}")

        except Exception as e:
            raise CDPConnectionError(f"Failed to connect to CDP: {e}") from e

    async def close(self) -> None:
        """Close CDP connection and cleanup resources."""
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        if self._websocket:
            await self._websocket.close()
            self._websocket = None

        # Cancel pending messages
        for future in self._pending_messages.values():
            if not future.done():
                future.cancel()
        self._pending_messages.clear()

        logger.info("CDP connection closed")

    async def send_command(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send CDP command and wait for response.

        Args:
            method: CDP method name (e.g., 'Page.navigate')
            params: Method parameters

        Returns:
            Command response result

        Raises:
            CDPError: If command fails
            CDPTimeoutError: If command times out
        """
        if not self._websocket:
            raise CDPConnectionError("Not connected to CDP")

        message_id = self._get_next_message_id()
        message = {"id": message_id, "method": method, "params": params or {}}

        # Create future for response
        response_future = asyncio.Future()
        self._pending_messages[message_id] = response_future

        try:
            # Send message
            await self._websocket.send(json.dumps(message))
            logger.debug(f"Sent CDP command: {method}")

            # Wait for response
            response = await asyncio.wait_for(response_future, timeout=self.timeout)

            if "error" in response:
                error_info = response["error"]
                raise CDPError(
                    f"CDP command failed: {error_info.get('message', 'Unknown error')}"
                )

            return response.get("result", {})

        except asyncio.TimeoutError:
            raise CDPTimeoutError(
                f"CDP command '{method}' timed out after {self.timeout}s"
            )
        finally:
            self._pending_messages.pop(message_id, None)

    def add_event_handler(
        self, event_name: str, handler: Callable[[Dict[str, Any]], None]
    ) -> None:
        """Add handler for CDP events.

        Args:
            event_name: CDP event name (e.g., 'Page.loadEventFired')
            handler: Event handler function
        """
        self._event_handlers[event_name] = handler

    async def enable_domain(self, domain: str) -> None:
        """Enable CDP domain to receive events.

        Args:
            domain: Domain name (e.g., 'Page', 'DOM', 'Runtime')
        """
        await self.send_command(f"{domain}.enable")

    async def _get_tab_websocket_url(self, tab_id: Optional[str] = None) -> str:
        """Get WebSocket URL for connecting to a Chrome tab.

        Args:
            tab_id: Specific tab ID (default: first available)

        Returns:
            WebSocket URL for the tab

        Raises:
            CDPConnectionError: If no suitable tab found
        """
        base_url = f"http://{self.host}:{self.port}"

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as session:
                async with session.get(f"{base_url}/json") as response:
                    tabs = await response.json()
        except Exception as e:
            raise CDPConnectionError(f"Failed to get Chrome tabs: {e}") from e

        if not tabs:
            raise CDPConnectionError("No Chrome tabs available")

        if tab_id:
            # Find specific tab
            target_tab = next((tab for tab in tabs if tab.get("id") == tab_id), None)
            if not target_tab:
                raise CDPConnectionError(f"Tab with ID '{tab_id}' not found")
        else:
            # Use first available tab
            target_tab = tabs[0]

        websocket_url = target_tab.get("webSocketDebuggerUrl")
        if not websocket_url:
            raise CDPConnectionError("No WebSocket URL available for tab")

        return websocket_url

    async def _receive_messages(self) -> None:
        """Background task to receive and process CDP messages."""
        try:
            async for message in self._websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse CDP message: {e}")
                except Exception as e:
                    logger.error(f"Error handling CDP message: {e}")
        except websockets.exceptions.ConnectionClosed:
            logger.info("CDP WebSocket connection closed")
        except Exception as e:
            logger.error(f"Error in CDP message receiver: {e}")

    async def _handle_message(self, data: Dict[str, Any]) -> None:
        """Handle incoming CDP message.

        Args:
            data: Parsed CDP message
        """
        if "id" in data:
            # Response to command
            message_id = data["id"]
            future = self._pending_messages.get(message_id)
            if future and not future.done():
                future.set_result(data)
        elif "method" in data:
            # Event notification
            event_name = data["method"]
            handler = self._event_handlers.get(event_name)
            if handler:
                try:
                    handler(data.get("params", {}))
                except Exception as e:
                    logger.error(f"Error in CDP event handler for {event_name}: {e}")

    def _get_next_message_id(self) -> int:
        """Get next message ID for CDP commands."""
        self._message_id += 1
        return self._message_id

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Convenience functions for common CDP operations


async def test_chrome_connection(host: str = "localhost", port: int = 9222) -> bool:
    """Test if Chrome is running with debugging enabled.

    Args:
        host: Chrome debugging host
        port: Chrome debugging port

    Returns:
        True if connection successful, False otherwise
    """
    try:
        async with CDPClient(host=host, port=port, timeout=5.0) as client:
            # Try a simple command
            await client.send_command("Runtime.evaluate", {"expression": "1 + 1"})
            return True
    except Exception as e:
        logger.debug(f"Chrome connection test failed: {e}")
        return False


async def get_chrome_version(
    host: str = "localhost", port: int = 9222
) -> Optional[Dict[str, Any]]:
    """Get Chrome version information.

    Args:
        host: Chrome debugging host
        port: Chrome debugging port

    Returns:
        Version information dict or None if failed
    """
    try:
        base_url = f"http://{host}:{port}"
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10.0)
        ) as session:
            async with session.get(f"{base_url}/json/version") as response:
                return await response.json()
    except Exception as e:
        logger.debug(f"Failed to get Chrome version: {e}")
        return None
