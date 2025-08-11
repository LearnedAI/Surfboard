"""
Tests for CDP connection functionality.

This module contains basic tests for the Chrome DevTools Protocol client,
including connection tests and basic command execution.
"""

from unittest.mock import AsyncMock, patch

import pytest

from surfboard.protocols.cdp import (
    CDPClient,
    CDPConnectionError,
    get_chrome_version,
    test_chrome_connection,
)


class TestCDPClient:
    """Test CDP client functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test CDP client initialization."""
        client = CDPClient(host="localhost", port=9222, timeout=30.0)

        assert client.host == "localhost"
        assert client.port == 9222
        assert client.timeout == 30.0
        assert client._websocket is None
        assert client._message_id == 0
        assert len(client._pending_messages) == 0

    @pytest.mark.asyncio
    async def test_get_next_message_id(self):
        """Test message ID generation."""
        client = CDPClient()

        first_id = client._get_next_message_id()
        second_id = client._get_next_message_id()

        assert first_id == 1
        assert second_id == 2
        assert client._message_id == 2

    @pytest.mark.asyncio
    async def test_connection_without_chrome_fails(self):
        """Test that connection fails when Chrome is not running."""
        client = CDPClient(port=99999, timeout=1.0)  # Invalid port

        with pytest.raises(CDPConnectionError):
            await client.connect()

    @pytest.mark.asyncio
    async def test_send_command_without_connection_fails(self):
        """Test that sending command without connection fails."""
        client = CDPClient()

        with pytest.raises(CDPConnectionError, match="Not connected to CDP"):
            await client.send_command("Runtime.evaluate", {"expression": "1+1"})

    @pytest.mark.asyncio
    async def test_add_event_handler(self):
        """Test adding event handlers."""
        client = CDPClient()

        def mock_handler(params):
            pass

        client.add_event_handler("Page.loadEventFired", mock_handler)

        assert "Page.loadEventFired" in client._event_handlers
        assert client._event_handlers["Page.loadEventFired"] == mock_handler

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    async def test_get_tab_websocket_url_success(self, mock_get):
        """Test successful tab WebSocket URL retrieval."""
        # Mock the HTTP response
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(
            return_value=[
                {
                    "id": "tab-1",
                    "url": "https://example.com",
                    "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/tab-1",
                }
            ]
        )
        mock_get.return_value.__aenter__.return_value = mock_response

        client = CDPClient()
        url = await client._get_tab_websocket_url()

        assert url == "ws://localhost:9222/devtools/page/tab-1"

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    async def test_get_tab_websocket_url_specific_tab(self, mock_get):
        """Test getting specific tab WebSocket URL."""
        # Mock the HTTP response with multiple tabs
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(
            return_value=[
                {
                    "id": "tab-1",
                    "url": "https://example.com",
                    "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/tab-1",
                },
                {
                    "id": "tab-2",
                    "url": "https://google.com",
                    "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/tab-2",
                },
            ]
        )
        mock_get.return_value.__aenter__.return_value = mock_response

        client = CDPClient()
        url = await client._get_tab_websocket_url(tab_id="tab-2")

        assert url == "ws://localhost:9222/devtools/page/tab-2"

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    async def test_get_tab_websocket_url_no_tabs(self, mock_get):
        """Test handling when no tabs are available."""
        # Mock the HTTP response with empty tabs
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=[])
        mock_get.return_value.__aenter__.return_value = mock_response

        client = CDPClient()

        with pytest.raises(CDPConnectionError, match="No Chrome tabs available"):
            await client._get_tab_websocket_url()

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    async def test_get_tab_websocket_url_tab_not_found(self, mock_get):
        """Test handling when specific tab is not found."""
        # Mock the HTTP response
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(
            return_value=[
                {
                    "id": "tab-1",
                    "url": "https://example.com",
                    "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/tab-1",
                }
            ]
        )
        mock_get.return_value.__aenter__.return_value = mock_response

        client = CDPClient()

        with pytest.raises(
            CDPConnectionError, match="Tab with ID 'nonexistent' not found"
        ):
            await client._get_tab_websocket_url(tab_id="nonexistent")


class TestCDPConvenienceFunctions:
    """Test CDP convenience functions."""

    @pytest.mark.asyncio
    @patch("surfboard.protocols.cdp.CDPClient")
    async def test_chrome_connection_success(self, mock_cdp_client):
        """Test successful Chrome connection test."""
        # Mock successful CDP client
        mock_client_instance = AsyncMock()
        mock_cdp_client.return_value.__aenter__.return_value = mock_client_instance

        result = await test_chrome_connection()

        assert result is True
        mock_client_instance.send_command.assert_called_once_with(
            "Runtime.evaluate", {"expression": "1 + 1"}
        )

    @pytest.mark.asyncio
    @patch("surfboard.protocols.cdp.CDPClient")
    async def test_chrome_connection_failure(self, mock_cdp_client):
        """Test Chrome connection test failure."""
        # Mock failing CDP client
        mock_cdp_client.return_value.__aenter__.side_effect = CDPConnectionError(
            "Connection failed"
        )

        result = await test_chrome_connection()

        assert result is False

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    async def test_get_chrome_version_success(self, mock_get):
        """Test successful Chrome version retrieval."""
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(
            return_value={
                "Browser": "Chrome/120.0.6099.129",
                "Protocol-Version": "1.3",
                "User-Agent": "Mozilla/5.0...",
                "V8-Version": "12.0.267.17",
            }
        )
        mock_get.return_value.__aenter__.return_value = mock_response

        version_info = await get_chrome_version()

        assert version_info is not None
        assert "Browser" in version_info
        assert "Protocol-Version" in version_info

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    async def test_get_chrome_version_failure(self, mock_get):
        """Test Chrome version retrieval failure."""
        mock_get.return_value.__aenter__.side_effect = Exception("Connection failed")

        version_info = await get_chrome_version()

        assert version_info is None


# Integration test that can run with real Chrome (marked for manual testing)
@pytest.mark.manual
@pytest.mark.asyncio
async def test_real_chrome_connection():
    """
    Integration test for real Chrome connection.

    This test requires Chrome to be running with --remote-debugging-port=9222
    Mark with @pytest.mark.manual to exclude from automatic test runs.
    """
    # Test real connection
    connection_successful = await test_chrome_connection()

    if connection_successful:
        # Test getting version info
        version_info = await get_chrome_version()
        assert version_info is not None
        assert "Browser" in version_info

        # Test basic CDP operations
        async with CDPClient() as client:
            # Enable Runtime domain
            await client.enable_domain("Runtime")

            # Test JavaScript execution
            result = await client.send_command(
                "Runtime.evaluate", {"expression": "2 + 3", "returnByValue": True}
            )

            assert "value" in result
            assert result["value"] == 5
    else:
        pytest.skip("Chrome not available for integration testing")
