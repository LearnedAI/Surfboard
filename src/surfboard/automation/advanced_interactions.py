"""
Advanced Interaction Patterns.

This module provides sophisticated interaction capabilities including
hover effects, drag-and-drop, multi-step workflows, and gesture-based interactions.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

from ..protocols.cdp_domains import CDPSession
from ..protocols.llm_protocol import ElementSelector, ElementSelectorType

logger = logging.getLogger(__name__)


class InteractionType(str, Enum):
    """Types of advanced interactions."""
    
    HOVER = "hover"
    DRAG_DROP = "drag_drop"
    SCROLL_INTO_VIEW = "scroll_into_view"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    LONG_PRESS = "long_press"
    SWIPE = "swipe"
    PINCH_ZOOM = "pinch_zoom"
    KEYBOARD_SHORTCUT = "keyboard_shortcut"
    MULTI_TOUCH = "multi_touch"


class GestureDirection(str, Enum):
    """Gesture directions."""
    
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    DIAGONAL_UP_LEFT = "diagonal_up_left"
    DIAGONAL_UP_RIGHT = "diagonal_up_right"
    DIAGONAL_DOWN_LEFT = "diagonal_down_left"
    DIAGONAL_DOWN_RIGHT = "diagonal_down_right"


@dataclass
class InteractionPoint:
    """Point for interactions."""
    
    x: float
    y: float
    pressure: float = 1.0
    tiltX: float = 0.0
    tiltY: float = 0.0


@dataclass
class InteractionSequence:
    """Sequence of interactions for complex workflows."""
    
    steps: List[Dict[str, Any]] = field(default_factory=list)
    delays: List[float] = field(default_factory=list)
    conditions: List[Optional[str]] = field(default_factory=list)
    rollback_steps: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class InteractionResult:
    """Result of an advanced interaction."""
    
    success: bool
    interaction_type: InteractionType
    execution_time: float
    element_info: Dict[str, Any] = field(default_factory=dict)
    state_changes: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


class AdvancedInteractionEngine:
    """Engine for advanced browser interactions."""
    
    def __init__(self):
        """Initialize advanced interaction engine."""
        self.hover_timeout = 2.0
        self.drag_sensitivity = 5  # pixels
        self.scroll_behavior = "smooth"
        self.gesture_recognition_threshold = 10  # pixels
        self.multi_touch_enabled = False
        
    async def hover_element(
        self,
        session: CDPSession,
        selector: ElementSelector,
        duration: float = 1.0,
        offset: Optional[Tuple[int, int]] = None
    ) -> InteractionResult:
        """Hover over an element with optional offset and duration.
        
        Args:
            session: CDP session
            selector: Element selector
            duration: Hover duration in seconds
            offset: Optional (x, y) offset from element center
            
        Returns:
            Interaction result
        """
        start_time = time.time()
        
        logger.debug(f"Hovering over element: {selector.value}")
        
        try:
            # Get element position and bounds
            element_info = await self._get_element_bounds(session, selector)
            if not element_info["found"]:
                return InteractionResult(
                    success=False,
                    interaction_type=InteractionType.HOVER,
                    execution_time=time.time() - start_time,
                    error_message="Element not found"
                )
                
            bounds = element_info["bounds"]
            
            # Calculate hover position
            hover_x = bounds["x"] + bounds["width"] / 2
            hover_y = bounds["y"] + bounds["height"] / 2
            
            if offset:
                hover_x += offset[0]
                hover_y += offset[1]
                
            # Capture state before hover
            before_state = await self._capture_element_state(session, selector)
            
            # Perform hover
            await session.input.dispatch_mouse_event(
                type="mouseMoved",
                x=hover_x,
                y=hover_y
            )
            
            # Wait for hover effects
            await asyncio.sleep(duration)
            
            # Capture state after hover
            after_state = await self._capture_element_state(session, selector)
            
            # Detect state changes
            state_changes = self._compare_states(before_state, after_state)
            
            execution_time = time.time() - start_time
            
            return InteractionResult(
                success=True,
                interaction_type=InteractionType.HOVER,
                execution_time=execution_time,
                element_info=element_info,
                state_changes=state_changes
            )
            
        except Exception as e:
            return InteractionResult(
                success=False,
                interaction_type=InteractionType.HOVER,
                execution_time=time.time() - start_time,
                error_message=str(e)
            )
            
    async def drag_and_drop(
        self,
        session: CDPSession,
        source_selector: ElementSelector,
        target_selector: Optional[ElementSelector] = None,
        target_coordinates: Optional[Tuple[float, float]] = None,
        drag_duration: float = 1.0,
        steps: int = 10
    ) -> InteractionResult:
        """Perform drag and drop operation.
        
        Args:
            session: CDP session
            source_selector: Source element selector
            target_selector: Target element selector (if dropping on element)
            target_coordinates: Target coordinates (if dropping at specific location)
            drag_duration: Duration of drag operation
            steps: Number of intermediate steps in drag motion
            
        Returns:
            Interaction result
        """
        start_time = time.time()
        
        logger.debug(f"Dragging element: {source_selector.value}")
        
        try:
            # Get source element bounds
            source_info = await self._get_element_bounds(session, source_selector)
            if not source_info["found"]:
                return InteractionResult(
                    success=False,
                    interaction_type=InteractionType.DRAG_DROP,
                    execution_time=time.time() - start_time,
                    error_message="Source element not found"
                )
                
            source_bounds = source_info["bounds"]
            source_x = source_bounds["x"] + source_bounds["width"] / 2
            source_y = source_bounds["y"] + source_bounds["height"] / 2
            
            # Determine target position
            if target_selector:
                target_info = await self._get_element_bounds(session, target_selector)
                if not target_info["found"]:
                    return InteractionResult(
                        success=False,
                        interaction_type=InteractionType.DRAG_DROP,
                        execution_time=time.time() - start_time,
                        error_message="Target element not found"
                    )
                    
                target_bounds = target_info["bounds"]
                target_x = target_bounds["x"] + target_bounds["width"] / 2
                target_y = target_bounds["y"] + target_bounds["height"] / 2
            elif target_coordinates:
                target_x, target_y = target_coordinates
            else:
                return InteractionResult(
                    success=False,
                    interaction_type=InteractionType.DRAG_DROP,
                    execution_time=time.time() - start_time,
                    error_message="No target specified"
                )
                
            # Capture initial state
            before_state = await self._capture_page_state(session)
            
            # Start drag operation
            await session.input.dispatch_mouse_event(
                type="mousePressed",
                x=source_x,
                y=source_y,
                button="left"
            )
            
            # Perform smooth drag motion
            step_delay = drag_duration / steps
            
            for i in range(1, steps + 1):
                # Calculate intermediate position
                progress = i / steps
                current_x = source_x + (target_x - source_x) * progress
                current_y = source_y + (target_y - source_y) * progress
                
                # Move mouse
                await session.input.dispatch_mouse_event(
                    type="mouseMoved",
                    x=current_x,
                    y=current_y,
                    button="left"
                )
                
                await asyncio.sleep(step_delay)
                
            # Release mouse button to complete drop
            await session.input.dispatch_mouse_event(
                type="mouseReleased",
                x=target_x,
                y=target_y,
                button="left"
            )
            
            # Wait for drop effects
            await asyncio.sleep(0.5)
            
            # Capture final state
            after_state = await self._capture_page_state(session)
            
            # Detect state changes
            state_changes = self._compare_states(before_state, after_state)
            
            execution_time = time.time() - start_time
            
            return InteractionResult(
                success=True,
                interaction_type=InteractionType.DRAG_DROP,
                execution_time=execution_time,
                element_info={
                    "source": source_info,
                    "target": {"x": target_x, "y": target_y}
                },
                state_changes=state_changes
            )
            
        except Exception as e:
            # Try to release mouse button in case of error
            try:
                await session.input.dispatch_mouse_event(
                    type="mouseReleased",
                    x=source_x if 'source_x' in locals() else 0,
                    y=source_y if 'source_y' in locals() else 0,
                    button="left"
                )
            except Exception:
                pass
                
            return InteractionResult(
                success=False,
                interaction_type=InteractionType.DRAG_DROP,
                execution_time=time.time() - start_time,
                error_message=str(e)
            )
            
    async def scroll_into_view(
        self,
        session: CDPSession,
        selector: ElementSelector,
        behavior: str = "smooth",
        block: str = "center",
        inline: str = "center"
    ) -> InteractionResult:
        """Scroll element into view with smooth animation.
        
        Args:
            session: CDP session
            selector: Element selector
            behavior: Scroll behavior ('smooth' or 'instant')
            block: Vertical alignment ('start', 'center', 'end', 'nearest')
            inline: Horizontal alignment ('start', 'center', 'end', 'nearest')
            
        Returns:
            Interaction result
        """
        start_time = time.time()
        
        logger.debug(f"Scrolling element into view: {selector.value}")
        
        try:
            # Get element for scrolling
            script = f"""
            (function() {{
                let element = null;
                
                if ({repr(selector.type.value)} === 'css') {{
                    element = document.querySelector({repr(selector.value)});
                }} else if ({repr(selector.type.value)} === 'xpath') {{
                    const result = document.evaluate(
                        {repr(selector.value)}, document, null,
                        XPathResult.FIRST_ORDERED_NODE_TYPE, null
                    );
                    element = result.singleNodeValue;
                }}
                
                if (!element) {{
                    return {{success: false, error: 'Element not found'}};
                }}
                
                // Capture initial scroll position
                const initialScrollTop = window.pageYOffset || document.documentElement.scrollTop;
                const initialScrollLeft = window.pageXOffset || document.documentElement.scrollLeft;
                
                // Scroll element into view
                element.scrollIntoView({{
                    behavior: {repr(behavior)},
                    block: {repr(block)},
                    inline: {repr(inline)}
                }});
                
                // Return result
                const rect = element.getBoundingClientRect();
                const finalScrollTop = window.pageYOffset || document.documentElement.scrollTop;
                const finalScrollLeft = window.pageXOffset || document.documentElement.scrollLeft;
                
                return {{
                    success: true,
                    initialScroll: {{
                        top: initialScrollTop,
                        left: initialScrollLeft
                    }},
                    finalScroll: {{
                        top: finalScrollTop,
                        left: finalScrollLeft
                    }},
                    elementRect: {{
                        x: rect.x,
                        y: rect.y,
                        width: rect.width,
                        height: rect.height
                    }},
                    scrollDistance: {{
                        vertical: Math.abs(finalScrollTop - initialScrollTop),
                        horizontal: Math.abs(finalScrollLeft - initialScrollLeft)
                    }}
                }};
            }})()
            """
            
            result = await session.runtime.evaluate(script)
            
            if not result or not result.get("success"):
                return InteractionResult(
                    success=False,
                    interaction_type=InteractionType.SCROLL_INTO_VIEW,
                    execution_time=time.time() - start_time,
                    error_message=result.get("error", "Scroll operation failed")
                )
                
            # Wait for smooth scroll animation if applicable
            if behavior == "smooth":
                scroll_distance = max(
                    result["scrollDistance"]["vertical"],
                    result["scrollDistance"]["horizontal"]
                )
                # Estimate scroll duration based on distance
                scroll_duration = min(1.0, scroll_distance / 1000)
                await asyncio.sleep(scroll_duration)
                
            execution_time = time.time() - start_time
            
            return InteractionResult(
                success=True,
                interaction_type=InteractionType.SCROLL_INTO_VIEW,
                execution_time=execution_time,
                element_info=result,
                state_changes={"scrolled": True}
            )
            
        except Exception as e:
            return InteractionResult(
                success=False,
                interaction_type=InteractionType.SCROLL_INTO_VIEW,
                execution_time=time.time() - start_time,
                error_message=str(e)
            )
            
    async def perform_gesture(
        self,
        session: CDPSession,
        gesture_type: str,
        start_point: InteractionPoint,
        end_point: Optional[InteractionPoint] = None,
        direction: Optional[GestureDirection] = None,
        distance: int = 100,
        duration: float = 0.5
    ) -> InteractionResult:
        """Perform gesture-based interactions.
        
        Args:
            session: CDP session
            gesture_type: Type of gesture ('swipe', 'pinch', 'tap')
            start_point: Starting point of gesture
            end_point: End point for directional gestures
            direction: Direction for swipe gestures
            distance: Distance for directional gestures
            duration: Duration of gesture
            
        Returns:
            Interaction result
        """
        start_time = time.time()
        
        logger.debug(f"Performing gesture: {gesture_type}")
        
        try:
            if gesture_type == "swipe":
                return await self._perform_swipe(
                    session, start_point, direction, distance, duration
                )
            elif gesture_type == "pinch":
                return await self._perform_pinch(
                    session, start_point, end_point, duration
                )
            elif gesture_type == "tap":
                return await self._perform_tap(session, start_point)
            elif gesture_type == "long_press":
                return await self._perform_long_press(session, start_point, duration)
            else:
                return InteractionResult(
                    success=False,
                    interaction_type=InteractionType.SWIPE,  # Default
                    execution_time=time.time() - start_time,
                    error_message=f"Unknown gesture type: {gesture_type}"
                )
                
        except Exception as e:
            return InteractionResult(
                success=False,
                interaction_type=InteractionType.SWIPE,  # Default
                execution_time=time.time() - start_time,
                error_message=str(e)
            )
            
    async def execute_workflow(
        self,
        session: CDPSession,
        workflow: InteractionSequence,
        rollback_on_failure: bool = True
    ) -> List[InteractionResult]:
        """Execute a complex multi-step interaction workflow.
        
        Args:
            session: CDP session
            workflow: Sequence of interactions to execute
            rollback_on_failure: Whether to rollback on failure
            
        Returns:
            List of interaction results for each step
        """
        logger.debug(f"Executing workflow with {len(workflow.steps)} steps")
        
        results = []
        
        for i, step in enumerate(workflow.steps):
            try:
                # Check pre-condition if specified
                if i < len(workflow.conditions) and workflow.conditions[i]:
                    condition_met = await self._check_condition(session, workflow.conditions[i])
                    if not condition_met:
                        results.append(InteractionResult(
                            success=False,
                            interaction_type=InteractionType.HOVER,  # Default
                            execution_time=0.0,
                            error_message=f"Pre-condition not met for step {i + 1}"
                        ))
                        break
                        
                # Execute step
                result = await self._execute_workflow_step(session, step)
                results.append(result)
                
                # If step failed and rollback is enabled
                if not result.success and rollback_on_failure:
                    logger.warning(f"Step {i + 1} failed, initiating rollback")
                    await self._rollback_workflow(session, workflow, i)
                    break
                    
                # Wait between steps if specified
                if i < len(workflow.delays) and workflow.delays[i] > 0:
                    await asyncio.sleep(workflow.delays[i])
                    
            except Exception as e:
                error_result = InteractionResult(
                    success=False,
                    interaction_type=InteractionType.HOVER,  # Default
                    execution_time=0.0,
                    error_message=str(e)
                )
                results.append(error_result)
                
                if rollback_on_failure:
                    await self._rollback_workflow(session, workflow, i)
                    
                break
                
        return results
        
    async def _get_element_bounds(
        self,
        session: CDPSession,
        selector: ElementSelector
    ) -> Dict[str, Any]:
        """Get element bounds and position information."""
        
        script = f"""
        (function() {{
            let element = null;
            
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
            
            if (!element) {{
                return {{found: false}};
            }}
            
            const rect = element.getBoundingClientRect();
            const style = window.getComputedStyle(element);
            
            return {{
                found: true,
                bounds: {{
                    x: rect.x,
                    y: rect.y,
                    width: rect.width,
                    height: rect.height,
                    top: rect.top,
                    left: rect.left,
                    bottom: rect.bottom,
                    right: rect.right
                }},
                tagName: element.tagName.toLowerCase(),
                visible: style.display !== 'none' && style.visibility !== 'hidden',
                clickable: !element.disabled && style.pointerEvents !== 'none'
            }};
        }})()
        """
        
        return await session.runtime.evaluate(script) or {"found": False}
        
    async def _capture_element_state(
        self,
        session: CDPSession,
        selector: ElementSelector
    ) -> Dict[str, Any]:
        """Capture element state for comparison."""
        
        script = f"""
        (function() {{
            let element = null;
            
            if ({repr(selector.type.value)} === 'css') {{
                element = document.querySelector({repr(selector.value)});
            }}
            
            if (!element) return {{}};
            
            const style = window.getComputedStyle(element);
            const rect = element.getBoundingClientRect();
            
            return {{
                className: element.className,
                textContent: element.textContent.trim(),
                innerHTML: element.innerHTML.length, // Just length for comparison
                style: {{
                    display: style.display,
                    visibility: style.visibility,
                    opacity: style.opacity,
                    backgroundColor: style.backgroundColor,
                    color: style.color,
                    transform: style.transform
                }},
                bounds: {{
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
        
        return await session.runtime.evaluate(script) or {}
        
    async def _capture_page_state(self, session: CDPSession) -> Dict[str, Any]:
        """Capture general page state."""
        
        script = """
        (function() {
            return {
                url: window.location.href,
                title: document.title,
                scrollPosition: {
                    x: window.pageXOffset || document.documentElement.scrollLeft,
                    y: window.pageYOffset || document.documentElement.scrollTop
                },
                elementCount: document.querySelectorAll('*').length,
                timestamp: Date.now()
            };
        })()
        """
        
        return await session.runtime.evaluate(script) or {}
        
    def _compare_states(
        self,
        before: Dict[str, Any],
        after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare two states and return differences."""
        
        changes = {}
        
        # Compare specific properties
        for key in ["className", "textContent", "innerHTML"]:
            if key in before and key in after:
                if before[key] != after[key]:
                    changes[key] = {"before": before[key], "after": after[key]}
                    
        # Compare style changes
        if "style" in before and "style" in after:
            style_changes = {}
            for style_key in before["style"]:
                if style_key in after["style"]:
                    if before["style"][style_key] != after["style"][style_key]:
                        style_changes[style_key] = {
                            "before": before["style"][style_key],
                            "after": after["style"][style_key]
                        }
            if style_changes:
                changes["style"] = style_changes
                
        # Compare bounds changes
        if "bounds" in before and "bounds" in after:
            bounds_changed = False
            for bound_key in ["x", "y", "width", "height"]:
                if abs(before["bounds"].get(bound_key, 0) - after["bounds"].get(bound_key, 0)) > 1:
                    bounds_changed = True
                    break
            if bounds_changed:
                changes["bounds"] = {"before": before["bounds"], "after": after["bounds"]}
                
        return changes
        
    async def _perform_swipe(
        self,
        session: CDPSession,
        start_point: InteractionPoint,
        direction: Optional[GestureDirection],
        distance: int,
        duration: float
    ) -> InteractionResult:
        """Perform swipe gesture."""
        
        start_time = time.time()
        
        # Calculate end point based on direction and distance
        direction_vectors = {
            GestureDirection.UP: (0, -distance),
            GestureDirection.DOWN: (0, distance),
            GestureDirection.LEFT: (-distance, 0),
            GestureDirection.RIGHT: (distance, 0),
            GestureDirection.DIAGONAL_UP_LEFT: (-distance * 0.7, -distance * 0.7),
            GestureDirection.DIAGONAL_UP_RIGHT: (distance * 0.7, -distance * 0.7),
            GestureDirection.DIAGONAL_DOWN_LEFT: (-distance * 0.7, distance * 0.7),
            GestureDirection.DIAGONAL_DOWN_RIGHT: (distance * 0.7, distance * 0.7),
        }
        
        if direction and direction in direction_vectors:
            dx, dy = direction_vectors[direction]
            end_x = start_point.x + dx
            end_y = start_point.y + dy
        else:
            return InteractionResult(
                success=False,
                interaction_type=InteractionType.SWIPE,
                execution_time=time.time() - start_time,
                error_message="Invalid swipe direction"
            )
            
        # Perform swipe
        steps = 20
        step_delay = duration / steps
        
        # Start touch
        await session.input.dispatch_touch_event(
            type="touchStart",
            touchPoints=[{
                "x": start_point.x,
                "y": start_point.y,
                "radiusX": 5,
                "radiusY": 5,
                "force": start_point.pressure
            }]
        )
        
        # Move touch
        for i in range(1, steps + 1):
            progress = i / steps
            current_x = start_point.x + dx * progress
            current_y = start_point.y + dy * progress
            
            await session.input.dispatch_touch_event(
                type="touchMove",
                touchPoints=[{
                    "x": current_x,
                    "y": current_y,
                    "radiusX": 5,
                    "radiusY": 5,
                    "force": start_point.pressure
                }]
            )
            
            await asyncio.sleep(step_delay)
            
        # End touch
        await session.input.dispatch_touch_event(
            type="touchEnd",
            touchPoints=[]
        )
        
        execution_time = time.time() - start_time
        
        return InteractionResult(
            success=True,
            interaction_type=InteractionType.SWIPE,
            execution_time=execution_time,
            element_info={
                "start": {"x": start_point.x, "y": start_point.y},
                "end": {"x": end_x, "y": end_y},
                "direction": direction.value if direction else None,
                "distance": distance
            }
        )
        
    async def _perform_pinch(
        self,
        session: CDPSession,
        center_point: InteractionPoint,
        end_point: Optional[InteractionPoint],
        duration: float
    ) -> InteractionResult:
        """Perform pinch zoom gesture."""
        
        start_time = time.time()
        
        # For pinch, we need two touch points
        # Start with points close together, then move them apart (zoom in)
        # or start apart and move together (zoom out)
        
        initial_distance = 50  # pixels apart
        final_distance = 150 if not end_point else \
            ((end_point.x - center_point.x) ** 2 + (end_point.y - center_point.y) ** 2) ** 0.5
            
        # Calculate touch points
        point1_start_x = center_point.x - initial_distance / 2
        point1_start_y = center_point.y
        point2_start_x = center_point.x + initial_distance / 2
        point2_start_y = center_point.y
        
        point1_end_x = center_point.x - final_distance / 2
        point1_end_y = center_point.y
        point2_end_x = center_point.x + final_distance / 2
        point2_end_y = center_point.y
        
        steps = 20
        step_delay = duration / steps
        
        # Start touch with both points
        await session.input.dispatch_touch_event(
            type="touchStart",
            touchPoints=[
                {
                    "x": point1_start_x,
                    "y": point1_start_y,
                    "radiusX": 5,
                    "radiusY": 5,
                    "force": center_point.pressure
                },
                {
                    "x": point2_start_x,
                    "y": point2_start_y,
                    "radiusX": 5,
                    "radiusY": 5,
                    "force": center_point.pressure
                }
            ]
        )
        
        # Move both touch points
        for i in range(1, steps + 1):
            progress = i / steps
            
            current1_x = point1_start_x + (point1_end_x - point1_start_x) * progress
            current1_y = point1_start_y + (point1_end_y - point1_start_y) * progress
            current2_x = point2_start_x + (point2_end_x - point2_start_x) * progress
            current2_y = point2_start_y + (point2_end_y - point2_start_y) * progress
            
            await session.input.dispatch_touch_event(
                type="touchMove",
                touchPoints=[
                    {
                        "x": current1_x,
                        "y": current1_y,
                        "radiusX": 5,
                        "radiusY": 5,
                        "force": center_point.pressure
                    },
                    {
                        "x": current2_x,
                        "y": current2_y,
                        "radiusX": 5,
                        "radiusY": 5,
                        "force": center_point.pressure
                    }
                ]
            )
            
            await asyncio.sleep(step_delay)
            
        # End touch
        await session.input.dispatch_touch_event(
            type="touchEnd",
            touchPoints=[]
        )
        
        execution_time = time.time() - start_time
        
        zoom_type = "zoom_in" if final_distance > initial_distance else "zoom_out"
        
        return InteractionResult(
            success=True,
            interaction_type=InteractionType.PINCH_ZOOM,
            execution_time=execution_time,
            element_info={
                "center": {"x": center_point.x, "y": center_point.y},
                "initial_distance": initial_distance,
                "final_distance": final_distance,
                "zoom_type": zoom_type
            }
        )
        
    async def _perform_tap(
        self,
        session: CDPSession,
        point: InteractionPoint
    ) -> InteractionResult:
        """Perform tap gesture."""
        
        start_time = time.time()
        
        # Single tap
        await session.input.dispatch_touch_event(
            type="touchStart",
            touchPoints=[{
                "x": point.x,
                "y": point.y,
                "radiusX": 5,
                "radiusY": 5,
                "force": point.pressure
            }]
        )
        
        await asyncio.sleep(0.1)  # Brief touch duration
        
        await session.input.dispatch_touch_event(
            type="touchEnd",
            touchPoints=[]
        )
        
        execution_time = time.time() - start_time
        
        return InteractionResult(
            success=True,
            interaction_type=InteractionType.HOVER,  # Using HOVER as closest match
            execution_time=execution_time,
            element_info={"tap_position": {"x": point.x, "y": point.y}}
        )
        
    async def _perform_long_press(
        self,
        session: CDPSession,
        point: InteractionPoint,
        duration: float
    ) -> InteractionResult:
        """Perform long press gesture."""
        
        start_time = time.time()
        
        # Start touch
        await session.input.dispatch_touch_event(
            type="touchStart",
            touchPoints=[{
                "x": point.x,
                "y": point.y,
                "radiusX": 5,
                "radiusY": 5,
                "force": point.pressure
            }]
        )
        
        # Hold for duration
        await asyncio.sleep(duration)
        
        # End touch
        await session.input.dispatch_touch_event(
            type="touchEnd",
            touchPoints=[]
        )
        
        execution_time = time.time() - start_time
        
        return InteractionResult(
            success=True,
            interaction_type=InteractionType.LONG_PRESS,
            execution_time=execution_time,
            element_info={
                "position": {"x": point.x, "y": point.y},
                "duration": duration
            }
        )
        
    async def _execute_workflow_step(
        self,
        session: CDPSession,
        step: Dict[str, Any]
    ) -> InteractionResult:
        """Execute a single workflow step."""
        
        step_type = step.get("type")
        
        if step_type == "hover":
            return await self.hover_element(
                session,
                ElementSelector(**step["selector"]),
                step.get("duration", 1.0),
                step.get("offset")
            )
        elif step_type == "drag_drop":
            return await self.drag_and_drop(
                session,
                ElementSelector(**step["source_selector"]),
                ElementSelector(**step["target_selector"]) if "target_selector" in step else None,
                step.get("target_coordinates"),
                step.get("duration", 1.0)
            )
        elif step_type == "scroll":
            return await self.scroll_into_view(
                session,
                ElementSelector(**step["selector"]),
                step.get("behavior", "smooth")
            )
        else:
            return InteractionResult(
                success=False,
                interaction_type=InteractionType.HOVER,  # Default
                execution_time=0.0,
                error_message=f"Unknown workflow step type: {step_type}"
            )
            
    async def _check_condition(
        self,
        session: CDPSession,
        condition: str
    ) -> bool:
        """Check if a condition is met."""
        
        try:
            result = await session.runtime.evaluate(f"({condition})")
            return bool(result)
        except Exception:
            return False
            
    async def _rollback_workflow(
        self,
        session: CDPSession,
        workflow: InteractionSequence,
        failed_step: int
    ) -> None:
        """Rollback workflow to previous state."""
        
        logger.debug(f"Rolling back workflow from step {failed_step}")
        
        # Execute rollback steps in reverse order
        for i in range(min(failed_step, len(workflow.rollback_steps))):
            rollback_step = workflow.rollback_steps[failed_step - i - 1]
            try:
                await self._execute_workflow_step(session, rollback_step)
            except Exception as e:
                logger.warning(f"Rollback step failed: {e}")
                # Continue with remaining rollback steps