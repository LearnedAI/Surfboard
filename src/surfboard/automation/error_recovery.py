"""
Error Recovery and Retry Systems.

This module provides intelligent error recovery with contextual retry strategies,
failure analysis, and adaptive recovery mechanisms.
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, Union

from ..protocols.cdp_domains import CDPSession
from ..protocols.llm_protocol import (
    BaseCommand,
    BaseResponse,
    ElementSelector,
    StatusType,
)

logger = logging.getLogger(__name__)


class ErrorType(str, Enum):
    """Types of errors that can occur."""

    ELEMENT_NOT_FOUND = "element_not_found"
    ELEMENT_NOT_CLICKABLE = "element_not_clickable"
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    NAVIGATION_ERROR = "navigation_error"
    SCRIPT_ERROR = "script_error"
    ELEMENT_STALE = "element_stale"
    PAGE_CRASH = "page_crash"
    CONNECTION_LOST = "connection_lost"
    PERMISSION_DENIED = "permission_denied"
    RATE_LIMITED = "rate_limited"
    UNKNOWN_ERROR = "unknown_error"


class RecoveryStrategy(str, Enum):
    """Error recovery strategies."""

    IMMEDIATE_RETRY = "immediate_retry"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    ELEMENT_WAIT_RETRY = "element_wait_retry"
    PAGE_REFRESH = "page_refresh"
    ALTERNATIVE_SELECTOR = "alternative_selector"
    NAVIGATION_RETRY = "navigation_retry"
    SESSION_RESTART = "session_restart"
    CONTEXT_RECOVERY = "context_recovery"
    GRACEFUL_DEGRADATION = "graceful_degradation"


@dataclass
class ErrorContext:
    """Context information about an error."""

    error_type: ErrorType
    error_message: str
    command: BaseCommand
    attempt_count: int
    timestamp: float
    page_state: Dict[str, Any] = field(default_factory=dict)
    element_info: Dict[str, Any] = field(default_factory=dict)
    network_info: Dict[str, Any] = field(default_factory=dict)
    additional_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryResult:
    """Result of error recovery attempt."""

    success: bool
    strategy_used: RecoveryStrategy
    attempts_made: int
    recovery_time: float
    final_result: Optional[Any] = None
    fallback_used: bool = False
    lessons_learned: List[str] = field(default_factory=list)


class ErrorRecoverySystem:
    """Intelligent error recovery with contextual strategies."""

    def __init__(self):
        """Initialize error recovery system."""
        self.error_history = []
        self.recovery_patterns = {}
        self.max_retry_attempts = 3
        self.base_retry_delay = 1.0
        self.max_retry_delay = 30.0

        # Strategy mapping
        self.strategy_map = {
            ErrorType.ELEMENT_NOT_FOUND: [
                RecoveryStrategy.ELEMENT_WAIT_RETRY,
                RecoveryStrategy.ALTERNATIVE_SELECTOR,
                RecoveryStrategy.PAGE_REFRESH,
            ],
            ErrorType.ELEMENT_NOT_CLICKABLE: [
                RecoveryStrategy.ELEMENT_WAIT_RETRY,
                RecoveryStrategy.CONTEXT_RECOVERY,
                RecoveryStrategy.ALTERNATIVE_SELECTOR,
            ],
            ErrorType.TIMEOUT_ERROR: [
                RecoveryStrategy.EXPONENTIAL_BACKOFF,
                RecoveryStrategy.PAGE_REFRESH,
                RecoveryStrategy.NAVIGATION_RETRY,
            ],
            ErrorType.NETWORK_ERROR: [
                RecoveryStrategy.EXPONENTIAL_BACKOFF,
                RecoveryStrategy.NAVIGATION_RETRY,
                RecoveryStrategy.SESSION_RESTART,
            ],
            ErrorType.NAVIGATION_ERROR: [
                RecoveryStrategy.NAVIGATION_RETRY,
                RecoveryStrategy.SESSION_RESTART,
                RecoveryStrategy.GRACEFUL_DEGRADATION,
            ],
            ErrorType.PAGE_CRASH: [
                RecoveryStrategy.SESSION_RESTART,
                RecoveryStrategy.NAVIGATION_RETRY,
                RecoveryStrategy.GRACEFUL_DEGRADATION,
            ],
        }

    async def handle_error(
        self,
        session: CDPSession,
        error: Exception,
        command: BaseCommand,
        attempt_count: int = 1,
        context: Optional[Dict[str, Any]] = None,
    ) -> RecoveryResult:
        """Handle error with appropriate recovery strategy.

        Args:
            session: CDP session
            error: The error that occurred
            command: Command that failed
            attempt_count: Current attempt number
            context: Additional context information

        Returns:
            Recovery result with success status and strategy used
        """
        start_time = time.time()

        # Analyze error to determine type and context
        error_context = await self._analyze_error(
            session, error, command, attempt_count, context or {}
        )

        logger.warning(
            f"Handling error: {error_context.error_type} (attempt {attempt_count})"
        )

        # Get appropriate recovery strategies
        strategies = self._get_recovery_strategies(error_context)

        # Try each strategy
        for strategy in strategies:
            try:
                logger.debug(f"Attempting recovery strategy: {strategy}")

                success, result = await self._apply_recovery_strategy(
                    session, strategy, error_context
                )

                if success:
                    recovery_time = time.time() - start_time

                    # Learn from successful recovery
                    self._record_successful_recovery(
                        error_context, strategy, recovery_time
                    )

                    return RecoveryResult(
                        success=True,
                        strategy_used=strategy,
                        attempts_made=attempt_count,
                        recovery_time=recovery_time,
                        final_result=result,
                        lessons_learned=["Successful recovery with " + strategy.value],
                    )

            except Exception as strategy_error:
                logger.debug(f"Recovery strategy {strategy} failed: {strategy_error}")
                continue

        # All strategies failed
        recovery_time = time.time() - start_time

        # Try graceful degradation as last resort
        fallback_result = await self._attempt_graceful_degradation(
            session, error_context
        )

        self._record_failed_recovery(error_context, strategies, recovery_time)

        return RecoveryResult(
            success=fallback_result is not None,
            strategy_used=RecoveryStrategy.GRACEFUL_DEGRADATION,
            attempts_made=attempt_count,
            recovery_time=recovery_time,
            final_result=fallback_result,
            fallback_used=True,
            lessons_learned=["All recovery strategies failed"],
        )

    async def retry_with_recovery(
        self,
        session: CDPSession,
        operation: Callable,
        command: BaseCommand,
        max_attempts: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> tuple[bool, Any]:
        """Retry operation with intelligent error recovery.

        Args:
            session: CDP session
            operation: Operation to retry
            command: Command being executed
            max_attempts: Maximum retry attempts
            context: Additional context

        Returns:
            (success, result) tuple
        """
        max_attempts = max_attempts or self.max_retry_attempts
        last_error = None

        for attempt in range(1, max_attempts + 1):
            try:
                logger.debug(f"Executing operation (attempt {attempt}/{max_attempts})")
                result = await operation()
                logger.debug(f"Operation succeeded on attempt {attempt}")
                return True, result

            except Exception as error:
                last_error = error
                logger.debug(f"Operation failed on attempt {attempt}: {error}")

                if attempt == max_attempts:
                    logger.error(f"Operation failed after {max_attempts} attempts")
                    break

                # Apply error recovery
                recovery_result = await self.handle_error(
                    session, error, command, attempt, context
                )

                if not recovery_result.success:
                    logger.error(f"Error recovery failed on attempt {attempt}")
                    # Continue to next attempt anyway

                # Wait before retry with exponential backoff
                delay = min(
                    self.base_retry_delay * (2 ** (attempt - 1)), self.max_retry_delay
                ) + random.uniform(
                    0, 0.5
                )  # Add jitter

                logger.debug(f"Waiting {delay:.1f}s before retry")
                await asyncio.sleep(delay)

        return False, last_error

    async def _analyze_error(
        self,
        session: CDPSession,
        error: Exception,
        command: BaseCommand,
        attempt_count: int,
        context: Dict[str, Any],
    ) -> ErrorContext:
        """Analyze error to determine type and gather context."""

        error_type = self._classify_error(error)

        # Gather page state information
        page_state = await self._get_page_state(session)

        # Gather element information if relevant
        element_info = {}
        if hasattr(command, "selector") and command.selector:
            element_info = await self._get_element_info(session, command.selector)

        # Gather network information
        network_info = await self._get_network_info(session)

        return ErrorContext(
            error_type=error_type,
            error_message=str(error),
            command=command,
            attempt_count=attempt_count,
            timestamp=time.time(),
            page_state=page_state,
            element_info=element_info,
            network_info=network_info,
            additional_context=context,
        )

    def _classify_error(self, error: Exception) -> ErrorType:
        """Classify error type based on error message and type."""

        error_str = str(error).lower()

        if "element not found" in error_str or "no such element" in error_str:
            return ErrorType.ELEMENT_NOT_FOUND
        elif "not clickable" in error_str or "not interactable" in error_str:
            return ErrorType.ELEMENT_NOT_CLICKABLE
        elif "timeout" in error_str:
            return ErrorType.TIMEOUT_ERROR
        elif "network" in error_str or "connection" in error_str:
            return ErrorType.NETWORK_ERROR
        elif "navigation" in error_str:
            return ErrorType.NAVIGATION_ERROR
        elif "script" in error_str or "javascript" in error_str:
            return ErrorType.SCRIPT_ERROR
        elif "stale" in error_str:
            return ErrorType.ELEMENT_STALE
        elif "crash" in error_str:
            return ErrorType.PAGE_CRASH
        elif "permission" in error_str:
            return ErrorType.PERMISSION_DENIED
        elif "rate limit" in error_str:
            return ErrorType.RATE_LIMITED
        else:
            return ErrorType.UNKNOWN_ERROR

    async def _get_page_state(self, session: CDPSession) -> Dict[str, Any]:
        """Get current page state information."""

        script = """
        (function() {
            return {
                url: window.location.href,
                title: document.title,
                readyState: document.readyState,
                elementCount: document.querySelectorAll('*').length,
                errorElements: document.querySelectorAll('.error, .alert, .warning').length,
                modalElements: document.querySelectorAll('.modal, .popup, .dialog').length,
                loadingElements: document.querySelectorAll('.loading, .spinner').length,
                timestamp: Date.now()
            };
        })()
        """

        try:
            return await session.runtime.evaluate(script) or {}
        except Exception:
            return {"error": "Could not retrieve page state"}

    async def _get_element_info(
        self, session: CDPSession, selector: ElementSelector
    ) -> Dict[str, Any]:
        """Get information about the target element."""

        script = f"""
        (function() {{
            let element = null;

            try {{
                if ({repr(selector.type.value)} === 'css') {{
                    element = document.querySelector({repr(selector.value)});
                }} else if ({repr(selector.type.value)} === 'xpath') {{
                    const result = document.evaluate(
                        {repr(selector.value)}, document, null,
                        XPathResult.FIRST_ORDERED_NODE_TYPE, null
                    );
                    element = result.singleNodeValue;
                }}
            }} catch (e) {{
                return {{error: e.message}};
            }}

            if (!element) {{
                return {{found: false, similar: []}};
            }}

            const rect = element.getBoundingClientRect();
            const style = window.getComputedStyle(element);

            return {{
                found: true,
                tagName: element.tagName.toLowerCase(),
                text: element.textContent.trim().substring(0, 100),
                visible: style.display !== 'none' && style.visibility !== 'hidden',
                rect: {{
                    x: rect.x,
                    y: rect.y,
                    width: rect.width,
                    height: rect.height
                }},
                attributes: Object.fromEntries(
                    Array.from(element.attributes).map(attr => [attr.name, attr.value])
                )
            }};
        }})()
        """

        try:
            return await session.runtime.evaluate(script) or {}
        except Exception:
            return {"error": "Could not retrieve element info"}

    async def _get_network_info(self, session: CDPSession) -> Dict[str, Any]:
        """Get network-related information."""

        script = """
        (function() {
            const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
            return {
                online: navigator.onLine,
                connectionType: connection ? connection.effectiveType : 'unknown',
                networkState: document.readyState,
                performanceEntries: performance.getEntriesByType('navigation').length
            };
        })()
        """

        try:
            return await session.runtime.evaluate(script) or {}
        except Exception:
            return {"error": "Could not retrieve network info"}

    def _get_recovery_strategies(
        self, error_context: ErrorContext
    ) -> List[RecoveryStrategy]:
        """Get appropriate recovery strategies for error type."""

        strategies = self.strategy_map.get(
            error_context.error_type,
            [
                RecoveryStrategy.EXPONENTIAL_BACKOFF,
                RecoveryStrategy.GRACEFUL_DEGRADATION,
            ],
        ).copy()

        # Adjust strategies based on context
        if error_context.attempt_count > 2:
            # On later attempts, prioritize more aggressive strategies
            if RecoveryStrategy.PAGE_REFRESH in strategies:
                strategies.remove(RecoveryStrategy.PAGE_REFRESH)
                strategies.insert(0, RecoveryStrategy.PAGE_REFRESH)

        # Learn from history
        learned_strategies = self._get_learned_strategies(error_context)
        if learned_strategies:
            # Prioritize strategies that have worked before
            for strategy in reversed(learned_strategies):
                if strategy in strategies:
                    strategies.remove(strategy)
                    strategies.insert(0, strategy)

        return strategies[:3]  # Limit to top 3 strategies

    async def _apply_recovery_strategy(
        self,
        session: CDPSession,
        strategy: RecoveryStrategy,
        error_context: ErrorContext,
    ) -> tuple[bool, Any]:
        """Apply specific recovery strategy."""

        if strategy == RecoveryStrategy.IMMEDIATE_RETRY:
            return await self._immediate_retry(session, error_context)
        elif strategy == RecoveryStrategy.EXPONENTIAL_BACKOFF:
            return await self._exponential_backoff(session, error_context)
        elif strategy == RecoveryStrategy.ELEMENT_WAIT_RETRY:
            return await self._element_wait_retry(session, error_context)
        elif strategy == RecoveryStrategy.PAGE_REFRESH:
            return await self._page_refresh(session, error_context)
        elif strategy == RecoveryStrategy.ALTERNATIVE_SELECTOR:
            return await self._alternative_selector(session, error_context)
        elif strategy == RecoveryStrategy.NAVIGATION_RETRY:
            return await self._navigation_retry(session, error_context)
        elif strategy == RecoveryStrategy.SESSION_RESTART:
            return await self._session_restart(session, error_context)
        elif strategy == RecoveryStrategy.CONTEXT_RECOVERY:
            return await self._context_recovery(session, error_context)
        elif strategy == RecoveryStrategy.GRACEFUL_DEGRADATION:
            return await self._graceful_degradation(session, error_context)
        else:
            return False, None

    async def _immediate_retry(
        self, session: CDPSession, error_context: ErrorContext
    ) -> tuple[bool, Any]:
        """Immediate retry without delay."""

        # Simple retry - let the caller handle it
        return True, "retry_ready"

    async def _exponential_backoff(
        self, session: CDPSession, error_context: ErrorContext
    ) -> tuple[bool, Any]:
        """Wait with exponential backoff."""

        delay = min(
            self.base_retry_delay * (2 ** (error_context.attempt_count - 1)),
            self.max_retry_delay,
        )

        logger.debug(f"Exponential backoff: waiting {delay:.1f}s")
        await asyncio.sleep(delay)

        return True, "backoff_complete"

    async def _element_wait_retry(
        self, session: CDPSession, error_context: ErrorContext
    ) -> tuple[bool, Any]:
        """Wait for element to appear/become clickable."""

        if not hasattr(error_context.command, "selector"):
            return False, "No selector to wait for"

        selector = error_context.command.selector

        # Wait for element with extended timeout
        script = f"""
        (function() {{
            return new Promise((resolve) => {{
                let attempts = 0;
                const maxAttempts = 30; // 3 seconds

                function checkElement() {{
                    let element = null;

                    if ({repr(selector.type.value)} === 'css') {{
                        element = document.querySelector({repr(selector.value)});
                    }}

                    if (element) {{
                        const rect = element.getBoundingClientRect();
                        const style = window.getComputedStyle(element);

                        if (style.display !== 'none' &&
                            style.visibility !== 'hidden' &&
                            rect.width > 0 && rect.height > 0) {{
                            resolve(true);
                            return;
                        }}
                    }}

                    attempts++;
                    if (attempts >= maxAttempts) {{
                        resolve(false);
                        return;
                    }}

                    setTimeout(checkElement, 100);
                }}

                checkElement();
            }});
        }})()
        """

        try:
            result = await session.runtime.evaluate(script)
            return bool(result), "element_wait_complete"
        except Exception:
            return False, "Wait script failed"

    async def _page_refresh(
        self, session: CDPSession, error_context: ErrorContext
    ) -> tuple[bool, Any]:
        """Refresh the page."""

        try:
            current_url = error_context.page_state.get("url")
            if current_url:
                await session.page.navigate(current_url)

                # Wait for page to load
                await asyncio.sleep(2)

                return True, "page_refreshed"
            else:
                return False, "No URL to refresh"
        except Exception as e:
            return False, f"Refresh failed: {e}"

    async def _alternative_selector(
        self, session: CDPSession, error_context: ErrorContext
    ) -> tuple[bool, Any]:
        """Try alternative selectors for element."""

        if not hasattr(error_context.command, "selector"):
            return False, "No selector to alternate"

        original_selector = error_context.command.selector

        # Generate alternative selectors
        alternatives = await self._generate_alternative_selectors(
            session, original_selector
        )

        for alt_selector in alternatives:
            script = f"""
            (function() {{
                let element = null;

                if ({repr(alt_selector['type'])} === 'css') {{
                    element = document.querySelector({repr(alt_selector['value'])});
                }}

                if (element) {{
                    const rect = element.getBoundingClientRect();
                    const style = window.getComputedStyle(element);

                    return style.display !== 'none' &&
                           style.visibility !== 'hidden' &&
                           rect.width > 0 && rect.height > 0;
                }}

                return false;
            }})()
            """

            try:
                found = await session.runtime.evaluate(script)
                if found:
                    # Update the command selector
                    error_context.command.selector.type = alt_selector["type"]
                    error_context.command.selector.value = alt_selector["value"]
                    return True, f"Alternative selector found: {alt_selector['value']}"
            except Exception:
                continue

        return False, "No alternative selectors worked"

    async def _navigation_retry(
        self, session: CDPSession, error_context: ErrorContext
    ) -> tuple[bool, Any]:
        """Retry navigation."""

        current_url = error_context.page_state.get("url")
        if not current_url:
            return False, "No URL for navigation retry"

        try:
            # Go back and forward to trigger fresh navigation
            await session.page.go_back()
            await asyncio.sleep(1)
            await session.page.navigate(current_url)
            await asyncio.sleep(2)

            return True, "navigation_retried"
        except Exception as e:
            return False, f"Navigation retry failed: {e}"

    async def _session_restart(
        self, session: CDPSession, error_context: ErrorContext
    ) -> tuple[bool, Any]:
        """Restart session (placeholder - would need browser manager)."""

        # This would require access to browser manager
        # For now, just return failure
        return False, "Session restart not implemented"

    async def _context_recovery(
        self, session: CDPSession, error_context: ErrorContext
    ) -> tuple[bool, Any]:
        """Recover by addressing context issues."""

        # Close modals or popups that might be blocking interaction
        script = """
        (function() {
            let closed = 0;

            // Close common modal patterns
            const closeSelectors = [
                '.modal .close', '.modal button[aria-label="Close"]',
                '.popup .close', '.dialog .close',
                '.overlay .close', '.lightbox .close',
                '[data-dismiss="modal"]', '[data-close="modal"]'
            ];

            closeSelectors.forEach(selector => {
                document.querySelectorAll(selector).forEach(btn => {
                    if (btn.offsetParent !== null) {  // Visible element
                        btn.click();
                        closed++;
                    }
                });
            });

            // Try pressing Escape key
            document.body.dispatchEvent(new KeyboardEvent('keydown', {
                key: 'Escape',
                keyCode: 27,
                bubbles: true
            }));

            return {closed: closed, escapeSent: true};
        })()
        """

        try:
            result = await session.runtime.evaluate(script)
            await asyncio.sleep(0.5)  # Give time for modals to close

            return True, f"Context recovery: closed {result.get('closed', 0)} elements"
        except Exception as e:
            return False, f"Context recovery failed: {e}"

    async def _graceful_degradation(
        self, session: CDPSession, error_context: ErrorContext
    ) -> tuple[bool, Any]:
        """Graceful degradation fallback."""

        # Provide alternative result or skip operation
        return True, {
            "status": "degraded",
            "message": f"Operation failed but continuing: {error_context.error_type}",
            "original_command": error_context.command.command_type,
        }

    async def _attempt_graceful_degradation(
        self, session: CDPSession, error_context: ErrorContext
    ) -> Optional[Any]:
        """Attempt graceful degradation as final fallback."""

        success, result = await self._graceful_degradation(session, error_context)
        return result if success else None

    async def _generate_alternative_selectors(
        self, session: CDPSession, original_selector: ElementSelector
    ) -> List[Dict[str, str]]:
        """Generate alternative selectors for an element."""

        alternatives = []

        if original_selector.type.value == "css":
            # Try variations of CSS selector
            value = original_selector.value

            # If it's an ID selector, try class-based alternatives
            if value.startswith("#"):
                element_id = value[1:]
                alternatives.append({"type": "css", "value": f'[id="{element_id}"]'})

            # If it's a class selector, try tag-based alternatives
            elif "." in value:
                parts = value.split(".")
                if len(parts) > 1:
                    alternatives.append({"type": "css", "value": parts[0]})

            # Try broader selectors
            if " " in value:
                # Try the last part of a compound selector
                last_part = value.split()[-1]
                alternatives.append({"type": "css", "value": last_part})

        elif original_selector.type.value == "text":
            # Try partial text matches
            text = original_selector.value
            if len(text) > 10:
                alternatives.append({"type": "text", "value": text[: len(text) // 2]})

        return alternatives[:3]  # Limit alternatives

    def _get_learned_strategies(
        self, error_context: ErrorContext
    ) -> List[RecoveryStrategy]:
        """Get strategies that have worked for similar errors."""

        # Filter history for similar errors
        similar_errors = [
            entry
            for entry in self.error_history[-50:]  # Last 50 errors
            if (
                entry.get("error_type") == error_context.error_type
                and entry.get("success", False)
            )
        ]

        # Extract successful strategies
        strategies = [
            entry.get("strategy") for entry in similar_errors if entry.get("strategy")
        ]

        # Return most frequent strategies
        strategy_counts = {}
        for strategy in strategies:
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1

        return sorted(
            strategy_counts.keys(), key=lambda s: strategy_counts[s], reverse=True
        )

    def _record_successful_recovery(
        self,
        error_context: ErrorContext,
        strategy: RecoveryStrategy,
        recovery_time: float,
    ) -> None:
        """Record successful recovery for learning."""

        entry = {
            "error_type": error_context.error_type,
            "strategy": strategy,
            "recovery_time": recovery_time,
            "success": True,
            "timestamp": time.time(),
            "attempt_count": error_context.attempt_count,
        }

        self.error_history.append(entry)
        self._update_recovery_patterns(error_context.error_type, strategy, True)

    def _record_failed_recovery(
        self,
        error_context: ErrorContext,
        strategies_tried: List[RecoveryStrategy],
        recovery_time: float,
    ) -> None:
        """Record failed recovery for learning."""

        for strategy in strategies_tried:
            entry = {
                "error_type": error_context.error_type,
                "strategy": strategy,
                "recovery_time": recovery_time,
                "success": False,
                "timestamp": time.time(),
                "attempt_count": error_context.attempt_count,
            }

            self.error_history.append(entry)
            self._update_recovery_patterns(error_context.error_type, strategy, False)

        # Keep history manageable
        if len(self.error_history) > 500:
            self.error_history = self.error_history[-250:]

    def _update_recovery_patterns(
        self, error_type: ErrorType, strategy: RecoveryStrategy, success: bool
    ) -> None:
        """Update recovery patterns for learning."""

        if error_type not in self.recovery_patterns:
            self.recovery_patterns[error_type] = {}

        if strategy not in self.recovery_patterns[error_type]:
            self.recovery_patterns[error_type][strategy] = {
                "success_count": 0,
                "failure_count": 0,
                "total_attempts": 0,
            }

        pattern = self.recovery_patterns[error_type][strategy]
        pattern["total_attempts"] += 1

        if success:
            pattern["success_count"] += 1
        else:
            pattern["failure_count"] += 1
