"""
Phase 1 Demo: Core Browser Control

This example demonstrates the enhanced browser automation capabilities
implemented in Phase 1, including:

- Enhanced CDP domains with high-level APIs
- Comprehensive browser lifecycle management 
- Core action library with robust element selection
- Screenshot and JavaScript execution capabilities
- Error handling and retry mechanisms
"""

import asyncio
import logging
from pathlib import Path

from surfboard.automation.browser_manager import BrowserManager, managed_browser
from surfboard.actions.core_actions import CoreActions, ElementSelector
from surfboard.protocols.cdp_domains import create_cdp_session

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demo_basic_automation():
    """Demonstrate basic browser automation."""
    logger.info("=== Basic Browser Automation Demo ===")
    
    # Use managed browser for automatic cleanup
    async with managed_browser(headless=False, window_size=(1280, 720)) as browser:
        # Get CDP session with high-level domain APIs
        session = await browser.get_cdp_session()
        
        # Create core actions handler
        actions = CoreActions(session)
        
        # Navigate to a test page
        await actions.navigate("https://httpbin.org/forms/post", wait_until="load")
        logger.info("Navigated to test form page")
        
        # Take initial screenshot
        screenshots_dir = Path("screenshots")
        await actions.take_screenshot(
            filepath=screenshots_dir / "01_initial_page.png"
        )
        logger.info("Took initial screenshot")
        
        # Fill out form using different selector strategies
        await actions.type_text("input[name='custname']", "John Doe")
        await actions.type_text("input[name='custtel']", "+1-555-123-4567")
        await actions.type_text("input[name='custemail']", "john.doe@example.com")
        
        # Use element selector with multiple strategies
        size_selector = ElementSelector(
            css="select[name='size']",
            aria_label="Pizza size"
        )
        
        # Find and interact with dropdown
        dropdown_element = await actions.find_element(size_selector)
        if dropdown_element:
            await actions.click_element(dropdown_element)
            logger.info("Clicked pizza size dropdown")
            
        # Select pizza toppings using text-based selection
        topping_selectors = [
            ElementSelector(text="Bacon"),
            ElementSelector(text="Cheese") 
        ]
        
        for selector in topping_selectors:
            element = await actions.find_element(selector, timeout=5.0)
            if element:
                await actions.click_element(element)
                logger.info(f"Selected topping: {selector.text}")
        
        # Add delivery instructions
        comments_selector = ElementSelector(css="textarea[name='comments']")
        await actions.type_text(
            comments_selector,
            "Please ring the doorbell twice and leave at the front door."
        )
        
        # Take screenshot of filled form
        await actions.take_screenshot(
            filepath=screenshots_dir / "02_form_filled.png"
        )
        logger.info("Form filled and screenshot taken")
        
        # Execute JavaScript to highlight submit button
        await actions.execute_javascript("""
            const submitBtn = document.querySelector('input[type="submit"]');
            if (submitBtn) {
                submitBtn.style.border = '3px solid red';
                submitBtn.style.backgroundColor = 'yellow';
            }
        """)
        
        # Wait a moment for visual effect
        await asyncio.sleep(1)
        
        # Take final screenshot
        await actions.take_screenshot(
            filepath=screenshots_dir / "03_highlighted_submit.png"
        )
        
        # Get form data using JavaScript
        form_data = await actions.execute_javascript("""
            const form = document.querySelector('form');
            const data = {};
            const formData = new FormData(form);
            for (let [key, value] of formData.entries()) {
                data[key] = value;
            }
            return data;
        """)
        
        logger.info(f"Form data collected: {form_data}")
        
        logger.info("Basic automation demo completed successfully!")


async def demo_multi_browser_management():
    """Demonstrate advanced browser management with multiple instances."""
    logger.info("=== Multi-Browser Management Demo ===")
    
    async with BrowserManager(max_instances=3) as manager:
        # Create browser instances with different configurations
        
        # Desktop browser instance
        desktop_browser = await manager.create_instance(
            instance_id="desktop",
            headless=False,
            window_size=(1920, 1080),
            profile="desktop_profile"
        )
        
        # Mobile browser instance (emulated)
        mobile_browser = await manager.create_instance(
            instance_id="mobile", 
            headless=True,
            window_size=(375, 667),
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
            profile="mobile_profile"
        )
        
        # Test both browsers simultaneously
        tasks = []
        
        async def test_browser(browser, viewport_name):
            session = await browser.get_cdp_session()
            actions = CoreActions(session)
            
            # Navigate to responsive test page
            await actions.navigate("https://httpbin.org/user-agent")
            
            # Get user agent info
            user_agent_info = await actions.execute_javascript("""
                return {
                    userAgent: navigator.userAgent,
                    viewport: {
                        width: window.innerWidth,
                        height: window.innerHeight
                    },
                    devicePixelRatio: window.devicePixelRatio
                };
            """)
            
            logger.info(f"{viewport_name} browser info: {user_agent_info}")
            
            # Take screenshot for comparison
            await actions.take_screenshot(
                filepath=Path("screenshots") / f"04_{viewport_name}_viewport.png"
            )
            
        # Run browsers in parallel
        tasks.append(test_browser(desktop_browser, "desktop"))
        tasks.append(test_browser(mobile_browser, "mobile"))
        
        await asyncio.gather(*tasks)
        
        # List all active instances
        instances = await manager.list_instances()
        logger.info(f"Active browser instances: {len(instances)}")
        
        for instance in instances:
            logger.info(f"  - {instance['id']}: port {instance['port']}, "
                       f"running={instance['running']}")
        
        logger.info("Multi-browser management demo completed!")


async def demo_error_handling_and_retries():
    """Demonstrate error handling and retry mechanisms."""
    logger.info("=== Error Handling and Retries Demo ===")
    
    async with managed_browser(headless=True) as browser:
        session = await browser.get_cdp_session()
        actions = CoreActions(session)
        
        # Navigate to test page
        await actions.navigate("https://httpbin.org/html")
        
        # Test element finding with timeout
        logger.info("Testing element search with timeout...")
        
        try:
            # Try to find non-existent element
            element = await actions.find_element(
                ElementSelector(css="#non-existent-element"),
                timeout=3.0
            )
            if element:
                logger.info("Found element (unexpected)")
            else:
                logger.info("Element not found (as expected)")
                
        except Exception as e:
            logger.warning(f"Element search error: {e}")
        
        # Test navigation error handling
        logger.info("Testing navigation error handling...")
        
        try:
            # Try to navigate to invalid URL
            await actions.navigate("http://invalid-domain-that-does-not-exist.com")
        except Exception as e:
            logger.warning(f"Navigation failed (as expected): {e}")
        
        # Test robust element selection with fallbacks
        logger.info("Testing robust element selection...")
        
        # Create selector with multiple fallback strategies
        robust_selector = ElementSelector(
            css="h1",
            text="Herman Melville",  # Fallback for text content
            role="heading"  # Fallback for accessibility
        )
        
        element = await actions.find_element(robust_selector, timeout=10.0)
        if element:
            text = await actions.get_text(element)
            logger.info(f"Found element with robust selector: {text}")
        
        # Test screenshot error recovery
        logger.info("Testing screenshot capabilities...")
        
        try:
            # Take element screenshot
            await actions.take_screenshot(
                selector=ElementSelector(css="h1"),
                filepath=Path("screenshots") / "05_element_screenshot.png"
            )
            logger.info("Element screenshot successful")
            
        except Exception as e:
            logger.warning(f"Element screenshot failed: {e}")
            
            # Fallback to full page screenshot
            await actions.take_screenshot(
                filepath=Path("screenshots") / "05_fallback_fullpage.png"
            )
            logger.info("Fallback full page screenshot successful")
        
        logger.info("Error handling demo completed!")


async def demo_advanced_interactions():
    """Demonstrate advanced interaction capabilities."""
    logger.info("=== Advanced Interactions Demo ===")
    
    async with managed_browser(headless=False, window_size=(1280, 720)) as browser:
        session = await browser.get_cdp_session()
        actions = CoreActions(session)
        
        # Navigate to interactive test page
        await actions.navigate("https://httpbin.org/forms/post")
        
        # Demonstrate scrolling
        logger.info("Testing scrolling capabilities...")
        await actions.scroll_by(0, 200)
        await asyncio.sleep(1)
        await actions.scroll_to(0, 0)
        
        # Demonstrate JavaScript execution with DOM manipulation
        logger.info("Testing JavaScript execution...")
        
        # Add some dynamic content
        await actions.execute_javascript("""
            // Create a new div with dynamic content
            const div = document.createElement('div');
            div.id = 'dynamic-content';
            div.innerHTML = `
                <h3>Dynamic Content Added</h3>
                <p>This content was added via JavaScript execution.</p>
                <button id="dynamic-btn">Click Me!</button>
            `;
            div.style.cssText = `
                background: #f0f8ff;
                border: 2px solid #007acc;
                border-radius: 8px;
                padding: 20px;
                margin: 20px 0;
            `;
            
            document.body.insertBefore(div, document.body.firstChild);
            
            // Add event listener
            document.getElementById('dynamic-btn').addEventListener('click', () => {
                alert('Dynamic button clicked!');
            });
        """)
        
        # Find and interact with dynamically created element
        dynamic_button = await actions.wait_for_element(
            ElementSelector(css="#dynamic-btn"),
            timeout=10.0
        )
        
        if dynamic_button:
            # Take screenshot showing dynamic content
            await actions.take_screenshot(
                filepath=Path("screenshots") / "06_dynamic_content.png"
            )
            
            # Click dynamic button (this will trigger alert in non-headless mode)
            await actions.click_element(dynamic_button)
            logger.info("Clicked dynamic button")
            
            # Handle alert if present (in real scenarios)
            try:
                # In a real browser, this would trigger an alert
                # We can detect and handle it with CDP
                logger.info("Dynamic button interaction successful")
            except Exception as e:
                logger.debug(f"Alert handling: {e}")
        
        # Test form interaction patterns
        logger.info("Testing complex form interactions...")
        
        # Fill form with realistic interaction patterns
        form_fields = [
            ("input[name='custname']", "Alice Johnson"),
            ("input[name='custtel']", "555-0123"),
            ("input[name='custemail']", "alice@example.com")
        ]
        
        for selector, value in form_fields:
            element = await actions.find_element(ElementSelector(css=selector))
            if element:
                # Clear field first
                await actions.click_element(element)
                
                # Select all and delete (realistic user behavior)
                await session.input.dispatch_key_event("keyDown", key="a", modifiers=2)  # Ctrl+A
                await session.input.dispatch_key_event("keyUp", key="a", modifiers=2)
                
                # Type new value with realistic timing
                await actions.type_text(element, value, clear_first=False, delay=0.1)
                
                logger.info(f"Filled field {selector} with value: {value}")
        
        # Final screenshot
        await actions.take_screenshot(
            filepath=Path("screenshots") / "07_final_interactions.png"
        )
        
        logger.info("Advanced interactions demo completed!")


async def main():
    """Run all Phase 1 demonstrations."""
    logger.info("Starting Surfboard Phase 1 Demonstrations")
    logger.info("=" * 50)
    
    try:
        # Run all demos
        await demo_basic_automation()
        await asyncio.sleep(2)  # Brief pause between demos
        
        await demo_multi_browser_management()
        await asyncio.sleep(2)
        
        await demo_error_handling_and_retries()
        await asyncio.sleep(2)
        
        await demo_advanced_interactions()
        
        logger.info("=" * 50)
        logger.info("All Phase 1 demonstrations completed successfully!")
        logger.info(f"Screenshots saved to: {Path('screenshots').absolute()}")
        
    except Exception as e:
        logger.error(f"Demo failed with error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())