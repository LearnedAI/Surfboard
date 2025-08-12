"""
Smart Waiting System with Adaptive Timeouts.

This module provides intelligent waiting mechanisms that adapt to page conditions
and provide predictive timeout adjustments.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from ..protocols.cdp_domains import CDPSession
from ..protocols.llm_protocol import ElementSelector, WaitCondition

logger = logging.getLogger(__name__)


class WaitType(str, Enum):
    """Types of wait conditions."""

    ELEMENT_VISIBLE = "element_visible"
    ELEMENT_CLICKABLE = "element_clickable"
    ELEMENT_STABLE = "element_stable"
    PAGE_LOAD = "page_load"
    NETWORK_IDLE = "network_idle"
    CUSTOM_CONDITION = "custom_condition"
    DOM_CHANGE = "dom_change"
    ANIMATION_COMPLETE = "animation_complete"


@dataclass
class WaitResult:
    """Result of a wait operation."""

    success: bool
    wait_time: float
    condition_met: str
    additional_info: Dict[str, Any]
    timeout_occurred: bool = False


class SmartWaiter:
    """Smart waiting system with adaptive timeouts and predictive logic."""

    def __init__(self):
        """Initialize smart waiter."""
        self.wait_history = []  # Track wait times for learning
        self.page_complexity_cache = {}
        self.network_activity_baseline = None

    async def wait_for_condition(
        self,
        session: CDPSession,
        condition: Union[WaitType, str],
        target: Optional[Any] = None,
        timeout: float = 30.0,
        poll_interval: float = 0.1,
        adaptive: bool = True,
        stability_time: float = 0.5,
    ) -> WaitResult:
        """Wait for a specific condition with smart timing.

        Args:
            session: CDP session
            condition: Wait condition type
            target: Target element or custom condition
            timeout: Maximum wait time
            poll_interval: Polling interval
            adaptive: Use adaptive timeout adjustment
            stability_time: Time to wait for stability

        Returns:
            Wait result with timing information
        """
        start_time = time.time()

        # Adjust timeout if adaptive
        if adaptive:
            adjusted_timeout = await self._calculate_adaptive_timeout(
                session, condition, timeout
            )
            logger.debug(
                f"Adaptive timeout: {adjusted_timeout:.1f}s (original: {timeout:.1f}s)"
            )
            timeout = adjusted_timeout

        logger.debug(f"Waiting for condition: {condition} (timeout: {timeout:.1f}s)")

        # Set up condition checker
        condition_checker = self._get_condition_checker(condition, target)

        last_check_time = 0
        stability_start = None
        consecutive_successes = 0

        while time.time() - start_time < timeout:
            try:
                # Check condition
                condition_met, additional_info = await condition_checker(session)

                if condition_met:
                    # Start stability tracking if needed
                    if stability_time > 0:
                        if stability_start is None:
                            stability_start = time.time()
                            consecutive_successes = 1
                        else:
                            consecutive_successes += 1

                        # Check if stable for required time
                        if time.time() - stability_start >= stability_time:
                            wait_time = time.time() - start_time
                            logger.debug(
                                f"Condition met after {wait_time:.2f}s with stability"
                            )

                            # Record success for learning
                            self._record_wait_result(condition, wait_time, True)

                            return WaitResult(
                                success=True,
                                wait_time=wait_time,
                                condition_met=str(condition),
                                additional_info=additional_info,
                            )
                    else:
                        # No stability required
                        wait_time = time.time() - start_time
                        logger.debug(f"Condition met after {wait_time:.2f}s")

                        self._record_wait_result(condition, wait_time, True)

                        return WaitResult(
                            success=True,
                            wait_time=wait_time,
                            condition_met=str(condition),
                            additional_info=additional_info,
                        )
                else:
                    # Reset stability tracking
                    stability_start = None
                    consecutive_successes = 0

                # Adaptive polling interval based on condition type
                current_interval = self._calculate_poll_interval(
                    condition, poll_interval, time.time() - start_time
                )

                await asyncio.sleep(current_interval)

            except Exception as e:
                logger.debug(f"Wait condition check error: {e}")
                await asyncio.sleep(poll_interval)

        # Timeout occurred
        wait_time = time.time() - start_time
        logger.warning(
            f"Wait timeout after {wait_time:.2f}s for condition: {condition}"
        )

        self._record_wait_result(condition, wait_time, False)

        return WaitResult(
            success=False,
            wait_time=wait_time,
            condition_met="timeout",
            additional_info={},
            timeout_occurred=True,
        )

    async def wait_for_element(
        self,
        session: CDPSession,
        selector: ElementSelector,
        condition: WaitType = WaitType.ELEMENT_VISIBLE,
        timeout: float = 30.0,
        stability_time: float = 0.5,
    ) -> WaitResult:
        """Wait for element with specific condition."""

        return await self.wait_for_condition(
            session=session,
            condition=condition,
            target=selector,
            timeout=timeout,
            stability_time=stability_time,
        )

    async def wait_for_page_load(
        self,
        session: CDPSession,
        wait_condition: WaitCondition = WaitCondition.LOAD,
        timeout: float = 30.0,
        additional_wait: float = 1.0,
    ) -> WaitResult:
        """Wait for page load with additional smart waiting."""

        condition_map = {
            WaitCondition.LOAD: WaitType.PAGE_LOAD,
            WaitCondition.DOM_CONTENT_LOADED: WaitType.PAGE_LOAD,
            WaitCondition.NETWORK_IDLE: WaitType.NETWORK_IDLE,
        }

        condition = condition_map.get(wait_condition, WaitType.PAGE_LOAD)

        result = await self.wait_for_condition(
            session=session, condition=condition, timeout=timeout
        )

        # Additional wait for dynamic content
        if result.success and additional_wait > 0:
            logger.debug(f"Additional wait: {additional_wait}s for dynamic content")
            await asyncio.sleep(additional_wait)
            result.wait_time += additional_wait

        return result

    async def wait_for_network_idle(
        self,
        session: CDPSession,
        idle_time: float = 2.0,
        timeout: float = 30.0,
        max_connections: int = 2,
    ) -> WaitResult:
        """Wait for network activity to become idle."""

        start_time = time.time()
        last_activity_time = start_time
        active_requests = 0

        # Enable network domain
        await session.network.enable()

        def on_request_started():
            nonlocal active_requests, last_activity_time
            active_requests += 1
            last_activity_time = time.time()

        def on_request_finished():
            nonlocal active_requests, last_activity_time
            active_requests = max(0, active_requests - 1)
            last_activity_time = time.time()

        # Set up network monitoring (simplified)
        # In real implementation, would use CDP events

        while time.time() - start_time < timeout:
            current_time = time.time()

            # Check if network has been idle for required time
            time_since_activity = current_time - last_activity_time

            if active_requests <= max_connections and time_since_activity >= idle_time:
                wait_time = current_time - start_time
                logger.debug(f"Network idle achieved after {wait_time:.2f}s")

                return WaitResult(
                    success=True,
                    wait_time=wait_time,
                    condition_met="network_idle",
                    additional_info={
                        "active_requests": active_requests,
                        "idle_duration": time_since_activity,
                    },
                )

            await asyncio.sleep(0.1)

        # Timeout
        wait_time = time.time() - start_time
        return WaitResult(
            success=False,
            wait_time=wait_time,
            condition_met="timeout",
            additional_info={"active_requests": active_requests},
            timeout_occurred=True,
        )

    def _get_condition_checker(
        self, condition: Union[WaitType, str], target: Optional[Any]
    ) -> Callable:
        """Get appropriate condition checker function."""

        if isinstance(condition, str):
            condition = WaitType(condition)

        if condition == WaitType.ELEMENT_VISIBLE:
            return self._check_element_visible
        elif condition == WaitType.ELEMENT_CLICKABLE:
            return self._check_element_clickable
        elif condition == WaitType.ELEMENT_STABLE:
            return self._check_element_stable
        elif condition == WaitType.PAGE_LOAD:
            return self._check_page_load
        elif condition == WaitType.NETWORK_IDLE:
            return self._check_network_idle
        elif condition == WaitType.DOM_CHANGE:
            return self._check_dom_change
        elif condition == WaitType.ANIMATION_COMPLETE:
            return self._check_animation_complete
        else:
            return self._check_custom_condition

    async def _check_element_visible(
        self, session: CDPSession, selector: Optional[ElementSelector] = None
    ) -> tuple[bool, Dict[str, Any]]:
        """Check if element is visible."""

        if not selector:
            return False, {"error": "No selector provided"}

        script = f"""
        (function() {{
            let element;

            if ({repr(selector.type.value)} === 'css') {{
                element = document.querySelector({repr(selector.value)});
            }} else if ({repr(selector.type.value)} === 'xpath') {{
                const result = document.evaluate(
                    {repr(selector.value)}, document, null,
                    XPathResult.FIRST_ORDERED_NODE_TYPE, null
                );
                element = result.singleNodeValue;
            }} else if ({repr(selector.type.value)} === 'text') {{
                const walker = document.createTreeWalker(
                    document.body, NodeFilter.SHOW_ELEMENT
                );
                while (walker.nextNode()) {{
                    if (walker.currentNode.textContent.trim().toLowerCase() ===
                        {repr(selector.value.lower())}) {{
                        element = walker.currentNode;
                        break;
                    }}
                }}
            }}

            if (!element) return {{visible: false, found: false}};

            const rect = element.getBoundingClientRect();
            const style = window.getComputedStyle(element);

            const visible = style.display !== 'none' &&
                          style.visibility !== 'hidden' &&
                          style.opacity !== '0' &&
                          rect.width > 0 &&
                          rect.height > 0;

            return {{
                visible: visible,
                found: true,
                rect: {{
                    x: rect.x,
                    y: rect.y,
                    width: rect.width,
                    height: rect.height
                }},
                style: {{
                    display: style.display,
                    visibility: style.visibility,
                    opacity: style.opacity
                }}
            }};
        }})()
        """

        result = await session.runtime.evaluate(script)
        if not result:
            return False, {"error": "Script execution failed"}

        return result.get("visible", False), result

    async def _check_element_clickable(
        self, session: CDPSession, selector: Optional[ElementSelector] = None
    ) -> tuple[bool, Dict[str, Any]]:
        """Check if element is clickable."""

        # First check if visible
        visible, info = await self._check_element_visible(session, selector)
        if not visible:
            return False, info

        if not selector:
            return False, {"error": "No selector provided"}

        script = f"""
        (function() {{
            let element;

            if ({repr(selector.type.value)} === 'css') {{
                element = document.querySelector({repr(selector.value)});
            }}

            if (!element) return {{clickable: false}};

            const rect = element.getBoundingClientRect();
            const style = window.getComputedStyle(element);

            // Check if element is not disabled and not covered
            const clickable = !element.disabled &&
                            style.pointerEvents !== 'none' &&
                            rect.width > 0 &&
                            rect.height > 0;

            // Check if element is covered by another element
            const centerX = rect.x + rect.width / 2;
            const centerY = rect.y + rect.height / 2;
            const elementAtPoint = document.elementFromPoint(centerX, centerY);

            const notCovered = elementAtPoint === element ||
                             element.contains(elementAtPoint) ||
                             (elementAtPoint && elementAtPoint.contains(element));

            return {{
                clickable: clickable && notCovered,
                disabled: element.disabled,
                covered: !notCovered,
                elementAtPoint: elementAtPoint ? elementAtPoint.tagName : null
            }};
        }})()
        """

        result = await session.runtime.evaluate(script)
        if not result:
            return False, {"error": "Script execution failed"}

        return result.get("clickable", False), {**info, **result}

    async def _check_element_stable(
        self, session: CDPSession, selector: Optional[ElementSelector] = None
    ) -> tuple[bool, Dict[str, Any]]:
        """Check if element position is stable."""

        if not selector:
            return False, {"error": "No selector provided"}

        # Take two measurements with small delay
        script = f"""
        (function() {{
            let element;

            if ({repr(selector.type.value)} === 'css') {{
                element = document.querySelector({repr(selector.value)});
            }}

            if (!element) return null;

            const rect = element.getBoundingClientRect();
            return {{
                x: rect.x,
                y: rect.y,
                width: rect.width,
                height: rect.height
            }};
        }})()
        """

        first_measurement = await session.runtime.evaluate(script)
        if not first_measurement:
            return False, {"error": "Element not found"}

        # Small delay for stability check
        await asyncio.sleep(0.1)

        second_measurement = await session.runtime.evaluate(script)
        if not second_measurement:
            return False, {"error": "Element disappeared"}

        # Check if position changed significantly
        position_change = abs(first_measurement["x"] - second_measurement["x"]) + abs(
            first_measurement["y"] - second_measurement["y"]
        )

        size_change = abs(
            first_measurement["width"] - second_measurement["width"]
        ) + abs(first_measurement["height"] - second_measurement["height"])

        stable = position_change < 2 and size_change < 2  # 2px tolerance

        return stable, {
            "position_change": position_change,
            "size_change": size_change,
            "first_measurement": first_measurement,
            "second_measurement": second_measurement,
        }

    async def _check_page_load(
        self, session: CDPSession, target: Optional[Any] = None
    ) -> tuple[bool, Dict[str, Any]]:
        """Check if page is fully loaded."""

        script = """
        (function() {
            return {
                readyState: document.readyState,
                isLoading: document.readyState !== 'complete',
                pendingImages: Array.from(document.images).filter(img => !img.complete).length,
                pendingScripts: Array.from(document.scripts).filter(script =>
                    script.src && !script.readyState || script.readyState === 'loading'
                ).length
            };
        })()
        """

        result = await session.runtime.evaluate(script)
        if not result:
            return False, {"error": "Script execution failed"}

        loaded = (
            result.get("readyState") == "complete"
            and result.get("pendingImages", 0) == 0
            and result.get("pendingScripts", 0) == 0
        )

        return loaded, result

    async def _check_network_idle(
        self, session: CDPSession, target: Optional[Any] = None
    ) -> tuple[bool, Dict[str, Any]]:
        """Check if network is idle."""

        # This would integrate with CDP Network events
        # For now, return a simple implementation
        script = """
        (function() {
            const performanceEntries = performance.getEntriesByType('resource');
            const recentRequests = performanceEntries.filter(entry =>
                performance.now() - entry.startTime < 2000  // Last 2 seconds
            );

            return {
                recentRequestCount: recentRequests.length,
                totalRequests: performanceEntries.length,
                networkIdle: recentRequests.length === 0
            };
        })()
        """

        result = await session.runtime.evaluate(script)
        if not result:
            return False, {"error": "Script execution failed"}

        return result.get("networkIdle", False), result

    async def _check_dom_change(
        self, session: CDPSession, target: Optional[Any] = None
    ) -> tuple[bool, Dict[str, Any]]:
        """Check for DOM changes."""

        # This would use MutationObserver
        # Simplified implementation for now
        return True, {"dom_stable": True}

    async def _check_animation_complete(
        self, session: CDPSession, target: Optional[Any] = None
    ) -> tuple[bool, Dict[str, Any]]:
        """Check if animations are complete."""

        script = """
        (function() {
            const animations = document.getAnimations ? document.getAnimations() : [];
            const runningAnimations = animations.filter(anim =>
                anim.playState === 'running' || anim.playState === 'pending'
            );

            return {
                totalAnimations: animations.length,
                runningAnimations: runningAnimations.length,
                animationsComplete: runningAnimations.length === 0
            };
        })()
        """

        result = await session.runtime.evaluate(script)
        if not result:
            return False, {"error": "Script execution failed"}

        return result.get("animationsComplete", True), result

    async def _check_custom_condition(
        self, session: CDPSession, target: Optional[Any] = None
    ) -> tuple[bool, Dict[str, Any]]:
        """Check custom condition."""

        if callable(target):
            try:
                result = await target(session)
                return bool(result), {"custom_result": result}
            except Exception as e:
                return False, {"error": str(e)}

        return False, {"error": "Invalid custom condition"}

    async def _calculate_adaptive_timeout(
        self, session: CDPSession, condition: WaitType, base_timeout: float
    ) -> float:
        """Calculate adaptive timeout based on conditions and history."""

        # Page complexity factor
        complexity_factor = await self._get_page_complexity_factor(session)

        # Historical data factor
        history_factor = self._get_historical_factor(condition)

        # Condition-specific factor
        condition_factor = self._get_condition_factor(condition)

        # Combine factors
        total_factor = complexity_factor * history_factor * condition_factor

        # Apply bounds
        adaptive_timeout = base_timeout * max(0.5, min(3.0, total_factor))

        return adaptive_timeout

    async def _get_page_complexity_factor(self, session: CDPSession) -> float:
        """Get page complexity factor for timeout adjustment."""

        script = """
        (function() {
            return {
                elementCount: document.querySelectorAll('*').length,
                scriptCount: document.querySelectorAll('script').length,
                imageCount: document.querySelectorAll('img').length,
                iframeCount: document.querySelectorAll('iframe').length,
                readyState: document.readyState
            };
        })()
        """

        result = await session.runtime.evaluate(script)
        if not result:
            return 1.0

        element_count = result.get("elementCount", 100)
        script_count = result.get("scriptCount", 0)
        image_count = result.get("imageCount", 0)

        # Calculate complexity score
        complexity = 1.0

        if element_count > 1000:
            complexity += 0.5
        elif element_count > 500:
            complexity += 0.3

        if script_count > 10:
            complexity += 0.3
        elif script_count > 5:
            complexity += 0.1

        if image_count > 20:
            complexity += 0.2

        return complexity

    def _get_historical_factor(self, condition: WaitType) -> float:
        """Get historical performance factor."""

        # Filter history for this condition type
        condition_history = [
            entry
            for entry in self.wait_history[-50:]  # Last 50 entries
            if entry.get("condition") == condition
        ]

        if not condition_history:
            return 1.0

        # Calculate average success time
        successful_waits = [
            entry["wait_time"]
            for entry in condition_history
            if entry.get("success", False)
        ]

        if not successful_waits:
            return 1.2  # Increase timeout if recent failures

        avg_time = sum(successful_waits) / len(successful_waits)

        # Factor based on average time
        if avg_time > 10.0:
            return 1.3
        elif avg_time > 5.0:
            return 1.1
        elif avg_time < 1.0:
            return 0.8
        else:
            return 1.0

    def _get_condition_factor(self, condition: WaitType) -> float:
        """Get condition-specific timeout factor."""

        factors = {
            WaitType.ELEMENT_VISIBLE: 1.0,
            WaitType.ELEMENT_CLICKABLE: 1.2,
            WaitType.ELEMENT_STABLE: 1.5,
            WaitType.PAGE_LOAD: 2.0,
            WaitType.NETWORK_IDLE: 2.5,
            WaitType.ANIMATION_COMPLETE: 1.3,
            WaitType.DOM_CHANGE: 1.1,
            WaitType.CUSTOM_CONDITION: 1.0,
        }

        return factors.get(condition, 1.0)

    def _calculate_poll_interval(
        self, condition: WaitType, base_interval: float, elapsed_time: float
    ) -> float:
        """Calculate adaptive polling interval."""

        # Start with more frequent polling, then back off
        if elapsed_time < 1.0:
            return base_interval * 0.5
        elif elapsed_time < 5.0:
            return base_interval
        else:
            return base_interval * 2.0

    def _record_wait_result(
        self, condition: WaitType, wait_time: float, success: bool
    ) -> None:
        """Record wait result for learning."""

        entry = {
            "condition": condition,
            "wait_time": wait_time,
            "success": success,
            "timestamp": time.time(),
        }

        self.wait_history.append(entry)

        # Keep only recent history
        if len(self.wait_history) > 200:
            self.wait_history = self.wait_history[-100:]
