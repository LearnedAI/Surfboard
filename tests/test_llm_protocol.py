"""
Tests for LLM communication protocol.
"""

import json
import uuid
from pathlib import Path

import pytest
from pydantic import ValidationError

from surfboard.protocols.llm_protocol import (
    BaseCommand,
    BaseResponse,
    BrowserConfig,
    ClickCommand,
    CommandType,
    CreateBrowserCommand,
    ElementSelector,
    ExecuteScriptCommand,
    FindElementCommand,
    GetPageSummaryCommand,
    GetTextCommand,
    LLMMessage,
    NavigateCommand,
    PageInfo,
    ScreenshotResponse,
    StatusType,
    TakeScreenshotCommand,
    TypeTextCommand,
    Viewport,
    WaitCondition,
    create_command_from_dict,
    create_error_response,
    deserialize_command,
    export_json_schemas,
    serialize_response,
    validate_command_schema,
)


class TestElementSelector:
    """Test ElementSelector model."""

    def test_valid_css_selector(self):
        """Test valid CSS selector."""
        selector = ElementSelector(
            type="css", value="button.submit", timeout=10.0, visible_only=True
        )

        assert selector.type.value == "css"
        assert selector.value == "button.submit"
        assert selector.timeout == 10.0
        assert selector.visible_only is True

    def test_default_values(self):
        """Test default values."""
        selector = ElementSelector(type="css", value="div")

        assert selector.timeout == 10.0
        assert selector.visible_only is True

    def test_invalid_selector_type(self):
        """Test invalid selector type."""
        with pytest.raises(ValidationError):
            ElementSelector(type="invalid", value="div")


class TestViewport:
    """Test Viewport model."""

    def test_valid_viewport(self):
        """Test valid viewport configuration."""
        viewport = Viewport(
            width=1920, height=1080, device_scale_factor=2.0, mobile=True
        )

        assert viewport.width == 1920
        assert viewport.height == 1080
        assert viewport.device_scale_factor == 2.0
        assert viewport.mobile is True

    def test_default_viewport(self):
        """Test default viewport values."""
        viewport = Viewport()

        assert viewport.width == 1280
        assert viewport.height == 720
        assert viewport.device_scale_factor == 1.0
        assert viewport.mobile is False


class TestBrowserConfig:
    """Test BrowserConfig model."""

    def test_valid_config(self):
        """Test valid browser configuration."""
        viewport = Viewport(width=800, height=600)
        config = BrowserConfig(
            headless=False,
            viewport=viewport,
            user_agent="test-agent",
            profile="test-profile",
            additional_args=["--disable-web-security"],
        )

        assert config.headless is False
        assert config.viewport == viewport
        assert config.user_agent == "test-agent"
        assert config.profile == "test-profile"
        assert config.additional_args == ["--disable-web-security"]

    def test_default_config(self):
        """Test default configuration values."""
        config = BrowserConfig()

        assert config.headless is True
        assert config.viewport is None
        assert config.user_agent is None
        assert config.profile is None
        assert config.additional_args == []


class TestCommands:
    """Test command models."""

    def test_base_command(self):
        """Test base command structure."""
        command = BaseCommand(
            command_type=CommandType.NAVIGATE, timeout=45.0, browser_id="test-browser"
        )

        assert command.command_type == CommandType.NAVIGATE
        assert command.timeout == 45.0
        assert command.browser_id == "test-browser"
        assert command.command_id is not None
        assert command.timestamp > 0

    def test_navigate_command(self):
        """Test navigate command."""
        command = NavigateCommand(
            url="https://example.com",
            wait_until=WaitCondition.DOM_CONTENT_LOADED,
            timeout=20.0,
        )

        assert command.command_type == CommandType.NAVIGATE
        assert command.url == "https://example.com"
        assert command.wait_until == WaitCondition.DOM_CONTENT_LOADED
        assert command.timeout == 20.0

    def test_find_element_command(self):
        """Test find element command."""
        selector = ElementSelector(type="css", value="button")
        command = FindElementCommand(selector=selector, multiple=True)

        assert command.command_type == CommandType.FIND_ELEMENT
        assert command.selector == selector
        assert command.multiple is True

    def test_click_command(self):
        """Test click command."""
        selector = ElementSelector(type="text", value="Submit")
        command = ClickCommand(
            selector=selector, button="right", scroll_into_view=False
        )

        assert command.command_type == CommandType.CLICK
        assert command.selector == selector
        assert command.button == "right"
        assert command.scroll_into_view is False

    def test_type_text_command(self):
        """Test type text command."""
        selector = ElementSelector(type="css", value="input[name='email']")
        command = TypeTextCommand(
            selector=selector, text="test@example.com", clear_first=False, delay=0.1
        )

        assert command.command_type == CommandType.TYPE_TEXT
        assert command.selector == selector
        assert command.text == "test@example.com"
        assert command.clear_first is False
        assert command.delay == 0.1

    def test_get_text_command(self):
        """Test get text command."""
        selector = ElementSelector(type="css", value="h1")
        command = GetTextCommand(selector=selector)

        assert command.command_type == CommandType.GET_TEXT
        assert command.selector == selector

    def test_take_screenshot_command(self):
        """Test take screenshot command."""
        selector = ElementSelector(type="css", value="div.content")
        command = TakeScreenshotCommand(
            selector=selector, format="jpeg", quality=80, full_page=True
        )

        assert command.command_type == CommandType.TAKE_SCREENSHOT
        assert command.selector == selector
        assert command.format == "jpeg"
        assert command.quality == 80
        assert command.full_page is True

    def test_execute_script_command(self):
        """Test execute script command."""
        command = ExecuteScriptCommand(
            script="return document.title", await_promise=True
        )

        assert command.command_type == CommandType.EXECUTE_SCRIPT
        assert command.script == "return document.title"
        assert command.await_promise is True

    def test_get_page_summary_command(self):
        """Test get page summary command."""
        command = GetPageSummaryCommand(
            include_text=False,
            include_links=True,
            include_images=True,
            include_forms=False,
            max_elements=100,
        )

        assert command.command_type == CommandType.GET_PAGE_SUMMARY
        assert command.include_text is False
        assert command.include_links is True
        assert command.include_images is True
        assert command.include_forms is False
        assert command.max_elements == 100

    def test_create_browser_command(self):
        """Test create browser command."""
        config = BrowserConfig(headless=False)
        command = CreateBrowserCommand(browser_id="new-browser", config=config)

        assert command.command_type == CommandType.CREATE_BROWSER
        assert command.browser_id == "new-browser"
        assert command.config == config


class TestResponses:
    """Test response models."""

    def test_base_response(self):
        """Test base response structure."""
        response = BaseResponse(
            command_id="test-cmd-123",
            status=StatusType.SUCCESS,
            execution_time=1.5,
            message="Operation completed",
        )

        assert response.command_id == "test-cmd-123"
        assert response.status == StatusType.SUCCESS
        assert response.execution_time == 1.5
        assert response.message == "Operation completed"
        assert response.timestamp > 0

    def test_screenshot_response(self):
        """Test screenshot response."""
        response = ScreenshotResponse(
            command_id="screenshot-123",
            status=StatusType.SUCCESS,
            execution_time=0.8,
            image_data="base64-encoded-data",
            image_format="png",
            dimensions={"width": 1280, "height": 720},
        )

        assert response.command_id == "screenshot-123"
        assert response.image_data == "base64-encoded-data"
        assert response.image_format == "png"
        assert response.dimensions == {"width": 1280, "height": 720}


class TestLLMMessage:
    """Test LLM message wrapper."""

    def test_command_message(self):
        """Test message with command."""
        command = NavigateCommand(url="https://example.com")
        message = LLMMessage(command=command, session_id="session-123")

        assert message.version == "1.0"
        assert message.command == command
        assert message.response is None
        assert message.session_id == "session-123"
        assert message.message_id is not None
        assert message.source == "llm"

    def test_response_message(self):
        """Test message with response."""
        response = BaseResponse(
            command_id="test", status=StatusType.SUCCESS, execution_time=1.0
        )
        message = LLMMessage(response=response, batch_id="batch-456")

        assert message.response == response
        assert message.command is None
        assert message.batch_id == "batch-456"

    def test_batch_message(self):
        """Test batch message."""
        command = GetTextCommand(selector=ElementSelector(type="css", value="h1"))
        message = LLMMessage(command=command, batch_id="batch-789", is_batch=True)

        assert message.is_batch is True
        assert message.batch_id == "batch-789"


class TestUtilityFunctions:
    """Test utility functions."""

    def test_create_command_from_dict(self):
        """Test creating command from dictionary."""
        data = {
            "command_type": "navigate",
            "url": "https://example.com",
            "wait_until": "load",
        }

        command = create_command_from_dict(data)

        assert isinstance(command, NavigateCommand)
        assert command.url == "https://example.com"
        assert command.wait_until == WaitCondition.LOAD

    def test_create_command_from_dict_unknown_type(self):
        """Test creating command with unknown type."""
        data = {
            "command_type": "navigate",  # This will create NavigateCommand
            "url": "https://example.com",
        }

        command = create_command_from_dict(data)
        assert isinstance(command, NavigateCommand)

    def test_serialize_response(self):
        """Test response serialization."""
        response = BaseResponse(
            command_id="test",
            status=StatusType.SUCCESS,
            execution_time=1.0,
            message="Test message",
        )

        json_str = serialize_response(response)
        parsed = json.loads(json_str)

        assert parsed["command_id"] == "test"
        assert parsed["status"] == "success"
        assert parsed["execution_time"] == 1.0
        assert parsed["message"] == "Test message"

    def test_deserialize_command(self):
        """Test command deserialization."""
        command = NavigateCommand(url="https://example.com")
        json_str = command.model_dump_json()

        deserialized = deserialize_command(json_str)

        assert isinstance(deserialized, NavigateCommand)
        assert deserialized.url == "https://example.com"

    def test_create_error_response(self):
        """Test error response creation."""
        response = create_error_response(
            "cmd-123", "Something went wrong", StatusType.ERROR, 2.5
        )

        assert response.command_id == "cmd-123"
        assert response.status == StatusType.ERROR
        assert response.message == "Something went wrong"
        assert response.execution_time == 2.5

    def test_validate_command_schema_valid(self):
        """Test valid command validation."""
        data = {"command_type": "navigate", "url": "https://example.com"}

        assert validate_command_schema(data) is True

    def test_validate_command_schema_invalid(self):
        """Test invalid command validation."""
        data = {"command_type": "invalid_type", "url": "https://example.com"}

        assert validate_command_schema(data) is False

    def test_export_json_schemas(self, tmp_path):
        """Test JSON schema export."""
        export_json_schemas(tmp_path)

        # Check that schema files were created
        assert (tmp_path / "command_types.json").exists()
        assert (tmp_path / "commands.json").exists()
        assert (tmp_path / "responses.json").exists()
        assert (tmp_path / "llm_message.json").exists()

        # Verify content
        with open(tmp_path / "command_types.json") as f:
            command_types = json.load(f)
            assert "navigate" in command_types
            assert "click" in command_types


class TestExampleCommands:
    """Test example command structures."""

    def test_example_navigate_command(self):
        """Test example navigate command."""
        from surfboard.protocols.llm_protocol import EXAMPLE_COMMANDS

        nav_example = EXAMPLE_COMMANDS["navigate"]
        command = create_command_from_dict(nav_example)

        assert isinstance(command, NavigateCommand)
        assert command.url == "https://example.com"

    def test_example_click_command(self):
        """Test example click command."""
        from surfboard.protocols.llm_protocol import EXAMPLE_COMMANDS

        click_example = EXAMPLE_COMMANDS["click"]
        command = create_command_from_dict(click_example)

        assert isinstance(command, ClickCommand)
        assert command.selector.value == "Submit"

    def test_all_examples_valid(self):
        """Test that all example commands are valid."""
        from surfboard.protocols.llm_protocol import EXAMPLE_COMMANDS

        for cmd_name, cmd_data in EXAMPLE_COMMANDS.items():
            assert validate_command_schema(cmd_data), f"Example {cmd_name} is invalid"


class TestPageInfo:
    """Test PageInfo model."""

    def test_page_info_creation(self):
        """Test PageInfo creation."""
        page_info = PageInfo(
            title="Test Page",
            url="https://example.com",
            domain="example.com",
            meta_description="A test page",
            headings=[{"level": "h1", "text": "Welcome"}],
            links=[{"url": "https://example.com/about", "text": "About"}],
            images=[{"src": "https://example.com/logo.png", "alt": "Logo"}],
            forms=[{"action": "/submit", "method": "POST", "fields": []}],
            text_content="Welcome to our test page",
            word_count=5,
        )

        assert page_info.title == "Test Page"
        assert page_info.url == "https://example.com"
        assert page_info.domain == "example.com"
        assert page_info.word_count == 5
        assert len(page_info.headings) == 1
        assert len(page_info.links) == 1
