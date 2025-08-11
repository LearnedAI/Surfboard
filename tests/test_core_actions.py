"""
Tests for core browser actions.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from surfboard.actions.core_actions import (
    ActionError,
    CoreActions,
    ElementNotFoundError,
    ElementSelector,
    TimeoutError,
)


class TestElementSelector:
    """Test ElementSelector functionality."""

    def test_css_selector_creation(self):
        """Test creating CSS selector."""
        selector = ElementSelector(css="div.test")
        
        assert selector.css == "div.test"
        assert selector.xpath is None
        assert selector.text is None

    def test_multiple_strategies(self):
        """Test selector with multiple strategies."""
        selector = ElementSelector(
            css="input[name='test']",
            text="Click me",
            placeholder="Enter text",
            role="button",
            aria_label="Test button"
        )
        
        selectors = selector.to_css_selectors()
        
        assert "input[name='test']" in selectors
        assert "*:contains('Click me')" in selectors
        assert "[placeholder='Enter text']" in selectors
        assert "[role='button']" in selectors
        assert "[aria-label='Test button']" in selectors

    def test_javascript_finder(self):
        """Test JavaScript finder generation."""
        selector = ElementSelector(
            css="div.test",
            text="Hello World"
        )
        
        js_finder = selector.to_javascript_finder()
        
        assert "document.querySelector('div.test')" in js_finder
        assert "textContent" in js_finder
        assert "Hello World" in js_finder

    def test_empty_selector(self):
        """Test empty selector."""
        selector = ElementSelector()
        
        selectors = selector.to_css_selectors()
        js_finder = selector.to_javascript_finder()
        
        assert selectors == []
        assert js_finder == "null"


class TestCoreActions:
    """Test CoreActions functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = MagicMock()
        self.mock_session.page = AsyncMock()
        self.mock_session.dom = AsyncMock()
        self.mock_session.runtime = AsyncMock()
        self.mock_session.input = AsyncMock()
        
        self.actions = CoreActions(self.mock_session)

    @pytest.mark.asyncio
    async def test_navigate_success(self):
        """Test successful navigation."""
        self.mock_session.page.navigate = AsyncMock(return_value={"frameId": "123"})
        
        result = await self.actions.navigate("https://example.com")
        
        self.mock_session.page.navigate.assert_called_once_with(
            "https://example.com", "load"
        )
        assert result == {"frameId": "123"}

    @pytest.mark.asyncio
    async def test_navigate_timeout(self):
        """Test navigation timeout."""
        self.mock_session.page.navigate = AsyncMock(
            side_effect=asyncio.TimeoutError()
        )
        
        with pytest.raises(TimeoutError, match="Navigation.*timed out"):
            await self.actions.navigate("https://example.com", timeout=1.0)

    @pytest.mark.asyncio
    async def test_find_element_success(self):
        """Test successful element finding."""
        # Mock DOM responses
        self.mock_session.dom.get_document = AsyncMock(
            return_value={"root": {"nodeId": 1}}
        )
        self.mock_session.dom.query_selector = AsyncMock(return_value=123)
        
        # Mock visibility check
        with patch.object(self.actions, '_is_element_visible', return_value=True):
            result = await self.actions.find_element("div.test")
            
        assert result == 123
        self.mock_session.dom.query_selector.assert_called()

    @pytest.mark.asyncio
    async def test_find_element_not_found(self):
        """Test element not found."""
        # Mock DOM responses - no element found
        self.mock_session.dom.get_document = AsyncMock(
            return_value={"root": {"nodeId": 1}}
        )
        self.mock_session.dom.query_selector = AsyncMock(return_value=None)
        
        result = await self.actions.find_element("div.nonexistent", timeout=0.1)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_find_elements_multiple(self):
        """Test finding multiple elements."""
        # Mock DOM responses
        self.mock_session.dom.get_document = AsyncMock(
            return_value={"root": {"nodeId": 1}}
        )
        self.mock_session.dom.query_selector_all = AsyncMock(
            return_value=[123, 124, 125]
        )
        
        # Mock visibility checks
        with patch.object(self.actions, '_is_element_visible', return_value=True):
            result = await self.actions.find_elements("div.test")
            
        assert result == [123, 124, 125]

    @pytest.mark.asyncio
    async def test_click_element_with_selector(self):
        """Test clicking element with selector."""
        # Mock element finding
        with patch.object(self.actions, 'find_element', return_value=123):
            with patch.object(self.actions, '_scroll_into_view'):
                with patch.object(self.actions, '_get_element_center', 
                                return_value=(100, 200)):
                    
                    result = await self.actions.click_element("div.test")
                    
        assert result is True
        self.mock_session.input.click.assert_called_once_with(100, 200, "left")

    @pytest.mark.asyncio
    async def test_click_element_not_found(self):
        """Test clicking non-existent element."""
        with patch.object(self.actions, 'find_element', return_value=None):
            with pytest.raises(ElementNotFoundError):
                await self.actions.click_element("div.nonexistent")

    @pytest.mark.asyncio
    async def test_type_text_success(self):
        """Test successful text typing."""
        # Mock element finding and clicking
        with patch.object(self.actions, 'find_element', return_value=123):
            with patch.object(self.actions, 'click_element'):
                
                result = await self.actions.type_text("input.test", "Hello World")
                
        assert result is True
        self.mock_session.input.type_text.assert_called_once_with("Hello World", 0.05)

    @pytest.mark.asyncio
    async def test_type_text_with_clear(self):
        """Test typing text with clearing existing content."""
        with patch.object(self.actions, 'find_element', return_value=123):
            with patch.object(self.actions, 'click_element'):
                
                await self.actions.type_text("input.test", "New Text", clear_first=True)
                
        # Should call key events for Ctrl+A to select all
        key_calls = self.mock_session.input.dispatch_key_event.call_args_list
        assert len(key_calls) >= 2  # At least keyDown and keyUp for Ctrl+A

    @pytest.mark.asyncio
    async def test_get_text(self):
        """Test getting element text."""
        with patch.object(self.actions, 'find_element', return_value=123):
            self.mock_session.runtime.evaluate = AsyncMock(
                return_value="Element text content"
            )
            
            result = await self.actions.get_text("div.test")
            
        assert result == "Element text content"
        self.mock_session.runtime.evaluate.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_attribute(self):
        """Test getting element attribute."""
        with patch.object(self.actions, 'find_element', return_value=123):
            self.mock_session.dom.get_attributes = AsyncMock(
                return_value={"class": "test-class", "id": "test-id"}
            )
            
            result = await self.actions.get_attribute("div.test", "class")
            
        assert result == "test-class"

    @pytest.mark.asyncio
    async def test_wait_for_element_success(self):
        """Test waiting for element successfully."""
        with patch.object(self.actions, 'find_element', return_value=123):
            result = await self.actions.wait_for_element("div.test", timeout=1.0)
            
        assert result == 123

    @pytest.mark.asyncio
    async def test_wait_for_element_timeout(self):
        """Test waiting for element timeout."""
        with patch.object(self.actions, 'find_element', return_value=None):
            with pytest.raises(TimeoutError, match="Element not found within"):
                await self.actions.wait_for_element("div.test", timeout=0.1)

    @pytest.mark.asyncio
    async def test_take_screenshot_full_page(self):
        """Test taking full page screenshot."""
        self.mock_session.page.capture_screenshot = AsyncMock(
            return_value=b"fake_screenshot_data"
        )
        
        result = await self.actions.take_screenshot()
        
        assert result == b"fake_screenshot_data"
        self.mock_session.page.capture_screenshot.assert_called_once()

    @pytest.mark.asyncio
    async def test_take_screenshot_element(self):
        """Test taking element screenshot."""
        # Mock element finding and box model
        with patch.object(self.actions, 'find_element', return_value=123):
            self.mock_session.dom.get_box_model = AsyncMock(
                return_value={
                    "content": [10, 20, 110, 20, 110, 120, 10, 120]  # x1,y1,x2,y1,x2,y2,x1,y2
                }
            )
            self.mock_session.page.capture_screenshot = AsyncMock(
                return_value=b"element_screenshot"
            )
            
            result = await self.actions.take_screenshot(selector="div.test")
            
        assert result == b"element_screenshot"
        
        # Check that clip was calculated correctly
        call_args = self.mock_session.page.capture_screenshot.call_args
        clip = call_args[1]["clip"]
        assert clip["x"] == 10
        assert clip["y"] == 20
        assert clip["width"] == 100
        assert clip["height"] == 100

    @pytest.mark.asyncio
    async def test_take_screenshot_with_file(self):
        """Test taking screenshot and saving to file."""
        self.mock_session.page.capture_screenshot = AsyncMock(
            return_value=b"screenshot_data"
        )
        
        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            with patch("pathlib.Path.mkdir"):
                await self.actions.take_screenshot(
                    filepath=Path("/tmp/test.png")
                )
            
            mock_file.write.assert_called_once_with(b"screenshot_data")

    @pytest.mark.asyncio
    async def test_execute_javascript(self):
        """Test JavaScript execution."""
        self.mock_session.runtime.evaluate = AsyncMock(
            return_value={"result": "success"}
        )
        
        result = await self.actions.execute_javascript("console.log('test');")
        
        assert result == {"result": "success"}
        self.mock_session.runtime.evaluate.assert_called_once_with(
            "console.log('test');", await_promise=False
        )

    @pytest.mark.asyncio
    async def test_scroll_to(self):
        """Test scrolling to coordinates."""
        self.mock_session.runtime.evaluate = AsyncMock()
        
        await self.actions.scroll_to(100, 200)
        
        self.mock_session.runtime.evaluate.assert_called_once_with(
            "window.scrollTo(100, 200)", await_promise=False
        )

    @pytest.mark.asyncio
    async def test_scroll_by(self):
        """Test scrolling by offset."""
        self.mock_session.runtime.evaluate = AsyncMock()
        
        await self.actions.scroll_by(50, 100)
        
        self.mock_session.runtime.evaluate.assert_called_once_with(
            "window.scrollBy(50, 100)", await_promise=False
        )

    @pytest.mark.asyncio
    async def test_is_element_visible_true(self):
        """Test element visibility check - visible."""
        self.mock_session.runtime.evaluate = AsyncMock(return_value=True)
        
        result = await self.actions._is_element_visible(123)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_is_element_visible_false(self):
        """Test element visibility check - hidden."""
        self.mock_session.runtime.evaluate = AsyncMock(return_value=False)
        
        result = await self.actions._is_element_visible(123)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_get_element_center(self):
        """Test getting element center coordinates."""
        self.mock_session.dom.get_box_model = AsyncMock(
            return_value={
                "content": [10, 20, 60, 20, 60, 80, 10, 80]
            }
        )
        
        result = await self.actions._get_element_center(123)
        
        assert result == (35.0, 50.0)  # Center of rectangle

    @pytest.mark.asyncio
    async def test_get_element_center_no_box_model(self):
        """Test getting element center when box model unavailable."""
        self.mock_session.dom.get_box_model = AsyncMock(return_value=None)
        
        result = await self.actions._get_element_center(123)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_scroll_into_view(self):
        """Test scrolling element into view."""
        self.mock_session.runtime.evaluate = AsyncMock()
        
        with patch("asyncio.sleep"):
            await self.actions._scroll_into_view(123)
        
        self.mock_session.runtime.evaluate.assert_called_once()
        js_code = self.mock_session.runtime.evaluate.call_args[0][0]
        assert "scrollIntoView" in js_code