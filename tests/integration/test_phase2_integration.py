"""
Phase 2 Integration Tests - Real Chrome Testing

These tests validate Phase 2 functionality with actual Chrome instances
and real web pages, not mocks.
"""

import asyncio
import json
import logging

import pytest
import websockets

from surfboard.automation.browser_manager import BrowserManager
from surfboard.communication.command_executor import CommandExecutor
from surfboard.communication.page_analyzer import PageAnalyzer
from surfboard.communication.websocket_server import WebSocketServer
from surfboard.protocols.llm_protocol import (
    ElementSelector,
    ElementSelectorType,
    FindElementCommand,
    GetPageSummaryCommand,
    LLMMessage,
    NavigateCommand,
)

logger = logging.getLogger(__name__)


@pytest.mark.integration
class TestPhase2Integration:
    """Integration tests for Phase 2 LLM Communication Bridge."""

    @pytest.fixture
    async def browser_manager(self):
        """Create and cleanup browser manager."""
        manager = BrowserManager(max_instances=1)
        yield manager
        await manager.close_all_instances()

    @pytest.fixture
    async def browser_session(self, browser_manager):
        """Create browser instance and session."""
        browser = await browser_manager.create_browser("test-browser", headless=True)
        session = await browser.get_cdp_session()
        yield session
        await browser_manager.close_all_instances()

    @pytest.mark.asyncio
    async def test_basic_navigation(self, browser_session):
        """Test basic page navigation with real Chrome."""

        # Navigate to a simple, reliable page
        await browser_session.page.navigate("https://httpbin.org/html")

        # Wait for page to load
        await asyncio.sleep(2)

        # Get page title to verify navigation worked
        title_script = "document.title"
        title = await browser_session.runtime.evaluate(title_script)

        assert title is not None
        logger.info(f"Successfully navigated to page with title: {title}")

    @pytest.mark.asyncio
    async def test_page_analyzer_real(self, browser_session):
        """Test page analyzer with real web page."""

        analyzer = PageAnalyzer()

        # Navigate to test page
        await browser_session.page.navigate("https://httpbin.org/forms/post")
        await asyncio.sleep(2)  # Wait for page load

        # Analyze page
        page_info = await analyzer.analyze_page(
            browser_session,
            include_text=True,
            include_links=True,
            include_forms=True,
            max_elements=20,
        )

        # Verify analysis results
        assert page_info.title is not None
        assert page_info.url == "https://httpbin.org/forms/post"
        assert page_info.domain == "httpbin.org"
        assert len(page_info.forms) > 0  # Should detect the form
        assert page_info.word_count > 0

        logger.info(f"Page analysis successful:")
        logger.info(f"  Title: {page_info.title}")
        logger.info(f"  Forms found: {len(page_info.forms)}")
        logger.info(f"  Links found: {len(page_info.links)}")
        logger.info(f"  Word count: {page_info.word_count}")

    @pytest.mark.asyncio
    async def test_command_executor_real(self, browser_session):
        """Test command executor with real Chrome."""

        browser_manager = BrowserManager(max_instances=1)
        executor = CommandExecutor(browser_manager)

        try:
            # Create browser first
            await browser_manager.create_browser("test-browser", headless=True)

            # Test navigation command
            nav_command = NavigateCommand(
                url="https://httpbin.org/html", browser_id="test-browser"
            )

            response = await executor.execute_command(nav_command, "test-session")

            assert response.status.value == "success"
            logger.info(
                f"Navigation command executed successfully in {response.execution_time:.3f}s"
            )

            # Test find element command
            find_command = FindElementCommand(
                selector=ElementSelector(type=ElementSelectorType.CSS, value="h1"),
                browser_id="test-browser",
            )

            response = await executor.execute_command(find_command, "test-session")

            assert response.status.value == "success"
            logger.info(f"Find element command executed successfully")

            # Test page summary command
            summary_command = GetPageSummaryCommand(
                include_text=True,
                include_links=True,
                include_forms=False,
                max_elements=10,
                browser_id="test-browser",
            )

            response = await executor.execute_command(summary_command, "test-session")

            assert response.status.value == "success"
            assert hasattr(response, "page_info")
            logger.info(f"Page summary command executed successfully")

        finally:
            await browser_manager.close_all_instances()

    @pytest.mark.asyncio
    async def test_websocket_server_real(self):
        """Test WebSocket server with real client connection."""

        server = WebSocketServer(host="localhost", port=9876, max_clients=1)
        server_task = asyncio.create_task(server.start())

        # Wait for server to start
        await asyncio.sleep(0.5)

        try:
            # Test client connection
            async with websockets.connect("ws://localhost:9876") as websocket:
                logger.info("Connected to WebSocket server")

                # Receive welcome message
                welcome_raw = await websocket.recv()
                welcome = json.loads(welcome_raw)

                assert welcome["type"] == "welcome"
                logger.info(f"Received welcome message: {welcome['message']}")

                # Send a simple navigation command
                nav_command = NavigateCommand(
                    url="https://httpbin.org/html", browser_id="demo-browser"
                )

                message = LLMMessage(command=nav_command, session_id="test-session")

                await websocket.send(message.model_dump_json())
                logger.info("Sent navigation command")

                # Receive response
                response_raw = await websocket.recv()
                response = json.loads(response_raw)

                assert "response" in response
                logger.info(f"Received response: {response['response']['status']}")

        except Exception as e:
            logger.error(f"WebSocket test error: {e}")
            raise
        finally:
            await server.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_error_handling_real(self, browser_session):
        """Test error handling with real scenarios."""

        browser_manager = BrowserManager(max_instances=1)
        executor = CommandExecutor(browser_manager)

        try:
            # Create browser
            await browser_manager.create_browser("test-browser", headless=True)

            # Test invalid URL navigation
            nav_command = NavigateCommand(
                url="http://definitely-not-a-real-domain-12345.fake",
                browser_id="test-browser",
                timeout=5.0,
            )

            response = await executor.execute_command(nav_command, "test-session")

            # Should handle error gracefully
            assert response.status.value in ["error", "timeout"]
            assert response.message is not None
            logger.info(f"Error handling test: {response.status} - {response.message}")

            # Test element not found
            find_command = FindElementCommand(
                selector=ElementSelector(
                    type=ElementSelectorType.CSS,
                    value="#definitely-not-an-element-12345",
                ),
                browser_id="test-browser",
            )

            response = await executor.execute_command(find_command, "test-session")

            # Should handle gracefully
            assert response.status.value in ["error", "not_found"]
            logger.info(f"Element not found test: {response.status}")

        finally:
            await browser_manager.close_all_instances()

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, browser_session):
        """Test concurrent operations don't interfere."""

        browser_manager = BrowserManager(max_instances=2)
        executor = CommandExecutor(browser_manager)

        try:
            # Create multiple browsers
            await browser_manager.create_browser("browser-1", headless=True)
            await browser_manager.create_browser("browser-2", headless=True)

            # Create concurrent navigation commands
            commands = [
                NavigateCommand(url="https://httpbin.org/html", browser_id="browser-1"),
                NavigateCommand(url="https://httpbin.org/json", browser_id="browser-2"),
            ]

            # Execute concurrently
            tasks = []
            for i, command in enumerate(commands):
                task = executor.execute_command(command, f"session-{i}")
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Check results
            successful_results = [r for r in results if not isinstance(r, Exception)]
            assert len(successful_results) >= 1  # At least one should succeed

            logger.info(
                f"Concurrent operations: {len(successful_results)}/{len(commands)} succeeded"
            )

        finally:
            await browser_manager.close_all_instances()

    @pytest.mark.asyncio
    async def test_phase2_end_to_end(self):
        """Complete end-to-end test of Phase 2 functionality."""

        logger.info("Starting Phase 2 end-to-end integration test")

        # Start WebSocket server
        server = WebSocketServer(host="localhost", port=9877, max_clients=2)
        server_task = asyncio.create_task(server.start())
        await asyncio.sleep(0.5)

        try:
            async with websockets.connect("ws://localhost:9877") as websocket:
                # Welcome message
                welcome_raw = await websocket.recv()
                welcome = json.loads(welcome_raw)
                assert welcome["type"] == "welcome"

                # Navigate to test page
                nav_command = NavigateCommand(
                    url="https://httpbin.org/forms/post", browser_id="e2e-browser"
                )

                nav_message = LLMMessage(command=nav_command, session_id="e2e-session")
                await websocket.send(nav_message.model_dump_json())

                nav_response_raw = await websocket.recv()
                nav_response = json.loads(nav_response_raw)
                assert nav_response["response"]["status"] == "success"

                # Analyze the page
                summary_command = GetPageSummaryCommand(
                    include_text=True,
                    include_links=True,
                    include_forms=True,
                    max_elements=20,
                    browser_id="e2e-browser",
                )

                summary_message = LLMMessage(
                    command=summary_command, session_id="e2e-session"
                )
                await websocket.send(summary_message.model_dump_json())

                summary_response_raw = await websocket.recv()
                summary_response = json.loads(summary_response_raw)
                assert summary_response["response"]["status"] == "success"

                page_info = summary_response["response"]["page_info"]
                assert page_info["title"] is not None
                assert len(page_info["forms"]) > 0

                logger.info("End-to-end test completed successfully!")
                logger.info(f"Page analyzed: {page_info['title']}")
                logger.info(f"Found {len(page_info['forms'])} forms")

        finally:
            await server.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass


@pytest.mark.slow
class TestPhase2Performance:
    """Performance tests for Phase 2 components."""

    @pytest.mark.asyncio
    async def test_navigation_latency(self):
        """Test navigation latency benchmarks."""

        browser_manager = BrowserManager(max_instances=1)
        executor = CommandExecutor(browser_manager)

        try:
            await browser_manager.create_browser("perf-browser", headless=True)

            # Measure navigation times
            nav_times = []

            for i in range(5):
                nav_command = NavigateCommand(
                    url="https://httpbin.org/html", browser_id="perf-browser"
                )

                start_time = asyncio.get_event_loop().time()
                response = await executor.execute_command(
                    nav_command, f"perf-session-{i}"
                )
                end_time = asyncio.get_event_loop().time()

                if response.status.value == "success":
                    nav_times.append(end_time - start_time)

            if nav_times:
                avg_time = sum(nav_times) / len(nav_times)
                logger.info(
                    f"Average navigation time: {avg_time:.3f}s ({len(nav_times)} samples)"
                )

                # Performance assertion
                assert avg_time < 10.0  # Should navigate within 10 seconds

        finally:
            await browser_manager.close_all_instances()
