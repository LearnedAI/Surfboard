"""
Phase 2 Demo: LLM Communication Bridge

This example demonstrates the LLM communication capabilities implemented in Phase 2:

- JSON command protocol with comprehensive validation
- WebSocket server for real-time LLM communication  
- Command execution pipeline with structured responses
- Page analysis and content summarization
- State management and session handling
"""

import asyncio
import json
import logging
from pathlib import Path

import websockets

from surfboard.communication.websocket_server import WebSocketServer
from surfboard.protocols.llm_protocol import (
    CommandType,
    ElementSelector,
    ElementSelectorType,
    LLMMessage,
    NavigateCommand,
    FindElementCommand,
    ClickCommand,
    TypeTextCommand,
    TakeScreenshotCommand,
    GetPageSummaryCommand,
    ExecuteScriptCommand,
    export_json_schemas
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demo_websocket_server():
    """Demonstrate WebSocket server with LLM communication."""
    logger.info("=== WebSocket Server Demo ===")
    
    # Start server in background
    server = WebSocketServer(host="localhost", port=8765, max_clients=5)
    server_task = asyncio.create_task(server.start())
    
    # Wait a moment for server to start
    await asyncio.sleep(1)
    
    try:
        # Test client connection
        async with websockets.connect("ws://localhost:8765") as websocket:
            logger.info("Connected to WebSocket server")
            
            # Receive welcome message
            welcome = await websocket.recv()
            welcome_data = json.loads(welcome)
            logger.info(f"Welcome message: {welcome_data['type']}")
            
            # Test navigation command
            nav_command = NavigateCommand(
                url="https://httpbin.org/forms/post",
                browser_id="demo-browser"
            )
            
            message = LLMMessage(
                command=nav_command,
                session_id="demo-session"
            )
            
            await websocket.send(message.model_dump_json())
            logger.info("Sent navigation command")
            
            # Receive response
            response = await websocket.recv()
            response_data = json.loads(response)
            logger.info(f"Navigation response: {response_data['response']['status']}")
            
            # Test element finding
            find_command = FindElementCommand(
                selector=ElementSelector(
                    type=ElementSelectorType.CSS,
                    value="input[name='custname']"
                ),
                browser_id="demo-browser"
            )
            
            find_message = LLMMessage(command=find_command)
            await websocket.send(find_message.model_dump_json())
            logger.info("Sent find element command")
            
            response = await websocket.recv()
            response_data = json.loads(response)
            logger.info(f"Find element response: {response_data['response']['element_found']}")
            
            # Test form interaction sequence
            commands = [
                TypeTextCommand(
                    selector=ElementSelector(type=ElementSelectorType.CSS, value="input[name='custname']"),
                    text="John Doe",
                    browser_id="demo-browser"
                ),
                TypeTextCommand(
                    selector=ElementSelector(type=ElementSelectorType.CSS, value="input[name='custtel']"),
                    text="555-1234",
                    browser_id="demo-browser"
                ),
                TypeTextCommand(
                    selector=ElementSelector(type=ElementSelectorType.CSS, value="input[name='custemail']"),
                    text="john@example.com",
                    browser_id="demo-browser"
                )
            ]
            
            for cmd in commands:
                cmd_message = LLMMessage(command=cmd)
                await websocket.send(cmd_message.model_dump_json())
                response = await websocket.recv()
                response_data = json.loads(response)
                logger.info(f"Form fill response: {response_data['response']['status']}")
            
            # Test screenshot
            screenshot_command = TakeScreenshotCommand(
                format="png",
                browser_id="demo-browser"
            )
            
            screenshot_message = LLMMessage(command=screenshot_command)
            await websocket.send(screenshot_message.model_dump_json())
            logger.info("Sent screenshot command")
            
            response = await websocket.recv()
            response_data = json.loads(response)
            if response_data['response']['status'] == 'success':
                logger.info("Screenshot captured successfully")
            
            # Test page summary
            summary_command = GetPageSummaryCommand(
                include_text=True,
                include_links=True,
                include_forms=True,
                max_elements=20,
                browser_id="demo-browser"
            )
            
            summary_message = LLMMessage(command=summary_command)
            await websocket.send(summary_message.model_dump_json())
            logger.info("Sent page summary command")
            
            response = await websocket.recv()
            response_data = json.loads(response)
            if response_data['response']['status'] == 'success':
                page_info = response_data['response']['page_info']
                logger.info(f"Page analysis: {page_info['title']} - {page_info['word_count']} words")
                logger.info(f"Found {len(page_info['forms'])} forms, {len(page_info['links'])} links")
            
    except Exception as e:
        logger.error(f"Client demo error: {e}")
    
    finally:
        # Stop server
        await server.stop()
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass
    
    logger.info("WebSocket server demo completed!")


async def demo_command_protocol():
    """Demonstrate the LLM command protocol and validation."""
    logger.info("=== Command Protocol Demo ===")
    
    # Create various command types
    commands = [
        NavigateCommand(
            url="https://example.com",
            timeout=15.0
        ),
        FindElementCommand(
            selector=ElementSelector(
                type=ElementSelectorType.TEXT,
                value="Click here"
            ),
            multiple=False
        ),
        ClickCommand(
            selector=ElementSelector(
                type=ElementSelectorType.CSS,
                value="button.submit"
            ),
            button="left",
            scroll_into_view=True
        ),
        ExecuteScriptCommand(
            script="return { title: document.title, url: window.location.href }",
            await_promise=False
        )
    ]
    
    logger.info(f"Created {len(commands)} test commands")
    
    # Test serialization and validation
    for i, command in enumerate(commands):
        # Serialize command
        json_data = command.model_dump_json()
        logger.info(f"Command {i+1} serialized: {len(json_data)} bytes")
        
        # Parse back
        parsed_data = json.loads(json_data)
        logger.info(f"Command type: {parsed_data['command_type']}")
        
        # Validate structure
        from surfboard.protocols.llm_protocol import validate_command_schema
        is_valid = validate_command_schema(parsed_data)
        logger.info(f"Command validation: {'PASS' if is_valid else 'FAIL'}")
    
    # Test LLM message wrapper
    message = LLMMessage(
        command=commands[0],
        session_id="test-session",
        context={"user": "demo", "task": "automation"}
    )
    
    message_json = message.model_dump_json()
    logger.info(f"LLM message size: {len(message_json)} bytes")
    
    parsed_message = json.loads(message_json)
    logger.info(f"Message ID: {parsed_message['message_id']}")
    logger.info(f"Session ID: {parsed_message['session_id']}")
    
    logger.info("Command protocol demo completed!")


async def demo_page_analysis():
    """Demonstrate page analysis capabilities."""
    logger.info("=== Page Analysis Demo ===")
    
    from surfboard.communication.page_analyzer import PageAnalyzer
    from surfboard.automation.browser_manager import managed_browser
    
    async with managed_browser(headless=True) as browser:
        session = await browser.get_cdp_session()
        analyzer = PageAnalyzer()
        
        # Navigate to test page
        await session.page.navigate("https://httpbin.org/forms/post")
        logger.info("Navigated to test page")
        
        # Analyze page structure
        page_info = await analyzer.analyze_page(
            session,
            include_text=True,
            include_links=True,
            include_forms=True,
            max_elements=30
        )
        
        logger.info(f"Page Analysis Results:")
        logger.info(f"  Title: {page_info.title}")
        logger.info(f"  URL: {page_info.url}")
        logger.info(f"  Domain: {page_info.domain}")
        logger.info(f"  Word count: {page_info.word_count}")
        logger.info(f"  Headings: {len(page_info.headings)}")
        logger.info(f"  Links: {len(page_info.links)}")
        logger.info(f"  Forms: {len(page_info.forms)}")
        
        # Analyze interactive elements
        interactive_elements = await analyzer.get_interactive_elements(session, limit=10)
        logger.info(f"Interactive elements found: {len(interactive_elements)}")
        
        for i, element in enumerate(interactive_elements[:5]):
            logger.info(f"  {i+1}. {element['tag']} - {element['text'][:50]}...")
        
        # Analyze form fields
        form_fields = await analyzer.get_form_fields(session)
        logger.info(f"Form fields found: {len(form_fields)}")
        
        for i, field in enumerate(form_fields[:3]):
            logger.info(f"  {i+1}. {field['type']} field: {field.get('name', 'unnamed')} - {field.get('placeholder', '')}")
    
    logger.info("Page analysis demo completed!")


async def demo_schema_export():
    """Demonstrate JSON schema export for external use."""
    logger.info("=== Schema Export Demo ===")
    
    # Export schemas to directory
    schemas_dir = Path("schemas")
    export_json_schemas(schemas_dir)
    
    # List generated files
    schema_files = list(schemas_dir.glob("*.json"))
    logger.info(f"Generated {len(schema_files)} schema files:")
    
    for schema_file in schema_files:
        file_size = schema_file.stat().st_size
        logger.info(f"  {schema_file.name}: {file_size} bytes")
    
    # Show sample command schema
    with open(schemas_dir / "commands.json") as f:
        commands_schema = json.load(f)
    
    logger.info("Available command types:")
    for cmd_name in commands_schema.keys():
        logger.info(f"  - {cmd_name}")
    
    logger.info("Schema export demo completed!")


async def demo_error_handling():
    """Demonstrate error handling in the communication system."""
    logger.info("=== Error Handling Demo ===")
    
    from surfboard.protocols.llm_protocol import create_error_response, StatusType
    from surfboard.communication.command_executor import CommandExecutor
    from surfboard.automation.browser_manager import BrowserManager
    
    # Create command executor
    browser_manager = BrowserManager(max_instances=2)
    executor = CommandExecutor(browser_manager)
    
    try:
        # Test invalid URL navigation
        invalid_nav = NavigateCommand(
            url="http://invalid-domain-12345.fake",
            timeout=5.0
        )
        
        response = await executor.execute_command(invalid_nav, "test-session")
        logger.info(f"Invalid navigation response: {response.status}")
        
        # Test element not found
        invalid_find = FindElementCommand(
            selector=ElementSelector(
                type=ElementSelectorType.CSS,
                value="#nonexistent-element-12345"
            ),
            timeout=2.0
        )
        
        # First navigate to a real page
        valid_nav = NavigateCommand(url="https://httpbin.org/html")
        await executor.execute_command(valid_nav, "test-session")
        
        response = await executor.execute_command(invalid_find, "test-session")
        logger.info(f"Element not found response: {response.status}")
        
        # Test error response creation
        error_response = create_error_response(
            "test-command-123",
            "Simulated error for demonstration",
            StatusType.ERROR,
            1.5
        )
        
        logger.info(f"Error response created: {error_response.message}")
        
    finally:
        await browser_manager.close_all_instances()
    
    logger.info("Error handling demo completed!")


async def main():
    """Run all Phase 2 demonstrations."""
    logger.info("Starting Surfboard Phase 2 Demonstrations")
    logger.info("=" * 60)
    
    try:
        # Run demos in sequence
        await demo_command_protocol()
        await asyncio.sleep(1)
        
        await demo_schema_export()
        await asyncio.sleep(1)
        
        await demo_page_analysis()
        await asyncio.sleep(1)
        
        await demo_error_handling()
        await asyncio.sleep(1)
        
        # WebSocket demo last (most complex)
        await demo_websocket_server()
        
        logger.info("=" * 60)
        logger.info("All Phase 2 demonstrations completed successfully!")
        
        # Show statistics
        schemas_dir = Path("schemas")
        if schemas_dir.exists():
            schema_count = len(list(schemas_dir.glob("*.json")))
            logger.info(f"Generated {schema_count} JSON schema files in 'schemas/' directory")
        
        logger.info("Phase 2 LLM Communication Bridge is fully operational!")
        
    except Exception as e:
        logger.error(f"Demo failed with error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())