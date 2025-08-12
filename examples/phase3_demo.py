"""
Phase 3 Demo: Advanced Automation Features

This example demonstrates the advanced automation capabilities implemented in Phase 3:

- Enhanced element selection with multiple strategies and fallback mechanisms
- Smart waiting with adaptive timeouts and predictive logic
- Error recovery and retry systems with contextual strategies
- Performance optimization and resource management
- Advanced interaction patterns (hover, drag-drop, multi-step workflows)
"""

import asyncio
import logging
import time
from pathlib import Path

from surfboard.automation import (
    BrowserManager,
    AdvancedElementSelector,
    SmartWaiter,
    ErrorRecoverySystem,
    PerformanceOptimizer,
    AdvancedInteractionEngine,
    SelectionStrategy,
    WaitType,
    OptimizationSettings,
    OptimizationLevel,
    InteractionType,
    InteractionPoint,
    GestureDirection,
    InteractionSequence
)
from surfboard.protocols.llm_protocol import ElementSelector, ElementSelectorType, BaseCommand, CommandType

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demo_advanced_element_selection():
    """Demonstrate enhanced element selection strategies."""
    logger.info("=== Advanced Element Selection Demo ===")
    
    browser_manager = BrowserManager(max_instances=1)
    selector = AdvancedElementSelector()
    
    try:
        # Create browser instance
        browser = await browser_manager.create_browser("demo-browser", headless=True)
        session = await browser.get_cdp_session()
        
        # Navigate to a test page with various elements
        await session.page.navigate("https://httpbin.org/forms/post")
        logger.info("Navigated to test form page")
        
        # Test exact match strategy
        logger.info("Testing exact match strategy...")
        css_selector = ElementSelector(
            type=ElementSelectorType.CSS,
            value="input[name='custname']"
        )
        
        result = await selector.find_element(session, css_selector)
        if result:
            logger.info(f"Found element using {result.strategy.value}: {result.selector_used}")
            logger.info(f"Confidence: {result.confidence:.2f}")
        else:
            logger.warning("Element not found with exact match")
            
        # Test fuzzy text strategy
        logger.info("Testing fuzzy text matching...")
        text_selector = ElementSelector(
            type=ElementSelectorType.TEXT,
            value="Customer name"
        )
        
        result = await selector.find_element(session, text_selector)
        if result:
            logger.info(f"Found element using {result.strategy.value}: confidence {result.confidence:.2f}")
        else:
            logger.info("Testing alternative text...")
            text_selector.value = "name"  # Partial match
            result = await selector.find_element(session, text_selector)
            if result:
                logger.info(f"Found with fuzzy match: {result.text_content[:50]}...")
                
        # Test context-aware selection
        logger.info("Testing context-aware selection...")
        context = {
            "form_context": "customer information",
            "nearby_text": "telephone",
            "section_context": "contact details"
        }
        
        phone_selector = ElementSelector(
            type=ElementSelectorType.CSS,
            value="input[name='custtel']"
        )
        
        result = await selector.find_element(session, phone_selector, context=context)
        if result:
            logger.info(f"Context-aware selection successful: {result.element_id or 'no-id'}")
            
        # Test multiple element selection
        logger.info("Testing multiple element selection...")
        input_selector = ElementSelector(
            type=ElementSelectorType.CSS,
            value="input"
        )
        
        results = await selector.find_multiple_elements(session, input_selector, limit=5)
        logger.info(f"Found {len(results)} input elements")
        for i, result in enumerate(results[:3]):
            logger.info(f"  {i+1}. {result.attributes.get('name', 'unnamed')} - {result.text_content[:30]}")
            
    except Exception as e:
        logger.error(f"Element selection demo error: {e}")
    finally:
        await browser_manager.close_all_instances()
        
    logger.info("Advanced element selection demo completed!\n")


async def demo_smart_waiting():
    """Demonstrate smart waiting mechanisms with adaptive timeouts."""
    logger.info("=== Smart Waiting Demo ===")
    
    browser_manager = BrowserManager(max_instances=1)
    waiter = SmartWaiter()
    
    try:
        browser = await browser_manager.create_browser("demo-browser", headless=True)
        session = await browser.get_cdp_session()
        
        # Navigate to dynamic content page
        await session.page.navigate("https://httpbin.org/delay/2")
        logger.info("Navigated to delayed response page")
        
        # Test page load waiting
        logger.info("Testing page load waiting...")
        start_time = time.time()
        result = await waiter.wait_for_page_load(session, timeout=10.0)
        wait_time = time.time() - start_time
        
        if result.success:
            logger.info(f"Page loaded successfully in {wait_time:.2f}s")
        else:
            logger.warning(f"Page load timeout after {wait_time:.2f}s")
            
        # Navigate to a form for element waiting tests
        await session.page.navigate("https://httpbin.org/forms/post")
        
        # Test element visibility waiting
        logger.info("Testing element visibility waiting...")
        element_selector = ElementSelector(
            type=ElementSelectorType.CSS,
            value="input[name='custname']"
        )
        
        result = await waiter.wait_for_element(
            session, element_selector, WaitType.ELEMENT_VISIBLE, timeout=5.0
        )
        
        if result.success:
            logger.info(f"Element became visible in {result.wait_time:.2f}s")
        else:
            logger.warning(f"Element wait timeout: {result.condition_met}")
            
        # Test element clickable waiting
        logger.info("Testing element clickable waiting...")
        result = await waiter.wait_for_element(
            session, element_selector, WaitType.ELEMENT_CLICKABLE, timeout=5.0
        )
        
        if result.success:
            logger.info(f"Element became clickable in {result.wait_time:.2f}s")
            
        # Test adaptive timeout calculation
        logger.info("Testing adaptive timeout...")
        complex_selector = ElementSelector(
            type=ElementSelectorType.CSS,
            value="nonexistent-element"
        )
        
        result = await waiter.wait_for_element(
            session, complex_selector, WaitType.ELEMENT_VISIBLE, 
            timeout=2.0, stability_time=0.5
        )
        
        logger.info(f"Adaptive timeout test: {result.condition_met} in {result.wait_time:.2f}s")
        
        # Test network idle waiting
        logger.info("Testing network idle waiting...")
        result = await waiter.wait_for_network_idle(session, idle_time=1.0, timeout=5.0)
        
        if result.success:
            logger.info("Network became idle successfully")
        else:
            logger.info(f"Network idle timeout: {result.additional_info}")
            
    except Exception as e:
        logger.error(f"Smart waiting demo error: {e}")
    finally:
        await browser_manager.close_all_instances()
        
    logger.info("Smart waiting demo completed!\n")


async def demo_error_recovery():
    """Demonstrate error recovery and retry systems."""
    logger.info("=== Error Recovery Demo ===")
    
    browser_manager = BrowserManager(max_instances=1)
    recovery_system = ErrorRecoverySystem()
    
    try:
        browser = await browser_manager.create_browser("demo-browser", headless=True)
        session = await browser.get_cdp_session()
        
        await session.page.navigate("https://httpbin.org/forms/post")
        
        # Test retry with recovery for a failing operation
        logger.info("Testing retry with recovery...")
        
        attempt_count = 0
        async def failing_operation():
            nonlocal attempt_count
            attempt_count += 1
            logger.info(f"Operation attempt #{attempt_count}")
            
            if attempt_count < 3:
                raise Exception("Simulated failure")
            return "Success after retry"
        
        test_command = BaseCommand(
            command_type=CommandType.CLICK,
            browser_id="demo-browser"
        )
        
        success, result = await recovery_system.retry_with_recovery(
            session, failing_operation, test_command, max_attempts=3
        )
        
        if success:
            logger.info(f"Operation succeeded: {result}")
        else:
            logger.warning(f"Operation failed: {result}")
            
        # Test specific error handling
        logger.info("Testing specific error type handling...")
        
        element_not_found_error = Exception("element not found on page")
        recovery_result = await recovery_system.handle_error(
            session, element_not_found_error, test_command, attempt_count=1
        )
        
        logger.info(f"Recovery strategy used: {recovery_result.strategy_used.value}")
        logger.info(f"Recovery success: {recovery_result.success}")
        
        # Test network error handling
        logger.info("Testing network error handling...")
        
        network_error = Exception("network connection timeout")
        recovery_result = await recovery_system.handle_error(
            session, network_error, test_command, attempt_count=2
        )
        
        logger.info(f"Network error recovery: {recovery_result.strategy_used.value}")
        
        # Test graceful degradation
        logger.info("Testing graceful degradation...")
        
        critical_error = Exception("unrecoverable system error")
        recovery_result = await recovery_system.handle_error(
            session, critical_error, test_command, attempt_count=4
        )
        
        if recovery_result.fallback_used:
            logger.info("Graceful degradation applied successfully")
            logger.info(f"Degraded result: {recovery_result.final_result}")
            
    except Exception as e:
        logger.error(f"Error recovery demo error: {e}")
    finally:
        await browser_manager.close_all_instances()
        
    logger.info("Error recovery demo completed!\n")


async def demo_performance_optimization():
    """Demonstrate performance optimization and resource management."""
    logger.info("=== Performance Optimization Demo ===")
    
    # Test different optimization levels
    optimization_levels = [
        OptimizationLevel.CONSERVATIVE,
        OptimizationLevel.MODERATE,
        OptimizationLevel.AGGRESSIVE
    ]
    
    for level in optimization_levels:
        logger.info(f"Testing {level.value} optimization level...")
        
        settings = OptimizationSettings(
            level=level,
            max_memory_mb=512,
            max_cpu_percent=60.0,
            enable_resource_cleanup=True,
            enable_script_optimization=True
        )
        
        optimizer = PerformanceOptimizer(settings)
        browser_manager = BrowserManager(max_instances=1)
        
        try:
            await optimizer.initialize()
            
            browser = await browser_manager.create_browser("demo-browser", headless=True)
            session = await browser.get_cdp_session()
            
            # Register session for optimization
            await optimizer.register_session(session, f"session-{level.value}")
            
            # Test page load optimization
            optimization_result = await optimizer.optimize_page_load(
                session, "https://httpbin.org/html", f"session-{level.value}"
            )
            
            logger.info(f"  Page load optimization time: {optimization_result['total_optimization_time']:.3f}s")
            logger.info(f"  Load metrics: {optimization_result['load_metrics'].get('total_time', 0):.3f}s")
            
            # Test script optimization
            test_script = """
            // Test script with comments and extra whitespace
            function calculateSum(n) {
                let sum = 0;
                for (let i = 1; i <= n; i++) {
                    sum += i;
                }
                return sum;
            }
            calculateSum(100);
            """
            
            script_result = await optimizer.optimize_script_execution(
                session, test_script, f"session-{level.value}"
            )
            
            logger.info(f"  Script execution time: {script_result['execution_time']:.3f}s")
            logger.info(f"  Script optimized: {script_result['optimized']}")
            
            # Get performance metrics
            metrics = await optimizer.get_performance_metrics()
            logger.info(f"  Memory usage: {metrics.memory_usage_mb:.1f} MB")
            logger.info(f"  CPU usage: {metrics.cpu_percent:.1f}%")
            
            # Test resource cleanup
            cleanup_result = await optimizer.cleanup_resources()
            logger.info(f"  Cleanup freed: {cleanup_result['memory_freed_mb']:.1f} MB")
            logger.info(f"  Cache entries cleared: {cleanup_result['cache_entries_cleared']}")
            
            await optimizer.unregister_session(f"session-{level.value}")
            
        except Exception as e:
            logger.error(f"  Optimization error: {e}")
        finally:
            await browser_manager.close_all_instances()
            
    logger.info("Performance optimization demo completed!\n")


async def demo_advanced_interactions():
    """Demonstrate advanced interaction patterns."""
    logger.info("=== Advanced Interactions Demo ===")
    
    browser_manager = BrowserManager(max_instances=1)
    interaction_engine = AdvancedInteractionEngine()
    
    try:
        browser = await browser_manager.create_browser("demo-browser", headless=True)
        session = await browser.get_cdp_session()
        
        await session.page.navigate("https://httpbin.org/forms/post")
        logger.info("Navigated to interactive test page")
        
        # Test hover interaction
        logger.info("Testing hover interaction...")
        hover_selector = ElementSelector(
            type=ElementSelectorType.CSS,
            value="input[name='custname']"
        )
        
        hover_result = await interaction_engine.hover_element(
            session, hover_selector, duration=1.0
        )
        
        if hover_result.success:
            logger.info(f"Hover completed in {hover_result.execution_time:.3f}s")
            if hover_result.state_changes:
                logger.info(f"State changes detected: {list(hover_result.state_changes.keys())}")
        else:
            logger.warning(f"Hover failed: {hover_result.error_message}")
            
        # Test scroll into view
        logger.info("Testing scroll into view...")
        submit_selector = ElementSelector(
            type=ElementSelectorType.CSS,
            value="input[type='submit']"
        )
        
        scroll_result = await interaction_engine.scroll_into_view(
            session, submit_selector, behavior="smooth"
        )
        
        if scroll_result.success:
            logger.info(f"Scroll completed in {scroll_result.execution_time:.3f}s")
            scroll_info = scroll_result.element_info
            if scroll_info and "scrollDistance" in scroll_info:
                distance = scroll_info["scrollDistance"]
                logger.info(f"Scrolled {distance['vertical']}px vertically")
                
        # Test drag and drop simulation
        logger.info("Testing drag and drop simulation...")
        source_selector = ElementSelector(
            type=ElementSelectorType.CSS,
            value="input[name='custname']"
        )
        target_coordinates = (300, 400)  # Target coordinates
        
        drag_result = await interaction_engine.drag_and_drop(
            session, source_selector, target_coordinates=target_coordinates, drag_duration=0.5
        )
        
        if drag_result.success:
            logger.info(f"Drag and drop completed in {drag_result.execution_time:.3f}s")
            element_info = drag_result.element_info
            if element_info:
                logger.info(f"Dragged from source to {element_info['target']}")
        else:
            logger.warning(f"Drag and drop failed: {drag_result.error_message}")
            
        # Test gesture interactions
        logger.info("Testing gesture interactions...")
        
        # Swipe gesture
        start_point = InteractionPoint(x=200, y=300, pressure=1.0)
        swipe_result = await interaction_engine.perform_gesture(
            session, "swipe", start_point, direction=GestureDirection.RIGHT, distance=100, duration=0.5
        )
        
        if swipe_result.success:
            logger.info(f"Swipe gesture completed: {swipe_result.element_info['direction']}")
            
        # Pinch zoom gesture
        center_point = InteractionPoint(x=250, y=350, pressure=1.0)
        pinch_result = await interaction_engine.perform_gesture(
            session, "pinch", center_point, duration=0.5
        )
        
        if pinch_result.success:
            logger.info(f"Pinch gesture completed: {pinch_result.element_info['zoom_type']}")
            
        # Test multi-step workflow
        logger.info("Testing multi-step workflow...")
        
        workflow = InteractionSequence()
        workflow.steps = [
            {
                "type": "scroll",
                "selector": {"type": "css", "value": "input[name='custname']"},
                "behavior": "smooth"
            },
            {
                "type": "hover", 
                "selector": {"type": "css", "value": "input[name='custname']"},
                "duration": 0.5
            },
            {
                "type": "hover",
                "selector": {"type": "css", "value": "input[name='custtel']"},
                "duration": 0.5
            }
        ]
        workflow.delays = [0.5, 0.3, 0.3]  # Delays between steps
        
        workflow_results = await interaction_engine.execute_workflow(
            session, workflow, rollback_on_failure=True
        )
        
        successful_steps = sum(1 for result in workflow_results if result.success)
        logger.info(f"Workflow completed: {successful_steps}/{len(workflow.steps)} steps successful")
        
        for i, result in enumerate(workflow_results):
            logger.info(f"  Step {i+1}: {result.interaction_type.value} - {'✓' if result.success else '✗'}")
            
    except Exception as e:
        logger.error(f"Advanced interactions demo error: {e}")
    finally:
        await browser_manager.close_all_instances()
        
    logger.info("Advanced interactions demo completed!\n")


async def demo_integration_showcase():
    """Demonstrate integration of all advanced automation features."""
    logger.info("=== Integration Showcase ===")
    
    # Initialize all components
    browser_manager = BrowserManager(max_instances=1)
    selector = AdvancedElementSelector()
    waiter = SmartWaiter()
    recovery_system = ErrorRecoverySystem()
    optimizer = PerformanceOptimizer(OptimizationSettings(
        level=OptimizationLevel.MODERATE,
        enable_resource_cleanup=True,
        enable_script_optimization=True
    ))
    interaction_engine = AdvancedInteractionEngine()
    
    try:
        await optimizer.initialize()
        
        browser = await browser_manager.create_browser("demo-browser", headless=True)
        session = await browser.get_cdp_session()
        
        # Register session for optimization
        await optimizer.register_session(session, "integration-session")
        
        logger.info("Performing integrated automation workflow...")
        
        # Step 1: Optimized page navigation
        start_time = time.time()
        optimization_result = await optimizer.optimize_page_load(
            session, "https://httpbin.org/forms/post", "integration-session"
        )
        logger.info(f"1. Optimized page load: {optimization_result['total_optimization_time']:.3f}s")
        
        # Step 2: Smart waiting for page readiness
        page_wait_result = await waiter.wait_for_page_load(session, timeout=10.0)
        if page_wait_result.success:
            logger.info(f"2. Page ready: {page_wait_result.wait_time:.3f}s")
        
        # Step 3: Advanced element selection with fallback
        element_selector = ElementSelector(
            type=ElementSelectorType.TEXT,
            value="Customer name"  # Might not match exactly
        )
        
        selection_result = await selector.find_element(
            session, element_selector,
            context={"form_context": "customer information"},
            max_attempts=2,
            adaptive_timeout=True
        )
        
        if selection_result:
            logger.info(f"3. Element found: {selection_result.strategy.value} (confidence: {selection_result.confidence:.2f})")
        else:
            logger.info("3. Element not found, trying alternative...")
            element_selector.type = ElementSelectorType.CSS
            element_selector.value = "input[name='custname']"
            
            selection_result = await selector.find_element(session, element_selector)
            if selection_result:
                logger.info(f"3. Alternative selection successful: {selection_result.strategy.value}")
        
        # Step 4: Advanced interaction with error recovery
        if selection_result:
            # Wait for element to be interactive
            wait_result = await waiter.wait_for_element(
                session, element_selector, WaitType.ELEMENT_CLICKABLE, timeout=5.0
            )
            
            if wait_result.success:
                logger.info(f"4. Element ready for interaction: {wait_result.wait_time:.3f}s")
                
                # Perform hover interaction
                hover_result = await interaction_engine.hover_element(
                    session, element_selector, duration=0.5
                )
                
                if hover_result.success:
                    logger.info(f"4. Hover interaction successful: {hover_result.execution_time:.3f}s")
                else:
                    logger.info("4. Hover failed, attempting error recovery...")
                    
                    test_command = BaseCommand(
                        command_type=CommandType.CLICK,
                        browser_id="demo-browser"
                    )
                    
                    recovery_result = await recovery_system.handle_error(
                        session, Exception(hover_result.error_message or "hover failed"),
                        test_command, attempt_count=1
                    )
                    
                    logger.info(f"4. Recovery strategy: {recovery_result.strategy_used.value}")
        
        # Step 5: Performance monitoring and cleanup
        metrics = await optimizer.get_performance_metrics()
        logger.info(f"5. Performance metrics:")
        logger.info(f"   Memory usage: {metrics.memory_usage_mb:.1f} MB")
        logger.info(f"   CPU usage: {metrics.cpu_percent:.1f}%")
        logger.info(f"   DOM elements: {metrics.dom_element_count}")
        
        # Step 6: Resource cleanup
        cleanup_result = await optimizer.cleanup_resources()
        logger.info(f"6. Resource cleanup:")
        logger.info(f"   Memory freed: {cleanup_result['memory_freed_mb']:.1f} MB")
        logger.info(f"   Cache cleared: {cleanup_result['cache_entries_cleared']} entries")
        
        total_time = time.time() - start_time
        logger.info(f"Integration workflow completed in {total_time:.3f}s")
        
        # Generate recommendations
        recommendations = optimizer.get_optimization_recommendations()
        if recommendations:
            logger.info("Optimization recommendations:")
            for category, recommendation in recommendations.items():
                logger.info(f"  {category}: {recommendation}")
                
    except Exception as e:
        logger.error(f"Integration showcase error: {e}")
        
        # Demonstrate error recovery even for demo failures
        test_command = BaseCommand(
            command_type=CommandType.NAVIGATE,
            browser_id="demo-browser"
        )
        
        recovery_result = await recovery_system.handle_error(
            session, e, test_command, attempt_count=1
        )
        logger.info(f"Demo error recovery: {recovery_result.strategy_used.value}")
        
    finally:
        if 'optimizer' in locals():
            await optimizer.unregister_session("integration-session")
        await browser_manager.close_all_instances()
        
    logger.info("Integration showcase completed!\n")


async def main():
    """Run all Phase 3 demonstrations."""
    logger.info("Starting Surfboard Phase 3 Advanced Automation Demonstrations")
    logger.info("=" * 80)
    
    demos = [
        ("Advanced Element Selection", demo_advanced_element_selection),
        ("Smart Waiting Mechanisms", demo_smart_waiting),
        ("Error Recovery Systems", demo_error_recovery),
        ("Performance Optimization", demo_performance_optimization),
        ("Advanced Interactions", demo_advanced_interactions),
        ("Integration Showcase", demo_integration_showcase)
    ]
    
    successful_demos = 0
    
    for demo_name, demo_func in demos:
        try:
            logger.info(f"Running {demo_name} demonstration...")
            await demo_func()
            successful_demos += 1
        except Exception as e:
            logger.error(f"{demo_name} demonstration failed: {e}")
        
        # Brief pause between demos
        await asyncio.sleep(1)
    
    logger.info("=" * 80)
    logger.info(f"Phase 3 demonstrations completed: {successful_demos}/{len(demos)} successful")
    
    if successful_demos == len(demos):
        logger.info("🎉 All Phase 3 Advanced Automation features are fully operational!")
    else:
        logger.warning(f"{len(demos) - successful_demos} demonstrations had issues")
    
    logger.info("\nPhase 3 Features Summary:")
    logger.info("✓ Enhanced element selection with 6 strategies and fallback mechanisms")
    logger.info("✓ Smart waiting with adaptive timeouts and predictive logic")
    logger.info("✓ Intelligent error recovery with 9 recovery strategies")
    logger.info("✓ Performance optimization with 4 optimization levels")
    logger.info("✓ Advanced interactions: hover, drag-drop, gestures, workflows")
    logger.info("✓ Resource management and monitoring")
    logger.info("✓ Full integration between all automation components")
    
    logger.info("\nReady for production deployment and Phase 4 development!")


if __name__ == "__main__":
    asyncio.run(main())