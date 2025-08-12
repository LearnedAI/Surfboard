"""
LLM Communication Protocol.

This module defines the JSON schema and message formats for communication
between LLMs and the Surfboard browser automation system.
"""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Literal
from pathlib import Path

import json
from pydantic import BaseModel, Field, field_validator


class CommandType(str, Enum):
    """Available command types for LLM requests."""
    
    # Navigation commands
    NAVIGATE = "navigate"
    RELOAD = "reload"
    GO_BACK = "go_back"
    GO_FORWARD = "go_forward"
    
    # Element interaction
    FIND_ELEMENT = "find_element"
    FIND_ELEMENTS = "find_elements"
    CLICK = "click"
    TYPE_TEXT = "type_text"
    CLEAR_TEXT = "clear_text"
    
    # Information retrieval
    GET_TEXT = "get_text"
    GET_ATTRIBUTE = "get_attribute"
    GET_PAGE_TITLE = "get_page_title"
    GET_PAGE_URL = "get_page_url"
    GET_PAGE_SOURCE = "get_page_source"
    
    # Screenshots and visual
    TAKE_SCREENSHOT = "take_screenshot"
    GET_ELEMENT_SCREENSHOT = "get_element_screenshot"
    
    # JavaScript execution
    EXECUTE_SCRIPT = "execute_script"
    
    # Page analysis
    GET_PAGE_SUMMARY = "get_page_summary"
    ANALYZE_ELEMENTS = "analyze_elements"
    GET_FORM_DATA = "get_form_data"
    
    # Waiting and timing
    WAIT_FOR_ELEMENT = "wait_for_element"
    WAIT_FOR_PAGE_LOAD = "wait_for_page_load"
    SLEEP = "sleep"
    
    # Browser management
    CREATE_BROWSER = "create_browser"
    CLOSE_BROWSER = "close_browser"
    SWITCH_BROWSER = "switch_browser"
    LIST_BROWSERS = "list_browsers"


class StatusType(str, Enum):
    """Command execution status types."""
    
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    NOT_FOUND = "not_found"
    INVALID_INPUT = "invalid_input"


class ElementSelectorType(str, Enum):
    """Types of element selectors."""
    
    CSS = "css"
    XPATH = "xpath"
    TEXT = "text"
    PLACEHOLDER = "placeholder"
    ROLE = "role"
    ARIA_LABEL = "aria_label"
    TAG_NAME = "tag_name"


class WaitCondition(str, Enum):
    """Page load wait conditions."""
    
    LOAD = "load"
    DOM_CONTENT_LOADED = "domcontentloaded"
    NETWORK_IDLE = "networkidle"


# Base Models

class ElementSelector(BaseModel):
    """Element selector with multiple strategies."""
    
    type: ElementSelectorType = Field(..., description="Selector type")
    value: str = Field(..., description="Selector value")
    timeout: float = Field(10.0, description="Timeout in seconds")
    visible_only: bool = Field(True, description="Only find visible elements")


class Viewport(BaseModel):
    """Browser viewport configuration."""
    
    width: int = Field(1280, description="Viewport width")
    height: int = Field(720, description="Viewport height")
    device_scale_factor: float = Field(1.0, description="Device scale factor")
    mobile: bool = Field(False, description="Mobile emulation")


class BrowserConfig(BaseModel):
    """Browser instance configuration."""
    
    headless: bool = Field(True, description="Run in headless mode")
    viewport: Optional[Viewport] = Field(None, description="Viewport settings")
    user_agent: Optional[str] = Field(None, description="Custom user agent")
    profile: Optional[str] = Field(None, description="Browser profile name")
    additional_args: List[str] = Field(default_factory=list, description="Additional Chrome args")


# Command Models

class BaseCommand(BaseModel):
    """Base command structure."""
    
    command_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique command ID")
    command_type: CommandType = Field(..., description="Type of command")
    timestamp: float = Field(default_factory=time.time, description="Command timestamp")
    browser_id: Optional[str] = Field(None, description="Target browser instance")
    timeout: float = Field(30.0, description="Command timeout in seconds")


class NavigateCommand(BaseCommand):
    """Navigate to URL command."""
    
    command_type: Literal[CommandType.NAVIGATE] = Field(CommandType.NAVIGATE, description="Command type")
    url: str = Field(..., description="URL to navigate to")
    wait_until: WaitCondition = Field(WaitCondition.LOAD, description="Wait condition")


class FindElementCommand(BaseCommand):
    """Find element command."""
    
    command_type: Literal[CommandType.FIND_ELEMENT] = Field(CommandType.FIND_ELEMENT, description="Command type")
    selector: ElementSelector = Field(..., description="Element selector")
    multiple: bool = Field(False, description="Find multiple elements")


class ClickCommand(BaseCommand):
    """Click element command."""
    
    command_type: Literal[CommandType.CLICK] = Field(CommandType.CLICK, description="Command type")
    selector: ElementSelector = Field(..., description="Element selector")
    button: str = Field("left", description="Mouse button")
    scroll_into_view: bool = Field(True, description="Scroll element into view")


class TypeTextCommand(BaseCommand):
    """Type text command."""
    
    command_type: Literal[CommandType.TYPE_TEXT] = Field(CommandType.TYPE_TEXT, description="Command type")
    selector: ElementSelector = Field(..., description="Element selector")
    text: str = Field(..., description="Text to type")
    clear_first: bool = Field(True, description="Clear existing text first")
    delay: float = Field(0.05, description="Delay between characters")


class GetTextCommand(BaseCommand):
    """Get element text command."""
    
    command_type: Literal[CommandType.GET_TEXT] = Field(CommandType.GET_TEXT, description="Command type")
    selector: ElementSelector = Field(..., description="Element selector")


class TakeScreenshotCommand(BaseCommand):
    """Take screenshot command."""
    
    command_type: Literal[CommandType.TAKE_SCREENSHOT] = Field(CommandType.TAKE_SCREENSHOT, description="Command type")
    selector: Optional[ElementSelector] = Field(None, description="Element selector for clipping")
    format: str = Field("png", description="Image format")
    quality: int = Field(100, description="Image quality (for JPEG)")
    full_page: bool = Field(False, description="Capture full page")


class ExecuteScriptCommand(BaseCommand):
    """Execute JavaScript command."""
    
    command_type: Literal[CommandType.EXECUTE_SCRIPT] = Field(CommandType.EXECUTE_SCRIPT, description="Command type")
    script: str = Field(..., description="JavaScript code to execute")
    await_promise: bool = Field(False, description="Await promise resolution")


class GetPageSummaryCommand(BaseCommand):
    """Get page summary command."""
    
    command_type: Literal[CommandType.GET_PAGE_SUMMARY] = Field(CommandType.GET_PAGE_SUMMARY, description="Command type")
    include_text: bool = Field(True, description="Include text content")
    include_links: bool = Field(True, description="Include links")
    include_images: bool = Field(False, description="Include images")
    include_forms: bool = Field(True, description="Include forms")
    max_elements: int = Field(50, description="Maximum elements to analyze")


class CreateBrowserCommand(BaseCommand):
    """Create browser instance command."""
    
    command_type: Literal[CommandType.CREATE_BROWSER] = Field(CommandType.CREATE_BROWSER, description="Command type")
    browser_id: str = Field(..., description="Browser instance ID")
    config: BrowserConfig = Field(default_factory=BrowserConfig, description="Browser configuration")


# Response Models

class BaseResponse(BaseModel):
    """Base response structure."""
    
    command_id: str = Field(..., description="Original command ID")
    status: StatusType = Field(..., description="Execution status")
    timestamp: float = Field(default_factory=time.time, description="Response timestamp")
    execution_time: float = Field(..., description="Command execution time in seconds")
    message: Optional[str] = Field(None, description="Status message")


class ElementInfo(BaseModel):
    """Element information."""
    
    tag_name: str = Field(..., description="HTML tag name")
    text: Optional[str] = Field(None, description="Element text content")
    attributes: Dict[str, str] = Field(default_factory=dict, description="Element attributes")
    is_visible: bool = Field(..., description="Element visibility")
    bounding_box: Optional[Dict[str, float]] = Field(None, description="Element bounding box")


class FindElementResponse(BaseResponse):
    """Find element response."""
    
    element_found: bool = Field(..., description="Whether element was found")
    elements: List[ElementInfo] = Field(default_factory=list, description="Found elements")
    total_count: int = Field(0, description="Total elements found")


class TextResponse(BaseResponse):
    """Text content response."""
    
    text: Optional[str] = Field(None, description="Retrieved text")
    length: int = Field(0, description="Text length")


class ScreenshotResponse(BaseResponse):
    """Screenshot response."""
    
    image_data: Optional[str] = Field(None, description="Base64 encoded image data")
    image_path: Optional[str] = Field(None, description="Saved image file path")
    image_format: str = Field("png", description="Image format")
    dimensions: Dict[str, int] = Field(default_factory=dict, description="Image dimensions")


class ScriptResponse(BaseResponse):
    """JavaScript execution response."""
    
    result: Any = Field(None, description="Script execution result")
    console_logs: List[str] = Field(default_factory=list, description="Console output")


class PageInfo(BaseModel):
    """Page information summary."""
    
    title: str = Field(..., description="Page title")
    url: str = Field(..., description="Current URL")
    domain: str = Field(..., description="Page domain")
    meta_description: Optional[str] = Field(None, description="Meta description")
    headings: List[Dict[str, str]] = Field(default_factory=list, description="Page headings")
    links: List[Dict[str, str]] = Field(default_factory=list, description="Page links")
    images: List[Dict[str, str]] = Field(default_factory=list, description="Page images")
    forms: List[Dict[str, Any]] = Field(default_factory=list, description="Page forms")
    text_content: Optional[str] = Field(None, description="Main text content")
    word_count: int = Field(0, description="Approximate word count")


class PageSummaryResponse(BaseResponse):
    """Page summary response."""
    
    page_info: PageInfo = Field(..., description="Page information")
    elements_analyzed: int = Field(0, description="Number of elements analyzed")
    processing_time: float = Field(0.0, description="Summary processing time")


class BrowserInfo(BaseModel):
    """Browser instance information."""
    
    browser_id: str = Field(..., description="Browser instance ID")
    is_active: bool = Field(..., description="Whether browser is active")
    current_url: Optional[str] = Field(None, description="Current URL")
    title: Optional[str] = Field(None, description="Current page title")
    viewport: Optional[Viewport] = Field(None, description="Viewport configuration")
    created_at: float = Field(..., description="Creation timestamp")


class ListBrowsersResponse(BaseResponse):
    """List browsers response."""
    
    browsers: List[BrowserInfo] = Field(default_factory=list, description="Active browsers")
    total_count: int = Field(0, description="Total browser count")


# Message Wrapper

class LLMMessage(BaseModel):
    """Complete LLM message wrapper."""
    
    version: str = Field("1.0", description="Protocol version")
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Message ID")
    timestamp: float = Field(default_factory=time.time, description="Message timestamp")
    source: str = Field("llm", description="Message source")
    
    # Command or response payload
    command: Optional[BaseCommand] = Field(None, description="Command payload")
    response: Optional[BaseResponse] = Field(None, description="Response payload")
    
    # Batch processing
    batch_id: Optional[str] = Field(None, description="Batch processing ID")
    is_batch: bool = Field(False, description="Is part of batch")
    
    # Session management
    session_id: Optional[str] = Field(None, description="Session identifier")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")


# Utility Functions

def create_command_from_dict(data: Dict[str, Any]) -> BaseCommand:
    """Create command object from dictionary."""
    command_type = CommandType(data.get("command_type"))
    
    command_map = {
        CommandType.NAVIGATE: NavigateCommand,
        CommandType.FIND_ELEMENT: FindElementCommand,
        CommandType.CLICK: ClickCommand,
        CommandType.TYPE_TEXT: TypeTextCommand,
        CommandType.GET_TEXT: GetTextCommand,
        CommandType.TAKE_SCREENSHOT: TakeScreenshotCommand,
        CommandType.EXECUTE_SCRIPT: ExecuteScriptCommand,
        CommandType.GET_PAGE_SUMMARY: GetPageSummaryCommand,
        CommandType.CREATE_BROWSER: CreateBrowserCommand,
    }
    
    command_class = command_map.get(command_type, BaseCommand)
    return command_class(**data)


def serialize_response(response: BaseResponse) -> str:
    """Serialize response to JSON string."""
    return response.model_dump_json(exclude_none=True)


def deserialize_command(json_str: str) -> BaseCommand:
    """Deserialize JSON string to command object."""
    data = json.loads(json_str)
    return create_command_from_dict(data)


def create_error_response(
    command_id: str,
    error_message: str,
    status: StatusType = StatusType.ERROR,
    execution_time: float = 0.0
) -> BaseResponse:
    """Create error response."""
    return BaseResponse(
        command_id=command_id,
        status=status,
        execution_time=execution_time,
        message=error_message
    )


def validate_command_schema(data: Dict[str, Any]) -> bool:
    """Validate command against schema."""
    try:
        create_command_from_dict(data)
        return True
    except Exception:
        return False


# Schema Export

def export_json_schemas(output_dir: Path) -> None:
    """Export all schemas to JSON files for external use."""
    schemas = {
        "command_types": {cmd.value: cmd.value for cmd in CommandType},
        "status_types": {status.value: status.value for status in StatusType},
        "element_selector": ElementSelector.model_json_schema(),
        "viewport": Viewport.model_json_schema(),
        "browser_config": BrowserConfig.model_json_schema(),
        "commands": {
            "base_command": BaseCommand.model_json_schema(),
            "navigate": NavigateCommand.model_json_schema(),
            "find_element": FindElementCommand.model_json_schema(),
            "click": ClickCommand.model_json_schema(),
            "type_text": TypeTextCommand.model_json_schema(),
            "get_text": GetTextCommand.model_json_schema(),
            "take_screenshot": TakeScreenshotCommand.model_json_schema(),
            "execute_script": ExecuteScriptCommand.model_json_schema(),
            "get_page_summary": GetPageSummaryCommand.model_json_schema(),
            "create_browser": CreateBrowserCommand.model_json_schema(),
        },
        "responses": {
            "base_response": BaseResponse.model_json_schema(),
            "find_element": FindElementResponse.model_json_schema(),
            "text": TextResponse.model_json_schema(),
            "screenshot": ScreenshotResponse.model_json_schema(),
            "script": ScriptResponse.model_json_schema(),
            "page_summary": PageSummaryResponse.model_json_schema(),
            "list_browsers": ListBrowsersResponse.model_json_schema(),
        },
        "llm_message": LLMMessage.model_json_schema(),
    }
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for schema_name, schema_data in schemas.items():
        schema_file = output_dir / f"{schema_name}.json"
        with open(schema_file, 'w') as f:
            json.dump(schema_data, f, indent=2, ensure_ascii=False)


# Example Usage and Documentation

EXAMPLE_COMMANDS = {
    "navigate": {
        "command_type": "navigate",
        "url": "https://example.com",
        "wait_until": "load",
        "timeout": 30.0
    },
    "find_element": {
        "command_type": "find_element",
        "selector": {
            "type": "css",
            "value": "button.submit",
            "timeout": 10.0
        }
    },
    "click": {
        "command_type": "click",
        "selector": {
            "type": "text",
            "value": "Submit"
        }
    },
    "type_text": {
        "command_type": "type_text",
        "selector": {
            "type": "css",
            "value": "input[name='email']"
        },
        "text": "user@example.com",
        "clear_first": True
    },
    "get_page_summary": {
        "command_type": "get_page_summary",
        "include_text": True,
        "include_links": True,
        "include_forms": True,
        "max_elements": 50
    }
}