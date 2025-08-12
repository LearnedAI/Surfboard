"""
Tests for Phase 3: Advanced Automation features.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from surfboard.automation.advanced_interactions import (
    AdvancedInteractionEngine,
    GestureDirection,
    InteractionPoint,
    InteractionType,
)
from surfboard.automation.element_selector import (
    AdvancedElementSelector,
    SelectionResult,
    SelectionStrategy,
)
from surfboard.automation.error_recovery import (
    ErrorContext,
    ErrorRecoverySystem,
    ErrorType,
    RecoveryStrategy,
)
from surfboard.automation.performance_optimizer import (
    OptimizationLevel,
    OptimizationSettings,
    PerformanceOptimizer,
    ResourceMetrics,
)
from surfboard.automation.smart_waiter import SmartWaiter, WaitResult, WaitType
from surfboard.protocols.llm_protocol import (
    BaseCommand,
    CommandType,
    ElementSelector,
    ElementSelectorType,
)


class TestAdvancedElementSelector:
    """Test advanced element selection strategies."""

    @pytest.fixture
    def selector(self):
        """Create selector instance."""
        return AdvancedElementSelector()

    @pytest.fixture
    def mock_session(self):
        """Create mock CDP session."""
        session = AsyncMock()
        session.runtime.evaluate = AsyncMock()
        return session

    @pytest.fixture
    def element_selector_css(self):
        """Create CSS element selector."""
        return ElementSelector(
            type=ElementSelectorType.CSS, value="button.submit", timeout=10.0
        )

    @pytest.fixture
    def element_selector_text(self):
        """Create text element selector."""
        return ElementSelector(
            type=ElementSelectorType.TEXT, value="Click me", timeout=10.0
        )

    @pytest.mark.asyncio
    async def test_exact_match_strategy_success(
        self, selector, mock_session, element_selector_css
    ):
        """Test exact match strategy with successful result."""

        # Mock successful element found
        mock_session.runtime.evaluate.return_value = {
            "elementId": "test-button",
            "tagName": "button",
            "text": "Submit",
            "attributes": {"class": "submit", "type": "button"},
            "boundingBox": {"x": 100, "y": 200, "width": 80, "height": 30},
            "isVisible": True,
        }

        result = await selector.find_element(mock_session, element_selector_css)

        assert result is not None
        assert result.strategy == SelectionStrategy.EXACT_MATCH
        assert result.confidence == 1.0
        assert result.element_id == "test-button"
        assert result.text_content == "Submit"

    @pytest.mark.asyncio
    async def test_fuzzy_text_strategy(
        self, selector, mock_session, element_selector_text
    ):
        """Test fuzzy text matching strategy."""

        # Test the fuzzy text strategy directly
        mock_session.runtime.evaluate.return_value = {
            "elementId": "fuzzy-match",
            "tagName": "button",
            "text": "Click me now",
            "attributes": {"class": "action-btn"},
            "boundingBox": {"x": 150, "y": 250, "width": 100, "height": 35},
            "score": 0.85,
        }

        # Call the fuzzy text strategy directly
        result = await selector._fuzzy_text_strategy(
            mock_session, element_selector_text
        )

        assert result is not None
        assert result.strategy == SelectionStrategy.FUZZY_TEXT
        assert result.confidence == 0.85
        assert "Click me now" in result.text_content

    @pytest.mark.asyncio
    async def test_context_aware_strategy(
        self, selector, mock_session, element_selector_css
    ):
        """Test context-aware selection strategy."""

        context = {
            "nearby_text": "form submission",
            "form_context": "login form",
            "section_context": "main content",
        }

        mock_session.runtime.evaluate.return_value = {
            "elementId": "context-button",
            "tagName": "button",
            "text": "Submit",
            "attributes": {"class": "submit primary"},
            "boundingBox": {"x": 200, "y": 300, "width": 90, "height": 40},
            "score": 0.9,
        }

        result = await selector.find_element(
            mock_session, element_selector_css, context=context
        )

        assert result is not None
        assert result.confidence >= 0.7

    @pytest.mark.asyncio
    async def test_multiple_elements_selection(
        self, selector, mock_session, element_selector_css
    ):
        """Test finding multiple elements."""

        # Mock multiple elements found
        mock_session.runtime.evaluate.return_value = [
            {
                "elementId": "button1",
                "tagName": "button",
                "text": "Submit 1",
                "attributes": {"class": "submit"},
                "boundingBox": {"x": 100, "y": 200, "width": 80, "height": 30},
                "isVisible": True,
            },
            {
                "elementId": "button2",
                "tagName": "button",
                "text": "Submit 2",
                "attributes": {"class": "submit"},
                "boundingBox": {"x": 100, "y": 250, "width": 80, "height": 30},
                "isVisible": True,
            },
        ]

        results = await selector.find_multiple_elements(
            mock_session, element_selector_css, limit=5
        )

        assert len(results) == 2
        assert all(
            result.strategy == SelectionStrategy.EXACT_MATCH for result in results
        )
        assert results[0].element_id == "button1"
        assert results[1].element_id == "button2"

    @pytest.mark.asyncio
    async def test_adaptive_timeout(self, selector, mock_session, element_selector_css):
        """Test adaptive timeout calculation."""

        # Mock page complexity data
        mock_session.runtime.evaluate.return_value = {
            "elementCount": 1500,  # High complexity
            "scriptCount": 15,
            "imageCount": 25,
            "readyState": "complete",
        }

        # This would test the internal timeout calculation
        # For now, just verify the selector can handle adaptive timeout
        result = await selector.find_element(
            mock_session, element_selector_css, adaptive_timeout=True
        )

        # Should still work even with complex page
        # (Result depends on mock return value)

    @pytest.mark.asyncio
    async def test_element_not_found(
        self, selector, mock_session, element_selector_css
    ):
        """Test handling when element is not found."""

        # Mock no element found
        mock_session.runtime.evaluate.return_value = None

        result = await selector.find_element(mock_session, element_selector_css)

        assert result is None


class TestSmartWaiter:
    """Test smart waiting mechanisms."""

    @pytest.fixture
    def waiter(self):
        """Create waiter instance."""
        return SmartWaiter()

    @pytest.fixture
    def mock_session(self):
        """Create mock CDP session."""
        session = AsyncMock()
        session.runtime.evaluate = AsyncMock()
        session.network.enable = AsyncMock()
        session.profiler.enable = AsyncMock()
        session.profiler.disable = AsyncMock()
        return session

    @pytest.fixture
    def element_selector(self):
        """Create element selector."""
        return ElementSelector(
            type=ElementSelectorType.CSS, value="#test-element", timeout=5.0
        )

    @pytest.mark.asyncio
    async def test_wait_for_element_visible_success(
        self, waiter, mock_session, element_selector
    ):
        """Test waiting for element to become visible."""

        # Mock element found and visible immediately
        mock_session.runtime.evaluate.return_value = {
            "visible": True,
            "found": True,
            "rect": {"x": 100, "y": 200, "width": 80, "height": 30},
            "style": {"display": "block", "visibility": "visible", "opacity": "1"},
        }

        # Test the internal method directly
        condition_met, info = await waiter._check_element_visible(
            mock_session, element_selector
        )

        assert condition_met is True
        assert info["visible"] is True
        assert info["found"] is True

    @pytest.mark.asyncio
    async def test_wait_for_element_clickable(
        self, waiter, mock_session, element_selector
    ):
        """Test waiting for element to become clickable."""

        # Mock element visible first, then clickable
        mock_session.runtime.evaluate.side_effect = [
            # First call for visibility check
            {
                "visible": True,
                "found": True,
                "rect": {"x": 100, "y": 200, "width": 80, "height": 30},
                "style": {"display": "block", "visibility": "visible", "opacity": "1"},
            },
            # Second call for clickability check
            {
                "clickable": True,
                "disabled": False,
                "covered": False,
                "elementAtPoint": "BUTTON",
            },
        ]

        # Test the internal method directly
        condition_met, info = await waiter._check_element_clickable(
            mock_session, element_selector
        )

        assert condition_met is True
        assert info["clickable"] is True

    @pytest.mark.asyncio
    async def test_wait_for_page_load(self, waiter, mock_session):
        """Test waiting for page load completion."""

        # Mock page loaded
        mock_session.runtime.evaluate.return_value = {
            "readyState": "complete",
            "pendingImages": 0,
            "pendingScripts": 0,
        }

        result = await waiter.wait_for_page_load(mock_session, timeout=3.0)

        assert result.success
        assert result.condition_met == str(WaitType.PAGE_LOAD)

    @pytest.mark.asyncio
    async def test_wait_timeout(self, waiter, mock_session, element_selector):
        """Test wait operation timeout."""

        # Mock element never found
        mock_session.runtime.evaluate.return_value = {"visible": False, "found": False}

        result = await waiter.wait_for_element(
            mock_session, element_selector, WaitType.ELEMENT_VISIBLE, timeout=0.5
        )

        assert not result.success
        assert result.timeout_occurred
        assert result.condition_met == "timeout"

    @pytest.mark.asyncio
    async def test_network_idle_wait(self, waiter, mock_session):
        """Test waiting for network idle state."""

        result = await waiter.wait_for_network_idle(
            mock_session, idle_time=1.0, timeout=2.0
        )

        # Network idle detection is simplified in tests
        assert result.condition_met == "network_idle"

    @pytest.mark.asyncio
    async def test_adaptive_timeout_calculation(self, waiter, mock_session):
        """Test adaptive timeout calculation."""

        # Mock complex page
        mock_session.runtime.evaluate.return_value = {
            "elementCount": 2000,
            "scriptCount": 20,
            "imageCount": 50,
            "readyState": "complete",
        }

        # Test that adaptive timeout works (internal method)
        adaptive_timeout = await waiter._calculate_adaptive_timeout(
            mock_session, WaitType.ELEMENT_VISIBLE, 10.0
        )

        # Should increase timeout for complex page
        assert adaptive_timeout >= 10.0


class TestErrorRecoverySystem:
    """Test error recovery and retry systems."""

    @pytest.fixture
    def recovery_system(self):
        """Create recovery system instance."""
        return ErrorRecoverySystem()

    @pytest.fixture
    def mock_session(self):
        """Create mock CDP session."""
        session = AsyncMock()
        session.runtime.evaluate = AsyncMock()
        session.page.navigate = AsyncMock()
        session.page.go_back = AsyncMock()
        return session

    @pytest.fixture
    def test_command(self):
        """Create test command."""
        return BaseCommand(command_type=CommandType.NAVIGATE, browser_id="test-browser")

    def test_error_classification(self, recovery_system):
        """Test error type classification."""

        # Test element not found error
        error1 = Exception("element not found")
        error_type1 = recovery_system._classify_error(error1)
        assert error_type1 == ErrorType.ELEMENT_NOT_FOUND

        # Test timeout error
        error2 = Exception("timeout occurred")
        error_type2 = recovery_system._classify_error(error2)
        assert error_type2 == ErrorType.TIMEOUT_ERROR

        # Test network error
        error3 = Exception("network connection failed")
        error_type3 = recovery_system._classify_error(error3)
        assert error_type3 == ErrorType.NETWORK_ERROR

        # Test unknown error
        error4 = Exception("something unexpected")
        error_type4 = recovery_system._classify_error(error4)
        assert error_type4 == ErrorType.UNKNOWN_ERROR

    @pytest.mark.asyncio
    async def test_immediate_retry_strategy(
        self, recovery_system, mock_session, test_command
    ):
        """Test immediate retry recovery strategy."""

        error = Exception("temporary failure")

        result = await recovery_system.handle_error(
            mock_session, error, test_command, attempt_count=1
        )

        # Should attempt recovery
        assert result.attempts_made == 1

    @pytest.mark.asyncio
    async def test_exponential_backoff_strategy(
        self, recovery_system, mock_session, test_command
    ):
        """Test exponential backoff strategy."""

        error_context = ErrorContext(
            error_type=ErrorType.NETWORK_ERROR,
            error_message="network timeout",
            command=test_command,
            attempt_count=2,
            timestamp=1234567890.0,
        )

        # Test backoff strategy
        success, result = await recovery_system._apply_recovery_strategy(
            mock_session, RecoveryStrategy.EXPONENTIAL_BACKOFF, error_context
        )

        assert success  # Backoff always succeeds (just waits)
        assert result == "backoff_complete"

    @pytest.mark.asyncio
    async def test_page_refresh_strategy(
        self, recovery_system, mock_session, test_command
    ):
        """Test page refresh recovery strategy."""

        error_context = ErrorContext(
            error_type=ErrorType.ELEMENT_NOT_FOUND,
            error_message="element not found",
            command=test_command,
            attempt_count=1,
            timestamp=1234567890.0,
            page_state={"url": "https://example.com"},
        )

        success, result = await recovery_system._apply_recovery_strategy(
            mock_session, RecoveryStrategy.PAGE_REFRESH, error_context
        )

        assert success
        assert result == "page_refreshed"
        mock_session.page.navigate.assert_called_once_with("https://example.com")

    @pytest.mark.asyncio
    async def test_retry_with_recovery(
        self, recovery_system, mock_session, test_command
    ):
        """Test retry operation with recovery."""

        # Mock operation that fails first, then succeeds
        call_count = 0

        async def mock_operation():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("first attempt fails")
            return "success"

        success, result = await recovery_system.retry_with_recovery(
            mock_session, mock_operation, test_command, max_attempts=2
        )

        assert success
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_graceful_degradation(
        self, recovery_system, mock_session, test_command
    ):
        """Test graceful degradation fallback."""

        error_context = ErrorContext(
            error_type=ErrorType.UNKNOWN_ERROR,
            error_message="unrecoverable error",
            command=test_command,
            attempt_count=3,
            timestamp=1234567890.0,
        )

        success, result = await recovery_system._graceful_degradation(
            mock_session, error_context
        )

        assert success
        assert result["status"] == "degraded"
        assert result["original_command"] == test_command.command_type

    def test_recovery_pattern_learning(self, recovery_system):
        """Test recovery pattern learning."""

        # Record successful recovery
        recovery_system._record_successful_recovery(
            ErrorContext(
                error_type=ErrorType.ELEMENT_NOT_FOUND,
                error_message="test",
                command=BaseCommand(command_type=CommandType.CLICK),
                attempt_count=1,
                timestamp=1234567890.0,
            ),
            RecoveryStrategy.ELEMENT_WAIT_RETRY,
            1.5,
        )

        # Check that pattern was recorded
        assert len(recovery_system.error_history) == 1
        assert (
            recovery_system.error_history[0]["strategy"]
            == RecoveryStrategy.ELEMENT_WAIT_RETRY
        )
        assert recovery_system.error_history[0]["success"] == True


class TestPerformanceOptimizer:
    """Test performance optimization and resource management."""

    @pytest.fixture
    def optimizer_settings(self):
        """Create optimization settings."""
        return OptimizationSettings(
            level=OptimizationLevel.MODERATE,
            max_memory_mb=1024,
            max_cpu_percent=70.0,
            enable_resource_cleanup=True,
        )

    @pytest.fixture
    def optimizer(self, optimizer_settings):
        """Create performance optimizer."""
        return PerformanceOptimizer(optimizer_settings)

    @pytest.fixture
    def mock_session(self):
        """Create mock CDP session."""
        session = AsyncMock()
        session.runtime.evaluate = AsyncMock()
        session.performance.enable = AsyncMock()
        session.network.set_cache_disabled = AsyncMock()
        session.page.set_resource_response_interception = AsyncMock()
        session.profiler.enable = AsyncMock()
        session.profiler.disable = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_session_registration(self, optimizer, mock_session):
        """Test session registration for optimization."""

        await optimizer.register_session(mock_session, "test-session")

        # Check session was added
        assert len(optimizer.active_sessions) == 1
        session_ids = [sid for _, sid in optimizer.active_sessions]
        assert "test-session" in session_ids

    @pytest.mark.asyncio
    async def test_session_unregistration(self, optimizer, mock_session):
        """Test session unregistration."""

        # Register first
        await optimizer.register_session(mock_session, "test-session")
        assert len(optimizer.active_sessions) == 1

        # Then unregister
        await optimizer.unregister_session("test-session")
        assert len(optimizer.active_sessions) == 0

    @pytest.mark.asyncio
    async def test_page_load_optimization(self, optimizer, mock_session):
        """Test page load optimization."""

        # Mock performance metrics
        mock_session.runtime.evaluate.return_value = {
            "loadTime": 1500,
            "domContentLoaded": 800,
            "resourceCount": 25,
            "totalResourceSize": 1024000,
            "largestResource": 500000,
        }

        result = await optimizer.optimize_page_load(
            mock_session, "https://example.com", "test-session"
        )

        assert result["url"] == "https://example.com"
        assert result["session_id"] == "test-session"
        assert "load_metrics" in result
        assert "total_optimization_time" in result

    @pytest.mark.asyncio
    async def test_script_optimization(self, optimizer, mock_session):
        """Test JavaScript execution optimization."""

        script = """
        // This is a test script
        function calculate() {
            let result = 0;
            for (let i = 0; i < 1000; i++) {
                result += i;
            }
            return result;
        }
        calculate();
        """

        mock_session.runtime.evaluate.return_value = 499500  # Expected result

        result = await optimizer.optimize_script_execution(
            mock_session, script, "test-session"
        )

        assert result["optimized"] == True
        assert result["result"] == 499500
        assert "execution_time" in result
        assert "optimized_script_length" in result

    @pytest.mark.asyncio
    @patch("psutil.virtual_memory")
    @patch("psutil.cpu_percent")
    @patch("psutil.net_connections")
    async def test_performance_metrics_collection(
        self,
        mock_net_connections,
        mock_cpu_percent,
        mock_virtual_memory,
        optimizer,
        mock_session,
    ):
        """Test performance metrics collection."""

        # Mock system metrics
        mock_memory = MagicMock()
        mock_memory.used = 1024 * 1024 * 512  # 512 MB
        mock_virtual_memory.return_value = mock_memory
        mock_cpu_percent.return_value = 45.0
        mock_net_connections.return_value = [1, 2, 3]  # 3 connections

        # Mock DOM element count
        mock_session.runtime.evaluate.return_value = 150

        # Register session for metrics
        await optimizer.register_session(mock_session, "test-session")

        metrics = await optimizer.get_performance_metrics()

        assert isinstance(metrics, ResourceMetrics)
        assert metrics.memory_usage_mb == 512.0
        assert metrics.cpu_percent == 45.0
        assert metrics.network_active_connections == 3
        assert metrics.dom_element_count == 150
        assert metrics.active_browser_instances == 1

    @pytest.mark.asyncio
    async def test_resource_cleanup(self, optimizer, mock_session):
        """Test resource cleanup functionality."""

        # Add some data to clean up
        optimizer.optimization_cache["test-url"] = {"data": "test"}
        optimizer.metrics_history = [MagicMock() for _ in range(100)]

        # Register session
        await optimizer.register_session(mock_session, "test-session")

        # Mock DOM cleanup
        mock_session.runtime.evaluate.return_value = 15  # 15 nodes removed

        result = await optimizer.cleanup_resources()

        assert "cache_entries_cleared" in result
        assert "sessions_cleaned" in result
        assert "dom_nodes_removed" in result
        assert result["sessions_cleaned"] == 1

    def test_optimization_recommendations(self, optimizer):
        """Test optimization recommendations."""

        # Add some metrics to history
        high_memory_metrics = ResourceMetrics(
            timestamp=1234567890.0,
            memory_usage_mb=900.0,  # High memory usage
            cpu_percent=30.0,
            network_active_connections=5,
            dom_element_count=1000,
            active_browser_instances=2,
        )

        optimizer.metrics_history = [high_memory_metrics] * 10

        recommendations = optimizer.get_optimization_recommendations()

        assert "memory" in recommendations
        assert "aggressive optimization" in recommendations["memory"]

    def test_different_optimization_levels(self):
        """Test different optimization level configurations."""

        conservative = OptimizationSettings(level=OptimizationLevel.CONSERVATIVE)
        conservative_optimizer = PerformanceOptimizer(conservative)

        aggressive = OptimizationSettings(level=OptimizationLevel.AGGRESSIVE)
        aggressive_optimizer = PerformanceOptimizer(aggressive)

        maximum = OptimizationSettings(level=OptimizationLevel.MAXIMUM)
        maximum_optimizer = PerformanceOptimizer(maximum)

        # Check that different levels have different strategies
        conservative_strategy = conservative_optimizer.optimization_strategies[
            OptimizationLevel.CONSERVATIVE
        ]
        aggressive_strategy = aggressive_optimizer.optimization_strategies[
            OptimizationLevel.AGGRESSIVE
        ]
        maximum_strategy = maximum_optimizer.optimization_strategies[
            OptimizationLevel.MAXIMUM
        ]

        # More aggressive levels should have shorter cleanup intervals
        assert (
            conservative_strategy["dom_cleanup_interval"]
            > aggressive_strategy["dom_cleanup_interval"]
        )
        assert (
            aggressive_strategy["dom_cleanup_interval"]
            > maximum_strategy["dom_cleanup_interval"]
        )


class TestAdvancedInteractionEngine:
    """Test advanced interaction patterns."""

    @pytest.fixture
    def interaction_engine(self):
        """Create interaction engine instance."""
        return AdvancedInteractionEngine()

    @pytest.fixture
    def mock_session(self):
        """Create mock CDP session."""
        session = AsyncMock()
        session.runtime.evaluate = AsyncMock()
        session.input.dispatch_mouse_event = AsyncMock()
        session.input.dispatch_touch_event = AsyncMock()
        return session

    @pytest.fixture
    def element_selector(self):
        """Create element selector."""
        return ElementSelector(
            type=ElementSelectorType.CSS, value="button#test", timeout=5.0
        )

    @pytest.mark.asyncio
    async def test_hover_element(
        self, interaction_engine, mock_session, element_selector
    ):
        """Test hover interaction."""

        # Mock element bounds
        mock_session.runtime.evaluate.side_effect = [
            # Element bounds call
            {
                "found": True,
                "bounds": {"x": 100, "y": 200, "width": 80, "height": 30},
                "tagName": "button",
                "visible": True,
                "clickable": True,
            },
            # Before state capture
            {
                "className": "btn",
                "textContent": "Click me",
                "style": {"backgroundColor": "blue"},
            },
            # After state capture
            {
                "className": "btn hover",
                "textContent": "Click me",
                "style": {"backgroundColor": "lightblue"},
            },
        ]

        result = await interaction_engine.hover_element(
            mock_session, element_selector, duration=0.5
        )

        assert result.success
        assert result.interaction_type == InteractionType.HOVER
        assert "style" in result.state_changes  # Background color changed

        # Verify mouse event was dispatched
        mock_session.input.dispatch_mouse_event.assert_called_once_with(
            type="mouseMoved",
            x=140.0,  # center x: 100 + 80/2
            y=215.0,  # center y: 200 + 30/2
        )

    @pytest.mark.asyncio
    async def test_drag_and_drop(self, interaction_engine, mock_session):
        """Test drag and drop interaction."""

        source_selector = ElementSelector(type=ElementSelectorType.CSS, value="#source")
        target_selector = ElementSelector(type=ElementSelectorType.CSS, value="#target")

        # Mock source and target element bounds
        mock_session.runtime.evaluate.side_effect = [
            # Source element bounds
            {"found": True, "bounds": {"x": 100, "y": 200, "width": 50, "height": 50}},
            # Target element bounds
            {"found": True, "bounds": {"x": 300, "y": 400, "width": 50, "height": 50}},
            # Page state before
            {"url": "test.html", "elementCount": 100},
            # Page state after
            {"url": "test.html", "elementCount": 100},
        ]

        result = await interaction_engine.drag_and_drop(
            mock_session, source_selector, target_selector, drag_duration=0.5
        )

        assert result.success
        assert result.interaction_type == InteractionType.DRAG_DROP

        # Verify mouse events were called (press, moves, release)
        assert mock_session.input.dispatch_mouse_event.call_count >= 3

        # Check that it started with mousePressed and ended with mouseReleased
        calls = mock_session.input.dispatch_mouse_event.call_args_list
        assert calls[0][1]["type"] == "mousePressed"
        assert calls[-1][1]["type"] == "mouseReleased"

    @pytest.mark.asyncio
    async def test_scroll_into_view(
        self, interaction_engine, mock_session, element_selector
    ):
        """Test scroll into view interaction."""

        # Mock scroll result
        mock_session.runtime.evaluate.return_value = {
            "success": True,
            "initialScroll": {"top": 0, "left": 0},
            "finalScroll": {"top": 500, "left": 0},
            "elementRect": {"x": 100, "y": 200, "width": 80, "height": 30},
            "scrollDistance": {"vertical": 500, "horizontal": 0},
        }

        result = await interaction_engine.scroll_into_view(
            mock_session, element_selector, behavior="smooth"
        )

        assert result.success
        assert result.interaction_type == InteractionType.SCROLL_INTO_VIEW
        assert result.element_info["scrollDistance"]["vertical"] == 500

    @pytest.mark.asyncio
    async def test_swipe_gesture(self, interaction_engine, mock_session):
        """Test swipe gesture."""

        start_point = InteractionPoint(x=200, y=300, pressure=1.0)

        result = await interaction_engine.perform_gesture(
            mock_session,
            "swipe",
            start_point,
            direction=GestureDirection.RIGHT,
            distance=100,
            duration=0.5,
        )

        assert result.success
        assert result.interaction_type == InteractionType.SWIPE
        assert result.element_info["direction"] == GestureDirection.RIGHT.value
        assert result.element_info["distance"] == 100

        # Verify touch events were dispatched
        touch_calls = mock_session.input.dispatch_touch_event.call_args_list
        assert len(touch_calls) >= 3  # touchStart, touchMove(s), touchEnd
        assert touch_calls[0][1]["type"] == "touchStart"
        assert touch_calls[-1][1]["type"] == "touchEnd"

    @pytest.mark.asyncio
    async def test_pinch_gesture(self, interaction_engine, mock_session):
        """Test pinch zoom gesture."""

        center_point = InteractionPoint(x=250, y=350, pressure=1.0)

        result = await interaction_engine.perform_gesture(
            mock_session, "pinch", center_point, duration=0.5
        )

        assert result.success
        assert result.interaction_type == InteractionType.PINCH_ZOOM
        assert "zoom_type" in result.element_info

        # Verify multi-touch events were dispatched
        touch_calls = mock_session.input.dispatch_touch_event.call_args_list
        assert len(touch_calls) >= 3

        # Check that touchStart had two touch points
        start_call = touch_calls[0]
        assert len(start_call[1]["touchPoints"]) == 2

    @pytest.mark.asyncio
    async def test_long_press_gesture(self, interaction_engine, mock_session):
        """Test long press gesture."""

        point = InteractionPoint(x=150, y=250, pressure=1.0)

        result = await interaction_engine.perform_gesture(
            mock_session, "long_press", point, duration=1.0
        )

        assert result.success
        assert result.interaction_type == InteractionType.LONG_PRESS
        assert result.element_info["duration"] == 1.0

    @pytest.mark.asyncio
    async def test_element_not_found_error(
        self, interaction_engine, mock_session, element_selector
    ):
        """Test handling when element is not found."""

        # Mock element not found
        mock_session.runtime.evaluate.return_value = {"found": False}

        result = await interaction_engine.hover_element(mock_session, element_selector)

        assert not result.success
        assert result.error_message == "Element not found"

    def test_gesture_direction_calculations(self, interaction_engine):
        """Test gesture direction vector calculations."""

        # This tests the internal direction calculation logic
        # The actual vectors are defined in the _perform_swipe method

        directions = [
            GestureDirection.UP,
            GestureDirection.DOWN,
            GestureDirection.LEFT,
            GestureDirection.RIGHT,
            GestureDirection.DIAGONAL_UP_LEFT,
            GestureDirection.DIAGONAL_UP_RIGHT,
            GestureDirection.DIAGONAL_DOWN_LEFT,
            GestureDirection.DIAGONAL_DOWN_RIGHT,
        ]

        # All directions should be valid enum values
        for direction in directions:
            assert isinstance(direction.value, str)
            assert len(direction.value) > 0


@pytest.mark.asyncio
async def test_integration_advanced_automation():
    """Integration test for advanced automation components."""

    # Test that all components can work together
    selector = AdvancedElementSelector()
    waiter = SmartWaiter()
    recovery_system = ErrorRecoverySystem()
    optimizer = PerformanceOptimizer(
        OptimizationSettings(level=OptimizationLevel.MODERATE)
    )
    interaction_engine = AdvancedInteractionEngine()

    # Mock session
    mock_session = AsyncMock()
    mock_session.runtime.evaluate = AsyncMock(return_value={})

    # Test that components can be initialized without error
    assert selector is not None
    assert waiter is not None
    assert recovery_system is not None
    assert optimizer is not None
    assert interaction_engine is not None

    # Test basic interaction between components
    element_selector = ElementSelector(
        type=ElementSelectorType.CSS, value="#test-element"
    )

    # This would be part of a larger integration test
    # For now, just verify components can be created and basic methods exist
    assert hasattr(selector, "find_element")
    assert hasattr(waiter, "wait_for_element")
    assert hasattr(recovery_system, "handle_error")
    assert hasattr(optimizer, "get_performance_metrics")
    assert hasattr(interaction_engine, "hover_element")


# Performance and stress tests
@pytest.mark.performance
class TestPerformanceStress:
    """Performance and stress tests for advanced automation."""

    @pytest.mark.asyncio
    async def test_large_number_of_elements(self):
        """Test handling of pages with many elements."""

        selector = AdvancedElementSelector()
        mock_session = AsyncMock()

        # Mock large number of similar elements
        large_element_list = []
        for i in range(1000):
            large_element_list.append(
                {
                    "elementId": f"element-{i}",
                    "tagName": "div",
                    "text": f"Element {i}",
                    "attributes": {"class": "item"},
                    "boundingBox": {
                        "x": i % 100,
                        "y": i // 100,
                        "width": 50,
                        "height": 20,
                    },
                    "isVisible": True,
                }
            )

        mock_session.runtime.evaluate.return_value = large_element_list

        element_selector = ElementSelector(type=ElementSelectorType.CSS, value=".item")

        # Should handle large result sets efficiently
        results = await selector.find_multiple_elements(
            mock_session, element_selector, limit=50
        )

        assert len(results) <= 50  # Should respect limit

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test concurrent automation operations."""

        waiter = SmartWaiter()
        mock_session = AsyncMock()
        mock_session.runtime.evaluate = AsyncMock(
            return_value={"visible": True, "found": True}
        )

        element_selector = ElementSelector(type=ElementSelectorType.CSS, value="#test")

        # Run multiple wait operations concurrently
        tasks = []
        for i in range(10):
            task = waiter.wait_for_element(
                mock_session, element_selector, WaitType.ELEMENT_VISIBLE, timeout=1.0
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        # All operations should complete successfully
        assert all(result.success for result in results)
        assert len(results) == 10
