"""
Tests for CDP domains implementation.
"""

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from surfboard.protocols.cdp import CDPClient
from surfboard.protocols.cdp_domains import (
    CDPSession,
    DOMDomain,
    EmulationDomain,
    InputDomain,
    NetworkDomain,
    PageDomain,
    RuntimeDomain,
    create_cdp_session,
)


class TestPageDomain:
    """Test PageDomain functionality."""

    @pytest.mark.asyncio
    async def test_navigate_basic(self):
        """Test basic navigation."""
        mock_client = AsyncMock()
        mock_client.enable_domain = AsyncMock()
        mock_client.send_command = AsyncMock(return_value={"frameId": "123"})
        
        page = PageDomain(mock_client)
        
        # Mock event handling
        with patch.object(page, '_wait_for_network_idle') as mock_wait:
            result = await page.navigate("https://example.com", "networkidle")
            
            mock_client.enable_domain.assert_called_once_with("Page")
            mock_client.send_command.assert_called_once_with(
                "Page.navigate", {"url": "https://example.com"}
            )
            mock_wait.assert_called_once()
            assert result == {"frameId": "123"}

    @pytest.mark.asyncio
    async def test_capture_screenshot(self):
        """Test screenshot capture."""
        mock_client = AsyncMock()
        mock_client.enable_domain = AsyncMock()
        mock_client.send_command = AsyncMock(
            return_value={"data": base64.b64encode(b"fake_image_data").decode()}
        )
        
        page = PageDomain(mock_client)
        
        result = await page.capture_screenshot(format="png", quality=90)
        
        mock_client.send_command.assert_called_once_with(
            "Page.captureScreenshot",
            {"format": "png", "fromSurface": True}
        )
        assert result == b"fake_image_data"

    @pytest.mark.asyncio
    async def test_capture_screenshot_with_clip(self):
        """Test screenshot capture with clipping."""
        mock_client = AsyncMock()
        mock_client.enable_domain = AsyncMock()
        mock_client.send_command = AsyncMock(
            return_value={"data": base64.b64encode(b"clipped_image").decode()}
        )
        
        page = PageDomain(mock_client)
        
        clip = {"x": 10, "y": 10, "width": 100, "height": 100}
        result = await page.capture_screenshot(clip=clip)
        
        mock_client.send_command.assert_called_once_with(
            "Page.captureScreenshot",
            {"format": "png", "fromSurface": True, "clip": clip}
        )
        assert result == b"clipped_image"

    @pytest.mark.asyncio
    async def test_reload(self):
        """Test page reload."""
        mock_client = AsyncMock()
        mock_client.enable_domain = AsyncMock()
        mock_client.send_command = AsyncMock()
        
        page = PageDomain(mock_client)
        
        await page.reload(ignore_cache=True)
        
        mock_client.send_command.assert_called_once_with(
            "Page.reload", {"ignoreCache": True}
        )


class TestRuntimeDomain:
    """Test RuntimeDomain functionality."""

    @pytest.mark.asyncio
    async def test_evaluate_success(self):
        """Test successful JavaScript evaluation."""
        mock_client = AsyncMock()
        mock_client.enable_domain = AsyncMock()
        mock_client.send_command = AsyncMock(
            return_value={"result": {"value": 42}}
        )
        
        runtime = RuntimeDomain(mock_client)
        
        result = await runtime.evaluate("1 + 1")
        
        mock_client.send_command.assert_called_once_with(
            "Runtime.evaluate",
            {
                "expression": "1 + 1",
                "returnByValue": True,
                "awaitPromise": False
            }
        )
        assert result == 42

    @pytest.mark.asyncio
    async def test_evaluate_with_exception(self):
        """Test JavaScript evaluation with exception."""
        from surfboard.protocols.cdp import CDPError
        
        mock_client = AsyncMock()
        mock_client.enable_domain = AsyncMock()
        mock_client.send_command = AsyncMock(
            return_value={"exceptionDetails": {"text": "ReferenceError"}}
        )
        
        runtime = RuntimeDomain(mock_client)
        
        with pytest.raises(CDPError, match="JavaScript error"):
            await runtime.evaluate("undefinedVariable")

    @pytest.mark.asyncio
    async def test_call_function_on(self):
        """Test calling function on object."""
        mock_client = AsyncMock()
        mock_client.enable_domain = AsyncMock()
        mock_client.send_command = AsyncMock(
            return_value={"result": {"value": "test_result"}}
        )
        
        runtime = RuntimeDomain(mock_client)
        
        result = await runtime.call_function_on(
            "function() { return 'test'; }",
            "object_123",
            arguments=[{"value": "arg1"}]
        )
        
        mock_client.send_command.assert_called_once_with(
            "Runtime.callFunctionOn",
            {
                "functionDeclaration": "function() { return 'test'; }",
                "objectId": "object_123",
                "returnByValue": True,
                "arguments": [{"value": "arg1"}]
            }
        )
        assert result == "test_result"


class TestDOMDomain:
    """Test DOMDomain functionality."""

    @pytest.mark.asyncio
    async def test_get_document(self):
        """Test getting document."""
        mock_client = AsyncMock()
        mock_client.enable_domain = AsyncMock()
        mock_client.send_command = AsyncMock(
            return_value={"root": {"nodeId": 1}}
        )
        
        dom = DOMDomain(mock_client)
        
        result = await dom.get_document()
        
        mock_client.send_command.assert_called_once_with("DOM.getDocument")
        assert result == {"root": {"nodeId": 1}}

    @pytest.mark.asyncio
    async def test_query_selector(self):
        """Test querySelector."""
        mock_client = AsyncMock()
        mock_client.enable_domain = AsyncMock()
        mock_client.send_command = AsyncMock(
            return_value={"nodeId": 123}
        )
        
        dom = DOMDomain(mock_client)
        
        result = await dom.query_selector(1, "div.test")
        
        mock_client.send_command.assert_called_once_with(
            "DOM.querySelector",
            {"nodeId": 1, "selector": "div.test"}
        )
        assert result == 123

    @pytest.mark.asyncio
    async def test_query_selector_all(self):
        """Test querySelectorAll."""
        mock_client = AsyncMock()
        mock_client.enable_domain = AsyncMock()
        mock_client.send_command = AsyncMock(
            return_value={"nodeIds": [123, 124, 125]}
        )
        
        dom = DOMDomain(mock_client)
        
        result = await dom.query_selector_all(1, "div.test")
        
        mock_client.send_command.assert_called_once_with(
            "DOM.querySelectorAll",
            {"nodeId": 1, "selector": "div.test"}
        )
        assert result == [123, 124, 125]

    @pytest.mark.asyncio
    async def test_get_attributes(self):
        """Test getting element attributes."""
        mock_client = AsyncMock()
        mock_client.enable_domain = AsyncMock()
        mock_client.send_command = AsyncMock(
            return_value={"attributes": ["class", "test-class", "id", "test-id"]}
        )
        
        dom = DOMDomain(mock_client)
        
        result = await dom.get_attributes(123)
        
        mock_client.send_command.assert_called_once_with(
            "DOM.getAttributes", {"nodeId": 123}
        )
        assert result == {"class": "test-class", "id": "test-id"}


class TestInputDomain:
    """Test InputDomain functionality."""

    @pytest.mark.asyncio
    async def test_dispatch_mouse_event(self):
        """Test mouse event dispatch."""
        mock_client = AsyncMock()
        mock_client.enable_domain = AsyncMock()
        mock_client.send_command = AsyncMock()
        
        input_domain = InputDomain(mock_client)
        
        await input_domain.dispatch_mouse_event(
            "mousePressed", 100, 200, button="right", click_count=2
        )
        
        mock_client.send_command.assert_called_once_with(
            "Input.dispatchMouseEvent",
            {
                "type": "mousePressed",
                "x": 100,
                "y": 200,
                "modifiers": 0,
                "button": "right",
                "clickCount": 2
            }
        )

    @pytest.mark.asyncio
    async def test_click(self):
        """Test click action."""
        mock_client = AsyncMock()
        mock_client.enable_domain = AsyncMock()
        mock_client.send_command = AsyncMock()
        
        input_domain = InputDomain(mock_client)
        
        with patch("asyncio.sleep"):
            await input_domain.click(150, 250)
        
        # Should call mousePressed and mouseReleased
        assert mock_client.send_command.call_count == 2
        
        # Check first call (mousePressed)
        args1 = mock_client.send_command.call_args_list[0]
        assert args1[0][0] == "Input.dispatchMouseEvent"
        assert args1[0][1]["type"] == "mousePressed"
        assert args1[0][1]["x"] == 150
        assert args1[0][1]["y"] == 250
        
        # Check second call (mouseReleased)
        args2 = mock_client.send_command.call_args_list[1]
        assert args2[0][0] == "Input.dispatchMouseEvent"
        assert args2[0][1]["type"] == "mouseReleased"

    @pytest.mark.asyncio
    async def test_type_text(self):
        """Test text typing."""
        mock_client = AsyncMock()
        mock_client.enable_domain = AsyncMock()
        mock_client.send_command = AsyncMock()
        
        input_domain = InputDomain(mock_client)
        
        with patch("asyncio.sleep"):
            await input_domain.type_text("hi", delay=0)
        
        # Should dispatch char events for each character
        assert mock_client.send_command.call_count == 2
        
        # Check calls
        calls = mock_client.send_command.call_args_list
        assert calls[0][0][1]["type"] == "char"
        assert calls[0][0][1]["text"] == "h"
        assert calls[1][0][1]["type"] == "char"
        assert calls[1][0][1]["text"] == "i"


class TestCDPSession:
    """Test CDPSession integration."""

    @pytest.mark.asyncio
    async def test_session_creation(self):
        """Test CDP session creation."""
        mock_client = AsyncMock()
        
        session = CDPSession(mock_client)
        
        assert session.client == mock_client
        assert isinstance(session.page, PageDomain)
        assert isinstance(session.runtime, RuntimeDomain)
        assert isinstance(session.dom, DOMDomain)
        assert isinstance(session.input, InputDomain)
        assert isinstance(session.network, NetworkDomain)
        assert isinstance(session.emulation, EmulationDomain)

    @pytest.mark.asyncio
    async def test_session_context_manager(self):
        """Test CDP session as context manager."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        async with CDPSession(mock_client) as session:
            assert session.client == mock_client
        
        mock_client.__aenter__.assert_called_once()
        mock_client.__aexit__.assert_called_once()


class TestConvenienceFunctions:
    """Test convenience functions."""

    @pytest.mark.asyncio
    async def test_create_cdp_session(self):
        """Test creating CDP session."""
        with patch('surfboard.protocols.cdp_domains.CDPClient') as mock_cdp_class:
            mock_client = AsyncMock()
            mock_cdp_class.return_value = mock_client
            
            session = await create_cdp_session(host="test", port=9999, timeout=10.0)
            
            mock_cdp_class.assert_called_once_with(host="test", port=9999, timeout=10.0)
            assert isinstance(session, CDPSession)
            assert session.client == mock_client